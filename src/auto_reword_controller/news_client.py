# news_client.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Protocol

import os
import requests


@dataclass
class NewsItem:
    """뉴스 한 건을 표현하는 최소 단위 모델."""
    title: str
    summary: str
    url: str
    source: str
    published_at: datetime


class NewsClient(Protocol):
    """뉴스 소스를 추상화하는 클라이언트 인터페이스."""

    def search(self, query: str, limit: int = 10) -> List[NewsItem]:
        """query 기준으로 최신 뉴스 최대 limit건 반환."""
        ...


class NaverNewsClient:
    """네이버 검색 > 뉴스 OpenAPI 기반 구현.

    참고:
    - 요청 URL: https://openapi.naver.com/v1/search/news.json :contentReference[oaicite:0]{index=0}
    - 헤더:
        X-Naver-Client-Id, X-Naver-Client-Secret
    - 파라미터:
        query (필수), display, start, sort=date/sim :contentReference[oaicite:1]{index=1}
    """

    BASE_URL = "https://openapi.naver.com/v1/search/news.json"

    def __init__(
            self,
            client_id: str | None = None,
            client_secret: str | None = None,
            timeout: float = 5.0,
    ) -> None:
        self.client_id = "1PUmDLYSeoiKjjHQBI0u"
        self.client_secret = "7mtVAIMWLA"
        self.timeout = timeout

        # 키가 아예 없으면 바로 에러 내고 싶지 않으면, 여기서 warn 로그만 찍고 넘어가도 됨
        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 설정되어 있지 않습니다."
            )

    def search(self, query: str, limit: int = 10) -> List[NewsItem]:
        # 네이버 API display는 최대 100, 기본 10 :contentReference[oaicite:2]{index=2}
        display = max(1, min(limit, 100))

        params = {
            "query": query,
            "display": display,
            "start": 1,
            "sort": "date",  # 최신순
        }

        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }

        resp = requests.get(self.BASE_URL, params=params, headers=headers, timeout=self.timeout)
        resp.raise_for_status()

        data = resp.json()
        items = data.get("items", []) or []

        results: List[NewsItem] = []
        for it in items:
            # JSON 필드는 docs 상 XML 구조와 1:1 매핑: title, originallink, link, description, pubDate 등 :contentReference[oaicite:3]{index=3}
            title = _strip_html(it.get("title", "")).strip()
            summary = _strip_html(it.get("description", "")).strip()
            url = it.get("link") or it.get("originallink") or ""
            pub_raw = it.get("pubDate", "")

            # pubDate 예: "Mon, 26 Sep 2016 07:50:00 +0900" :contentReference[oaicite:4]{index=4}
            try:
                published_at = datetime.strptime(pub_raw, "%a, %d %b %Y %H:%M:%S %z")
            except Exception:
                # 포맷이 안 맞으면 그냥 naive now로 fallback
                published_at = datetime.now()

            # 네이버 뉴스인데도 원문 출처(언론사) 정보는 따로 안 줄 수 있으니, 일단 "naver"로 둠
            source = "naver"

            results.append(
                NewsItem(
                    title=title or "(제목 없음)",
                    summary=summary or "(요약 없음)",
                    url=url,
                    source=source,
                    published_at=published_at,
                )
            )

        return results


def _strip_html(text: str) -> str:
    """네이버 응답의 <b>태그 등 간단한 HTML 태그 제거용."""
    import re

    # 아주 간단한 태그 제거 (정교함 필요 없으니 이 정도면 충분)
    return re.sub(r"<[^>]+>", "", text or "")
