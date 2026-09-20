#!/usr/bin/env bash
# ==============================================================================
# Autonomous Research Agent - 1-Click Installer
# ==============================================================================

set -e

# Colors for terminal output
BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

echo -e "${BOLD}${BLUE}"
echo "========================================================"
echo "    Autonomous Research Agent - Easy Installer          "
echo "========================================================"
echo -e "${RESET}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Check Python
echo -e "${BLUE}▶ Checking Python installation...${RESET}"
PYTHON_BIN=""

# Prefer python3.12 or python3.11 if available, otherwise python3
for p in python3.12 python3.11 python3.10 python3; do
    if command -v "$p" >/dev/null 2>&1; then
        PYTHON_BIN="$p"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}❌ Error: Python 3.10+ is required but was not found.${RESET}"
    echo "Please install Python from https://www.python.org or via 'brew install python@3.12'."
    exit 1
fi

PY_VER=$($PYTHON_BIN --version)
echo -e "${GREEN}✓ Found ${PY_VER} (${PYTHON_BIN})${RESET}"

# 2. Setup Virtual Environment
VENV_DIR="$SCRIPT_DIR/.venv"

if command -v uv >/dev/null 2>&1; then
    echo -e "${BLUE}▶ Fast installer detected (uv). Setting up virtual environment...${RESET}"
    if [ ! -d "$VENV_DIR" ]; then
        uv venv "$VENV_DIR" --python "$PYTHON_BIN"
    fi
    echo -e "${BLUE}▶ Installing dependencies...${RESET}"
    uv pip install --python "$VENV_DIR/bin/python" -r requirements.txt
    uv pip install --python "$VENV_DIR/bin/python" -e .
else
    echo -e "${BLUE}▶ Creating virtual environment using ${PYTHON_BIN}...${RESET}"
    if [ ! -d "$VENV_DIR" ]; then
        "$PYTHON_BIN" -m venv "$VENV_DIR"
    fi
    echo -e "${BLUE}▶ Installing dependencies using pip...${RESET}"
    "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
    "$VENV_DIR/bin/pip" install -r requirements.txt
    "$VENV_DIR/bin/pip" install -e .
fi

echo -e "${GREEN}✓ Dependencies successfully installed!${RESET}"

# 3. Create directories & .env if not present
mkdir -p "$SCRIPT_DIR/vault/reports" "$SCRIPT_DIR/vault/conversations"

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${BLUE}▶ Creating default .env configuration...${RESET}"
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
fi

# 4. Check Ollama Status
echo -e "${BLUE}▶ Checking local LLM (Ollama) status...${RESET}"
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    MODELS_COUNT=$(curl -s http://localhost:11434/api/tags | grep -o '"name"' | wc -l | tr -d ' ')
    if [ "$MODELS_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Ollama is online with ${MODELS_COUNT} local model(s) available!${RESET}"
    else
        echo -e "${YELLOW}Notice: Ollama is running, but no model is downloaded yet.${RESET}"
        echo -e "  To download the fast default model, run:"
        echo -e "    ${BOLD}ollama pull llama3.2${RESET}"
    fi
else
    echo -e "${YELLOW}Notice: Ollama is not currently detected on localhost:11434.${RESET}"
    echo -e "  If you want 100% free local AI:"
    echo -e "    1. Install Ollama: https://ollama.com (or 'brew install ollama' on Mac)"
    echo -e "    2. Download model: ollama pull llama3.2"
    echo -e "  If you prefer cloud AI (Gemini, OpenAI, Groq):"
    echo -e "    • You can skip Ollama! Just click 'Settings' in the web UI to paste your API key."
fi

# 5. Make start.sh executable
chmod +x "$SCRIPT_DIR/start.sh"
chmod +x "$SCRIPT_DIR/install.sh"
chmod +x "$SCRIPT_DIR/run.py"

echo ""
echo -e "${BOLD}${GREEN}========================================================${RESET}"
echo -e "${BOLD}${GREEN}  Installation Complete!                               ${RESET}"
echo -e "${BOLD}${GREEN}========================================================${RESET}"
echo ""
echo -e "To start your Research Agent anytime, simply run:"
echo -e "  ${BOLD}${BLUE}./start.sh${RESET}"
echo ""
echo -e "Or via command-line:"
echo -e "  ${BOLD}${BLUE}./start.sh cli --topic \"Latest advances in fusion energy\"${RESET}"
echo ""
