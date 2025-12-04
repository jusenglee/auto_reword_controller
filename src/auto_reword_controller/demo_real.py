# demo_real.py (예시)

from datetime import date

from pipeline import DailyReportPipeline
from planner import LLMPlanBuilder
from report import ReportBuilder
from executor import ExecutionConfig
from runners import RealToolRunner  # 새로 만든 클래스


def main() -> None:
    target = date(2025, 12, 4)

    runner = RealToolRunner(target_date=target)
    pipeline = DailyReportPipeline(
        runner=runner,
        planner=LLMPlanBuilder(client=None),  # 아직 플래너 LLM은 안 붙여도 됨
        report_builder=ReportBuilder(),
        exec_config=ExecutionConfig(
            minimum_quality=0.5,
            main_threshold=0.7,
        ),
    )

    output = pipeline.run(target_date=target, cues=["코스닥", "밸류업"])
    print(output)


if __name__ == "__main__":
    main()
