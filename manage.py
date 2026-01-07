#!/usr/bin/env python3
"""
FastAPI Project Management CLI

Usage:
    python manage.py test              # Run all tests with coverage
    python manage.py test:unit         # Run unit tests only
    python manage.py test:integration  # Run integration tests only
    python manage.py test:watch        # Run tests in watch mode
    python manage.py db:create         # Create database
    python manage.py db:drop           # Drop database
    python manage.py db:migrate        # Create and apply migrations
    python manage.py db:upgrade        # Apply migrations
    python manage.py db:downgrade      # Rollback migrations
    python manage.py db:seed           # Seed database with test data
    python manage.py db:reset          # Full reset (drop + create + migrate + seed)
    python manage.py lint              # Run code linters
    python manage.py format            # Format code
    python manage.py dev               # Start development server
    python manage.py prod              # Start production server
    python manage.py shell             # Interactive Python shell
    python manage.py clean             # Clean up generated files
    python manage.py info              # Display project info
    python manage.py docs              # Generate OpenAPI docs
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.table import Table

from app.core.logger import console, log_section, log_status, logger

# Project paths
PROJECT_ROOT = Path(__file__).parent
APP_DIR = PROJECT_ROOT / "app"


# Load the .env file in the project root
load_dotenv(dotenv_path=PROJECT_ROOT.parent / ".env")


# Database configuration from environment
DB_NAME = os.getenv("POSTGRES_DB", "wakazi")
DB_USER = os.getenv("POSTGRES_USER", "tosh")
DB_HOST = os.getenv("POSTGRES_SERVER", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
ENV = os.getenv("ENVIRONMENT", "development")


app = typer.Typer(
    name="FastAPI Management CLI",
    help="Professional CLI tool for FastAPI project management",
    add_completion=False,
)


# HELPER FUNCTIONS
def check_production():
    """Prevent destructive operations in production"""
    if ENV == "production":
        console.print("[bold red]❌ Operation not allowed in production environment![/bold red]")
        raise typer.Exit(code=1)


def run_command(
    cmd: list[str], check: bool = True, cwd: Path = PROJECT_ROOT
) -> subprocess.CompletedProcess:
    """Run subprocess command with consistent error handling"""
    return subprocess.run(cmd, check=check, cwd=cwd)


# TESTING COMMANDS
@app.command(name="test")
def run_tests(
    coverage: bool = typer.Option(True, help="Generate coverage report"),
    html: bool = typer.Option(False, help="Generate HTML coverage report"),
    verbose: bool = typer.Option(False, "-v", help="Verbose output"),
    failfast: bool = typer.Option(False, "-x", help="Stop on first failure"),
    markers: str = typer.Option(None, "-m", help="Run tests matching markers"),
    keyword: str = typer.Option(None, "-k", help="Run tests matching keyword"),
):
    log_section("🧪 RUNNING TEST SUITE", "bold cyan")
    cmd = ["uv", "run", "pytest"]

    if coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing"])
        if html:
            cmd.append("--cov-report=html:htmlcov")

    if verbose:
        cmd.append("-v")
    if failfast:
        cmd.append("-x")
    if markers:
        cmd.extend(["-m", markers])
    if keyword:
        cmd.extend(["-k", keyword])

    cmd.extend(["--color=yes", "-ra"])

    with log_status("Running tests...", spinner="dots"):
        result = run_command(cmd, check=False)

    if result.returncode == 0:
        logger.success("✅ All tests passed!")
        if html:
            console.print("\n[dim]HTML coverage report: htmlcov/index.html[/dim]")
    else:
        sys.exit(1)


@app.command(name="test:unit")
def run_unit_tests(verbose: bool = typer.Option(False, "-v")):
    log_section("🔬 RUNNING UNIT TESTS", "bold blue")
    cmd = ["pytest", "-m", "unit", "--cov=app"]
    if verbose:
        cmd.append("-v")

    result = run_command(cmd, check=False)
    sys.exit(result.returncode)


@app.command(name="test:integration")
def run_integration_tests(verbose: bool = typer.Option(False, "-v")):
    log_section("🔗 RUNNING INTEGRATION TESTS", "bold magenta")
    cmd = ["pytest", "-m", "integration", "--cov=app"]
    if verbose:
        cmd.append("-v")

    result = run_command(cmd, check=False)
    sys.exit(result.returncode)


@app.command(name="test:watch")
def run_tests_watch():
    log_section("👀 WATCHING FOR CHANGES", "bold yellow")
    console.print("[dim]Tests will re-run when files change. Press Ctrl+C to stop.[/dim]\n")

    try:
        run_command(["pytest-watch", "--", "-v", "--color=yes"], check=False)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped watching for changes.[/yellow]")


# DATABASE COMMANDS
def db_execute_sql(sql: str, autocommit: bool = True) -> bool:
    """Execute raw SQL command via psql"""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    try:
        # Connect to postgres database (default)
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_USER,
            host=DB_HOST,
            port=DB_PORT,
        )
        if autocommit:
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        cursor = conn.cursor()
        cursor.execute(sql)
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        console.print(f"[yellow]⚠️  SQL execution issue: {e}[/yellow]")
        return False


@app.command(name="db:create")
def create_database():
    """Create the database (idempotent - won't fail if exists)"""
    log_section("📦 CREATING DATABASE", "bold green")

    with log_status(f"Creating database '{DB_NAME}'...", spinner="dots"):
        sql = f"CREATE DATABASE {DB_NAME}"
        success = db_execute_sql(sql)

    if success:
        logger.success(f"✅ Database '{DB_NAME}' created successfully!")
    else:
        console.print(f"[yellow]ℹ️  Database '{DB_NAME}' may already exist[/yellow]")


@app.command(name="db:drop")
def drop_database(confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")):
    """Drop the database (⚠️ DESTRUCTIVE)"""
    check_production()

    log_section("🗑️  DROPPING DATABASE", "bold red")

    if not confirm:
        console.print(f"[bold red]⚠️  WARNING: This will permanently delete '{DB_NAME}'![/bold red]")
        confirm = typer.confirm("Are you sure?")
        if not confirm:
            console.print("[yellow]Aborted.[/yellow]")
            return

    with log_status(f"Dropping database '{DB_NAME}'...", spinner="dots"):
        # Terminate existing connections first
        sql_terminate = f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{DB_NAME}'
        AND pid <> pg_backend_pid()
        """
        db_execute_sql(sql_terminate)

        # Drop database
        sql_drop = f"DROP DATABASE IF EXISTS {DB_NAME}"
        success = db_execute_sql(sql_drop)

    if success:
        logger.success(f"✅ Database '{DB_NAME}' dropped successfully!")
    else:
        console.print(f"[yellow]⚠️  Could not drop database '{DB_NAME}'[/yellow]")


@app.command(name="db:migrate")
def migrate_database(message: str = typer.Option("Auto migration", "-m", help="Migration message")):
    """Create a new migration and apply it"""
    log_section("📝 DATABASE MIGRATION", "bold cyan")

    # Generate migration
    with log_status("Generating migration...", spinner="dots"):
        run_command(["alembic", "revision", "--autogenerate", "-m", message])

    # Apply migration
    with log_status("Applying migration...", spinner="dots"):
        run_command(["alembic", "upgrade", "head"])

    logger.success("✅ Migration created and applied!")


@app.command(name="db:upgrade")
def upgrade_database(revision: str = typer.Option("head", "-r", help="Target revision")):
    """Apply database migrations"""
    log_section("⬆️  APPLYING MIGRATIONS", "bold green")

    with log_status(f"Upgrading to {revision}...", spinner="dots"):
        result = run_command(["alembic", "upgrade", revision], check=False)

    if result.returncode == 0:
        logger.success("✅ Migrations applied successfully!")
    else:
        console.print("[bold red]❌ Migration failed![/bold red]")
        sys.exit(1)


@app.command(name="db:downgrade")
def downgrade_database(
    revision: str = typer.Option("-1", "-r", help="Target revision"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Rollback database migrations"""
    check_production()

    log_section("⬇️  ROLLING BACK MIGRATIONS", "bold yellow")

    if not confirm:
        console.print(f"[yellow]⚠️  Rolling back to: {revision}[/yellow]")
        confirm = typer.confirm("Are you sure?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            return

    with log_status(f"Rolling back to {revision}...", spinner="dots"):
        result = run_command(["alembic", "downgrade", revision], check=False)

    if result.returncode == 0:
        logger.success("✅ Rollback successful!")
    else:
        console.print("[bold red]❌ Rollback failed![/bold red]")
        sys.exit(1)


@app.command(name="db:seed")
def seed_database():
    """Seed the database with initial/test data"""
    log_section("🌱 SEEDING DATABASE", "bold green")

    with log_status("Seeding data...", spinner="dots"):
        from seed_data import seed_all_data

        asyncio.run(seed_all_data())

    logger.success("✅ Database seeded successfully!")


@app.command(name="db:reset")
def reset_database(confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")):
    """
    Complete database reset for daily development

    Steps: drop → create → migrate → seed
    ⚠️  Only works in development!
    """
    check_production()

    log_section(f"🔄 RESETTING DATABASE: {DB_NAME}", "bold red")

    if not confirm:
        console.print(
            "[bold red]⚠️  This will destroy ALL data and rebuild from scratch![/bold red]"
        )
        confirm = typer.confirm("Continue?")
        if not confirm:
            console.print("[yellow]Aborted.[/yellow]")
            return

    try:
        # Step 1: Drop database
        console.print("\n[cyan]Step 1/4: Dropping database...[/cyan]")
        drop_database(confirm=True)

        # Step 2: Create database
        console.print("\n[cyan]Step 2/4: Creating database...[/cyan]")
        create_database()

        # Step 3: Apply migrations
        console.print("\n[cyan]Step 3/4: Applying migrations...[/cyan]")
        with log_status("Running migrations...", spinner="dots"):
            run_command(["alembic", "upgrade", "head"])

        # Step 4: Seed data
        console.print("\n[cyan]Step 4/4: Seeding data...[/cyan]")
        seed_database()

        logger.success(f"\n✅ Database '{DB_NAME}' reset complete! Ready for development.")

    except Exception as e:
        console.print(f"\n[bold red]❌ Reset failed: {e}[/bold red]")
        console.print("[yellow]💡 Try running steps individually to debug:[/yellow]")
        console.print("   python manage.py db:drop -y")
        console.print("   python manage.py db:create")
        console.print("   python manage.py db:upgrade")
        console.print("   python manage.py db:seed")
        sys.exit(1)


# CODE QUALITY COMMANDS
@app.command(name="lint")
def run_linter(fix: bool = typer.Option(False, "--fix", help="Auto-fix issues")):
    log_section("🔍 RUNNING LINTERS", "bold blue")

    cmd = ["ruff", "check", "app", "tests"]
    if fix:
        cmd.append("--fix")

    result = run_command(cmd, check=False)

    if result.returncode == 0:
        logger.success("✅ No linting issues found!")
    else:
        console.print("[yellow]⚠️  Linting issues found. Run with --fix to auto-correct.[/yellow]")


@app.command(name="format")
def format_code(check: bool = typer.Option(False, "--check", help="Check without modifying")):
    log_section("✨ FORMATTING CODE", "bold cyan")

    cmd = ["ruff", "format", "app", "tests"]
    if check:
        cmd.append("--check")

    result = run_command(cmd, check=False)

    if result.returncode == 0:
        logger.success("✅ Code formatted successfully!")
    else:
        console.print("[yellow]⚠️  Formatting issues found.[/yellow]")


# DEVELOPMENT COMMANDS
@app.command(name="dev")
def run_dev_server(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(True, help="Enable auto-reload"),
):
    log_section("🚀 STARTING DEVELOPMENT SERVER", "bold green")
    console.print(f"[dim]Server starting at[/dim] [cyan]http://{host}:{port}[/cyan]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    cmd = ["uvicorn", "app.main:app", "--host", host, "--port", str(port)]
    if reload:
        cmd.append("--reload")

    try:
        run_command(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped.[/yellow]")


@app.command(name="prod")
def run_prod_server(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "-p", help="Port to bind to"),
    workers: int = typer.Option(4, "-w", help="Number of workers"),
):
    log_section("🏭 STARTING PRODUCTION SERVER", "bold green")
    console.print(f"[cyan]🌐 Production server: http://{host}:{port}[/cyan]\n")

    cmd = [
        "gunicorn",
        "app.main:app",
        "--bind",
        f"{host}:{port}",
        "--workers",
        str(workers),
        "--worker-class",
        "uvicorn.workers.UvicornWorker",
        "--access-logfile",
        "-",
        "--error-logfile",
        "-",
    ]

    try:
        run_command(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped.[/yellow]")


# UTILITY COMMANDS
@app.command(name="shell")
def start_shell():
    log_section("🐚 INTERACTIVE SHELL", "bold cyan")

    try:
        import IPython

        from app.core.db import AsyncSessionLocal  # noqa: F401
        from app.main import app  # noqa: F401

        console.print("[cyan]IPython shell with app context loaded[/cyan]\n")
        IPython.embed(header="FastAPI Shell - app, AsyncSessionLocal available", colors="neutral")
    except ImportError:
        console.print("[yellow]IPython not found. Using standard shell...[/yellow]\n")
        import code

        code.interact(local=globals())


@app.command(name="docs")
def generate_docs():
    log_section("📚 GENERATING OPENAPI DOCS", "bold magenta")

    with log_status("Generating OpenAPI schema...", spinner="dots"):
        import json

        from app.main import app as fastapi_app

        schema = fastapi_app.openapi()
        with open("openapi.json", "w") as f:
            json.dump(schema, f, indent=2)

    logger.success("✅ OpenAPI schema saved to: openapi.json")


@app.command(name="info")
def show_info():
    log_section("📊 PROJECT INFORMATION", "bold cyan")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    app_files = len(list(APP_DIR.rglob("*.py")))
    test_files = len(list((PROJECT_ROOT / "tests").rglob("*.py")))
    app_loc = sum(len(f.read_text().splitlines()) for f in APP_DIR.rglob("*.py"))

    table.add_row("Environment", ENV)
    table.add_row("Database", f"{DB_NAME}@{DB_HOST}")
    table.add_row("Python Files", str(app_files))
    table.add_row("Test Files", str(test_files))
    table.add_row("Lines of Code", f"~{app_loc:,}")
    table.add_row("Python Version", sys.version.split()[0])

    console.print(table)
    console.print()


@app.command(name="clean")
def clean_project():
    log_section("🧹 CLEANING PROJECT", "bold yellow")

    patterns = [
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        "**/*.pyd",
        ".pytest_cache",
        ".ruff_cache",
        "htmlcov",
        ".coverage",
        "*.egg-info",
    ]

    removed_count = 0
    for pattern in patterns:
        for path in PROJECT_ROOT.rglob(pattern):
            if path.is_file():
                path.unlink()
                removed_count += 1
            elif path.is_dir():
                import shutil

                shutil.rmtree(path)
                removed_count += 1

    logger.success(f"✅ Cleaned {removed_count} files/directories!")


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        sys.exit(1)
