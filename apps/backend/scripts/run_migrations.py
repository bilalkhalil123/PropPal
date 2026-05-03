"""Run Alembic migrations programmatically.

Usage (PowerShell):
  cd apps/backend
  .\venv\Scripts\Activate.ps1
  python scripts/run_migrations.py

This will load the alembic.ini in the backend folder and run `upgrade head`.
"""
from pathlib import Path
import sys

from alembic.config import Config
from alembic import command


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    # make backend package importable so we can read settings
    sys.path.insert(0, str(repo_root))

    alembic_ini = repo_root / "alembic.ini"

    if not alembic_ini.exists():
        print(f"alembic.ini not found at {alembic_ini}")
        return 2

    # Import settings from the backend package
    try:
        from common.config import get_settings

        settings = get_settings()
        db_url = settings.get_postgres_url()
        if not db_url:
            print("DATABASE_URL / POSTGRES_URL not set in .env; set it before running migrations.")
            return 2
    except Exception as exc:
        print("Failed to load backend settings:", exc)
        return 2

    cfg = Config(str(alembic_ini))
    # ensure script_location is correct relative to the backend folder
    cfg.set_main_option("script_location", str(repo_root / "alembic"))
    # override DB URL so alembic uses the same database as the app
    cfg.set_main_option("sqlalchemy.url", db_url)

    print("Running alembic upgrade head against:", db_url)
    try:
        command.upgrade(cfg, "head")
        print("Migrations applied successfully.")
        return 0
    except Exception as exc:  # pragma: no cover - simple wrapper
        print("Failed to apply migrations:", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
