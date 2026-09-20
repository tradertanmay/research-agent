# Autonomous Deep Research Agent

> An autonomous, local-first research agent designed for in-depth topic investigation, academic synthesis, document cross-referencing, and evidence-grounded report generation.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Local First](https://img.shields.io/badge/Inference-100%25%20Local%20Ollama-orange.svg)](https://ollama.com)

---

## Key Features

- **100% Free & Local-First**: Run entirely on your machine with **Ollama** (`llama3.2`, `deepseek-r1`, `qwen2.5:7b`, `llama3.1`, etc.). No mandatory API keys, no subscription costs, and your data never leaves your computer.
- **Multi-Source Evidence Discovery**: Automatically plans search queries and gathers peer-reviewed preprints (**arXiv**), real-time web articles (**DuckDuckGo**), and encyclopedic context (**Wikipedia**).
- **Local PDF & Document Analysis**: Upload local research documents (`.pdf`, `.txt`, `.md`) to be parsed, analyzed, and cross-referenced with live web and arXiv papers.
- **Intelligent Web Crawler**: Strips advertisements, cookie banners, navigation links, and HTML boilerplate to extract clean, dense factual content.
- **Strict Citation Grounding**: Reports include inline numbered citations (`[1]`, `[2]`), comparative tables, key findings, bottlenecks, and a verified bibliography with clickable URLs.
- **Executive Professional Light Theme**: Academic-grade interface (styled like Nature, Perplexity, and Linear) with high-contrast typography, syntax highlighting, zero emojis, and real-time SSE progress streaming.
- **In-App Settings Modal**: Configure cloud AI keys (Gemini, OpenAI, Groq, OpenRouter) or custom local endpoints (LM Studio, vLLM) directly in the UI without editing Python code.
- **Interactive Q&A and Deep Dive**: Ask follow-up questions to clarify report findings, or trigger an autonomous incremental deep dive that recursively searches new evidence and appends to the report.
- **Privacy-Preserving Guest Sharing**: Safely share your research agent with teammates or friends over your local network or Cloudflare Tunnel — guests get a clean slate with zero access to your personal past history.
- **1-Click Export**: Copy clean Markdown, download `.md` files, or print/export professional publication-ready PDF reports.

---

## Prerequisites

Before installing, make sure you have:

### 1. Python 3.10 or higher
- Check version:
  ```bash
  python3 --version
  ```
- Install if needed:
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
  - Configure Google Gemini, OpenAI, Groq, or OpenRouter directly inside the Web UI Settings modal, or add keys to `.env`.

---

## Quick Start (1-Click Install)

### macOS & Linux

```bash
# 1. Clone the repository
git clone https://github.com/tradertanmay/research-agent.git
cd research-agent

# 2. Run the automated installer
./install.sh

# 3. Launch the research agent
./start.sh
```

Your browser will automatically open to `http://localhost:8080` ready to conduct research.

### Windows

```cmd
:: 1. Clone the repository
git clone https://github.com/tradertanmay/research-agent.git
cd research-agent

:: 2. Launch (automatically sets up environment on first run)
start.bat
```

---

## How to Use

### 1. Web Dashboard

1. Run `./start.sh` (or `python run.py web`).
2. Enter any research question or topic in the prompt box.
3. *(Optional)* **Attach Local Documents**: Drag and drop local papers or documents (`.pdf`, `.txt`, `.md`) into the attachment dropzone to include them in the research synthesis.
4. Select your **Research Depth**:
   - **Quick** (~1 min): Fast overview synthesized from 3–5 sources.
   - **Standard** (~2–4 min): Balanced technical report across 6–10 sources.
   - **Deep Dive**: Exhaustive technical analysis across academic & web indices.
5. Select your **Source Focus**:
   - **All Sources**: Blends web search, academic preprints, and Wikipedia.
   - **arXiv Papers**: Restricts research specifically to peer-reviewed academic papers.
   - **Web & News**: Prioritizes recent industry blogs, articles, and documentation.
6. Click **Start Research** to observe the real-time execution tracker formulate plans, discover sources, and stream the generated report live.
7. **Follow-Up & Deep Dive**:
   - **Ask Question**: Chat directly with the synthesized report to clarify findings.
   - **Deepen Search**: Trigger an autonomous incremental deep dive on a specific subtopic without re-running the entire search.
8. **Export**:
   - **Copy**: Copies clean Markdown to clipboard.
   - **Save .md**: Saves the report to your local disk.
   - **Print / PDF**: Opens a print-ready formatted layout for instant PDF export.

---

### 2. Command Line Interface (CLI Mode)

Run research directly in your terminal for automation and scripting:

```bash
# Standard research query
./start.sh cli "Breakthroughs in solid-state sodium battery chemistries"

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
+----------------+-----------+-------------------------------------------------+
| Component      | Status    | Details                                         |
+----------------+-----------+-------------------------------------------------+
| Python         | OK        | 3.12.x (>= 3.10 satisfied)                      |
| Ollama Service | Online    | 16 local models detected                        |
| Storage Vault  | Ready     | ./vault/reports                                 |
+----------------+-----------+-------------------------------------------------+
```
*(Note: Any installed Python version 3.10 or higher will pass with `Status: OK`)*

---

## Model Providers & API Keys

### Method 1: Local Ollama Models (100% Free & Auto-Discovered)
Any model you download with Ollama is **automatically detected and displayed** in the Web UI Engine dropdown:
```bash
ollama pull llama3.2          # Fast 3B model (Default, runs on any laptop)
ollama pull deepseek-r1:8b    # High-reasoning model for complex synthesis
ollama pull qwen2.5:14b       # Exceptional coding and technical accuracy
ollama pull mistral           # Reliable 7B generalist model
```
No config files to edit. Just pull the model, and it immediately appears in your dashboard.

### Method 2: In-App Settings Modal (Zero-Code Setup)
Click the **Settings** button in the top navigation bar of the Web UI:
1. Enter your API key for Google Gemini, OpenAI, Groq, or OpenRouter.
2. Click **Save Settings**.
3. The **Engine** dropdown immediately refreshes with your new models.
4. Keys are stored safely in your private `.env` file and are never committed to git.

### Method 3: Custom Local Endpoints (LM Studio, vLLM, LocalAI)
Connect any OpenAI-compatible local model server via the UI Settings modal or `.env`:
```env
CUSTOM_LLM_URL=http://localhost:1234/v1
CUSTOM_LLM_MODEL=llama-3.3-70b-instruct
CUSTOM_LLM_API_KEY=not-needed
```

---

## Sharing & Privacy (Guest Isolation)

You can share your running agent with colleagues over your local network or via a secure Cloudflare Tunnel (`./start.sh share`):

- **Zero-Password Friction**: Remote visitors connect instantly without PINs or logins.
- **Host Data Protection**:
  - Remote visitors are automatically restricted to **Guest Role**.
  - **Personal Research Vault**: The host's past research history is 100% hidden from visitors (visitors see a clean slate).
  - **Settings & API Keys**: The Settings modal is completely hidden from guests, and the `/api/settings/keys` endpoint rejects guest requests with `403 Forbidden`.
  - **Activity Audit Log**: The host's inquiry log is restricted to localhost (`403 Forbidden` for guests).
- **Inquiry Audit**: All queries and questions submitted by visitors are recorded locally to `vault/user_queries.md` with timestamps and visitor IP addresses.

---

## Repository Structure

```
research-agent/
|-- install.sh             # Automated installer for macOS / Linux
|-- start.sh               # 1-Click launcher for macOS / Linux
|-- start.bat              # 1-Click launcher for Windows
|-- run.py                 # Unified CLI, Web & Diagnostic entrypoint
|-- requirements.txt       # Core Python dependencies
|-- pyproject.toml         # Packaging metadata
|-- .env.example           # Environment template
|-- .gitignore             # Strict privacy & hygiene rules
|-- vault/                 # Local data storage (gitignored)
|   |-- reports/           # Saved research reports (.md)
|   |-- conversations/     # Follow-up Q&A chat sessions
|   |-- uploads/           # Uploaded local PDF & text documents
|   `-- user_queries.md    # Permanent inquiry activity log
|-- agent/
|   |-- core/              # Planner, Synthesizer & Master Agent
|   |-- llm/               # Ollama & OpenAI-compatible providers
|   |-- search/            # DuckDuckGo, arXiv, Wikipedia clients
|   |-- scraper/           # Async HTML crawler & text cleaner
|   |-- storage/           # Vault, document loader & PDF exporter
|   `-- web/               # FastAPI server & responsive UI
`-- tests/                 # Unit & integration test suite
```

---

## Running Tests

Run the automated test suite to verify search clients, document parsers, scrapers, and synthesis:

```bash
./start.sh test
```

---

## Contributing

Contributions, feature requests, and bug reports are welcome!
1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

---

## License

This project is licensed under the [MIT License](LICENSE).
