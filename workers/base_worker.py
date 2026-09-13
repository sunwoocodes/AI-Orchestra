"""
Base AI Worker — Playwright 기반 공통 브라우저 자동화 추상 클래스

각 AI 서비스(Gemini, GPT, Claude)의 Worker가 이 클래스를 상속합니다.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from rich.console import Console

from config import BROWSER_CONFIG

console = Console()


class BaseAIWorker(ABC):
    """
    모든 AI 웹 워커의 공통 기반 클래스.

    서브클래스는 다음 메서드를 반드시 구현해야 합니다:
      - _get_input_selectors(): 프롬프트 입력창 CSS 셀렉터 리스트 (우선순위 순)
      - _get_send_selectors(): 전송 버튼 CSS 셀렉터 리스트 (우선순위 순)
      - _get_response_selectors(): 응답 텍스트 CSS 셀렉터 리스트 (우선순위 순)
      - _is_response_complete(page): 응답 생성 완료 여부 판단
    """

    def __init__(self, name: str, url: str, emoji: str, color: str):
        self.name = name
        self.url = url
        self.emoji = emoji
        self.color = color
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None

    # ── 추상 메서드 (서브클래스 구현 필수) ──────────────────

    @abstractmethod
    def _get_input_selectors(self) -> list[str]:
        """프롬프트 입력창 CSS 셀렉터 목록 (앞에서부터 우선 시도)"""
        ...

    @abstractmethod
    def _get_send_selectors(self) -> list[str]:
        """전송 버튼 CSS 셀렉터 목록 (앞에서부터 우선 시도)"""
        ...

    @abstractmethod
    def _get_response_selectors(self) -> list[str]:
        """마지막 응답 텍스트 CSS 셀렉터 목록 (앞에서부터 우선 시도)"""
        ...

    @abstractmethod
    async def _is_response_complete(self, page: Page) -> bool:
        """응답 생성이 완료됐는지 판단. True = 완료."""
        ...

    # ── 단일 셀렉터 호환 래퍼 ────────────────────────────────

    def _get_input_selector(self) -> str:
        return self._get_input_selectors()[0]

    def _get_send_selector(self) -> str:
        return self._get_send_selectors()[0]

    def _get_response_selector(self) -> str:
        return self._get_response_selectors()[0]

    # ── 폴백 셀렉터 헬퍼 ─────────────────────────────────────

    async def _find_element(self, selectors: list[str], timeout: int = 10_000):
        """셀렉터 목록을 순서대로 시도해 첫 번째 발견된 요소를 반환합니다."""
        for sel in selectors:
            try:
                el = await self._page.wait_for_selector(sel, timeout=timeout)
                if el:
                    return el, sel
            except Exception:
                continue
        raise RuntimeError(
            f"{self.name}: 요소를 찾지 못했습니다.\n"
            f"  시도한 셀렉터: {selectors}\n"
            f"  현재 URL: {self._page.url}"
        )

    # ── 브라우저 생명주기 ────────────────────────────────────

    async def launch(self, user_data_dir: Optional[str] = None):
        """
        브라우저를 시작하고 대상 URL로 이동합니다.
        user_data_dir을 지정하면 기존 로그인 세션(쿠키)을 재사용합니다.
        """
        self._playwright = await async_playwright().start()
        launch_kwargs = {
            "headless": BROWSER_CONFIG["headless"],
            "slow_mo": BROWSER_CONFIG["slow_mo"],
            "args": [
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        }

        if user_data_dir:
            # 기존 프로필을 사용해 로그인 유지
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                **launch_kwargs,
            )
            self._page = (
                self._context.pages[0] if self._context.pages
                else await self._context.new_page()
            )
        else:
            self._browser = await self._playwright.chromium.launch(**launch_kwargs)
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
                ),
            )
            self._page = await self._context.new_page()

        self._log(f"브라우저 시작 → {self.url}")
        await self._page.goto(
            self.url, wait_until="domcontentloaded",
            timeout=BROWSER_CONFIG["timeout"]
        )
        await asyncio.sleep(2)

    async def close(self):
        """브라우저를 닫습니다."""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._log("브라우저 종료")

    async def is_logged_in(self) -> bool:
        """로그인 상태를 확인합니다. 서브클래스에서 오버라이드 가능."""
        return True

    # ── 핵심 대화 메서드 ────────────────────────────────────

    async def chat(self, prompt: str) -> str:
        """
        프롬프트를 입력하고 응답을 받아 반환합니다.

        Args:
            prompt: 보낼 텍스트

        Returns:
            AI가 생성한 응답 텍스트
        """
        if not self._page:
            raise RuntimeError(
                f"{self.name} Worker가 시작되지 않았습니다. launch()를 먼저 호출하세요."
            )

        self._log(f"입력 중... ({len(prompt)}자)")

        # 0. 전송 전 기존 응답 상태 측정 (이전 답변 재사용 방지)
        initial_count = await self._get_response_count()
        prev_last_text = await self._get_latest_response()

        # 1. 입력창 찾기 (다중 셀렉터 폴백)
        input_el, input_sel = await self._find_element(
            self._get_input_selectors(), timeout=30_000
        )
        await input_el.click()
        await asyncio.sleep(0.3)

        # 2. 기존 내용 지우기 (Ctrl+A → Delete)
        await self._page.keyboard.press("Control+a")
        await asyncio.sleep(0.1)
        await self._page.keyboard.press("Delete")
        await asyncio.sleep(0.1)

        # 3. 프롬프트 입력 (fill 우선, contenteditable은 type으로 폴백)
        try:
            await self._page.fill(input_sel, prompt)
        except Exception:
            await self._page.type(input_sel, prompt, delay=15)

        await asyncio.sleep(0.6)

        # 4. 전송 (Enter 키 — 모든 AI 서비스에서 안정적으로 동작)
        await self._page.keyboard.press("Enter")

        self._log("전송 완료. 응답 대기 중...")

        # 5. 새 응답 완료 대기
        response_text = await self._wait_for_response(initial_count, prev_last_text)
        self._log(f"응답 수집 완료 ({len(response_text)}자)")
        return response_text

    async def _get_response_count(self) -> int:
        """현재 페이지에 존재하는 응답 카드의 개수를 반환합니다."""
        for sel in self._get_response_selectors():
            try:
                elements = await self._page.query_selector_all(sel)
                if elements:
                    return len(elements)
            except Exception:
                continue
        return 0

    async def _wait_for_response(self, initial_count: int, prev_last_text: str) -> str:
        """
        새 응답이 생성되고 완료될 때까지 폴링합니다.
        1. 새 응답 카드가 추가되거나 텍스트가 달라질 때까지 대기
        2. 응답 완료 신호 및 텍스트 안정화 검사
        """
        poll_interval = BROWSER_CONFIG["response_poll_interval"]
        stable_required = BROWSER_CONFIG["response_stable_count"]
        max_wait = BROWSER_CONFIG["timeout"] / 1000  # ms → 초
        elapsed = 0.0
        stable_count = 0
        last_observed_text = ""

        # 1단계: 새 응답 출현 대기 (최대 15초)
        new_response_started = False
        wait_start_limit = 15.0
        while elapsed < wait_start_limit:
            current_count = await self._get_response_count()
            current_text = await self._get_latest_response()

            # 응답 카드가 추가되었거나 내용이 바뀌기 시작한 경우
            if current_count > initial_count or (current_text and current_text != prev_last_text):
                new_response_started = True
                break

            await asyncio.sleep(0.5)
            elapsed += 0.5

        if not new_response_started:
            self._log("새 응답 생성이 감지되지 않았습니다. 계속 수집을 시도합니다.", level="warning")

        # 2단계: 응답 완료 및 안정화 대기
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            complete = await self._is_response_complete(self._page)
            current_text = await self._get_latest_response()

            # 이전 응답과 여전히 똑같은 경우 (아직 새 텍스트 안 뜸) 건너뜀
            if initial_count > 0 and current_text == prev_last_text:
                continue

            # 완료 신호 있고 텍스트가 존재하는 경우
            if complete and current_text and current_text != prev_last_text:
                if current_text == last_observed_text:
                    stable_count += 1
                    if stable_count >= 2:
                        return current_text
                else:
                    stable_count = 1
                    last_observed_text = current_text

            # 텍스트 안정화 판단
            if current_text and current_text == last_observed_text:
                stable_count += 1
                if stable_count >= stable_required:
                    return current_text
            else:
                stable_count = 0
                last_observed_text = current_text

        return last_observed_text or "(응답 수집 시간 초과)"

    def _get_exclude_selectors(self) -> list[str]:
        """추출 시 제외할 불필요한 노드(추천 칩, 버튼, 풋터 등) CSS 셀렉터 목록."""
        return [
            "suggestion-chip",
            ".suggestion-chip",
            ".suggestion-chips",
            "suggested-queries",
            ".suggested-queries",
            "suggested-prompt",
            ".suggested-prompt",
            ".query-suggestion",
            "button",
            ".action-buttons",
            ".response-actions",
            ".model-response-footer",
            "footer",
            "[data-test-id='suggestion-chip']",
            "gmp-icon-button",
            ".response-footer",
        ]

    async def _get_latest_response(self) -> str:
        """마지막 응답 텍스트를 다중 셀렉터로 추출하며, 추천 칩 및 버튼 텍스트를 제거합니다."""
        exclude_sels = self._get_exclude_selectors()
        for sel in self._get_response_selectors():
            try:
                elements = await self._page.query_selector_all(sel)
                if elements:
                    last = elements[-1]
                    clean_text = await last.evaluate(
                        """(el, excludes) => {
                            const clone = el.cloneNode(true);
                            excludes.forEach(s => {
                                clone.querySelectorAll(s).forEach(n => n.remove());
                            });
                            return clone.innerText ? clone.innerText.trim() : '';
                        }""",
                        exclude_sels
                    )
                    if clean_text:
                        return clean_text
            except Exception:
                continue
        return ""

    def _log(self, msg: str, level: str = "info"):
        """포맷된 로그 출력."""
        prefix = f"[{self.emoji} {self.name}]"
        if level == "warning":
            console.print(f"{prefix} ⚠️  {msg}", style="yellow")
        elif level == "error":
            console.print(f"{prefix} ❌ {msg}", style="red")
        else:
            console.print(f"{prefix} {msg}", style=self.color)
