# mock_runner.py
from __future__ import annotations

from datetime import date
from typing import Any, Dict, Iterable, List

class MockToolRunner:
    """실제 HTTP/API 없이 파이프라인을 돌려보기 위한 더미 Runner."""

    def __init__(self, target_date: date | None = None) -> None:
        self.target_date = target_date or date.today()

    # -------- PRICE 계열 --------
    def get_index_snapshot(self, *, indices: Iterable[str]) -> Iterable[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for idx in indices:
            if idx.upper() == "KOSPI":
                body = "KOSPI 4,000.1pt, 전일 대비 -0.7% (모의 데이터)"
            elif idx.upper() == "KOSDAQ":
                body = "KOSDAQ 930.5pt, 전일 대비 +1.2% (모의 데이터)"
            else:
                body = f"{idx} 지수 (모의 데이터)"
            records.append(
                {
                    "title": f"{idx} 지수 스냅샷(모의)",
                    "body": body,
                    "tags": [idx.upper(), "index", "mock"],
                    "source_id": "mock_price",
                    "source_score": 0.9,
                    "recency_score": 0.9,
                    "structure_score": 0.9,
                    "consistency_score": 0.9,
                }
            )
        return records

    def get_top_sectors(self, *,  limit: int ) -> Iterable[Dict[str, Any]]:
        lines = [
            "반도체 : +2.3%, 거래대금 상위",
            "2차 전지 : +1.8%",
            "인터넷/플랫폼: +1.2%",
            "바이오: -0.5",
            "철강/소재: -1.0%",
        ][:limit]
        return [
            {
                "title": f"섹터/테마 상위 {limit} (모의)",
                "body": "\n".join(lines),
                "tags": ["sector", "mock"],
                "source_id": "mock_price",
                "source_score": 0.8,
                "recency_score": 0.8,
                "structure_score": 0.8,
                "consistency_score": 0.7,
            }
        ]

        # -------- DISCLOSURE 계열 --------
    def get_dart_disclosures(self, *, importance: str) -> Iterable[Dict[str, Any]]:
    # 중요 공시 2개 정도만 샘플로
        return [
            {
                "title": "[모의] 삼성전자 - 자사주 소각 결정",
                "body": "주주가치 제고를 위한 자사주 일부 소각 (모의 데이터)",
                "tags": ["공시", "주주환원", "mock"],
                "source_id": "mock_dart",
                "source_score": 0.95,
                "recency_score": 0.9,
                "structure_score": 0.9,
                "consistency_score": 0.8,
            },
            {
                "title": "[모의] 카카오 - 신사업 투자 공시",
                "body": "AI/클라우드 관련 대규모 투자 계획 공시 (모의 데이터)",
                "tags": ["공시", "투자", "mock"],
                "source_id": "mock_dart",
                "source_score": 0.9,
                "recency_score": 0.9,
                "structure_score": 0.8,
                "consistency_score": 0.7,
            },
        ]

    # -------- MACRO 계열 --------
    def get_macro_snapshot(self) -> Iterable[Dict[str, Any]]:
        return [
            {
                "title": "거시 지표 스냅샷(모의)",
                "body": "기준금리 3.50%, 3년국채 3.20%, USD/KRW 1,350원 (모의 데이터)",
                "tags": ["macro", "rate", "fx", "mock"],
                "source_id": "mock_macro",
                "source_score": 0.9,
                "recency_score": 0.8,
                "structure_score": 0.8,
                "consistency_score": 0.8,
            }
        ]

    # -------- NEWS 계열 --------
    def search_kr_stock_news(self, *, query: str, limit: int) -> Iterable[Dict[str, Any]]:
        lines = [
                    f"[모의 뉴스] '{query}' 관련 시황 기사 1",
                    f"[모의 뉴스] '{query}' 관련 시황 기사 2",
                ][:limit]
        return [
            {
                "title": f"국내 증시 뉴스 요약(모의) - {query}",
                "body": "\n".join(lines),
                "tags": ["news", "mock"],
                "source_id": "mock_news",
                "source_score": 0.7,
                "recency_score": 0.7,
                "structure_score": 0.7,
                "consistency_score": 0.6,
            }
        ]

    # -------- OPINION 계열 --------
    def get_forum_sentiment(self, *, topics: Iterable[str]) -> Iterable[Dict[str, Any]]:
        topics_str = ", ".join(topics) if topics else "시장 전반"
        body = f"[모의] 커뮤니티에서 {topics_str} 관련 낙관/비관 의견이 혼재된 상태라는 요약"
        return [
            {
                "title": f"커뮤니티 심리 요약(모의) - {topics_str}",
                "body": body,
                "tags": ["forum", "sentiment", "mock"],
                "source_id": "mock_forum",
                "source_score": 0.3,   # OPINION이라 일부러 낮게
                "recency_score": 0.8,
                "structure_score": 0.6,
                "consistency_score": 0.4,
            }
        ]



