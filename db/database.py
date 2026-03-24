import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from models.campaign import Campaign

DB_PATH = Path(__file__).parent.parent / "data" / "campaigns.db"

logger = logging.getLogger(__name__)

_MIGRATION_COLUMNS = [
    ("registration_url", "TEXT"),
    ("eligible",         "BOOLEAN"),
    ("eligibility_reason", "TEXT"),
    ("ai_summary",       "TEXT"),
]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_name TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                max_amount TEXT,
                period TEXT,
                conditions TEXT,
                campaign_url TEXT UNIQUE NOT NULL,
                thumbnail_url TEXT,
                registration_url TEXT,
                eligible BOOLEAN,
                eligibility_reason TEXT,
                ai_summary TEXT,
                notified BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """)
        # 既存DBへのマイグレーション
        existing = [row[1] for row in conn.execute("PRAGMA table_info(campaigns)").fetchall()]
        for col_name, col_type in _MIGRATION_COLUMNS:
            if col_name not in existing:
                conn.execute(f"ALTER TABLE campaigns ADD COLUMN {col_name} {col_type}")
                logger.info("Migrated DB: added column %s", col_name)
    logger.info("DB initialized: %s", DB_PATH)


def save_campaign(campaign: Campaign) -> None:
    now = datetime.now().isoformat()
    try:
        with _connect() as conn:
            conn.execute("""
                INSERT INTO campaigns
                    (card_name, title, summary, max_amount, period, conditions,
                     campaign_url, thumbnail_url, registration_url, notified, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                campaign.card_name, campaign.title, campaign.summary,
                campaign.max_amount, campaign.period, campaign.conditions,
                campaign.campaign_url, campaign.thumbnail_url, campaign.registration_url,
                campaign.notified, now, now,
            ))
        logger.info("Saved campaign: %s", campaign.title)
    except sqlite3.IntegrityError:
        logger.debug("Duplicate skipped: %s", campaign.campaign_url)


def update_analysis(campaign_id: int, eligible: bool, eligibility_reason: str, ai_summary: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE campaigns SET eligible=?, eligibility_reason=?, ai_summary=?, updated_at=? WHERE id=?",
            (eligible, eligibility_reason, ai_summary, datetime.now().isoformat(), campaign_id),
        )
    logger.info("Analysis updated: id=%s eligible=%s", campaign_id, eligible)


def get_unnotified_campaigns() -> list[Campaign]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM campaigns WHERE notified = 0"
        ).fetchall()
    return [_row_to_campaign(r) for r in rows]


def mark_as_notified(campaign_id: int) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE campaigns SET notified = 1, updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), campaign_id),
        )
    logger.info("Marked as notified: id=%s", campaign_id)


def _row_to_campaign(row: sqlite3.Row) -> Campaign:
    return Campaign(
        id=row["id"],
        card_name=row["card_name"],
        title=row["title"],
        summary=row["summary"],
        max_amount=row["max_amount"],
        period=row["period"],
        conditions=row["conditions"],
        campaign_url=row["campaign_url"],
        thumbnail_url=row["thumbnail_url"],
        registration_url=row["registration_url"],
        eligible=bool(row["eligible"]) if row["eligible"] is not None else None,
        eligibility_reason=row["eligibility_reason"],
        ai_summary=row["ai_summary"],
        notified=bool(row["notified"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
