"""
AI 오케스트레이터 — CLI 진입점

사용법:
  python main.py                         # 대화형 모드
  python main.py --topic "교통사고 예측"  # 키워드 지정
  python main.py --topic "의료 AI" --dataset-file ./my_dataset.txt  # 데이터셋 파일 지정
"""

import asyncio
import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from dotenv import load_dotenv

load_dotenv()

from pipeline import AIPipeline
from aihub import AIHubFetcher
from config import PROJECT, BROWSER_CONFIG

console = Console()


def print_banner():
    """시작 배너를 출력합니다."""
    console.print(
        Panel.fit(
            f"[bold cyan]{PROJECT['name']}[/bold cyan]\n"
            f"[dim]{PROJECT['subtitle']}[/dim]\n"
            f"[dim]v{PROJECT['version']}[/dim]",
            border_style="cyan",
        )
    )
    console.print()


def parse_args():
    parser = argparse.ArgumentParser(
        description="AIHub 데이터 기반 AI 협업 기획·검증 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python main.py
  python main.py --topic "교통사고 예측"
  python main.py --topic "의료 영상 분석" --headless
  python main.py --topic "자율주행" --dataset-file ./dataset_info.txt
        """,
    )
    parser.add_argument("--topic", "-t", type=str, help="분석할 주제 (예: 교통사고 예측)")
    parser.add_argument(
        "--dataset-file", "-d", type=str,
        help="데이터셋 정보를 담은 텍스트 파일 경로 (없으면 자동 수집)"
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="브라우저 창을 숨기고 백그라운드에서 실행"
    )
    parser.add_argument(
        "--profile-dir", type=str, default="~/.config/ai-orchestrator",
        help="브라우저 로그인 프로필 저장 경로"
    )
    parser.add_argument(
        "--close-browsers", action="store_true",
        help="완료 후 브라우저를 닫음 (기본값: 유지)"
    )
    return parser.parse_args()


async def main():
    print_banner()
    args = parse_args()

    # 헤드리스 모드 및 브라우저 유지 설정
    import config
    if args.headless:
        config.BROWSER_CONFIG["headless"] = True
        console.print("[dim]🔕 헤드리스 모드: 브라우저 창이 표시되지 않습니다.[/dim]\n")

    if args.close_browsers:
        config.BROWSER_CONFIG["keep_open"] = False

    # ── 주제 입력 ────────────────────────────────────────────
    if args.topic:
        topic = args.topic
    else:
        console.print("[bold]📌 분석할 주제를 입력해주세요.[/bold]")
        console.print("   예) 교통사고 예측 / 의료 영상 진단 / 농작물 병충해 탐지\n")
        topic = Prompt.ask("  주제")

    if not topic.strip():
        console.print("[red]주제를 입력해야 합니다.[/red]")
        sys.exit(1)

    # ── 데이터셋 정보 수집 ───────────────────────────────────
    if args.dataset_file:
        # 파일에서 직접 읽기
        try:
            dataset_info = Path(args.dataset_file).read_text(encoding="utf-8")
            console.print(f"[dim]📂 데이터셋 파일 로드: {args.dataset_file}[/dim]")
        except FileNotFoundError:
            console.print(f"[red]파일을 찾을 수 없습니다: {args.dataset_file}[/red]")
            sys.exit(1)
    else:
        # AIHub에서 자동 수집
        console.print(f"\n[dim]🌐 AIHub에서 \"{topic}\" 관련 데이터셋 수집 중...[/dim]")
        fetcher = AIHubFetcher()
        datasets = fetcher.search_datasets(topic)

        if datasets:
            dataset_info = fetcher.format_for_prompt(datasets)
        else:
            console.print(
                "\n[yellow]⚠️  AIHub 자동 수집 실패 또는 결과 없음.[/yellow]"
            )
            use_manual = Confirm.ask(
                "  데이터셋 정보를 직접 입력하시겠습니까? (N = AIHub 정보 없이 진행)"
            )
            if use_manual:
                dataset_info = AIHubFetcher.manual_input()
            else:
                dataset_info = (
                    f"AI Hub 검색 주제: {topic}\n"
                    "자동 수집 실패 — AIHub에서 '{topic}' 관련 공개 데이터셋을 "
                    "활용한다고 가정하고 분석해주세요."
                )

    # ── 브라우저 프로필 경로 설정 ────────────────────────────
    profile_base = Path(args.profile_dir).expanduser()
    user_data_dirs = {
        "gemini": str(profile_base / "gemini"),
        "gpt": str(profile_base / "gpt"),
        "claude": str(profile_base / "claude"),
    }
    # 프로필 디렉터리 생성
    for path in user_data_dirs.values():
        Path(path).mkdir(parents=True, exist_ok=True)

    console.print(f"\n[dim]💾 브라우저 프로필: {profile_base}[/dim]")
    console.print(
        "[dim]   (첫 실행 시 각 AI 서비스에 로그인이 필요합니다. "
        "이후에는 자동으로 로그인 유지됩니다.)[/dim]\n"
    )

    # ── 파이프라인 실행 ──────────────────────────────────────
    pipeline = AIPipeline(user_data_dirs=user_data_dirs)

    try:
        report = await pipeline.run(topic=topic, dataset_info=dataset_info)

        # Notion/Discord 연동 (환경변수가 설정된 경우에만)
        import os
        if os.getenv("NOTION_TOKEN"):
            notion_result = await pipeline._report_builder.publish_to_notion(report)
            notion_url = notion_result.get("url")
            if os.getenv("DISCORD_WEBHOOK_URL"):
                await pipeline._report_builder.publish_to_discord(report, notion_url)
        elif os.getenv("DISCORD_WEBHOOK_URL"):
            await pipeline._report_builder.publish_to_discord(report)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ 사용자에 의해 중단되었습니다.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]❌ 실행 오류: {e}[/red]")
        raise


if __name__ == "__main__":
    asyncio.run(main())
