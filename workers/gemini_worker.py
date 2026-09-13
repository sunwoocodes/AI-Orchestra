"""
Gemini Worker — gemini.google.com 브라우저 자동화

다중 셀렉터를 우선순위 순으로 시도해 UI 변경에 강인하게 동작합니다.
"""

import asyncio
from playwright.async_api import Page
from .base_worker import BaseAIWorker


class GeminiWorker(BaseAIWorker):
    """Google Gemini 웹 인터페이스 자동화 워커."""

    def __init__(self):
        super().__init__(
            name="Gemini",
            url="https://gemini.google.com/app",
            emoji="✨",
            color="cyan",
        )

    # ── 셀렉터 (우선순위 순, 앞에서부터 시도) ──────────────

    def _get_input_selectors(self) -> list[str]:
        return [
            "rich-textarea .ql-editor",          # Gemini 기본
            "rich-textarea [contenteditable]",    # 폴백 1
            "textarea[placeholder]",              # 폴백 2
            "[data-placeholder][contenteditable]",# 폴백 3
        ]

    def _get_send_selectors(self) -> list[str]:
        return [
            "button[aria-label='Send message']",  # Gemini 기본
            "button.send-button",                 # 폴백 1
            "button[aria-label='전송']",          # 한국어 라벨
            "button[type='submit']",              # 폴백 2
        ]

    def _get_response_selectors(self) -> list[str]:
        return [
            "model-response .markdown",           # Gemini 기본
            ".response-content .markdown",        # 폴백 1
            "message-content .markdown",          # 폴백 2
            ".model-response-text",               # 폴백 3
            "[data-chunk-index] p",               # 폴백 4
        ]

    def _get_exclude_selectors(self) -> list[str]:
        return super()._get_exclude_selectors() + [
            "suggestion-container",
            ".suggestion-container",
            "suggested-queries-container",
            "suggestion-chip-container",
            "mat-chip-row",
            ".chips-container",
            ".suggested-queries",
        ]

    # ── 응답 완료 판단 ──────────────────────────────────────

    async def _is_response_complete(self, page: Page) -> bool:
        """로딩 인디케이터가 사라지면 완료로 판단합니다."""
        try:
            loading = await page.query_selector(
                "response-loading, "
                ".loading-indicator, "
                "[aria-label='Gemini is thinking'], "
                ".thinking-indicator"
            )
            return loading is None
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
            self._log("⚠️ 로그인이 필요합니다. 브라우저에서 Google 계정으로 로그인해주세요.", level="warning")
            return False
        except Exception:
            return False

    async def new_chat(self):
        """새 대화를 시작합니다."""
        await self._page.goto(self.url, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        self._log("새 대화 시작")
