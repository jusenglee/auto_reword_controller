"""Planner helper utilities.

LLM이 결정해야 하는 부분과 고정 루틴을 함께 표현한다.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable, List, Sequence

from .models import DailyStockReportPlan, DataLayer, TaskPlan

# 항상 수행되는 고정 루틴 툴 이름
BASE_TASKS: Sequence[str] = (
    "get_index_snapshot",
    "get_macro_snapshot",
    "get_dart_disclosures",
)


def build_base_plan(target_date: date) -> DailyStockReportPlan:
    """최소 동작을 위한 기본 Plan을 생성한다."""
    tasks: List[TaskPlan] = [
        TaskPlan(tool="get_index_snapshot", args={"indices": ["KOSPI", "KOSDAQ"]}, purpose="지수 스냅샷"),
        TaskPlan(tool="get_macro_snapshot", args={}, purpose="금리/환율 등 거시"),
        TaskPlan(
            tool="get_dart_disclosures",
            args={"importance": "high"},
            purpose="주요 공시 이벤트",
        ),
    ]
    return DailyStockReportPlan(date=target_date, tasks=tasks, base_tasks=list(BASE_TASKS))


def enrich_plan(base_plan: DailyStockReportPlan, cues: Iterable[str]) -> DailyStockReportPlan:
    """LLM이 제안한 힌트(cues)를 받아 확장 툴을 삽입한다.

    Args:
        base_plan: 기본 Plan 객체
        cues: 오늘 시장에서 주목할 키워드 리스트
    """
    tasks = list(base_plan.tasks)
    for cue in cues:
        tasks.append(
            TaskPlan(
                tool="search_kr_stock_news",
                args={"query": cue, "limit": 5},
                purpose=f"{cue} 관련 뉴스 보강",
            )
        )
        tasks.append(
            TaskPlan(
                tool="get_forum_sentiment",
                args={"topics": [cue]},
                purpose=f"{cue} 시장 심리",
            )
        )
    enrichment_reason = ", ".join(cues) if cues else None
    return DailyStockReportPlan(
        date=base_plan.date,
        tasks=tasks,
        base_tasks=base_plan.base_tasks,
        enrichment_reason=enrichment_reason,
    )


def layer_for_tool(tool: str) -> DataLayer:
    """툴 이름 기준으로 데이터 레이어를 결정한다."""
    if tool in {"get_index_snapshot", "get_top_sectors"}:
        return DataLayer.PRICE
    if tool == "get_dart_disclosures":
        return DataLayer.DISCLOSURE
    if tool == "get_macro_snapshot":
        return DataLayer.MACRO
    if tool in {"search_kr_stock_news"}:
        return DataLayer.NEWS
    if tool in {"get_forum_sentiment"}:
        return DataLayer.OPINION
    return DataLayer.NEWS
