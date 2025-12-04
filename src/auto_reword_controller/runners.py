
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Iterable, List
import requests
import yfinance as yf

from executor import ToolRunner


class RealToolRunner:
    """실제 API/크롤러를 붙이는 Runner. 우선 index부터 구현."""
    INDEX_TICKERS: Dict[str, str] = {
        "KOSPI": "^KS11",
        "KOSDAQ": "^KQ11",
    }

    def __init__(self, target_date: date | None = None) -> None:
        self.target_date = target_date or date.today()

    def get_index_snapshot(self, *, indices: Iterable[str]) -> Iterable[Dict[str, Any]]:
        """야후 파이낸스에서 KOSPI/KOSDAQ 지수 스냅샷을 가져온다."""
        records: List[Dict[str, Any]] = []

        for idx_name in indices:
            key = idx_name.upper()
            ticker = self.INDEX_TICKERS.get(key)
            if not ticker:
                # 알 수 없는 인덱스 이름이면 스킵
                continue

            # target_date 기준 최근 10영업일 정도만 조회
            start = (self.target_date - timedelta(days=10)).strftime("%Y-%m-%d")
            end = (self.target_date + timedelta(days=1)).strftime("%Y-%m-%d")

            df = yf.download(
                ticker,
                start=start,
                end=end,
                auto_adjust=False,
                progress=False,
            )

            if df.empty:
                # 데이터 자체가 없으면 낮은 신뢰도로 한 줄 남김
                records.append(
                    {
                        "title": f"{key} 지수 스냅샷 (데이터 없음)",
                        "body": f"야후 파이낸스에서 {key} 지수 데이터를 가져오지 못했습니다.",
                        "tags": [key, "index", "error"],
                        "source_id": "yahoo_finance",
                        "source_score": 0.3,
                        "recency_score": 0.0,
                        "structure_score": 0.3,
                        "consistency_score": 0.3,
                    }
                )
                continue

            # 날짜순 정렬 후, target_date 기준 가장 마지막 거래일 선택
            df = df.sort_index()
            # 최신/직전 종가
            close = float(df["Close"].iloc[-1])


            if len(df) >= 2:
                prev_close = float(df["Close"].iloc[-2])
                if prev_close > 0:
                    change_pct = (close / prev_close - 1.0) * 100.0
                else:
                    change_pct = 0.0
            else:
                prev_close = None
                change_pct = 0.0

            last_date = df.index[-1].date()

            body = f"{key} {close:,.2f}pt, 전일 대비 {change_pct:+.2f}% (야후 파이낸스 기준, {last_date.isoformat()} 종가)"

            # 조회일과 실제 데이터 날짜가 다르면 안내 문구 추가 (주말/휴장 등)
            if last_date != self.target_date:
                body += f" — {self.target_date.isoformat()}은(는) 휴장일로, 가장 가까운 과거 거래일 데이터를 사용했습니다."

            # 날짜 차이에 따라 recency_score 약간 조정
            day_diff = (self.target_date - last_date).days
            recency_score = 0.9 if day_diff == 0 else max(0.5, 0.9 - 0.05 * day_diff)

            records.append(
                {
                    "title": f"{key} 지수 스냅샷",
                    "body": body,
                    "tags": [key, "index"],
                    "source_id": "yahoo_finance",
                    "source_score": 0.9,          # 공식 지수는 아님이지만 신뢰도는 높은 편
                    "recency_score": recency_score,
                    "structure_score": 0.9,
                    "consistency_score": 0.9,
                }
            )

        return records

    # ------------------------
    # 2) 나머지 툴은 일단 Mock 재사용 or NotImplemented
    # ------------------------
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
        """
        OpenDART 공시검색(list.json)에서 target_date 기준 공시들을 가져와
        중요 공시 리스트를 만든다.

        importance:
          - "high": 키워드 기반으로 중요한 공시만 필터링
          - 그 외: 상위 N개 공시 반환
        """
        records: List[Dict[str, Any]] = []


        url = "https://opendart.fss.or.kr/api/list.json"
        ymd = self.target_date.strftime("%Y%m%d")

        params = {
            "crtfc_key": "4e8331d5b1d298378f4dce21f6ff955a398134d0",
            "bgn_de": ymd,
            "end_de": ymd,
            # 유가/코스닥 위주
            "corp_cls": "Y,K",
            # 많이 필요 없으니 100개 정도로 제한
            "page_no": 1,
            "page_count": 100,
            # 정기/주요사항/발행/지분/기타 전체
            # 필요하면 pblntf_ty로 좁힐 수 있음
        }

        try:
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()
        except Exception as e:
            records.append(
                {
                    "title": "DART 공시 조회 실패",
                    "body": f"OpenDART list.json 호출 중 오류 발생: {e}",
                    "tags": ["dart", "error"],
                    "source_id": "opendart_list",
                    "source_score": 0.4,
                    "recency_score": 0.0,
                    "structure_score": 0.5,
                    "consistency_score": 0.5,
                }
            )
            return records

        status = data.get("status")
        if status != "000":
            # 에러 코드일 경우 메시지와 함께 1개만 반환
            msg = data.get("message", "알 수 없는 오류")
            records.append(
                {
                    "title": f"DART 공시 조회 실패 (status={status})",
                    "body": f"OpenDART list.json 에서 에러 응답: {msg}",
                    "tags": ["dart", "error"],
                    "source_id": "opendart_list",
                    "source_score": 0.4,
                    "recency_score": 0.0,
                    "structure_score": 0.5,
                    "consistency_score": 0.5,
                }
            )
            return records

        items = data.get("list", []) or []

        if not items:
            records.append(
                {
                    "title": "당일 주요 공시 없음",
                    "body": f"{ymd} 기준으로 유가/코스닥 공시 목록이 없습니다.",
                    "tags": ["dart", "empty"],
                    "source_id": "opendart_list",
                    "source_score": 0.8,
                    "recency_score": 0.9,
                    "structure_score": 0.8,
                    "consistency_score": 0.8,
                }
            )
            return records

        # 중요 키워드: 합병/분할/증자/감자/자사주/배당/영업양수도/주요계약 등
        KEYWORDS = [
            "합병", "분할", "분할합병", "유상증자", "무상증자", "증자", "감자",
            "자기주식", "자사주", "배당", "영업양수도", "영업양도", "영업양수",
            "주요계약", "전환사채", "신주인수권부사채", "교환사채",
        ]

        def score_importance(report_nm: str) -> int:
            return sum(1 for kw in KEYWORDS if kw in report_nm)

        # 각 공시별 중요도 스코어 부여
        scored_items = []
        for item in items:
            report_nm = item.get("report_nm", "")
            imp_score = score_importance(report_nm)
            scored_items.append((imp_score, item))

        # importance='high'면 중요 키워드 없는 공시는 버리기
        if importance == "high":
            scored_items = [t for t in scored_items if t[0] > 0]

        # 그래도 아무 것도 없으면 상위 몇 개는 보여주자
        if not scored_items:
            scored_items = [(0, item) for item in items]

        # 중요도 → 내림차순 정렬 후 상위 N개만 사용
        scored_items.sort(key=lambda x: x[0], reverse=True)
        TOP_N = 10
        top_items = [item for _, item in scored_items[:TOP_N]]

        for item in top_items:
            corp_name = item.get("corp_name", "").strip()
            report_nm = item.get("report_nm", "").strip()
            rcept_no = item.get("rcept_no", "").strip()
            rcept_dt = item.get("rcept_dt", "").strip()  # YYYYMMDD

            # 공시뷰어 URL 형식: https://dart.fss.or.kr/dsaf001/main.do?rcpNo=접수번호 :contentReference[oaicite:1]{index=1}
            viewer_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}" if rcept_no else ""

            # YYYYMMDD → YYYY-MM-DD
            pretty_dt = (
                f"{rcept_dt[0:4]}-{rcept_dt[4:6]}-{rcept_dt[6:8]}"
                if len(rcept_dt) == 8
                else rcept_dt
            )

            title = f"{corp_name} - {report_nm}" if corp_name or report_nm else "무제 공시"

            body_lines = []
            if pretty_dt:
                body_lines.append(f"접수일자: {pretty_dt}")
            if rcept_no:
                body_lines.append(f"접수번호: {rcept_no}")
            if viewer_url:
                body_lines.append(f"공시보기: {viewer_url}")

            body = "\n".join(body_lines) if body_lines else "세부 정보 없음"

            # 당일 공시라서 recency는 거의 최상
            recency_score = 0.95

            records.append(
                {
                    "title": title,
                    "body": body,
                    "tags": ["dart", "disclosure"],
                    "source_id": "opendart_list",
                    "source_score": 0.95,
                    "recency_score": recency_score,
                    "structure_score": 0.9,
                    "consistency_score": 0.9,
                }
            )

        return records

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

