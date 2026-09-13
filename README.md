# 🎀 AI Orchestrator

**$0 API Cost** — Automates Gemini, ChatGPT, and Claude web interfaces using Playwright browser automation to **plan (Proposer) → evaluate (Planner) → verify (Critique)** projects based on [AIHub](https://aihub.or.kr) public datasets.

---

## ⚡ Key Features

- 💰 **Zero API Cost**: Leverages browser automation via Playwright without requiring paid API keys, utilizing official web interfaces directly.
- 🌐 **AIHub Dataset Integration**: Automatically fetches relevant public datasets from AIHub, with support for manual input fallback.
- 🤖 **3-Phase Multi-AI Role Separation**:
  - ✨ **Gemini (Proposer)**: Brainstorms project ideas and conducts data research.
  - 🔍 **ChatGPT (Planner)**: Evaluates feasibility & builds structured PM frameworks.
  - 🛡️ **Claude (Critique)**: Analyzes logical, ethical, and legal risks as a Devil's Advocate.
- 📄 **Unified Reporting**: Automatically builds and exports comprehensive Markdown reports and raw JSON data to the `results/` directory.
- 📬 **External Integrations**: Supports automated publishing to Notion Databases and notifications via Discord Webhooks.

---

## 🧩 3-Phase Pipeline Architecture

```
 📌 AIHub Dataset Topic Input (Auto-fetch or Manual Input)
                       │
                       ▼
 ── Phase 1 ──────────────────────────────────────────
 ✨ Gemini (Proposer: Ideation & Research)
    └─ Generates 5 innovative project ideas based on dataset context
                       │
                       ▼
 ── Phase 2 ──────────────────────────────────────────
 🔍 ChatGPT (Planner: PM & Feasibility Evaluation)
    └─ Rates feasibility (1-10) & designs TOP 2 project PM frameworks
                       │
                       ▼
 ── Phase 3 ──────────────────────────────────────────
 🛡️ Claude (Critique: Risk Analysis & Verification)
    └─ Devil's Advocate critique on logical/ethical risks & final recommendation
                       │
                       ▼
 📄 Final Report Generation (results/YYYYMMDD_HHMMSS_topic.md / .json)
                       │ (Optional Integrations)
                       ├─ 📚 Publish to Notion Database
                       └─ 💬 Send Discord Webhook Notification
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.11+**
- Chrome / Chromium Browser (Installed automatically via Playwright)

### 2. Installation

```bash
# Clone the repository and navigate into the project
cd ai-orchestrator

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt

# Install Playwright Chromium browser
playwright install chromium
```

### 3. (Optional) Notion & Discord Integration Setup

```bash
cp .env.example .env
```
Fill in your **Notion Token**, **Database ID**, and **Discord Webhook URL** in the `.env` file. (If left blank, these steps will be automatically skipped).

---

## 💡 Usage

### 1. Interactive Mode

If no topic argument is provided, the CLI will prompt you interactively:

```bash
python main.py
```

### 2. Specify Topic via CLI

```bash
# Example: Traffic Accident Prediction
python main.py --topic "Traffic Accident Prediction"

# Example: Crop Pest Detection
python main.py --topic "Crop Pest Detection"
```

### 3. Custom Dataset File & Headless Mode

```bash
# Specify a custom dataset text file and run in headless mode
python main.py --topic "Medical Image Diagnosis" --dataset-file ./my_dataset.txt --headless

# Auto-close browsers upon completion
python main.py --topic "Autonomous Driving" --close-browsers
```

---

## 🔑 Persistent Login Sessions

On the initial run, browser windows for Gemini, ChatGPT, and Claude will open.  
Log in **once manually** in each browser window. Your login sessions will be saved in your user profile, enabling **automatic login state persistence** for future runs.

- **Profile Directory**: `~/.config/ai-orchestrator/`
  - `gemini/`
  - `gpt/`
  - `claude/`

---

## 🛠️ Utility & Debugging Tools

Use these scripts if UI elements change or to verify individual AI workers independently.

### Single Worker Test (`tools/test_worker.py`)
Test a single AI worker's response without running the full pipeline:

```bash
python tools/test_worker.py --ai gemini --prompt "Hello!"
python tools/test_worker.py --ai gpt
python tools/test_worker.py --ai claude --headless
```

### UI Selector Debugger (`tools/debug_selector.py`)
Inspect and debug CSS selector validity across AI web interfaces:

```bash
python tools/debug_selector.py --ai gemini
python tools/debug_selector.py --ai gpt
python tools/debug_selector.py --ai claude
```

---

## 📂 Project Structure

```
ai-orchestrator/
├── config.py              # Configuration for AI agents, phases, and browser settings
├── main.py                # CLI entry point
├── requirements.txt       # Dependencies list
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── aihub/
│   ├── __init__.py
│   └── fetcher.py         # AIHub public dataset crawler & parser
├── pipeline/
│   ├── __init__.py
│   ├── orchestrator.py    # Core 3-AI pipeline orchestrator & state manager
│   └── prompts.py         # Prompt templates for Proposer, Planner, and Critique
├── report/
│   ├── __init__.py
│   └── builder.py         # Report builder (Markdown/JSON) & Notion/Discord publisher
├── workers/               # Playwright browser automation workers
│   ├── __init__.py
│   ├── base_worker.py     # Base worker abstract class
│   ├── gemini_worker.py   # Gemini worker
│   ├── gpt_worker.py      # ChatGPT worker
│   └── claude_worker.py   # Claude worker
├── tools/                 # Utility & debugging scripts
│   ├── debug_selector.py  # Selector diagnostic tool
│   └── test_worker.py     # Single worker test script
└── results/               # Output reports (.md, .json) directory
```

---

## 🔒 Security & Disclaimers

- Do **NOT** commit your `.env` file to Git as it contains sensitive tokens and webhook URLs.
- This project is an automated tool developed for educational and research purposes. Please abide by the Terms of Service for each AI provider.
