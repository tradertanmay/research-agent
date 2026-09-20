# ⚡ Autonomous Deep Research Agent

> An autonomous, local-first research agent designed for in-depth topic investigation, academic synthesis, and evidence-grounded report generation.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Local First](https://img.shields.io/badge/Inference-100%25%20Local%20Ollama-orange.svg)](https://ollama.com)

---

## 🌟 Key Features

- **100% Free & Local-First**: Run entirely on your own machine with **Ollama** (`llama3.2`, `deepseek-r1`, `qwen2.5:7b`, `llama3.1`, etc.). No mandatory API keys, no subscription costs, and your data never leaves your computer.
- **Multi-Source Evidence Discovery**: Automatically plans search queries and gathers peer-reviewed preprints (**arXiv**), real-time web articles (**DuckDuckGo**), and foundational encyclopedic context (**Wikipedia**).
- **Intelligent Web Crawler**: Strips advertisements, cookie banners, navigation links, and HTML boilerplate to extract clean, dense factual content.
- **Strict Citation Grounding**: Reports include inline numbered citations (`[1]`, `[2]`), comparative tables, key findings, bottlenecks, and a verified bibliography with clickable URLs.
- **Interactive Live Dashboard**: Modern dark-theme Web UI featuring real-time radar progress trackers, live Server-Sent Events (SSE), interactive Markdown reader, follow-up Q&A, and 1-click PDF/Markdown export.
- **Built-in Terminal CLI**: Full command-line interface for headless execution, automated scripts, and CI/CD pipelines.
- **Privacy-Preserving Guest Sharing**: Safely share your research agent with teammates or friends over your local network or Cloudflare Tunnel — guests get a clean slate with zero access to your personal past history.

---

## 📋 Prerequisites

Before installing, make sure you have:

### 1. Python 3.10 or higher
- **Check version**:
  ```bash
  python3 --version
  ```
- **Install if needed**:
  - **macOS**: `brew install python` or download from [python.org](https://www.python.org/downloads/)
  - **Linux (Ubuntu/Debian)**: `sudo apt update && sudo apt install python3 python3-venv python3-pip`
  - **Windows**: Download from [python.org](https://www.python.org/downloads/) *(Check "Add Python to PATH" during install)*

### 2. Model Provider (Choice of Free Local or Cloud)
- **Option A — Free Local LLM (Recommended)**:
  1. Download and install [Ollama](https://ollama.com).
  2. Pull a recommended model:
     ```bash
     ollama pull llama3.2       # Fast & lightweight (default)
     # OR
     ollama pull deepseek-r1    # Exceptional reasoning
     # OR
     ollama pull qwen2.5:7b     # High instruction accuracy
     ```
- **Option B — Cloud Models (Optional)**:
  - If you prefer cloud APIs, simply add your `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, or `ANTHROPIC_API_KEY` into `.env`.

---

## 🚀 Quick Start (1-Click Install)

### macOS & Linux

```bash
# 1. Clone the repository
git clone https://github.com/your-username/research-agent.git
cd research-agent

# 2. Run the automated installer
./install.sh

# 3. Launch the research agent
./start.sh
```

Your browser will automatically open to `http://127.0.0.1:8000` ready to conduct research!

### Windows

```cmd
:: 1. Clone the repository
git clone https://github.com/your-username/research-agent.git
cd research-agent

:: 2. Launch (automatically sets up environment on first run)
start.bat
```

---

## 🖥️ How to Use

### 1. Web Dashboard

1. Run `./start.sh` (or `python run.py web`).
2. Type any question, technology, or topic:
   - *e.g., "Advances in solid-state lithium battery chemistries and commercialization hurdles"*
   - *e.g., "Comparison of Rust vs Go for high-throughput distributed streaming"*
   - *e.g., "Mechanisms of CRISPR prime editing vs base editing"*
3. Select your **Research Depth**:
   - **⚡ Quick** (~1 min): Fast overview synthesized from 3–5 sources.
   - **🎯 Standard** (~2–4 min): Balanced technical report across 6–10 sources.
   - **🔬 Deep Dive**: Exhaustive technical analysis across academic & web indices.
4. Select your **Source Focus**:
   - **🌐 All Sources**: Blends web search, academic preprints, and Wikipedia.
   - **🎓 arXiv Papers**: Restricts research specifically to peer-reviewed academic papers.
   - **📰 Web & News**: Prioritizes recent industry blogs, articles, and documentation.
5. Click **Start Research** and watch the real-time planner formulate strategies, discover sources, and stream the generated report live.
6. **Follow-Up & Deepen**:
   - **💬 Ask Question**: Chat directly with the synthesized report to clarify findings.
   - **🔬 Deepen Search**: Trigger an autonomous incremental deep dive on a specific subtopic without re-running the entire search.
7. **Export**:
   - 📋 **Copy**: Copies clean Markdown to clipboard.
   - 💾 **Save .md**: Saves the report to your local disk.
   - 🖨️ **Export PDF**: Opens a print-ready formatted layout for instant PDF export.

---

### 2. Command Line Interface (CLI Mode)

Run research directly in your terminal for automation and scripting:

```bash
# Standard research query
./start.sh cli "Breakthroughs in room-temperature superconductors in 2026"

# Deep dive focused on arXiv academic papers
./start.sh cli "Transformer attention optimization techniques" --depth deep --focus academic

# Save output directly to a Markdown file
./start.sh cli "State of humanoid robotics" --output robotics_report.md

# Specify a custom Ollama model
./start.sh cli "Quantum key distribution protocols" --model deepseek-r1
```

---

### 3. System Diagnostics

Verify your Python environment, Ollama connectivity, and storage vault:

```bash
./start.sh check
```

Output:
```
                         System & LLM Environment Check                         
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component      ┃ Status    ┃ Details                                         ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Python         │ OK        │ 3.12.x                                          │
│ Ollama Service │ Online    │ 16 local models detected                        │
│ Storage Vault  │ Ready     │ ./vault/reports                                 │
└────────────────┴───────────┴─────────────────────────────────────────────────┘
```

---

## ⚙️ Configuration (`.env`)

Create a `.env` file (or copy `.env.example`) to customize settings:

```env
# Local Ollama Backend (Default)
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=auto

# Optional Cloud Providers
OPENAI_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=
ANTHROPIC_API_KEY=
OPENROUTER_API_KEY=

# Web Server Settings
HOST=127.0.0.1
PORT=8000
```

---

## 🔒 Sharing & Privacy (Guest Mode)

You can share your running agent with colleagues over your local Wi-Fi or a secure Cloudflare Tunnel (`./start.sh share`):

- **Zero-Friction Access**: No passwords or PIN codes required for visitors to start researching.
- **Total Privacy for the Host**:
  - Remote visitors are automatically scoped to **Guest Role**.
  - **Your personal past research history is 100% hidden** from remote visitors.
  - Your local Ollama model names are hidden from remote visitors.
  - The Activity Audit log is restricted to localhost (`403 Forbidden` for guests).
- **Inquiry Audit**:
  - All inquiries, questions, and topics asked by guests are logged locally to `vault/user_queries.md` with timestamps and visitor IPs.

---

## 📁 Repository Structure

```
research-agent/
├── install.sh             # Automated installer for macOS / Linux
├── start.sh               # 1-Click launcher for macOS / Linux
├── start.bat              # 1-Click launcher for Windows
├── run.py                 # Unified CLI, Web & Diagnostic entrypoint
├── requirements.txt       # Core Python dependencies
├── pyproject.toml         # Packaging metadata
├── .env.example           # Environment template
├── .gitignore             # Strict privacy & hygiene rules
├── vault/                 # Local data storage (gitignored)
│   ├── reports/           # Saved research reports (.md)
│   └── conversations/     # Follow-up Q&A chat sessions
├── agent/
│   ├── core/              # Planner, Synthesizer & Master Agent
│   ├── llm/               # Ollama & OpenAI-compatible providers
│   ├── search/            # DuckDuckGo, arXiv, Wikipedia clients
│   ├── scraper/           # Async HTML crawler & text cleaner
│   ├── storage/           # Vault, history index & PDF exporter
│   └── web/               # FastAPI server & responsive UI
└── tests/                 # Unit & integration test suite
```

---

## 🧪 Running Tests

Run the automated test suite to verify search clients, scrapers, and synthesis:

```bash
./start.sh test
```

---

## 🤝 Contributing

Contributions, feature requests, and bug reports are welcome!
1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
