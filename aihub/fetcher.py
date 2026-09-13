"""
AIHub 데이터셋 정보 수집기

aihub.or.kr에서 공개 데이터셋 목록과 상세 정보를 가져와
AI 프롬프트에 삽입 가능한 구조화된 텍스트로 변환합니다.

※ AIHub 공개 데이터셋 페이지를 크롤링합니다.
   로그인이 필요한 상세 데이터는 수집하지 않습니다.
"""

import re
from typing import Optional

import requests
from bs4 import BeautifulSoup
from rich.console import Console

from config import AIHUB_CONFIG

console = Console()


class AIHubFetcher:
    """AIHub 공개 데이터셋 정보를 수집하는 클래스."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9",
    }

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(self.HEADERS)

    # ── 검색 ────────────────────────────────────────────────

    def search_datasets(self, keyword: str, max_count: int = None) -> list[dict]:
        """
        키워드로 AIHub 데이터셋을 검색합니다.

        Args:
            keyword: 검색어 (예: "교통", "의료", "자율주행")
            max_count: 최대 가져올 데이터셋 수

        Returns:
            데이터셋 정보 딕셔너리 리스트
        """
        if max_count is None:
            max_count = AIHUB_CONFIG["max_datasets_per_search"]

        console.print(f"  [dim]🔍 AIHub 검색 중: \"{keyword}\"[/dim]")

        params = {
            "searchKeyword": keyword,
            "currPage": 1,
            "pageUnit": max_count,
        }

        try:
            resp = self._session.get(
                AIHUB_CONFIG["dataset_list_url"],
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            datasets = self._parse_dataset_list(resp.text)
            console.print(f"  [dim]✅ {len(datasets)}개 데이터셋 수집 완료[/dim]")
            return datasets[:max_count]

        except requests.RequestException as e:
            console.print(f"  [yellow]⚠️ AIHub 연결 실패: {e}[/yellow]")
            return []

    def get_dataset_detail(self, dataset_id: str) -> Optional[dict]:
        """특정 데이터셋의 상세 정보를 가져옵니다."""
        detail_url = f"{AIHUB_CONFIG['base_url']}/aihubdata/data/view.do"
        try:
            resp = self._session.get(
                detail_url,
                params={"currMenu": "115", "topMenu": "100", "dataSetSn": dataset_id},
                timeout=15,
            )
            resp.raise_for_status()
            return self._parse_dataset_detail(resp.text, dataset_id)
        except Exception as e:
            console.print(f"  [yellow]⚠️ 상세 정보 수집 실패 (id={dataset_id}): {e}[/yellow]")
            return None

    # ── 파싱 ────────────────────────────────────────────────

    def _parse_dataset_list(self, html: str) -> list[dict]:
        """데이터셋 목록 HTML을 파싱합니다."""
        soup = BeautifulSoup(html, "html.parser")
        datasets = []

        # AIHub의 실제 HTML 구조에 맞게 셀렉터를 조정해야 할 수 있습니다.
        items = soup.select(
            "ul.data-list li, .data-list-item, .dataset-item, li.item"
        )

        if not items:
            # 테이블 형태인 경우도 시도
            items = soup.select("table tbody tr")

        for item in items:
            try:
                title_el = item.select_one("a, .title, strong, h3, h4")
                desc_el = item.select_one(".desc, .description, p, td:nth-child(3)")
                tag_els = item.select(".tag, .badge, span.type")
                date_el = item.select_one(".date, time, td.date")

                title = title_el.get_text(strip=True) if title_el else "제목 없음"
                desc = desc_el.get_text(strip=True) if desc_el else "설명 없음"
                tags = [t.get_text(strip=True) for t in tag_els]
                date = date_el.get_text(strip=True) if date_el else ""

                # 링크에서 ID 추출
                link = title_el.get("href", "") if title_el else ""
                dataset_id = re.search(r"dataSetSn=(\d+)", link)
                ds_id = dataset_id.group(1) if dataset_id else ""

                if title and title != "제목 없음":
                    datasets.append({
                        "id": ds_id,
                        "title": title,
                        "description": desc[:300],
                        "tags": tags,
                        "date": date,
                        "url": f"{AIHUB_CONFIG['base_url']}{link}" if link.startswith("/") else link,
                    })
            except Exception:
                continue

        return datasets

    def _parse_dataset_detail(self, html: str, dataset_id: str) -> dict:
        """데이터셋 상세 페이지를 파싱합니다."""
        soup = BeautifulSoup(html, "html.parser")

        def text(sel):
            el = soup.select_one(sel)
            return el.get_text(strip=True) if el else ""

        return {
            "id": dataset_id,
            "title": text("h3.title, .dataset-title, h1, h2"),
            "description": text(".dataset-desc, .description, .content-body p"),
            "category": text(".category, .type-badge"),
            "size": text(".data-size, .file-size"),
            "format": text(".data-format, .file-type"),
            "license": text(".license, .data-license"),
            "updated": text(".update-date, .last-updated"),
        }

    # ── 프롬프트용 텍스트 생성 ──────────────────────────────

    def format_for_prompt(self, datasets: list[dict]) -> str:
        """
        데이터셋 정보를 AI 프롬프트에 삽입할 수 있는 텍스트로 변환합니다.
        """
        if not datasets:
            return "※ 데이터셋 정보를 수집하지 못했습니다. 아래 주제에 대해 AIHub에서 찾을 수 있는 일반적인 공개 데이터셋을 활용한다고 가정해주세요."

        lines = [f"총 {len(datasets)}개 데이터셋:"]
        for i, ds in enumerate(datasets, 1):
            lines.append(f"\n**[데이터셋 {i}] {ds['title']}**")
            if ds.get("description"):
                lines.append(f"- 설명: {ds['description'][:200]}")
            if ds.get("tags"):
                lines.append(f"- 태그: {', '.join(ds['tags'][:5])}")
            if ds.get("date"):
                lines.append(f"- 등록/수정일: {ds['date']}")
            if ds.get("url"):
                lines.append(f"- 링크: {ds['url']}")

        return "\n".join(lines)

    # ── 수동 입력 모드 (크롤링 실패 시) ─────────────────────

    @staticmethod
    def manual_input() -> str:
        """
        AIHub 크롤링이 실패한 경우 사용자가 직접 데이터셋 정보를 입력합니다.
        """
        console.print("\n[yellow]📋 AIHub에서 데이터셋을 자동으로 가져오지 못했습니다.[/yellow]")
        console.print("   아래에 분석할 데이터셋 정보를 직접 입력하거나 복붙해주세요.")
        console.print("   (입력 완료 후 빈 줄에서 Ctrl+D 또는 'END'를 입력하고 Enter)\n")

        lines = []
        try:
            while True:
                line = input()
                if line.strip().upper() == "END":
                    break
                lines.append(line)
        except EOFError:
            pass

        return "\n".join(lines) or "데이터셋 정보 없음 — 일반적인 공개 데이터를 가정하고 진행"
