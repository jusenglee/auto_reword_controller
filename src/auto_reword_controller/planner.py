"""LLM 기반 플래너 구현.

- 기본 플랜은 `plan.build_base_plan`으로 생성한다.
- LLM은 확장(뉴스/커뮤니티/특정 테마) 수집을 위해 추가 툴과 파라미터만 제안한다.
- 출력 JSON을 `PlanCompiler`가 검증/정규화하여 `DailyStockReportPlan`으로 변환한다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, List, Mapping, Protocol, Sequence

from .models import DailyStockReportPlan, TaskPlan
from .plan import BASE_TASKS, build_base_plan, enrich_plan

# MCP 툴 화이트리스트
ALLOWED_TOOLS: Sequence[str] = (
    "get_index_snapshot",
    "get_macro_snapshot",
    "get_dart_disclosures",
    "get_top_sectors",
    "search_kr_stock_news",
    "get_forum_sentiment",
)

# 필수/기본 파라미터가 존재하는 툴에 대해 안전한 기본값을 정의
DEFAULT_TOOL_ARGS: Dict[str, Dict[str, Any]] = {
    "get_index_snapshot": {"indices": ["KOSPI", "KOSDAQ"]},
    "get_dart_disclosures": {"importance": "high"},
    "search_kr_stock_news": {"limit": 5},
    "get_top_sectors": {"limit": 5},
    "get_forum_sentiment": {"topics": []},
}


class PlannerClient(Protocol):
    """LLM 또는 외부 플래너 인터페이스."""

    def complete(self, *, prompt: str) -> str:
        ...


@dataclass
class PlannerContext:
    """LLM 프롬프트에 함께 전달할 컨텍스트."""

    target_date: date
    cues: List[str]
    base_snapshot: Mapping[str, Any] | None = None

    def describe(self) -> str:
        base_summary = "" if not self.base_snapshot else json.dumps(self.base_snapshot, ensure_ascii=False)
        cue_line = ", ".join(self.cues) if self.cues else "없음"
        return (
            f"대상 일자: {self.target_date.isoformat()}\n"
            f"시장 키워드: {cue_line}\n"
            f"최근 스냅샷: {base_summary or '요약 없음'}"
        )


class PlanCompiler:
    """LLM이 반환한 JSON Plan을 안전하게 `DailyStockReportPlan`으로 정규화."""

    def __init__(self, *, target_date: date, allowed_tools: Sequence[str] | None = None):
        self.target_date = target_date
        self.allowed_tools = set(allowed_tools or ALLOWED_TOOLS)

    def compile_tasks(self, raw_tasks: Iterable[Mapping[str, Any]]) -> List[TaskPlan]:
        tasks: List[TaskPlan] = []
        for item in raw_tasks:
            tool = item.get("tool")
            if not tool or tool not in self.allowed_tools:
                continue
            args = {**DEFAULT_TOOL_ARGS.get(tool, {}), **item.get("args", {})}
            purpose = item.get("purpose")
            tasks.append(TaskPlan(tool=tool, args=args, purpose=purpose))
        return tasks

    def merge_with_base(self, base_plan: DailyStockReportPlan, raw_plan: Mapping[str, Any]) -> DailyStockReportPlan:
        extra_tasks = self.compile_tasks(raw_plan.get("tasks", []))
        base_tools = {task.tool for task in base_plan.tasks}
        merged: List[TaskPlan] = list(base_plan.tasks)
        for task in extra_tasks:
            if task.tool in base_tools and task.tool in BASE_TASKS:
                # 이미 포함된 필수 루틴은 중복 추가하지 않는다.
                continue
            merged.append(task)
        enrichment_reason = raw_plan.get("enrichment_reason")
        return DailyStockReportPlan(
            date=self.target_date,
            tasks=merged,
            base_tasks=list(base_plan.base_tasks),
            enrichment_reason=enrichment_reason,
        )


class LLMPlanBuilder:
    """Base Plan 위에 LLM이 제안한 확장 루틴을 합성한다."""

    def __init__(self, client: PlannerClient | None = None):
        self.client = client

    def _render_prompt(self, context: PlannerContext) -> str:
        return (
            "너는 국내 주식 일일 리포트용 정보 수집 플래너이다.\n"
            "반드시 MCP 툴 이름과 args만 포함된 JSON을 출력하라. 다른 텍스트는 금지.\n"
            "필수 툴: get_index_snapshot, get_macro_snapshot, get_dart_disclosures는 항상 포함한다.\n"
            "신뢰성 높은 데이터(지수/거시/공시) 위주로 두고, 필요시 뉴스/커뮤니티 확장을 추가한다.\n"
            "뉴스/커뮤니티는 다양한 관점을 섞기 위해 여러 query를 사용할 수 있다.\n"
            "structure: {\n  'date': 'YYYY-MM-DD',\n  'tasks': [ { 'tool': 'name', 'args': {...}, 'purpose': 'optional' } ],\n"
            "  'enrichment_reason': 'optional'\n}\n"
            f"컨텍스트:\n{context.describe()}\n"
        )

    def _fallback_plan(self, target_date: date, cues: Iterable[str]) -> Mapping[str, Any]:
        return {
            "date": target_date.isoformat(),
            "tasks": self._cue_tasks(list(cues)),
            "enrichment_reason": ", ".join(cues) if cues else None,
        }

    @staticmethod
    def _cue_tasks(cues: List[str]) -> List[Mapping[str, Any]]:
        tasks: List[Mapping[str, Any]] = []
        for cue in cues:
            tasks.append(
                {
                    "tool": "search_kr_stock_news",
                    "args": {"query": cue, "limit": 5},
                    "purpose": f"{cue} 뉴스 보강",
                }
            )
            tasks.append(
                {
                    "tool": "get_forum_sentiment",
                    "args": {"topics": [cue]},
                    "purpose": f"{cue} 커뮤니티 심리",
                }
            )
        return tasks

    def build(
        self, *, target_date: date, cues: Iterable[str] | None = None, base_snapshot: Mapping[str, Any] | None = None
    ) -> DailyStockReportPlan:
        base_plan = build_base_plan(target_date)
        cue_list = list(cues or [])
        raw_plan: Mapping[str, Any]

        if self.client:
            prompt = self._render_prompt(PlannerContext(target_date=target_date, cues=cue_list, base_snapshot=base_snapshot))
            response = self.client.complete(prompt=prompt)
            try:
                raw_plan = json.loads(response)
            except json.JSONDecodeError:
                raw_plan = self._fallback_plan(target_date, cue_list)
        else:
            raw_plan = self._fallback_plan(target_date, cue_list)

        compiler = PlanCompiler(target_date=target_date)
        compiled = compiler.merge_with_base(base_plan, raw_plan)
        if not cue_list and not raw_plan.get("tasks"):
            # cues도 LLM 확장도 없으면 기본 enrich 로직을 그대로 활용
            return enrich_plan(base_plan, [])
        return compiled
