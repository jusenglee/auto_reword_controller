# 자동 국내 주식 일일 리포트 컨트롤러

MCP 스타일 툴 세트 위에 LLM 플래너를 올려, 국내 주식용 일일 리포트를 자동으로 만들어내기 위한 설계와 파이프라인 스켈레톤이다. 신뢰성 높은 정량/공시/정책 정보를 우선적으로 확보하고, 뉴스·커뮤니티 등 다양한 관점을 레이어별로 결합할 수 있도록 구성했다.

## 주요 컴포넌트

- `models.py`: 데이터 레이어, 품질 점수, Plan/Report 스키마를 포함한 핵심 데이터클래스 정의. `SourceMeta.quality_band()`로 "main/support/discard"를 판정한다.
- `plan.py`: 고정 루틴을 담은 기본 Plan 생성기와 LLM 힌트를 반영한 확장 플랜 유틸리티.
- `planner.py`: LLM 프롬프트를 만들어주고, LLM이 반환한 Plan JSON을 화이트리스트/기본 파라미터 기반으로 정규화하는 `LLMPlanBuilder`·`PlanCompiler`를 제공한다.
- `executor.py`: MCP 툴 호출 인터페이스(`ToolRunner`)와 Plan 실행기(`PlanExecutor`). 레이어별 품질 점수를 계산해 최소 임계값 미만 데이터는 필터링한다.
- `report.py`: 수집 데이터를 LLM 프롬프트나 사람이 읽을 텍스트로 변환하는 Reporter 빌더. opinion 레이어는 자동으로 speculative 태그를 단다.
- `pipeline.py`: 플랜 생성 → 수집 → 리포트까지 한 번에 실행하는 `DailyReportPipeline` 오케스트레이터.

## 기본 흐름

1. `build_base_plan(date)`으로 지수/거시/공시를 포함한 최소 플랜을 생성.
2. 시장 키워드가 있다면 `enrich_plan` 또는 `LLMPlanBuilder.build()`로 뉴스/커뮤니티 확장 작업을 삽입.
3. `PlanExecutor`가 MCP 툴을 호출해 데이터를 모으고, 품질 임계값을 적용하여 `DailyStockReportData`를 생성.
4. `ReportBuilder`가 LLM용 프롬프트(`ReportPrompt`) 또는 텍스트 리포트(`DailyStockReportOutput.to_text`)를 구성하거나, `DailyReportPipeline.run()`으로 전 과정을 한 번에 실행.

## 품질 관리 규칙

- `SourceMeta.quality_score()`는 소스/최근성/구조/일관성 점수를 가중 평균하여 산출한다.
- `SourceMeta.quality_band()`는 0.7 이상(main) / 0.5 이상(support) / 미만(discard)으로 분류한다.
- `PlanExecutor`는 기본값으로 0.5 미만 데이터는 제거하며, Reporter는 0.7 미만이면 "low_confidence"나 "speculative" 태그를 부여한다.
- `ReportBuilder`는 support 밴드가 섞여 있으면 주의 문구를 자동 추가한다.

## LLM 플래너 사용 예시

```python
from datetime import date
from auto_reword_controller.planner import LLMPlanBuilder
from auto_reword_controller.pipeline import DailyReportPipeline

# runner는 MCP 툴을 실제 호출하는 구현체
pipeline = DailyReportPipeline(runner)

plan = pipeline.build_plan(target_date=date.today(), cues=["밸류업", "공매도 재개"])
data = pipeline.collect(plan)
report = pipeline.build_report(data)
print(report.to_text())
```

## 향후 확장 포인트

- MCP 툴 구현체(`ToolRunner`)를 실제 KRX/DART/뉴스/커뮤니티 API에 맞게 작성.
- LLM 플래너/리포터 프롬프트를 강화하여 섹터/테마 강조나 정책 이벤트 해석을 자동화.
- 품질 점수 계산을 규칙 기반에서 ML/통계 모델로 교체해 이상치 탐지 강화.
