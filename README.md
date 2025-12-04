# 자동 국내 주식 일일 리포트 컨트롤러

MCP 스타일 툴 세트 위에 LLM 플래너를 올려, 국내 주식용 일일 리포트를 자동으로 만들어내기 위한 설계와 파이프라인 스켈레톤이다. 신뢰성 높은 정량/공시/정책 정보를 우선적으로 확보하고, 뉴스·커뮤니티 등 다양한 관점을 레이어별로 결합할 수 있도록 구성했다.

## 주요 컴포넌트

- `models.py`: 데이터 레이어, 품질 점수, Plan/Report 스키마를 포함한 핵심 데이터클래스 정의.
- `plan.py`: 고정 루틴을 담은 기본 Plan 생성기와 LLM 힌트를 반영한 확장 플랜 유틸리티.
- `executor.py`: MCP 툴 호출 인터페이스(`ToolRunner`)와 Plan 실행기(`PlanExecutor`). 레이어별 품질 점수를 계산해 최소 임계값 미만 데이터는 필터링한다.
- `report.py`: 수집 데이터를 LLM 프롬프트나 사람이 읽을 텍스트로 변환하는 Reporter 빌더.

## 기본 흐름

1. `build_base_plan(date)`으로 지수/거시/공시를 포함한 최소 플랜을 생성.
2. 시장 키워드가 있다면 `enrich_plan`으로 뉴스/커뮤니티 확장 작업을 삽입.
3. `PlanExecutor`가 MCP 툴을 호출해 데이터를 모으고, 품질 임계값을 적용하여 `DailyStockReportData`를 생성.
4. `ReportBuilder`가 LLM용 프롬프트(`ReportPrompt`) 또는 텍스트 리포트(`DailyStockReportOutput.to_text`)를 구성.

## 품질 관리 규칙

- `SourceMeta.quality_score()`는 소스/최근성/구조/일관성 점수를 가중 평균하여 산출한다.
- `PlanExecutor`는 기본값으로 0.5 미만 데이터는 제거하며, Reporter는 0.7 미만이면 "low_confidence" 태그를 부여한다.

## 향후 확장 포인트

- MCP 툴 구현체(`ToolRunner`)를 실제 KRX/DART/뉴스/커뮤니티 API에 맞게 작성.
- LLM 플래너/리포터 프롬프트를 강화하여 섹터/테마 강조나 정책 이벤트 해석을 자동화.
- 품질 점수 계산을 규칙 기반에서 ML/통계 모델로 교체해 이상치 탐지 강화.
