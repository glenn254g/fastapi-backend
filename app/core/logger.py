"""
Beautiful, production-ready logging setup with Loguru + Rich
Handles console output, file rotation, and structured logging
"""

# backend/app/core/logger.py
import sys
from pathlib import Path
from typing import Any

from loguru import logger
from rich.console import Console
from rich.theme import Theme

# Custom Rich theme for consistent, beautiful colors
custom_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "critical": "bold white on red",
        "success": "bold green",
        "debug": "dim blue",
        "trace": "dim magenta",
    }
)

console = Console(theme=custom_theme)


def configure_logging(log_level: str = "INFO", log_to_file: bool = False) -> None:
    """
    Configure beautiful logging with Loguru + Rich integration

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to enable file logging with rotation
    """
    # Remove default logger
    logger.remove()

    # Add beautiful console logging with colors and formatting
    logger.add(
        sys.stderr,
        format=(
            "<level>{level: <8}</level>   "
            # "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
        enqueue=True,  # Thread-safe logging
    )

    # Add file logging with rotation (production-ready)
    if log_to_file:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Main application log with rotation
        # logger.add(
        #     log_dir / "app_{time:YYYY-MM-DD}.log",
        #     rotation="00:00",  # Rotate at midnight
        #     retention="30 days",  # Keep logs for 30 days
        #     compression="zip",  # Compress old logs
        #     format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        #     level="DEBUG",
        #     enqueue=True,
        # )

        # Error-only log for quick debugging
        # logger.add(
        #     log_dir / "errors_{time:YYYY-MM-DD}.log",
        #     rotation="00:00",
        #     retention="90 days",  # Keep error logs longer
        #     compression="zip",
        #     format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message} | {extra}",
        #     level="ERROR",
        #     enqueue=True,
        # )


# RICH CONSOLE UTILITIES FOR BEAUTIFUL OUTPUT
def log_section(title: str, style: str = "bold cyan") -> None:
    """Create a beautiful section divider with rule"""
    console.rule(f"[{style}]{title}[/{style}]", style=style.split()[-1])


def log_panel(message: str, title: str = "", style: str = "info") -> None:
    """Display message in a beautiful bordered panel"""
    from rich.panel import Panel

    console.print(Panel(message, title=title, style=style, border_style=style))


def log_table(data: list[dict], title: str = "Data", show_lines: bool = False) -> None:
    """Display data as a beautiful formatted table"""
    from rich.table import Table

    if not data:
        console.print("[dim]No data to display[/dim]")
        return

    table = Table(
        title=title,
        show_header=True,
        header_style="bold magenta",
        show_lines=show_lines,
        border_style="blue",
    )

    # Add columns from first item
    for key in data[0].keys():
        table.add_column(str(key).replace("_", " ").title(), style="cyan")

    # Add rows
    for item in data:
        table.add_row(*[str(v) for v in item.values()])

    console.print(table)


def log_dict(data: dict[str, Any], title: str = "Dict data") -> None:
    from rich.table import Table

    """Log dictionary data as a beautiful table"""
    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    for key, value in data.items():
        table.add_row(str(key), str(value))

    console.print(table)


def log_json(data: dict, title: str = "JSON Data") -> None:
    """Display JSON data with beautiful syntax highlighting"""
    from rich.json import JSON
    from rich.panel import Panel

    json_obj = JSON.from_data(data)
    console.print(Panel(json_obj, title=title, border_style="green"))


def log_tree(title: str, items: dict) -> None:
    """Display hierarchical data as a beautiful tree structure"""
    from rich.tree import Tree

    tree = Tree(f"[bold cyan]{title}[/bold cyan]")

    def add_items(node, data):
        for key, value in data.items():
            if isinstance(value, dict):
                branch = node.add(f"[yellow]{key}[/yellow]")
                add_items(branch, value)
            elif isinstance(value, list):
                branch = node.add(f"[yellow]{key}[/yellow]")
                for item in value:
                    if isinstance(item, dict):
                        add_items(branch, item)
                    else:
                        branch.add(f"[green]{item}[/green]")
            else:
                node.add(f"[yellow]{key}[/yellow]: [green]{value}[/green]")

    add_items(tree, items)
    console.print(tree)


def log_progress():
    """Return a beautiful progress bar context manager for long operations"""
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )

    return Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(complete_style="green", finished_style="bold green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def log_status(message: str, spinner: str = "dots"):
    """Return a status spinner context manager for operations"""
    from rich.status import Status

    return Status(message, spinner=spinner, console=console)


# STARTUP BANNER
def display_startup_banner(app_name: str, version: str, environment: str) -> None:
    """Display a beautiful startup banner"""
    from rich.panel import Panel
    from rich.text import Text

    banner = Text()
    banner.append(f"\n{app_name}\n", style="bold cyan")
    banner.append(f"Version: {version} | Environment: {environment}\n", style="dim")
    banner.append("\nApplication starting...\n", style="green")

    console.print(Panel(banner, border_style="cyan", padding=(1, 2)))


# Initialization
# Configure on module import with sensible defaults
configure_logging(log_level="INFO", log_to_file=False)
