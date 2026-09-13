"""
AI 파이프라인 오케스트레이터

갓생맘 AI OFFICE의 dayScript(Generator 기반 하루 시나리오) 컨셉에서 영감을 받아,
Phase별 순차 실행과 상태 추적을 구현합니다.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from config import PIPELINE_PHASES, PROJECT
from workers import GeminiWorker, GPTWorker, ClaudeWorker
from pipeline.prompts import (
    make_phase1_ideation,
    make_phase2_evaluation,
    make_phase3_critique,
)
from report.builder import ReportBuilder

console = Console()


class AIPipeline:
    """
    3-AI 협업 파이프라인 오케스트레이터.

    Phase 1 (Gemini): 아이디어 기획
    Phase 2 (GPT):   기술/시장 평가
    Phase 3 (Claude): 리스크 검토
    Phase 4 (Report): 최종 보고서 생성
    """

    def __init__(
        self,
        user_data_dirs: Optional[dict] = None,
        on_phase_change: Optional[Callable[[int, str], None]] = None,
    ):
        """
        Args:
            user_data_dirs: 각 AI 브라우저 프로필 경로
                예: {"gemini": "~/.config/chromium_gemini", "gpt": "...", "claude": "..."}
            on_phase_change: 페이즈 변경 콜백 함수 (index, phase_name) → None
        """
        self.user_data_dirs = user_data_dirs or {}
        self.on_phase_change = on_phase_change

        # 워커 인스턴스
        self._gemini = GeminiWorker()
        self._gpt = GPTWorker()
        self._claude = ClaudeWorker()

        # 상태 (갓생맘 Company 클래스의 상태 변수들에서 영감)
        self.phase_index = 0
        self.phase_name = PIPELINE_PHASES[0]
        self.running = False
        self.completed = False
        self.log: list[dict] = []

        # 각 단계 결과
        self.results = {
            "phase1_ideation": "",
            "phase2_evaluation": "",
            "phase3_critique": "",
        }

        # 보고서 빌더
        self._report_builder = ReportBuilder()

    # ── 메인 실행 ────────────────────────────────────────────

    async def run(self, topic: str, dataset_info: str) -> dict:
        """
        전체 파이프라인을 실행합니다.

        Args:
            topic: 분석 주제 (예: "교통사고 예측")
            dataset_info: AIHub에서 가져온 데이터셋 설명

        Returns:
            최종 결과 딕셔너리
        """
        self.running = True
        start_time = datetime.now()

        console.print(
            Panel.fit(
                f"[bold cyan]🚀 AI 오케스트레이터 시작[/bold cyan]\n"
                f"주제: [yellow]{topic}[/yellow]\n"
                f"시작 시각: {start_time.strftime('%H:%M:%S')}",
                border_style="cyan",
            )
        )

        try:
            # ① 브라우저 실행
            await self._launch_all_browsers()

            # ② Phase 1: Gemini 기획
            self._set_phase(2)
            prompt1 = make_phase1_ideation(dataset_info)
            self.results["phase1_ideation"] = await self._run_phase(
                worker=self._gemini,
                phase_label="Phase 1 — Gemini 아이디어 기획",
                prompt=prompt1,
            )

            # ③ Phase 2: GPT 평가
            self._set_phase(3)
            prompt2 = make_phase2_evaluation(dataset_info, self.results["phase1_ideation"])
            self.results["phase2_evaluation"] = await self._run_phase(
                worker=self._gpt,
                phase_label="Phase 2 — GPT 기술/시장 평가",
                prompt=prompt2,
            )

            # ④ Phase 3: Claude 검증
            self._set_phase(4)
            prompt3 = make_phase3_critique(
                dataset_info,
                self.results["phase1_ideation"],
                self.results["phase2_evaluation"],
            )
            self.results["phase3_critique"] = await self._run_phase(
                worker=self._claude,
                phase_label="Phase 3 — Claude 리스크 검토",
                prompt=prompt3,
            )

            # ⑤ Phase 4: 보고서 생성
            self._set_phase(5)
            report = await self._build_report(topic, dataset_info, start_time)

            self._set_phase(6)
            self.completed = True
            self.running = False

            self._print_summary(report)
            return report

        except Exception as e:
            console.print(f"\n[red]❌ 파이프라인 오류: {e}[/red]")
            raise
        finally:
            from config import BROWSER_CONFIG
            if BROWSER_CONFIG.get("keep_open", True):
                console.print("\n[cyan]🌐 파이프라인이 완료되었습니다. 브라우저는 열린 상태로 유지됩니다.[/cyan]")
                console.print("[dim]   브라우저를 닫으려면 Enter 키를 누르세요...[/dim]")
                try:
                    await asyncio.to_thread(input)
                except (EOFError, OSError):
                    pass
            await self._close_all_browsers()

    # ── 페이즈 관리 ──────────────────────────────────────────

    def _set_phase(self, index: int):
        """페이즈를 변경하고 콜백을 호출합니다 (갓생맘 phaseIndex와 동일한 컨셉)."""
        self.phase_index = index
        self.phase_name = PIPELINE_PHASES[index]
        self._push_log(f"📍 {self.phase_name} 시작")
        if self.on_phase_change:
            self.on_phase_change(index, self.phase_name)
        console.rule(f"[bold]{PIPELINE_PHASES[index]}[/bold]")

    def _push_log(self, message: str):
        """로그를 기록합니다 (갓생맘 pushLog와 동일한 컨셉)."""
        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message,
        }
        self.log.append(entry)
        console.print(f"  [dim]{entry['time']}[/dim]  {message}")

    # ── 브라우저 생명주기 ────────────────────────────────────

    async def _launch_all_browsers(self):
        """3개 브라우저를 순차로 실행합니다."""
        self._set_phase(1)

        workers_info = [
            (self._gemini, self.user_data_dirs.get("gemini")),
            (self._gpt, self.user_data_dirs.get("gpt")),
            (self._claude, self.user_data_dirs.get("claude")),
        ]

        for worker, udd in workers_info:
            await worker.launch(user_data_dir=udd)
            logged_in = await worker.is_logged_in()
            if not logged_in:
                console.print(
                    f"\n[yellow]⚠️  {worker.name} 로그인이 필요합니다.[/yellow]\n"
                    f"   브라우저 창에서 로그인 후 Enter를 눌러주세요..."
                )
                try:
                    await asyncio.to_thread(input)
                except (EOFError, OSError):
                    pass
            self._push_log(f"{worker.emoji} {worker.name} 준비 완료")

    async def _close_all_browsers(self):
        """3개 브라우저를 모두 닫습니다."""
        for worker in [self._gemini, self._gpt, self._claude]:
            try:
                await worker.close()
            except Exception:
                pass

    # ── 단계별 실행 ──────────────────────────────────────────

    async def _run_phase(self, worker, phase_label: str, prompt: str) -> str:
        """단일 AI에게 프롬프트를 전송하고 응답을 받습니다."""
        self._push_log(f"{worker.emoji} {phase_label} 실행 중...")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"  {worker.name} 응답 대기 중...", total=None)
            response = await worker.chat(prompt)
            progress.stop_task(task)

        self._push_log(f"✅ {worker.name} 응답 수집 완료 ({len(response)}자)")
        return response

    async def _build_report(self, topic: str, dataset_info: str, start_time: datetime) -> dict:
        """최종 통합 보고서를 생성하고 파일로 저장합니다."""
        self._push_log("📄 최종 보고서 생성 중...")

        report = self._report_builder.build(
            topic=topic,
            dataset_info=dataset_info,
            phase1=self.results["phase1_ideation"],
            phase2=self.results["phase2_evaluation"],
            phase3=self.results["phase3_critique"],
            log=self.log,
            start_time=start_time,
        )

        # 파일 저장
        output_dir = Path(PROJECT["report_dir"])
        output_dir.mkdir(exist_ok=True)

        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        safe_topic = topic.replace(" ", "_").replace("/", "-")[:30]

        # JSON (원본 데이터)
        json_path = output_dir / f"{timestamp}_{safe_topic}.json"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        # Markdown (읽기 쉬운 보고서)
        md_path = output_dir / f"{timestamp}_{safe_topic}.md"
        md_path.write_text(report["markdown"], encoding="utf-8")

        self._push_log(f"💾 보고서 저장: {md_path}")
        return report

    # ── 요약 출력 ────────────────────────────────────────────

    def _print_summary(self, report: dict):
        """파이프라인 완료 요약을 출력합니다."""
        table = Table(title="🎀 파이프라인 완료 요약", border_style="cyan")
        table.add_column("단계", style="bold")
        table.add_column("AI", style="cyan")
        table.add_column("결과 분량", justify="right")

        table.add_row("Phase 1", "✨ Gemini", f"{len(self.results['phase1_ideation']):,}자")
        table.add_row("Phase 2", "🔍 GPT", f"{len(self.results['phase2_evaluation']):,}자")
        table.add_row("Phase 3", "🛡️ Claude", f"{len(self.results['phase3_critique']):,}자")

        console.print(table)
        console.print(f"\n[green]✅ 보고서가 [bold]{PROJECT['report_dir']}/[/bold] 폴더에 저장됐습니다.[/green]")
