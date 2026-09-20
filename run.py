#!/usr/bin/env python3
import sys
import os
import argparse
import asyncio
import webbrowser
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.config import settings

def get_local_ip():
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

def print_banner():
    local_ip = get_local_ip()
    port = settings.port
    local_url = f"http://127.0.0.1:{port}"
    lan_url = f"http://{local_ip}:{port}"

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        console = Console()
        text = Text()
        text.append("Autonomous Deep Research Agent\n", style="bold cyan")
        text.append("Local-First • Multi-Source • Shared Web Interface\n\n", style="dim")
        text.append("• Local Access:   ", style="bold")
        text.append(f"{local_url}\n", style="bold green underline")
        text.append("• Network Share:  ", style="bold")
        text.append(f"{lan_url}", style="bold yellow underline")
        text.append("  (Share with anyone on your Wi-Fi!)\n\n", style="dim italic")
        text.append("• Ollama Backend: ", style="bold")
        text.append(f"{settings.ollama_base_url}\n", style="magenta")
        text.append("• Saved Reports:  ", style="bold")
        text.append(f"{settings.reports_dir}", style="dim")

        console.print(Panel(text, border_style="cyan", title="[bold white]DeepResearch Agent[/bold white]"))
    except ImportError:
        print("=" * 65)
        print("  Autonomous Deep Research Agent")
        print(f"  • Local Access:  {local_url}")
        print(f"  • Network Share: {lan_url}  (Share on your Wi-Fi!)")
        print("=" * 65)

def get_free_port(preferred_port=8080):
    import socket
    candidates = [preferred_port, 8000, 8501, 8050, 8888, 9000]
    for p in candidates:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except (AttributeError, OSError):
                    pass
                s.bind(("127.0.0.1", p))
                return p
        except OSError:
            continue
    return preferred_port

