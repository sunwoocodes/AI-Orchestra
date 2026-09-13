"""
보고서 빌더

갓생맘 AI OFFICE의 worker/report.ts에서 영감을 받아
세 AI의 결과물을 통합해 최종 기획서를 Markdown과 JSON으로 생성합니다.
선택적으로 Notion, Discord로 전송할 수 있습니다.
"""

import os
from datetime import datetime
from typing import Optional

from rich.console import Console
from dotenv import load_dotenv

load_dotenv()
console = Console()


class ReportBuilder:
    """
    3-AI 협업 결과를 통합해 최종 보고서를 생성합니다.
    갓생맘 AI OFFICE worker/report.ts의 publishReport() 컨셉 차용.
    """

    # ── 보고서 생성 ──────────────────────────────────────────

    def build(
        self,
        topic: str,
        dataset_info: str,
        phase1: str,
        phase2: str,
        phase3: str,
        log: list[dict],
        start_time: datetime,
    ) -> dict:
        """
        세 AI의 결과물을 통합해 보고서 딕셔너리를 반환합니다.
        """
        end_time = datetime.now()
        duration = (end_time - start_time).seconds

        markdown = self._build_markdown(
            topic, dataset_info, phase1, phase2, phase3, log, start_time, end_time
        )

        report = {
            "topic": topic,
            "generated_at": end_time.isoformat(),
            "duration_seconds": duration,
            "dataset_info": dataset_info[:500],
            "results": {
                "phase1_ideation": phase1,
                "phase2_evaluation": phase2,
                "phase3_critique": phase3,
            },
            "log": log,
            "markdown": markdown,
        }

        return report

    def _build_markdown(
        self,
        topic: str,
        dataset_info: str,
        phase1: str,
        phase2: str,
        phase3: str,
        log: list[dict],
        start_time: datetime,
        end_time: datetime,
    ) -> str:
        """최종 Markdown 보고서를 생성합니다."""
        duration = (end_time - start_time).seconds
        lines = [
            f"# 🎀 AI 오케스트레이터 — 프로젝트 기획 보고서",
            f"",
            f"> **주제**: {topic}  ",
            f"> **생성일**: {end_time.strftime('%Y년 %m월 %d일 %H:%M')}  ",
            f"> **소요 시간**: {duration}초  ",
            f"> **참여 AI 역할 분담**:  ",
            f"> - ✨ **Gemini**: 아이디어 제시 및 리서치 (Proposer)  ",
            f"> - 🔍 **ChatGPT**: 프로젝트 기획 및 구조화 (Planner / PM)  ",
            f"> - 🛡️ **Claude**: 논리적 반박 및 리스크 검토 (Critique / Devil's Advocate)",
            f"",
            f"---",
            f"",
            f"## 📂 분석 대상 데이터셋",
            f"",
            f"```",
            dataset_info[:800],
            f"```",
            f"",
            f"---",
            f"",
            f"## ✨ Phase 1 — Gemini (Proposer: 아이디어 제시 및 리서치)",
            f"",
            phase1,
            f"",
            f"---",
            f"",
            f"## 🔍 Phase 2 — ChatGPT (Planner: 프로젝트 기획 및 구조화)",
            f"",
            phase2,
            f"",
            f"---",
            f"",
            f"## 🛡️ Phase 3 — Claude (Critique: 논리적 반박 및 리스크 검토)",
            f"",
            phase3,
            f"",
            f"---",
            f"",
            f"## 📋 진행 로그",
            f"",
        ]

        for entry in log:
            lines.append(f"- `{entry['time']}` {entry['message']}")

        lines += [
            f"",
            f"---",
            f"",
            f"*이 보고서는 [AI 오케스트레이터](https://github.com/sunwoocodes/AILAP)가 자동 생성했습니다.*",
        ]

        return "\n".join(lines)

    # ── 외부 연동 (갓생맘 worker/report.ts의 publishReport 컨셉) ──

    async def publish_to_notion(self, report: dict) -> dict:
        """
        Notion 데이터베이스에 보고서를 저장합니다.
        NOTION_TOKEN, NOTION_DATABASE_ID 환경변수가 필요합니다.
        """
        import aiohttp

        token = os.getenv("NOTION_TOKEN")
        db_id = os.getenv("NOTION_DATABASE_ID")

        if not token or not db_id:
            console.print("  [dim]ℹ️  Notion 미설정 — 건너뜁니다.[/dim]")
            return {"status": "unconfigured"}

        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

        body = {
            "parent": {"database_id": db_id},
            "properties": {
                "주제": {"title": [{"text": {"content": report["topic"]}}]},
                "생성일": {"date": {"start": report["generated_at"][:10]}},
                "상태": {"select": {"name": "완료"}},
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": report["markdown"][:1900]}}]
                    },
                }
            ],
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.notion.com/v1/pages",
                    headers=headers,
                    json=body,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        console.print(f"  [green]✅ Notion 저장 완료: {data.get('url', '')}[/green]")
                        return {"status": "sent", "url": data.get("url")}
                    else:
                        text = await resp.text()
                        console.print(f"  [yellow]⚠️ Notion 저장 실패: {resp.status} {text[:100]}[/yellow]")
                        return {"status": "failed", "detail": text[:200]}
        except Exception as e:
            return {"status": "failed", "detail": str(e)}

    async def publish_to_discord(self, report: dict, notion_url: Optional[str] = None) -> dict:
        """
        Discord 웹훅으로 보고서 요약을 전송합니다.
        DISCORD_WEBHOOK_URL 환경변수가 필요합니다.
        """
        import aiohttp

        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            console.print("  [dim]ℹ️  Discord 미설정 — 건너뜁니다.[/dim]")
            return {"status": "unconfigured"}

        embed = {
            "title": f"🎀 AI 오케스트레이터 보고서 — {report['topic']}",
            "url": notion_url,
            "color": 0x6366F1,
            "description": f"AIHub 데이터 기반 프로젝트 기획 · 평가 · 검증 완료",
            "fields": [
                {"name": "주제", "value": report["topic"], "inline": True},
                {"name": "소요 시간", "value": f"{report['duration_seconds']}초", "inline": True},
                {
                    "name": "참여 AI",
                    "value": "✨ Gemini (기획) · 🔍 GPT (평가) · 🛡️ Claude (검토)",
                },
            ],
            "footer": {
                "text": "AI 오케스트레이터 · aihub.or.kr 데이터 활용"
            },
            "timestamp": report["generated_at"],
        }

        payload = {
            "username": "AI 오케스트레이터",
            "content": "📋 새 프로젝트 기획 보고서가 완성됐습니다.",
            "embeds": [embed],
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status in (200, 204):
                        console.print("  [green]✅ Discord 전송 완료[/green]")
                        return {"status": "sent"}
                    else:
                        return {"status": "failed", "detail": f"HTTP {resp.status}"}
        except Exception as e:
            return {"status": "failed", "detail": str(e)}
