# 🤖 APA Testing Agent — Hermes-Inspired Autonomous Testing

> **Microsoft AI Hackathon**
> Built as part of the Microsoft-organized AI Hackathon at Asian Paints.
>  This project showcases Agentic Process Automation (APA) — a Pro Code + Low Code hybrid approach combining Python backend automation with Microsoft Copilot Studio.

---

## 📌 What Is This?

An **autonomous testing agent** that:
- Logs into **any web application** (you provide URL + credentials via chat)
- **Discovers** all pages, buttons, forms, tables, and inputs automatically
- **Generates 40+ test cases** across 9 categories
- **Executes** all tests in a headless browser (non-intrusive — you can keep working)
- **Learns** from past sessions — remembers selectors, prioritizes failed tests, detects regressions
- **Self-heals** — retries failed tests with longer waits
- **Analyzes results using GPT-5.2** — root cause analysis, recommendations, new test suggestions
- **Reports** via a professional HTML dashboard with charts, animations, and filters
- **All controlled from a chat interface** in Microsoft Copilot Studio

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│              Microsoft Copilot Studio                │
│         (Low Code — 7 Chat Topics)                   │
│   Run Tests │ Test New App │ Check Status │ Results  │
│   Show Memory │ LLM Analysis │ Full Dashboard       │
└────────────────────┬────────────────────────────────┘
                     │ HTTPS (Dev Tunnels)
                     ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Server (server.py)              │
│              Port 8000 / Uvicorn                     │
│              14 REST Endpoints                       │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              Agent Core (brain.py)                   │
│          Hermes Loop: 6 Phases                       │
│   RECALL → PERCEIVE → PLAN → ACT → ADAPT → REPORT  │
│                                                      │
│   Executor │ Planner │ Validator │ Memory │ Reporter │
└────────┬───────────────────────────────┬────────────┘
         │                               │
         ▼                               ▼
┌─────────────────┐           ┌────────────────────┐
│   Playwright    │           │  Azure OpenAI      │
│   (Chromium)    │           │  GPT-5.2           │
│   Headless      │           │  Analysis + Insights│
└─────────────────┘           └────────────────────┘
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.10+** | Core programming language |
| **FastAPI** | REST API server (14 endpoints) |
| **Uvicorn** | ASGI server to run FastAPI |
| **Playwright** | Browser automation (Chromium, headless) |
| **Azure OpenAI GPT-5.2** | LLM-powered test analysis |
| **Microsoft Copilot Studio** | Low-code conversational interface |
| **VS Code Dev Tunnels** | Expose local server to internet |
| **requests** | HTTP client for Azure OpenAI API |

---

## 📁 Project Structure

```
apa-testing-agent/
│
├── main.py                  # Entry point — launches browser + runs Brain
├── server.py                # FastAPI server — 14 REST endpoints
├── config.py                # Configuration — URLs, credentials, LLM keys, selectors
│
├── agent/
│   ├── __init__.py          # Required — makes agent/ a Python package
│   ├── brain.py             # Orchestrator — 6-phase Hermes loop
│   ├── executor.py          # Browser automation — login, click, fill, screenshot
│   ├── planner.py           # Page discovery + test case generation
│   ├── validator.py         # Login validation — URL, element, form checks
│   ├── memory.py            # Persistent learning — selectors, skills, failures
│   ├── reporter.py          # HTML dashboard + JSON report generation
│   └── llm.py               # Azure OpenAI GPT-5.2 integration
│
├── utils/
│   ├── __init__.py          # Required — makes utils/ a Python package
│   ├── browser.py           # Playwright browser launch/close
│   └── logger.py            # Logging utility
│
├── reports/                 # Auto-generated — leave empty
│   ├── test_report.html     # HTML dashboard (created after first run)
│   ├── test_report.json     # Structured test results
│   └── agent_memory.json    # Persistent agent memory
│
├── screenshots/             # Auto-generated — leave empty
│   └── *.png                # Screenshots of pages + failures
│
└── requirements.txt         # Python dependencies
```

