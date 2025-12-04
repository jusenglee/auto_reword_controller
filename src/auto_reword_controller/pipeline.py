"""End-to-end 파이프라인 오케스트레이션.

LLM 플래너 → PlanExecutor → ReportBuilder의 순서를 캡슐화하여
"신뢰성 높은 기본 루틴 + LLM 확장 루틴" 흐름을 그대로 재현한다.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping

from .executor import ExecutionConfig, PlanExecutor, ToolRunner
from .planner import LLMPlanBuilder
from .report import ReportBuilder, ReportPrompt
from .models import DailyStockReportOutput, DailyStockReportData, DailyStockReportPlan


class DailyReportPipeline:
    """국내 주식 일일 리포트 자동 생성 파이프라인."""

    def __init__(
        self,
        runner: ToolRunner,
        planner: LLMPlanBuilder | None = None,
        report_builder: ReportBuilder | None = None,
        exec_config: ExecutionConfig | None = None,
    ):
        self.runner = runner
        self.planner = planner or LLMPlanBuilder()
        self.report_builder = report_builder or ReportBuilder()
        self.executor = PlanExecutor(runner, exec_config)

    def build_plan(
        self, *, target_date: date, cues: Iterable[str] | None = None, base_snapshot: Mapping[str, Any] | None = None
    ) -> DailyStockReportPlan:
        """LLM 플래너(또는 단순 규칙)로 Plan을 생성한다."""
        return self.planner.build(target_date=target_date, cues=cues, base_snapshot=base_snapshot)

    def collect(self, plan: DailyStockReportPlan) -> DailyStockReportData:
        """PlanExecutor로 데이터를 수집한다."""
        return self.executor.execute(plan)

    def build_report(self, data: DailyStockReportData) -> DailyStockReportOutput:
        """수집된 데이터로 사람이 읽을 텍스트 리포트를 만든다."""
        return self.report_builder.build_placeholder_report(data)

    def build_llm_prompt(self, data: DailyStockReportData) -> ReportPrompt:
        """LLM에 전달할 요약 프롬프트 페이로드를 생성한다."""
        return self.report_builder.build_prompt(data)

    def run(
        self,
        *,
        target_date: date,
        cues: Iterable[str] | None = None,
        base_snapshot: Mapping[str, Any] | None = None,
    ) -> DailyStockReportOutput:
        """계획/수집/요약까지 한 번에 처리."""
        plan = self.build_plan(target_date=target_date, cues=cues, base_snapshot=base_snapshot)
        data = self.collect(plan)
        return self.build_report(data)
