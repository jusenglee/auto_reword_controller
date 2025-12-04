"""Plan 실행기.

실제 HTTP/API 호출은 MCP 툴 래퍼 안에서만 일어나며, 여기서는
Plan을 순회하며 결과를 수집하는 책임만 가진다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Protocol

from models import ContentBlock, DailyStockReportData, DailyStockReportPlan, DataLayer, SourceMeta
from plan import layer_for_tool


class ToolRunner(Protocol):
    """MCP 툴 호출 인터페이스.

    실제 구현체는 화이트리스트된 도메인만 접근하도록 설계한다.
    """

    def get_index_snapshot(self, *, indices: Iterable[str]) -> Iterable[Dict[str, Any]]:
        ...

    def get_top_sectors(self, *, limit: int) -> Iterable[Dict[str, Any]]:
        ...

    def get_dart_disclosures(self, *, importance: str) -> Iterable[Dict[str, Any]]:
        ...

    def get_macro_snapshot(self) -> Iterable[Dict[str, Any]]:
        ...

    def search_kr_stock_news(self, *, query: str, limit: int) -> Iterable[Dict[str, Any]]:
        ...

    def get_forum_sentiment(self, *, topics: Iterable[str]) -> Iterable[Dict[str, Any]]:
        ...


@dataclass
class ExecutionConfig:
    minimum_quality: float = 0.5
    main_threshold: float = 0.7


class PlanExecutor:
    def __init__(self, runner: ToolRunner, config: ExecutionConfig | None = None):
        self.runner = runner
        self.config = config or ExecutionConfig()

    def execute(self, plan: DailyStockReportPlan) -> DailyStockReportData:
        """Plan 순서대로 툴을 호출해 데이터를 수집한다.

        - MCP 툴 호출 결과에 레이어/품질 메타를 부여하고,
        - minimum_quality 미만은 버려 신뢰성 1차 필터를 적용한다.
        """
        dataset = DailyStockReportData(date=plan.date)
        for task in plan.tasks:
            tool_method = getattr(self.runner, task.tool)
            records = list(tool_method(**task.args))  # type: ignore[arg-type]
            layer = layer_for_tool(task.tool)
            for record in records:
                meta = self._meta_from_record(record, layer)
                if meta.quality_score() < self.config.minimum_quality:
                    continue
                block = ContentBlock(
                    title=record.get("title", task.tool),
                    body=record.get("body", ""),
                    meta=meta,
                    tags=record.get("tags", []),
                )
                dataset.add_block(task.tool, block)
        return dataset

    def _meta_from_record(self, record: Dict[str, Any], layer: DataLayer) -> SourceMeta:
        base_meta = record.get(
            "meta",
            {
                "source_id": record.get("source_id", "unknown"),
                "source_score": record.get("source_score", 0.3 if layer == DataLayer.OPINION else 0.6),
                "recency_score": record.get("recency_score", 0.8),
                "structure_score": record.get("structure_score", 0.7),
                "consistency_score": record.get("consistency_score", 0.6),
            },
        )
        return SourceMeta(layer=layer, **base_meta)
