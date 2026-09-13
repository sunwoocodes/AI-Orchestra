"""
Claude Worker — claude.ai 브라우저 자동화

다중 셀렉터를 우선순위 순으로 시도해 UI 변경에 강인하게 동작합니다.
"""

import asyncio
from playwright.async_api import Page
from .base_worker import BaseAIWorker


class ClaudeWorker(BaseAIWorker):
    """Anthropic Claude 웹 인터페이스 자동화 워커."""

    def __init__(self):
        super().__init__(
            name="Claude",
            url="https://claude.ai/new",
            emoji="🛡️",
            color="magenta",
        )

    # ── 셀렉터 (우선순위 순) ────────────────────────────────

    def _get_input_selectors(self) -> list[str]:
        return [
            "div.ProseMirror[contenteditable='true']",   # Claude 기본 (ProseMirror)
            "div[contenteditable='true'][data-placeholder]",  # data-placeholder 폴백
            "div[contenteditable='true']",               # contenteditable 범용
            "textarea[placeholder]",                     # textarea 폴백
        ]

    def _get_send_selectors(self) -> list[str]:
        return [
            "button[aria-label='Send Message']",         # Claude 기본
            "button[data-testid='send-button']",         # data-testid 폴백
            "button[aria-label='메시지 전송']",           # 한국어 폴백
            "button[type='submit']",                     # 범용 폴백
        ]

    def _get_response_selectors(self) -> list[str]:
        return [
            "div[data-testid='chat-message-content'] .prose",  # 1순위: 본문 markdown/prose
            "div.font-claude-message .prose",                   # 2순위: Claude 폰트 메시지 내부 prose
            "div[class*='font-claude-message'] .prose",        # 3순위: 동적 클래스 내부 prose
            ".claude-message .prose",                           # 4순위: 클래스명 prose
            "div.prose",                                        # 5순위: 범용 prose
            "div.font-claude-message",                           # 6순위: 메시지 통째로 (폴백)
            "div[class*='font-claude-message']",                # 7순위: 메시지 통째로 (폴백)
            "div[data-testid='chat-message-content']",          # 8순위: testid 통째로 (폴백)
            "[data-testid='assistant-message']",                # 9순위: assistant-message testid
        ]

    def _get_exclude_selectors(self) -> list[str]:
        return super()._get_exclude_selectors() + [
            "button[aria-label='Copy']",
            "button[aria-label='Retry']",
            "button[aria-label='복사']",
            ".contents-copy-button",
            "[data-testid='chat-message-actions']",
            ".inline-flex.items-center",
            # Claude Extended Thinking (생각 과정) 블록 및 타이틀 완전 제외
            "[data-testid*='thinking']",
            "div[class*='thinking']",
            "div[class*='Thinking']",
            ".thinking-process",
            ".thinking-block",
            "details",
            "summary",
            "div[class*='thought']",
            "div[class*='Thought']",
            ".font-claude-thinking",
            "button[aria-label*='Thought']",
            "button[aria-label*='thinking']",
            "button[aria-label*='Thinking']",
        ]

    # ── 응답 완료 판단 ──────────────────────────────────────

    async def _is_response_complete(self, page: Page) -> bool:
        """Stop Response 버튼 및 스트리밍 인디케이터가 사라지면 완료로 판단합니다."""
        try:
            streaming = await page.query_selector(
                "button[aria-label*='Stop'], "
                "button[aria-label*='중지'], "
                "[data-is-streaming='true'], "
                ".streaming-indicator, "
                "svg.animate-spin"
            )
            return streaming is None
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
            self._log("⚠️ 로그인이 필요합니다. 브라우저에서 Claude에 로그인해주세요.", level="warning")
            return False
        except Exception:
            return False

    async def new_chat(self):
        """새 대화를 시작합니다."""
        await self._page.goto("https://claude.ai/new", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        self._log("새 대화 시작")
