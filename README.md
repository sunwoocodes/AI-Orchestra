# 🎀 AI 오케스트레이터 (AI Orchestrator)

**API 비용 0원** — Gemini · ChatGPT · Claude의 웹 브라우저 인터페이스를 Playwright 자동화로 제어하여,  
[AIHub](https://aihub.or.kr) 공개 데이터셋 기반 프로젝트를 **기획(Proposer) → 평가(Planner) → 검증(Critique)**하는 멀티-AI 협업 오케스트레이션 시스템입니다.

---

## ⚡ 주요 특징

- 💰 **API 비용 0원**: 웹 브라우저 자동화(Playwright)를 활용해 별도의 API 키 결제 없이 각 AI 서비스의 최신 웹 인터페이스 이용.
- 🌐 **AIHub 데이터셋 연동**: 입력한 주제에 맞추어 AIHub 공개 데이터셋을 자동 수집하며, 크롤링 실패 시 직접 데이터셋 정보 입력 가능.
- 🤖 **3-Phase 멀티 AI 역할 분담**:
  - ✨ **Gemini (Proposer)**: 아이디어 발제 및 데이터 리서치
  - 🔍 **ChatGPT (Planner)**: 기술/시장 실현 가능성 분석 & PM 기획 프레임워크 구축
  - 🛡️ **Claude (Critique)**: 논리적·윤리적 허점 검토 & 악마의 대변인(Devil's Advocate)
- 📄 **통합 보고서 생성**: Markdown 기획서 및 원본 JSON 데이터를 `results/` 폴더에 자동 저장.
- 📬 **외부 서비스 연동**: Notion 데이터베이스 저장 및 Discord 웹훅 전송 지원.

---

## 🧩 3-Phase 파이프라인 워크플로우

```
 📌 AIHub 데이터셋 주제 입력 (자동 수집 또는 수동 입력)
                       │
                       ▼
 ── Phase 1 ──────────────────────────────────────────
 ✨ Gemini (Proposer: 아이디어 발제 및 리서치)
    └─ AIHub 데이터 기반 신선한 프로젝트 아이디어 5개 제시
                       │
                       ▼
 ── Phase 2 ──────────────────────────────────────────
 🔍 ChatGPT (Planner: 프로젝트 기획 및 구조화)
    └─ 아이디어별 실현 가능성(1~10점) 평가 & TOP 2 PM 기획 프레임워크 구축
                       │
                       ▼
 ── Phase 3 ──────────────────────────────────────────
 🛡️ Claude (Critique: 논리적 반박 및 리스크 검토)
    └─ 악마의 대변인 관점 논리/윤리/법적 리스크 검토 & 최종 대안 제시
                       │
                       ▼
 📄 최종 보고서 빌드 (results/YYYYMMDD_HHMMSS_주제.md / .json)
                       │ (선택 연동)
                       ├─ 📚 Notion 데이터베이스 저장
                       └─ 💬 Discord 웹훅 메시지 전송
```

---

## 🚀 시작하기

### 1. 전제 조건
- Python 3.11 이상
- Chrome / Chromium 브라우저 (Playwright 자동 설치 지원)

### 2. 의존성 설치

```bash
# 레포지토리 클론 후 이동
cd ai-orchestrator

# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# Playwright Chromium 브라우저 설치
playwright install chromium
```

### 3. (선택) Notion / Discord 연동 설정

```bash
cp .env.example .env
```
`.env` 파일에 발급받은 **Notion Token**, **Database ID**, **Discord Webhook URL**을 입력합니다. (미입력 시 연동 단계 자동 스킵)

---

## 💡 사용법

### 1. 기본 실행 (대화형 모드)

주제를 입력하지 않으면 대화형 인터페이스에서 주제를 묻습니다.

```bash
python main.py
```

### 2. 주제 직접 지정

```bash
# 교통사고 예측 주제로 진행
python main.py --topic "교통사고 예측"

# 농작물 병충해 탐지 주제로 진행
python main.py --topic "농작물 병충해 탐지"
```

### 3. 데이터셋 파일 지정 및 헤드리스(백그라운드) 실행

```bash
# 커스텀 데이터셋 텍스트 파일을 지정하고 브라우저를 백그라운드에서 실행
python main.py --topic "의료 영상 진단" --dataset-file ./my_dataset.txt --headless

# 작업 완료 후 브라우저 자동 종료
python main.py --topic "자율주행" --close-browsers
```

---

## 🔑 첫 실행 시 로그인 세션 유지

첫 실행 시 각 AI 서비스(Gemini, ChatGPT, Claude)의 브라우저 창이 열립니다.  
각 서비스에 **최초 1회 직접 로그인**하면 사용자 프로필에 로그인 세션이 저장되어 **다음 실행부터는 자동으로 로그인 상태가 유지**됩니다.

- **브라우저 프로필 저장 위치**: `~/.config/ai-orchestrator/`
  - `gemini/`
  - `gpt/`
  - `claude/`

---

## 🛠️ 유틸리티 & 디버깅 도구

UI 변경으로 셀렉터가 변경되었거나 단일 워커를 별도로 테스트하고 싶을 때 사용합니다.

### 단일 Worker 테스트 (`tools/test_worker.py`)
파이프라인 전체를 구동하지 않고 특정 AI 워커의 응답 및 동작을 검증합니다.

```bash
python tools/test_worker.py --ai gemini --prompt "안녕하세요!"
python tools/test_worker.py --ai gpt
python tools/test_worker.py --ai claude --headless
```

### UI 셀렉터 디버그 (`tools/debug_selector.py`)
AI 웹사이트의 CSS 셀렉터가 유효한지 탐색하고 결과를 표로 보여줍니다.

```bash
python tools/debug_selector.py --ai gemini
python tools/debug_selector.py --ai gpt
python tools/debug_selector.py --ai claude
```

---

## 📂 프로젝트 구조

```
ai-orchestrator/
├── config.py              # AI 에이전트, 페이즈, 브라우저 설정
├── main.py                # CLI 진입점
├── requirements.txt       # 의존성 패키지 목록
├── .env.example           # 환경 변수 예시 템플릿
├── .gitignore             # Git 제외 규칙
├── aihub/
│   ├── __init__.py
│   └── fetcher.py         # AIHub 공개 데이터셋 수집기 & 파서
├── pipeline/
│   ├── __init__.py
│   ├── orchestrator.py    # 3-AI 파이프라인 엔진 (상태 추적 및 페이즈 제어)
│   └── prompts.py         # 페이즈별 프롬프트 템플릿 (Proposer/Planner/Critique)
├── report/
│   ├── __init__.py
│   └── builder.py         # 통합 보고서 생성기 (Markdown/JSON) & Notion/Discord 연동
├── workers/               # Playwright 기반 브라우저 자동화 워커
│   ├── __init__.py
│   ├── base_worker.py     # 브라우저 워커 추상 클래스
│   ├── gemini_worker.py   # Gemini 워커
│   ├── gpt_worker.py      # ChatGPT 워커
│   └── claude_worker.py   # Claude 워커
├── tools/                 # 유틸리티 및 디버깅 스크립트
│   ├── debug_selector.py  # 셀렉터 디버그 도구
│   └── test_worker.py     # 단일 워커 테스트 스크립트
└── results/               # 생성된 기획 보고서 (.md, .json) 저장 디렉토리
```

---

## 🔒 보안 및 주의사항

- `.env` 파일에는 토큰 및 개인 웹훅 URL이 포함될 수 있으므로 **절대 Git에 커밋하지 마세요**.
- 본 프로젝트는 교육 및 연구 용도의 자동화 도구입니다. 각 AI 서비스의 서비스 이용 약관을 준수해 주세요.
