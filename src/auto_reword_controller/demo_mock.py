# demo_mock.py
from datetime import date

from pipeline import DailyReportPipeline
from planner import LLMPlanBuilder
from report import ReportBuilder
from executor import ExecutionConfig
from mock_runner import MockToolRunner  # 방금 만든 클래스


def main() -> None:
    target = date(2025, 12, 4)

    runner = MockToolRunner(target_date=target)
    pipeline = DailyReportPipeline(
        runner=runner,
        planner=LLMPlanBuilder(client=None),  # LLM 플래너 없으면 base_plan + fallback만 사용
        report_builder=ReportBuilder(),
        exec_config=ExecutionConfig(
            minimum_quality=0.5,
            main_threshold=0.7,
        ),
    )

    output = pipeline.run(target_date=target, cues=["코스닥", "밸류업"])
    print("=== Daily Stock Report Output ===")
    print(f"Output type: {type(output)}")

    # 객체의 속성들을 확인하여 출력
    if hasattr(output, '__dict__'):
        for key, value in output.__dict__.items():
            print(f"{key}: {value}")
    else:
        # 객체를 문자열로 변환하여 출력
        print(str(output))



if __name__ == "__main__":
    main()