def cmd_web(args):
    """Launch FastAPI Web Server & open browser."""
    import uvicorn
    import subprocess

    host = getattr(args, "host", None) or settings.host
    settings.host = host
    port = getattr(args, "port", None) or settings.port
    # If port is occupied, find free port automatically
    port = get_free_port(port)
    settings.port = port

    print_banner()

    target_url = f"http://127.0.0.1:{settings.port}"

    # Attempt to open browser automatically on desktop environments
    def open_browser():
        import time
        time.sleep(1.2)
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", target_url], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform.startswith("win"):
                try:
                    os.startfile(target_url)
                except Exception:
                    webbrowser.open(target_url)
            elif sys.platform.startswith("linux"):
                try:
                    subprocess.run(["xdg-open", target_url], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    webbrowser.open(target_url)
            else:
                webbrowser.open(target_url)
        except Exception:
            pass

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # Run uvicorn
    uvicorn.run(
        "agent.web.server:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )

async def _run_cli_async(topic: str, depth: str, focus: str, model_id: str, output_file: str):
    from rich.console import Console
    from rich.status import Status
    from rich.markdown import Markdown
    from agent.core.research_agent import ResearchAgent

    console = Console()
    console.rule("[bold cyan]Autonomous Research Agent - CLI Mode[/bold cyan]")
    console.print(f"[bold]Topic:[/bold] {topic}")
    console.print(f"[bold]Depth:[/bold] {depth} | [bold]Focus:[/bold] {focus} | [bold]Model:[/bold] {model_id}\n")

    agent = ResearchAgent(model_id=model_id)
    final_data = None

    with Status("[bold green]Agent working...", console=console) as status:
        async for event in agent.run_stream(topic=topic, depth=depth, focus=focus):
            ev_type = event.get("type")
            if ev_type == "phase_start":
                phase = event.get("phase", "").upper()
                msg = event.get("message", "")
                status.update(f"[bold blue][{phase}][/bold blue] {msg}")
                console.print(f"  [dim]▶ [{phase}] {msg}[/dim]")
            elif ev_type == "plan_complete":
                plan = event.get("plan", {})
                console.print(f"  [green]✓ Plan ready: {len(plan.get('sub_questions', []))} questions formulated[/green]")
            elif ev_type == "search_complete":
                count = event.get("count", 0)
                console.print(f"  [green]✓ Discovered {count} sources[/green]")
            elif ev_type == "reading_complete":
                count = event.get("count", 0)
                console.print(f"  [green]✓ Scraped {count} source documents[/green]")
            elif ev_type == "complete":
                final_data = event.get("data")
                console.print("  [bold green]✓ Research cycle successfully completed![/bold green]\n")
            elif ev_type == "error":
                console.print(f"  [bold red]❌ Error: {event.get('message')}[/bold red]")

    if final_data and final_data.get("content"):
        content = final_data["content"]
        console.rule("[bold green]Generated Research Report[/bold green]")
        console.print(Markdown(content))
        console.rule()

        if output_file:
            out_path = Path(output_file)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
            console.print(f"[bold green]Report saved to: {out_path.resolve()}[/bold green]")
        else:
            console.print(f"[dim]Saved in vault: {final_data.get('filepath')}[/dim]")

def cmd_cli(args):
    """Run research query directly in terminal."""
    asyncio.run(_run_cli_async(
        topic=args.topic,
        depth=args.depth,
        focus=args.focus,
        model_id=args.model,
        output_file=args.output,
    ))

def cmd_check(args):
    """Verify system diagnostics and local Ollama setup."""
    from rich.console import Console
    from rich.table import Table
    import httpx

    console = Console()
    table = Table(title="System & LLM Environment Check")
    table.add_column("Component", style="bold cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    # 1. Python version
    py_ver = sys.version.split()[0]
    if sys.version_info >= (3, 10):
        table.add_row("Python", "[green]OK[/green]", f"{py_ver} (>= 3.10 satisfied)")
    else:
        table.add_row("Python", "[red]Outdated[/red]", f"{py_ver} (Python 3.10+ required)")

    # 2. Ollama connectivity
    ollama_ok = False
    models = []
    try:
        res = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3.0)
        if res.status_code == 200:
            ollama_ok = True
            models = [m["name"] for m in res.json().get("models", [])]
    except Exception:
        pass

    if ollama_ok:
        table.add_row("Ollama Service", "[green]Online[/green]", f"{len(models)} local models found")
        for m in models[:5]:
            table.add_row("  ↳ Model", "[green]Available[/green]", m)
        if len(models) > 5:
            table.add_row("  ↳ ...", "[dim]More[/dim]", f"+{len(models)-5} more models")
    else:
        table.add_row("Ollama Service", "[yellow]Offline[/yellow]", "Start with 'ollama serve' or provide cloud API keys")

    # 3. Vault directory
    table.add_row("Storage Vault", "[green]Ready[/green]", str(settings.reports_dir))

    console.print(table)

def main():
    parser = argparse.ArgumentParser(description="Autonomous Deep Research Agent")
    subparsers = parser.add_subparsers(dest="subcommand")

    # Web command (default)
    web_parser = subparsers.add_parser("web", help="Start web dashboard (default)")
    web_parser.add_argument("--port", "-p", type=int, default=8080, help="Port to bind (default: 8080 or next free)")
    web_parser.add_argument("--host", "-H", type=str, default="0.0.0.0", help="Host interface (default: 0.0.0.0 for LAN sharing)")

    # CLI command
    cli_parser = subparsers.add_parser("cli", help="Execute research directly in CLI")
    cli_parser.add_argument("topic", type=str, help="Research topic or question")
    cli_parser.add_argument("--depth", choices=["quick", "standard", "deep"], default="standard")
    cli_parser.add_argument("--focus", choices=["all", "academic", "web"], default="all")
    cli_parser.add_argument("--model", type=str, default="auto", help="Model ID (e.g. auto, ollama:llama3.1)")
    cli_parser.add_argument("--output", "-o", type=str, default="", help="Optional output .md path")

    # Check command
    subparsers.add_parser("check", help="Run system diagnostics")

    args = parser.parse_args()

    # Default to 'web' if no subcommand provided
    if not args.subcommand or args.subcommand == "web":
        cmd_web(args)
    elif args.subcommand == "cli":
        cmd_cli(args)
    elif args.subcommand == "check":
        cmd_check(args)

if __name__ == "__main__":
    main()
