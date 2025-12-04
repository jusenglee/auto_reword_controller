"""Reporter 역할 구현.

수집된 데이터를 LLM이 읽기 좋은 형태로 구성하기 위한 후처리를 담당한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .models import ContentBlock, DailyStockReportData, DailyStockReportOutput, DataLayer, LayeredSummary, ReportSection


@dataclass
class ReportPrompt:
    date: str
    summaries: List[LayeredSummary]
    guidance: str


class ReportBuilder:
    def build_prompt(self, data: DailyStockReportData) -> ReportPrompt:
        """LLM에게 줄 간결한 프롬프트 페이로드를 만든다."""
        summaries: List[LayeredSummary] = []
        for task_name, blocks in data.collected.items():
            for block in blocks:
                risk = "confirmed" if block.meta.quality_score() >= 0.7 else "low_confidence"
                summaries.append(
                    LayeredSummary(
                        layer=block.meta.layer,
                        content=f"{block.title}: {block.body}",
                        risk=risk,
                        references=block.tags,
                    )
                )
        guidance = (
            "정량 데이터는 있는 그대로 보고, 신뢰도가 낮은 레이어(opinion)는 추측임을 명확히 표시하라. "
            "지수/섹터/공시/정책/심리 순으로 요약을 구성한다."
        )
        return ReportPrompt(date=data.date.isoformat(), summaries=summaries, guidance=guidance)

    def build_placeholder_report(self, data: DailyStockReportData) -> DailyStockReportOutput:
        """LLM이 없는 환경에서 구조를 시연할 간단한 리포트."""
        sections: List[ReportSection] = []
        ordering = (
            (DataLayer.PRICE, "지수/섹터"),
            (DataLayer.DISCLOSURE, "공시/기업 이벤트"),
            (DataLayer.MACRO, "거시/정책"),
            (DataLayer.NEWS, "뉴스/해석"),
            (DataLayer.OPINION, "시장 심리"),
        )
        for layer, heading in ordering:
            layer_blocks = self._blocks_by_layer(data, layer)
            if not layer_blocks:
                continue
            summaries = [f"{block.title}" for block in layer_blocks]
            details = [block.body for block in layer_blocks]
            caution = None
            if layer == DataLayer.OPINION:
                caution = "커뮤니티 데이터로 신뢰도가 낮을 수 있습니다."
            sections.append(
                ReportSection(
                    heading=heading,
                    summary="; ".join(summaries),
                    details=details,
                    caution=caution,
                    layer=layer,
                )
            )
        return DailyStockReportOutput(date=data.date, sections=sections, raw_data=data)

    @staticmethod
    def _blocks_by_layer(data: DailyStockReportData, layer: DataLayer) -> List[ContentBlock]:
        items: List[ContentBlock] = []
        for blocks in data.collected.values():
            items.extend([block for block in blocks if block.meta.layer == layer])
        return items