> ⚠️ `reports/` and `screenshots/` are **auto-generated**. Leave them empty. The agent creates all files inside them when you run tests.

---

## ✨ Features

### Core Features
- **Dynamic Website Testing** — Test any web app by providing URL + credentials via chat
- **42 Autonomous Test Cases** — Auto-generated across 9 categories
- **Session-Based Learning** — Remembers selectors, skills, and failures across sessions
- **Self-Healing Retries** — Failed tests auto-retry with longer waits
- **LLM-Powered Analysis** — GPT-5.2 provides root cause analysis + recommendations
- **Professional HTML Dashboard** — Charts, progress ring, typing effect, filters

### Bonus Features (Hackathon)
- **Non-Intrusive** — Headless browser + async background execution. User can keep working.
- **Learning Skills** — Agent memory persists across 26+ sessions. Gets smarter over time.
- **Copilot Studio Integration** — Full chat-based control. No terminal needed.

---

## 🔄 Hermes-Inspired Agent Loop

The agent follows a 6-phase loop inspired by the Hermes autonomous agent architecture:

### Phase 1: RECALL
Loads memory from past sessions — previously learned CSS selectors, skills, failure history. If a test failed last session, it's marked as HIGH priority.

### Phase 2: PERCEIVE
Navigates to the login page, fills credentials, submits the form. After login, discovers all navigation links, visits each page, and catalogs every button, form, table, and input field found.

### Phase 3: PLAN
Generates test cases dynamically based on discovered pages and elements. Reorders tests so previously failed tests run first. Produces 40+ tests across 9 categories.

### Phase 4: ACT
Executes all tests sequentially in a headless Chromium browser. If a test fails, the agent automatically retries with a longer wait (self-healing). Takes screenshots of failures.

### Phase 5: ADAPT
Invokes GPT-5.2 to analyze all results. Detects patterns (multiple nav failures → app issue). Compares with past sessions to identify regressions and improvements. Learns new skills.

### Phase 6: REPORT
Generates a professional HTML dashboard with animated progress ring, charts, color-coded test rows, LLM analysis with typing effect, and agent memory visualization. Also generates a structured JSON report.

---

## 📋 Prerequisites

- Python 3.10 or higher
- VS Code (for Dev Tunnels)
- Microsoft Copilot Studio account
- Azure OpenAI endpoint + API key (for LLM features)

---

## 🚀 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/apa-testing-agent.git
cd apa-testing-agent
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install fastapi uvicorn playwright requests
playwright install chromium
```

### Step 4: Create Empty Folders

```bash
mkdir reports
mkdir screenshots
```

### Step 5: Create `__init__.py` Files (if not present)

```bash
# Windows
echo. > agent/__init__.py
echo. > utils/__init__.py

# Mac/Linux
touch agent/__init__.py
touch utils/__init__.py
```

---

## ⚙️ Configuration

Edit `config.py` with your details:

```python
# ============ TARGET APPLICATION ============
# Default app (used when no credentials passed via chat)
APP_URL = "https://your-app.com/login"
USERNAME = "your_username"
PASSWORD = "your_password"
ALLOWED_DOMAIN = "your-app.com"

# ============ AZURE OPENAI (LLM) ============
LLM_ENDPOINT = "https://your-resource.openai.azure.com/openai/deployments/your-model/chat/completions?api-version=2025-04-01-preview"
LLM_API_KEY = "your-api-key-here"

# ============ BROWSER ============
HEADLESS = True          # True = invisible browser, False = visible
SCREENSHOT_DIR = "screenshots"

# ============ DISCOVERY ============
MAX_PAGES = 10           # Max pages to discover

# ============ LOGIN SELECTORS ============
# Generic selectors that work with most login pages
LOGIN_SELECTORS = {
    "username": [
        'input[type="text"]',
        'input[type="email"]',
        'input[name="username"]',
        'input[name="email"]',
        '#username',
        '#email',
    ],
    "password": [
        'input[type="password"]',
        'input[name="password"]',
        '#password',
    ],
    "submit": [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Login")',
        'button:has-text("Sign in")',
        'button:has-text("Log in")',
    ]
}

