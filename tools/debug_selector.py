"""
셀렉터 디버그 도구

AI 서비스의 웹 UI가 바뀌어 셀렉터가 깨졌을 때
현재 페이지에서 유효한 셀렉터를 탐색하는 도구입니다.

사용:
  python tools/debug_selector.py --ai gemini
  python tools/debug_selector.py --ai gpt
  python tools/debug_selector.py --ai claude
"""

import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.async_api import async_playwright
from rich.console import Console
from rich.table import Table

console = Console()

# 각 AI별로 확인할 후보 셀렉터 목록
CANDIDATE_SELECTORS = {
    "input": [
        "rich-textarea .ql-editor",
        "rich-textarea [contenteditable]",
        "#prompt-textarea",
        "div.ProseMirror[contenteditable='true']",
        "div[contenteditable='true']",
        "textarea[placeholder]",
        "[data-testid='text-input']",
        "[data-placeholder][contenteditable]",
    ],
    "send": [
        "button[aria-label='Send message']",
        "button[aria-label='Send prompt']",
        "button[aria-label='Send Message']",
        "button[aria-label='전송']",
        "button[aria-label='메시지 전송']",
        "button[data-testid='send-button']",
        "button.send-button",
        "button[type='submit']",
    ],
    "response": [
        "model-response .markdown",
        "div[data-message-author-role='assistant'] .markdown",
        "article[data-testid*='conversation-turn'] .markdown",
        "div[data-testid='chat-message-content'] .prose",
        ".claude-message .prose",
        ".font-claude-message",
        ".agent-turn .markdown",
        ".response-content .markdown",
        "[data-message-author-role='assistant'] p",
    ],
}

AI_URLS = {
    "gemini": "https://gemini.google.com/app",
    "gpt": "https://chatgpt.com/",
    "claude": "https://claude.ai/new",
}


async def debug_selectors(ai: str, profile_dir: str):
    url = AI_URLS.get(ai)
    if not url:
        console.print(f"[red]알 수 없는 AI: {ai}. gemini/gpt/claude 중 하나를 선택하세요.[/red]")
        return

    console.print(f"\n[cyan]🔍 {ai.upper()} 셀렉터 디버그 시작[/cyan]")
    console.print(f"   URL: {url}")
    console.print(f"   프로필: {profile_dir}\n")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            slow_mo=50,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        for category, selectors in CANDIDATE_SELECTORS.items():
            table = Table(title=f"[{category.upper()}] 셀렉터 결과", border_style="cyan")
            table.add_column("셀렉터", style="dim", max_width=60)
            table.add_column("발견", justify="center")
            table.add_column("태그", justify="center")
            table.add_column("텍스트 (앞 30자)", max_width=35)

            for sel in selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        tag = await el.evaluate("el => el.tagName.toLowerCase()")
                        text = (await el.inner_text()).strip()[:30]
                        table.add_row(sel, "✅", tag, text or "(빈 요소)")
                    else:
                        table.add_row(sel, "❌", "-", "-")
                except Exception as e:
                    table.add_row(sel, "⚠️", "-", str(e)[:30])

            console.print(table)
            console.print()

        console.print("[yellow]창을 닫으려면 Enter를 누르세요...[/yellow]")
        input()
        await context.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI 셀렉터 디버그 도구")
    parser.add_argument(
        "--ai", required=True, choices=["gemini", "gpt", "claude"],
        help="디버그할 AI 서비스"
    )
    parser.add_argument(
        "--profile-dir", default=None,
        help="브라우저 프로필 경로 (기본: ~/.config/ai-orchestrator/{ai})"
    )
    args = parser.parse_args()

    profile = args.profile_dir or os.path.expanduser(
        f"~/.config/ai-orchestrator/{args.ai}"
    )
    os.makedirs(profile, exist_ok=True)

    asyncio.run(debug_selectors(args.ai, profile))
