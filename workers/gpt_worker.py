"""
GPT Worker — chatgpt.com 브라우저 자동화

다중 셀렉터를 우선순위 순으로 시도해 UI 변경에 강인하게 동작합니다.
"""

import asyncio
from playwright.async_api import Page
from .base_worker import BaseAIWorker


class GPTWorker(BaseAIWorker):
    """OpenAI ChatGPT 웹 인터페이스 자동화 워커."""

    def __init__(self):
        super().__init__(
            name="GPT",
            url="https://chatgpt.com/",
            emoji="🔍",
            color="green",
        )

    # ── 셀렉터 (우선순위 순) ────────────────────────────────

    def _get_input_selectors(self) -> list[str]:
        return [
            "#prompt-textarea",                          # ChatGPT 기본 (textarea)
            "div[contenteditable='true'][data-placeholder]",  # contenteditable 폴백
            "textarea[placeholder*='메시지']",           # 한국어 placeholder 폴백
            "textarea[placeholder*='Message']",          # 영어 폴백
            "[data-testid='text-input']",                # data-testid 폴백
        ]

    def _get_send_selectors(self) -> list[str]:
        return [
            "button[data-testid='send-button']",         # ChatGPT 기본
            "button[aria-label='Send prompt']",          # aria-label 폴백
            "button[aria-label='메시지 전송']",           # 한국어 폴백
            "button.send-button",                        # class 폴백
        ]

    def _get_response_selectors(self) -> list[str]:
        return [
            "div[data-message-author-role='assistant'] .markdown",  # 최신 구조
            "article[data-testid*='conversation-turn'] .markdown",  # article 구조
            ".agent-turn .markdown",                                # agent-turn
            "[data-message-author-role='assistant'] p",             # p 태그 폴백
            ".message.assistant .content",                          # 구형 폴백
        ]

    def _get_exclude_selectors(self) -> list[str]:
        return super()._get_exclude_selectors() + [
            "button[aria-label='Copy']",
            "button[aria-label='복사']",
            ".speech-player-button",
            "[data-testid='chat-completion-followup']",
            ".mb-2.grid.grid-cols-2",
        ]

    # ── 응답 완료 판단 ──────────────────────────────────────

    async def _is_response_complete(self, page: Page) -> bool:
        """Stop 버튼이 사라지면 응답 완료로 판단합니다."""
        try:
            stop_btn = await page.query_selector(
                "button[aria-label='Stop streaming'], "
                "button[data-testid='stop-button'], "
                "button[aria-label='생성 중지']"
            )
            return stop_btn is None
        except Exception:
            return False

    # ── 로그인 확인 ──────────────────────────────────────────

    async def is_logged_in(self) -> bool:
        try:
            for sel in self._get_input_selectors():
                try:
                    await self._page.wait_for_selector(sel, timeout=6_000)
                    return True
                except Exception:
                    continue
            self._log("⚠️ 로그인이 필요합니다. 브라우저에서 ChatGPT에 로그인해주세요.", level="warning")
            return False
        except Exception:
            return False

    async def new_chat(self):
        """새 대화를 시작합니다."""
        await self._page.goto("https://chatgpt.com/", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        self._log("새 대화 시작")
