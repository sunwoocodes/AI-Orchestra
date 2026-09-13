# ============================================================
#  AI 오케스트레이터 설정
#  갓생맘 AI OFFICE의 company.config.ts 컨셉을 Python으로 구현
# ============================================================
#  ⚠️ 규칙: 각 AI의 role·phase_order는 바꾸지 마세요.
#           파이프라인 엔진이 이 값으로 순서를 제어합니다.
#           바꿔도 되는 건: name, persona, color 입니다.
# ============================================================


# ── 프로젝트 기본 정보 ──────────────────────────────────────
PROJECT = {
    "name": "AI 오케스트레이터",
    "subtitle": "AIHub 데이터 기반 프로젝트 기획·검증 시스템",
    "version": "0.1.0",
    "report_dir": "results",
}

# ── AI 에이전트 설정 ────────────────────────────────────────
# role: 파이프라인 엔진 내부 식별자 (변경 금지)
# phase_order: 실행 순서 (1 → 2 → 3)
AI_AGENTS = [
    {
        "role": "ideation",      # 변경 금지
        "phase_order": 1,        # 변경 금지
        "name": "Gemini",
        "title": "아이디어 제시 및 리서치 (Proposer)",
        "persona": "구글 생태계와의 강력한 연동 및 방대한 컨텍스트 처리 능력을 바탕으로, 실시간 트렌드와 웹 데이터를 통해 신선하고 폭넓은 아이디어를 빠르게 발제합니다.",
        "color": "cyan",         # rich 라이브러리 색상
        "url": "https://gemini.google.com/app",
        "emoji": "✨",
    },
    {
        "role": "evaluation",    # 변경 금지
        "phase_order": 2,        # 변경 금지
        "name": "GPT",
        "title": "프로젝트 기획 및 구조화 (Planner)",
        "persona": "뛰어난 추론 능력과 범용성을 바탕으로 추상적인 개념을 구체적인 실행 계획(단계별 작업 분할, 마일스톤 설정, 프레임워크 구축)으로 변환하는 프로젝트 매니저(PM) 역할을 수행합니다.",
        "color": "green",
        "url": "https://chatgpt.com/",
        "emoji": "🔍",
    },
    {
        "role": "critique",      # 변경 금지
        "phase_order": 3,        # 변경 금지
        "name": "Claude",
        "title": "논리적 반박 및 리스크 검토 (Critique)",
        "persona": "미묘한 뉘앙스를 파악하고 윤리적·논리적 허점을 짚어내는 데 강점이 있어, 기획의 취약점을 찾아내고 대안을 요구하는 악마의 대변인(Devil's Advocate) 역할을 담당합니다.",
        "color": "magenta",
        "url": "https://claude.ai/new",
        "emoji": "🛡️",
    },
]

# ── 브라우저 설정 ───────────────────────────────────────────
BROWSER_CONFIG = {
    "headless": False,          # True = 완전 백그라운드, False = 창 보임
    "slow_mo": 80,              # 각 동작 사이 딜레이(ms) — 너무 빠르면 감지될 수 있음
    "timeout": 120_000,         # 응답 최대 대기 시간(ms): 2분
    "response_poll_interval": 2,  # 응답 완료 폴링 간격(초)
    "response_stable_count": 3,  # 이 횟수만큼 텍스트가 변하지 않으면 완료로 판단
    "keep_open": True,          # 작업 완료 후 브라우저 종료 여부 (True = 유지, False = 종료)
}

# ── 파이프라인 페이즈 설정 ──────────────────────────────────
# 갓생맘 AI OFFICE의 dayScript PHASES에서 영감을 받아 설계
PIPELINE_PHASES = [
    "대기",
    "AIHub 데이터셋 수집",
    "기획 — Gemini 아이디어 생성",
    "평가 — GPT 실현 가능성 분석",
    "검증 — Claude 리스크 검토",
    "보고서 통합 생성",
    "완료",
]

# ── AIHub 설정 ──────────────────────────────────────────────
AIHUB_CONFIG = {
    "base_url": "https://aihub.or.kr",
    "dataset_list_url": "https://aihub.or.kr/aihubdata/data/list.do",
    "max_datasets_per_search": 5,  # 한 번 검색에서 가져올 최대 데이터셋 수
}

# ── 보고서 연동 (갓생맘 worker/report.ts 컨셉 차용) ────────
# .env 파일에서 값을 불러옵니다. 비워두면 해당 연동은 건너뜁니다.
REPORT_INTEGRATIONS = {
    "notion": {
        "label": "Notion 저장",
        "env_key": "NOTION_TOKEN",
        "db_env_key": "NOTION_DATABASE_ID",
    },
    "discord": {
        "label": "Discord 전송",
        "env_key": "DISCORD_WEBHOOK_URL",
    },
}