# ============ NAVIGATION ============
NAV_SELECTORS = [
    "nav a",
    "aside a",
    ".sidebar a",
    ".menu a",
    ".nav-link",
]

SKIP_KEYWORDS = ["logout", "log out", "sign out", "javascript:", "mailto:", "#"]
```

---

## ▶️ Running the Project

### Option A: FastAPI Server (for Copilot Studio)

```bash
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

Server starts at `http://localhost:8000`. Test it:
```bash
curl http://localhost:8000/
```

### Option B: Direct Run (terminal only)

```bash
python main.py
```

Runs the full agent loop — login, discover, plan, test, analyze, report. Results saved to `reports/`.

### Option C: Trigger via API

```bash
# Test default app (from config.py)
curl -X POST http://localhost:8000/run-tests -H "Content-Type: application/json" -d "{}"

# Test a new app (dynamic)
curl -X POST http://localhost:8000/run-tests -H "Content-Type: application/json" -d "{\"url\": \"https://app.com/login\", \"username\": \"admin\", \"password\": \"pass123\"}"
```

---

## 🌐 VS Code Dev Tunnels Setup

Dev Tunnels expose your local FastAPI server to the internet so Copilot Studio can reach it.

### Step 1: Start FastAPI Server

```bash
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

### Step 2: Open Ports Panel

In VS Code → bottom panel → click **"PORTS"** tab.

### Step 3: Forward Port

Click **"Forward a Port"** → enter `8000` → press Enter.

### Step 4: Make It Public

Right-click the forwarded port → **"Port Visibility"** → **"Public"**.

### Step 5: Copy the URL

You'll get a URL like:
```
https://5qtsj1tn-8000.inc1.devtunnels.ms
```

This is your **public URL**. Use this in Copilot Studio HTTP nodes instead of `http://localhost:8000`.

### Step 6: Test It

Open in browser:
```
https://5qtsj1tn-8000.inc1.devtunnels.ms/
```

Should show the API home response with all endpoints listed.

> ⚠️ **Important:**
> - Dev Tunnel URL changes every time you restart VS Code
> - You must update Copilot Studio HTTP nodes if the URL changes
> - Server must be running for the tunnel to work
> - If you get 401 error, ensure port visibility is set to **Public**

---

## 💬 Copilot Studio Setup

