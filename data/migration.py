"""Safe one-time migration of the local account database from an older Stock AI Pro folder."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

CURRENT_DB = Path(__file__).resolve().parent / "stock_ai_accounts.db"


def _candidate_databases() -> list[Path]:
    here = Path(__file__).resolve()
    project_dir = here.parent.parent
    candidates: list[Path] = []

    # Explicit override takes precedence.
    override = os.getenv("STOCK_AI_LEGACY_DB", "").strip()
    if override:
        candidates.append(Path(override).expanduser())

    # Common layout when v4 and v5 are unpacked beside each other.
    parent = project_dir.parent
    for sibling in parent.iterdir() if parent.exists() else []:
        if not sibling.is_dir() or sibling.resolve() == project_dir.resolve():
            continue
        candidates.append(sibling / project_dir.name / "data" / "stock_ai_accounts.db")
        candidates.append(sibling / "data" / "stock_ai_accounts.db")

    # Also look one level below the current project for a legacy copy.
    candidates.extend([
        project_dir / "stock_ai_accounts.db",
        Path.cwd() / "data" / "stock_ai_accounts.db",
    ])

    unique: list[Path] = []
    seen: set[str] = set()
    for p in candidates:
        try:
            key = str(p.resolve()).lower()
        except OSError:
            key = str(p).lower()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def migrate_legacy_database() -> tuple[bool, str]:
    """Copy an older account DB only when the new DB does not exist.

    Returns (migrated, message). Existing v5 data is never overwritten.
    """
    if CURRENT_DB.exists():
        return False, "기존 v5 계좌 데이터베이스가 이미 있어 그대로 사용합니다."

    for source in _candidate_databases():
        try:
            if not source.is_file() or source.resolve() == CURRENT_DB.resolve():
                continue
        except OSError:
            continue
        CURRENT_DB.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, CURRENT_DB)
        return True, f"기존 계좌/포트폴리오 데이터를 가져왔습니다: {source}"

    return False, "이전 계좌 데이터베이스를 찾지 못했습니다. 새 데이터베이스로 시작합니다."

# Compatibility result used by the Streamlit sidebar.
_migrate_result = migrate_legacy_database()

