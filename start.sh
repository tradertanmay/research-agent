#!/usr/bin/env bash
# ==============================================================================
# Autonomous Research Agent - 1-Click Launcher
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
RESET="\033[0m"

# Verify virtual environment exists, otherwise prompt to install
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo -e "${BLUE}▶ Virtual environment not found. Running installer first...${RESET}"
    bash "$SCRIPT_DIR/install.sh"
fi

# Activate virtualenv
source "$SCRIPT_DIR/.venv/bin/activate"

# Check special subcommands
if [ "$1" = "test" ]; then
    python3 -m unittest discover -s tests
elif [ "$1" = "share" ] || [ "$1" = "tunnel" ]; then
    echo -e "${BOLD}${GREEN}🌐 Starting Public Tunnel for Research Agent...${RESET}"
    if ! command -v cloudflared >/dev/null 2>&1; then
        echo -e "${YELLOW}cloudflared is not installed.${RESET}"
        echo -e "To share your agent publicly, install cloudflared via 'brew install cloudflared' or visit:"
        echo -e "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        exit 1
    fi
    cloudflared tunnel --url http://localhost:8080
elif [ "$1" = "python" ] || [ "$1" = "python3" ]; then
    shift
    python3 "$@"
elif [ $# -eq 0 ]; then
    echo -e "${BOLD}${BLUE}🚀 Starting Autonomous Research Agent Dashboard...${RESET}"
    python3 "$SCRIPT_DIR/run.py" web
else
    python3 "$SCRIPT_DIR/run.py" "$@"
fi
