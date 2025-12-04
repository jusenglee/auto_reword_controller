"""Core dataclasses for the daily stock report pipeline.

이 모듈은 Planner, Executor, Reporter 사이를 오가는 데이터 구조를 정의한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Literal, Optional


class DataLayer(str, Enum):
    """데이터 성격에 따라 레이어를 구분한다.

    MCP 툴이 가져오는 결과물을 "정량·공식"과 "해석·감정" 영역으로 나눠
    품질과 신뢰도를 다르게 취급한다. Price/Disclosure/Macro는 숫자·공식
    소스를 기반으로 하며, News/Opinion은 맥락과 여론을 보강하는 용도다.
    """

    PRICE = "price"
    DISCLOSURE = "disclosure"
    MACRO = "macro"
    NEWS = "news"
    OPINION = "opinion"
    RISK = "risk"


@dataclass
class SourceMeta:
    """각 데이터 조각의 신뢰도/품질 메타 정보.

    - source_score: 1차/2차/커뮤니티 등 출처 신뢰도
    - recency_score: 오늘/어제/지난주의 시점 가중치
    - structure_score: 필수 필드 유무, 이상치 여부
    - consistency_score: 다른 소스 대비 일관성

    위 점수는 품질 관리 규칙(quality_score/quality_band)에서 사용된다.
    """

    source_id: str
    layer: DataLayer
    source_score: float
    recency_score: float
    structure_score: float
    consistency_score: float

    def quality_score(self) -> float:
        """Combine 개별 점수로 품질 지표를 생성한다.

        간단한 가중 평균을 사용하지만, 필요하면 향후 로지스틱/규칙 기반으로 교체한다.
        """
        weights = {
            "source_score": 0.35,
            "recency_score": 0.25,
            "structure_score": 0.2,
            "consistency_score": 0.2,
        }
        total = (
            self.source_score * weights["source_score"]
            + self.recency_score * weights["recency_score"]
            + self.structure_score * weights["structure_score"]
            + self.consistency_score * weights["consistency_score"]
        )
        return round(total, 3)

    def quality_band(self, *, main_threshold: float = 0.7, minimum_quality: float = 0.5) -> str:
        """품질 점수에 따라 데이터를 분류한다.

        - >= main_threshold: "main"
        - >= minimum_quality: "support"
        - else: "discard"
        """
        score = self.quality_score()
        if score >= main_threshold:
            return "main"
        if score >= minimum_quality:
            return "support"
        return "discard"


@dataclass
class ContentBlock:
    """각 데이터 조각의 내용과 메타 정보를 묶는다."""

    title: str
    body: str
    meta: SourceMeta
    tags: List[str] = field(default_factory=list)


@dataclass
class TaskPlan:
    tool: str
    args: Dict[str, Any] = field(default_factory=dict)
    purpose: Optional[str] = None


@dataclass
class DailyStockReportPlan:
    date: date
    tasks: List[TaskPlan]
    base_tasks: List[str] = field(default_factory=list)
    enrichment_reason: Optional[str] = None


@dataclass
class DailyStockReportData:
    date: date
    collected: Dict[str, List[ContentBlock]] = field(default_factory=dict)

    def add_block(self, task_name: str, block: ContentBlock) -> None:
        self.collected.setdefault(task_name, []).append(block)


@dataclass
class ReportSection:
    heading: str
    summary: str
    details: List[str] = field(default_factory=list)
    caution: Optional[str] = None
    layer: DataLayer = DataLayer.NEWS


@dataclass
class DailyStockReportOutput:
    date: date
    sections: List[ReportSection]
    raw_data: DailyStockReportData
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_text(self) -> str:
        """사람이 읽기 좋은 텍스트 리포트를 생성한다."""
        lines: List[str] = [f"국내 주식 일일 리포트 ({self.date.isoformat()})"]
        for section in self.sections:
            lines.append(f"\n## {section.heading}")
            lines.append(section.summary)
            for detail in section.details:
                lines.append(f"- {detail}")
            if section.caution:
                lines.append(f"[주의] {section.caution}")
        return "\n".join(lines)


RiskTag = Literal["confirmed", "low_confidence", "speculative"]


@dataclass
class LayeredSummary:
    layer: DataLayer
    content: str
    risk: RiskTag = "confirmed"
    references: List[str] = field(default_factory=list)
