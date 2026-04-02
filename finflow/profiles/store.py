"""SQLite-backed profile storage with migration from legacy glossary JSONs."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    ClientProfile,
    LanguageProfile,
    ScoringConfig,
    ToneProfile,
)

GLOSSARY_DIR = Path(__file__).parent.parent / "glossaries"
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "translation_engine.db"


class ProfileStore:
    """Manages client profiles in SQLite with fallback to legacy JSON glossaries."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS client_profiles (
                    client_id     TEXT PRIMARY KEY,
                    client_name   TEXT NOT NULL,
                    profile_json  TEXT NOT NULL,
                    created_at    TEXT NOT NULL,
                    updated_at    TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS translations (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id       TEXT NOT NULL,
                    language        TEXT NOT NULL,
                    source_hash     TEXT NOT NULL,
                    source_text     TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    scores_json     TEXT NOT NULL,
                    passed          INTEGER NOT NULL,
                    aggregate_score REAL NOT NULL,
                    revision_count  INTEGER DEFAULT 0,
                    audit_trail     TEXT DEFAULT '[]',
                    created_at      TEXT NOT NULL,
                    FOREIGN KEY (client_id) REFERENCES client_profiles(client_id)
                );

                CREATE TABLE IF NOT EXISTS reference_pairs (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id     TEXT NOT NULL,
                    language      TEXT NOT NULL,
                    source_text   TEXT NOT NULL,
                    translation   TEXT NOT NULL,
                    source_hash   TEXT NOT NULL,
                    added_at      TEXT NOT NULL,
                    FOREIGN KEY (client_id) REFERENCES client_profiles(client_id)
                );

                CREATE INDEX IF NOT EXISTS idx_translations_client
                    ON translations(client_id, language);
                CREATE INDEX IF NOT EXISTS idx_translations_score
                    ON translations(aggregate_score);
            """)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def save(self, profile: ClientProfile) -> None:
        """Insert or update a client profile."""
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO client_profiles (client_id, client_name, profile_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(client_id) DO UPDATE SET
                     client_name = excluded.client_name,
                     profile_json = excluded.profile_json,
                     updated_at = excluded.updated_at""",
                (
                    profile.client_id,
                    profile.client_name,
                    profile.to_json(),
                    profile.created_at,
                    profile.updated_at,
                ),
            )

    def load(self, client_id: str) -> ClientProfile | None:
        """Load a profile from SQLite. Falls back to legacy JSON if not in DB."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT profile_json FROM client_profiles WHERE client_id = ?",
                (client_id,),
            ).fetchone()

        if row:
            return ClientProfile.from_json(row[0])

        # Fallback: try legacy glossary JSON
        return self._migrate_from_legacy(client_id)

    def list_profiles(self) -> list[dict[str, str]]:
        """List all profiles (id + name + languages)."""
        profiles = []
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT client_id, client_name, profile_json FROM client_profiles"
            ).fetchall()

        for client_id, client_name, profile_json in rows:
            data = json.loads(profile_json)
            profiles.append({
                "client_id": client_id,
                "client_name": client_name,
                "languages": list(data.get("languages", {}).keys()),
            })

        # Also check for legacy glossaries not yet migrated
        for path in GLOSSARY_DIR.glob("client_*.json"):
            cid = path.stem.replace("client_", "")
            if not any(p["client_id"] == cid for p in profiles):
                profiles.append({
                    "client_id": cid,
                    "client_name": cid.upper(),
                    "languages": list(self._read_legacy_languages(cid)),
                    "source": "legacy_json",
                })

        return profiles

    def delete(self, client_id: str) -> bool:
        """Delete a profile."""
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM client_profiles WHERE client_id = ?", (client_id,)
            )
        return cursor.rowcount > 0

    def save_translation(
        self,
        client_id: str,
        language: str,
        source_hash: str,
        source_text: str,
        translated_text: str,
        scores: dict,
        passed: bool,
        aggregate_score: float,
        revision_count: int = 0,
        audit_trail: list | None = None,
    ) -> int:
        """Persist a translation result with scores and audit trail."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cursor = conn.execute(
                """INSERT INTO translations
                   (client_id, language, source_hash, source_text, translated_text,
                    scores_json, passed, aggregate_score, revision_count, audit_trail, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    client_id,
                    language,
                    source_hash,
                    source_text,
                    translated_text,
                    json.dumps(scores, ensure_ascii=False),
                    1 if passed else 0,
                    aggregate_score,
                    revision_count,
                    json.dumps(audit_trail or [], ensure_ascii=False),
                    now,
                ),
            )
        return cursor.lastrowid  # type: ignore[return-value]

    # --- Legacy migration ---

    def _migrate_from_legacy(self, client_id: str) -> ClientProfile | None:
        """Build a ClientProfile from legacy glossary JSON and save to DB."""
        path = GLOSSARY_DIR / f"client_{client_id}.json"
        if not path.exists():
            return None

        with open(path) as f:
            data = json.load(f)

        # Extract meta fields
        client_name = data.get("_client", client_id.upper())
        tone_desc = data.get("_tone", "professional, formal")
        brand_rules_str = data.get("_brand_rules", "")
        brand_rules = [r.strip() for r in brand_rules_str.split(".") if r.strip()] if brand_rules_str else []

        # Load base glossary for merging
        base_glossary = self._load_base_glossary()

        # Build language profiles
        languages: dict[str, LanguageProfile] = {}
        for key, value in data.items():
            if key.startswith("_"):
                continue
            if isinstance(value, dict):
                # Merge base + client glossary (client overrides base)
                merged = {**base_glossary.get(key, {}), **value}
                languages[key] = LanguageProfile(
                    glossary=merged,
                    tone=ToneProfile(description=tone_desc),
                    brand_rules=brand_rules,
                )

        profile = ClientProfile(
            client_id=client_id,
            client_name=client_name,
            languages=languages,
        )

        # Persist to DB
        self.save(profile)
        return profile

    def _load_base_glossary(self) -> dict[str, dict[str, str]]:
        """Load the base financial glossary."""
        path = GLOSSARY_DIR / "base_financial.json"
        if not path.exists():
            return {}
        with open(path) as f:
            return json.load(f)

    def _read_legacy_languages(self, client_id: str) -> list[str]:
        """Read available languages from a legacy glossary file."""
        path = GLOSSARY_DIR / f"client_{client_id}.json"
        if not path.exists():
            return []
        with open(path) as f:
            data = json.load(f)
        return [k for k in data if not k.startswith("_") and isinstance(data[k], dict)]