### Prerequisites
- Microsoft Copilot Studio account (https://copilotstudio.microsoft.com)
- Dev Tunnel URL ready

### Create a New Agent
1. Go to Copilot Studio → **"Create"** → **"New agent"**
2. Name: **"APA Testing Agent"**
3. Description: "Hermes-inspired autonomous testing agent"

### Topic 1: Run Tests (Default)

**Purpose:** Runs tests on the default application (from config.py).

1. **Topics** → **"+ Add a topic"** → **"From blank"**
2. Name: `Run Tests`
3. **Trigger phrases:**
   ```
   Run tests
   Start testing
   Execute tests
   Begin tests
   ```
4. Add **message node:** `🚀 Starting tests on default application...`
5. Add **HTTP node:**
   - URI: `https://YOUR-DEVTUNNEL-URL/run-tests`
   - Method: `POST`
   - Headers: `Content-Type` : `application/json`
   - Body: `{}`
6. **Response schema** (click "Get schema from sample JSON"):
   ```json
   {
     "message": "Agent started testing",
     "status": "running",
     "check_status": "/status",
     "get_results": "/results"
   }
   ```
7. Save response as: `runResponse`
8. Add **message node:** `✅ {runResponse.message}. Say 'Check status' to monitor progress.`
9. **Save**

### Topic 2: Test New App (Dynamic)

**Purpose:** Tests any website — user provides URL, username, password via chat.

1. Create new topic: `Test New App`
2. **Trigger phrases:**
   ```
   Test new app
   Test another website
   Test a website
   Test new website
   ```
3. Add **Question node 1:**
   - Text: `🌐 Enter the login URL of the application to test:`
   - Identify: **User's entire response**
   - Save as: `loginUrl`
4. Add **Question node 2:**
   - Text: `👤 Enter the username:`
   - Identify: **User's entire response**
   - Save as: `loginUsername`
5. Add **Question node 3:**
   - Text: `🔑 Enter the password:`
   - Identify: **User's entire response**
   - Save as: `loginPassword`
6. Add **HTTP node:**
   - URI: `https://YOUR-DEVTUNNEL-URL/run-tests`
   - Method: `POST`
   - Headers: `Content-Type` : `application/json`
   - Body (use {x} variables):
     ```json
     {"url": "{loginUrl}", "username": "{loginUsername}", "password": "{loginPassword}"}
     ```
7. **Response schema:**
   ```json
   {
     "message": "Agent started testing: https://example.com/login",
     "status": "running"
   }
   ```
8. Save response as: `testResponse`
9. Add **message node:** `🚀 Agent started! Testing: {loginUrl}. Say 'Check status' to monitor.`
10. **Save**

### Topic 3: Check Status

**Purpose:** Shows real-time progress of running tests.

1. Create new topic: `Check Status`
2. **Trigger phrases:**
   ```
   Check status
   What's the progress
   Is it done
   Status update
   ```
3. Add **HTTP node:**
   - URI: `https://YOUR-DEVTUNNEL-URL/status/detailed`
   - Method: `GET`
4. **Response schema:**
   ```json
   {
     "status": "completed",
     "progress": "All tests completed",
     "message": "All tests completed!"
   }
   ```
5. Save response as: `statusData`
6. Add **message node:**
   ```
   📊 Agent Status: {statusData.status}
   Progress: {statusData.progress}
   {statusData.message}
   ```
7. **Save**

### Topic 4: Show Results

**Purpose:** Shows test results with category breakdown.

1. Create new topic: `Show Results`
2. **Trigger phrases:**
   ```
   Show results
   Test results
   What were the results
   How did it go
   ```
3. Add **HTTP node:**
   - URI: `https://YOUR-DEVTUNNEL-URL/results/details`
   - Method: `GET`
4. **Response schema:**
   ```json
   {
     "total": 42,
     "categories": [{"category": "Login", "pass": 5, "fail": 0, "skip": 0}],
     "failed_tests": [],
     "report_link": "http://localhost:8000/report"
   }
   ```
5. Save response as: `resultData`
6. Add **message node:** `📊 Total Tests: {resultData.total}`
7. **Save**

### Topic 5: Show Memory

**Purpose:** Shows what the agent has learned across sessions.

1. Create new topic: `Show Memory`
2. **Trigger phrases:**
   ```
   Show memory
   Agent memory
   What did you learn
   What do you remember
   ```
3. Add **HTTP node:**
   - URI: `https://YOUR-DEVTUNNEL-URL/memory/details`
   - Method: `GET`
4. **Response schema:**
   ```json
   {
     "sessions": 26,
     "total_skills": 17,
     "total_selectors": 3,
     "total_pages": 4,
     "skills_text": "- login (used 26x)",
     "selectors_text": "- username: input[type=text]",
     "pages_text": "- Dashboard: https://..."
   }
   ```
5. Save response as: `memoryData`
6. Add **message node:**
   ```
   🧠 Agent Memory:
   Sessions: {memoryData.sessions}
   Skills: {memoryData.total_skills}
   Selectors: {memoryData.total_selectors}
   Pages: {memoryData.total_pages}
   ```
7. **Save**

### Topic 6: LLM Analysis

**Purpose:** Shows GPT-5.2 analysis of test results.

1. Create new topic: `LLM Analysis`
2. **Trigger phrases:**
   ```
   Analyze results
   LLM analysis
   Why did tests fail
   Give me insights
   ```
3. Add **message node:** `🧠 Running LLM analysis on test results...`
4. Add **HTTP node:**
   - URI: `https://YOUR-DEVTUNNEL-URL/analyze`
   - Method: `GET`
   - Timeout: `60000`
5. **Response schema:**
   ```json
   {
     "analysis": "All 42 tests passed. Recommend adding negative test cases."
   }
   ```
6. Save response as: `analysisData`
7. Add **message node:** `🧠 LLM Analysis (GPT-5.2): {analysisData.analysis}`
8. **Save**

---

## 🎮 Demo Flow

Open Copilot Studio → **"Test your agent"** panel (top right):

```
You: "Run tests"
Bot: "🚀 Starting tests on default application..."
Bot: "✅ Agent started testing. Say 'Check status' to monitor."

(wait 2-3 minutes)

You: "Check status"
Bot: "📊 Agent Status: completed. All tests completed!"

You: "Show results"
Bot: "📊 Total Tests: 42. Passed: 42. Failed: 0."

You: "Analyze results"
Bot: "🧠 LLM Analysis: All 42 tests passed. Application health excellent..."

You: "Show memory"
Bot: "🧠 Sessions: 26, Skills: 17, Selectors: 3, Pages: 4"
```

### Testing a New App:

```
You: "Test new app"
Bot: "🌐 Enter the login URL:"
You: "https://practice.expandtesting.com/login"
Bot: "👤 Enter the username:"
You: "practice"
Bot: "🔑 Enter the password:"
You: "SuperSecretPassword!"
Bot: "🚀 Agent started! Testing: https://practice.expandtesting.com/login"
```

---

## 📊 HTML Dashboard

After running tests, open the dashboard:

```bash
# Via browser
http://localhost:8000/report

# Or directly
start reports/test_report.html    # Windows
open reports/test_report.html     # Mac
```

### Dashboard Features:
- 🟢 **App Health Indicator** — EXCELLENT / GOOD / WARNING / CRITICAL
- 🔵 **Animated Circular Progress Ring** — Fills up to pass rate with glow
- 📊 **Doughnut Chart** — Pass / Fail / Skip distribution
- 📊 **Bar Chart** — Category breakdown (stacked pass/fail)
- 📋 **Color-Coded Test Table** — Each category has unique border color
- 🔍 **Filter Buttons** — Click to show All / Passed / Failed
- ⌨️ **LLM Typing Effect** — Analysis types itself letter by letter
- 🎯 **Skill Chips** — Shows learned skills with usage count
- 🔍 **Selector Memory** — Shows remembered CSS selectors
- 🌐 **Known Pages** — Shows discovered pages

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API info + endpoint list |
| `POST` | `/run-tests` | Start tests (accepts url, username, password) |
| `POST` | `/run-tests-sync` | Synchronous version |
| `GET` | `/status` | Basic status |
| `GET` | `/status/detailed` | Status + progress + LLM analysis |
| `GET` | `/results` | Full test results |
| `GET` | `/results/summary` | Summary only |
| `GET` | `/results/details` | Category breakdown |
| `GET` | `/report` | Serves HTML dashboard |
| `GET` | `/memory` | Raw memory JSON |
| `GET` | `/memory/details` | Formatted memory |
| `GET` | `/analyze` | LLM analysis (GPT-5.2) |
| `GET` | `/dashboard` | Full dashboard data |
| `POST` | `/reset` | Reset agent state |
| `POST` | `/stop` | Stop running agent |

---

## 🧪 Test Categories

| # | Category | Tests | What It Checks |
|---|---|---|---|
| 1 | **Login** | 5 | Page load, valid login, username/password/submit field exists |
| 2 | **Navigation** | 12 | Each page loads, has title, no console errors |
| 3 | **Button** | 2 | Buttons are visible and clickable |
| 4 | **Input** | 1 | Input fields accept text |
| 5 | **CrossNav** | 3 | Navigation between pages works |
| 6 | **Structure** | 4 | Pages are not blank, have content |
| 7 | **DeepFunctional** | 13 | Search, sort, filter, form submit, error handling, back nav, reload |
| 8 | **Logout** | 1 | Logout redirects to login page |
| 9 | **Table** | 1 | Tables have data rows |

> Test count varies based on how many pages / buttons / forms the agent discovers.

---

## 🧠 LLM Integration

### How It Works

After all tests complete (Phase 5: ADAPT), the agent sends results + memory to Azure OpenAI GPT-5.2:

```python
# agent/llm.py
prompt = f"""
You are a senior QA analyst. Analyze these test results:
Total: {total}, Passed: {passed}, Failed: {failed}
Session: {session}, Skills: {skills}

Results: {results_summary}

Provide:
1. Root cause analysis for any failures
2. Whether failures are real bugs or test issues
3. Recommendations for the dev team
4. 3 new test cases to add
"""
```

### Connection Details
- **Endpoint:** Azure Cognitive Services (OpenAI)
- **Model:** GPT-5.2 (2025-04-01-preview)
- **Library:** `requests` (not `openai` SDK — Zscaler proxy incompatibility)
- **SSL:** `verify=False` (corporate proxy environment)

---

## 🔧 Troubleshooting

| Issue | Solution |
|---|---|
| **401 on Dev Tunnel URL** | Right-click port → Port Visibility → **Public** |
| **422 on /run-tests** | Send `Content-Type: application/json` header + valid JSON body |
| **`openai` SDK proxy error** | Don't use `openai` SDK. Use `requests` library with `verify=False` |
| **ModuleNotFoundError** | Ensure `__init__.py` exists in `agent/` and `utils/` folders |
| **Playwright browser not found** | Run `playwright install chromium` |
| **Login fails on new app** | Check credentials are correct. Check if selectors in config.py match the login page |
| **LLM analysis fails** | Verify `LLM_ENDPOINT` and `LLM_API_KEY` in config.py |
| **Dev Tunnel URL changed** | Update all HTTP node URIs in Copilot Studio topics |
| **`reports/` folder missing** | Create it: `mkdir reports` — or just run `python main.py` |

---

## 🚀 Future Improvements

1. **LLM Generates New Test Cases** — Test count grows session over session
2. **Intelligent Retry Strategy** — LLM decides retry approach per failure type
3. **Bug vs Test Issue Classification** — LLM classifies each failure
4. **Session Trend Analysis** — LLM compares results across all past sessions
5. **Selector Suggestion** — LLM analyzes page HTML and suggests selectors when defaults fail
6. **Executive Summary** — LLM writes 3-line summary for stakeholders
7. **Continuous Monitoring** — Agent watches for code changes and auto-retests
8. **Email Reports** — Send results via email after each session

---

## 📜 Hackathon Requirements vs Implementation

| Requirement | Implementation | Status |
|---|---|---|
| Test-case generating agent | Planner auto-generates 42 tests | ✅ |
| Automatic testing agent | Executor runs all tests autonomously | ✅ |
| Non-SAP applications | Weatherseal 360 + any dynamic URL | ✅ |
| Showcase APA capabilities | Full Hermes loop with 6 phases | ✅ |
| Uses tools/frameworks | Playwright + FastAPI + Azure OpenAI + Copilot Studio | ✅ |
| Automate on laptop | Runs locally, headless browser | ✅ |
| Learning skills (bonus) | 26+ sessions, persistent memory | ✅ 🏆 |
| Non-intrusive (bonus) | Headless + async background task | ✅ 🏆 |
| At least 20-30 tests | 42 test cases | ✅ |
| Web-browser interaction | Playwright — click, fill, navigate, screenshot | ✅ |
| Assess pass/fail | Validator checks URL, elements, content, errors | ✅ |
| Autonomous + comprehensive | Zero human intervention after trigger | ✅ |
| Provide results | JSON + HTML + Chat + LLM analysis | ✅ |

---


