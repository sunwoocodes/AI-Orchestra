"""
단일 Worker 테스트 스크립트

전체 파이프라인 없이 특정 AI 하나만 테스트합니다.
로그인 확인 → 간단한 프롬프트 전송 → 응답 출력

사용:
  python tools/test_worker.py --ai gemini --prompt "안녕하세요!"
  python tools/test_worker.py --ai gpt
  python tools/test_worker.py --ai claude --headless
"""

import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rich.console import Console
from rich.panel import Panel
import config  # BROWSER_CONFIG 조작용

console = Console()

DEFAULT_PROMPTS = [
    "안녕하세요! 간단한 테스트입니다. AI 데이터 프로젝트에서 당신의 역할이 무엇인지 한 문장으로 소개해주세요.",
    "좋습니다! 그렇다면 AIHub 공개 데이터를 활용할 때 가장 중요하게 고려해야 할 포인트 1가지만 추천해주세요."
]


async def test_worker(ai_name: str, prompts: list[str], profile_dir: str):
    from workers import GeminiWorker, GPTWorker, ClaudeWorker

    worker_map = {
        "gemini": GeminiWorker,
        "gpt": GPTWorker,
        "claude": ClaudeWorker,
    }

    WorkerClass = worker_map.get(ai_name)
    if not WorkerClass:
        console.print(f"[red]알 수 없는 AI: {ai_name}[/red]")
        return

    worker = WorkerClass()
    os.makedirs(profile_dir, exist_ok=True)

    console.print(
        Panel.fit(
            f"[bold]{worker.emoji} {worker.name} Worker 테스트 (총 {len(prompts)}개 질문)[/bold]",
            border_style="cyan",
        )
    )

    try:
        await worker.launch(user_data_dir=profile_dir)

        logged_in = await worker.is_logged_in()
        if not logged_in:
            console.print(
                f"\n[yellow]⚠️  브라우저 창에서 {worker.name}에 로그인해주세요.[/yellow]\n"
                f"   로그인 완료 후 Enter를 누르세요..."
            )
            input()

        for i, prompt in enumerate(prompts, start=1):
            console.print(f"\n[cyan]💬 [질문 {i}/{len(prompts)}] 전송 중: [/cyan]{prompt}")
            response = await worker.chat(prompt)

            console.print(
                Panel(
                    response,
                    title=f"[bold]{worker.emoji} {worker.name} 응답 {i}[/bold]",
                    border_style="green",
                )
            )
            await asyncio.sleep(1.5)

        console.print(f"\n[green]✅ 질문 {len(prompts)}개 테스트 모두 성공![/green]")

        if config.BROWSER_CONFIG.get("keep_open", True):
            console.print("\n[cyan]🌐 브라우저를 닫지 않고 유지 중입니다. 종료하려면 Enter 키를 누르세요...[/cyan]")
            await asyncio.to_thread(input)

    except Exception as e:
        console.print(f"\n[red]❌ 테스트 실패: {e}[/red]")
        raise
    finally:
        await worker.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="단일 AI Worker 테스트")
    parser.add_argument(
        "--ai", required=True, choices=["gemini", "gpt", "claude"],
        help="테스트할 AI"
    )
    parser.add_argument(
        "--prompt", "-p", default=None,
        help="전송할 단일 프롬프트 (지정하지 않으면 기본 2개 질문 연속 실행)"
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="헤드리스 모드"
    )
    parser.add_argument(
        "--close", action="store_true",
        help="테스트 종료 후 브라우저 자동 닫기"
    )
    parser.add_argument(
        "--profile-dir", default=None,
        help="브라우저 프로필 경로"
    )
    args = parser.parse_args()

    if args.headless:
        config.BROWSER_CONFIG["headless"] = True
    if args.close:
        config.BROWSER_CONFIG["keep_open"] = False

    profile = args.profile_dir or os.path.expanduser(
        f"~/.config/ai-orchestrator/{args.ai}"
    )

    prompts = [args.prompt] if args.prompt else DEFAULT_PROMPTS

    asyncio.run(test_worker(args.ai, prompts, profile))
