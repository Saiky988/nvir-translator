import asyncio
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from config.settings import settings

logger = logging.getLogger("sachitone.bot.storage")


class AutoTranslateStorage:
    def __init__(self, db_path: str = "data/translator.db"):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()
        self._enabled_channels: set[int] = set()
        self._known_translated_ids: set[int] = set()

    def _init_sync(self) -> sqlite3.Connection:
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    async def connect(self) -> None:
        self._conn = await asyncio.to_thread(self._init_sync)
        await self._init_schema()
        await self._load_enabled_channels()

    async def _init_schema(self) -> None:
        await self.execute("""
        CREATE TABLE IF NOT EXISTS auto_translate_configs (
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            target_languages TEXT NOT NULL,
            output_mode TEXT NOT NULL DEFAULT 'text',
            sync_edits INTEGER NOT NULL DEFAULT 1,
            sync_deletes INTEGER NOT NULL DEFAULT 1,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """)
        await self.execute("""
        CREATE TABLE IF NOT EXISTS translation_messages (
            source_message_id INTEGER PRIMARY KEY,
            source_channel_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            source_author_id INTEGER NOT NULL,
            translated_message_ids TEXT NOT NULL,
            detected_source_language TEXT,
            source_content_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """)
        await self.execute(
            "CREATE INDEX IF NOT EXISTS idx_trans_channel ON translation_messages(source_channel_id);"
        )
        await self.execute(
            "CREATE INDEX IF NOT EXISTS idx_config_guild ON auto_translate_configs(guild_id);"
        )

        await self.execute("""
        CREATE TABLE IF NOT EXISTS update_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            enabled INTEGER NOT NULL DEFAULT 1,
            check_interval_hours INTEGER NOT NULL DEFAULT 6,
            include_prereleases INTEGER NOT NULL DEFAULT 0,
            notification_channel_id INTEGER,
            notify_owner INTEGER NOT NULL DEFAULT 1,
            running_version TEXT NOT NULL,
            latest_release_tag TEXT,
            latest_release_url TEXT,
            latest_release_title TEXT,
            latest_release_published_at TEXT,
            latest_release_body TEXT,
            last_notified_tag TEXT,
            last_check_timestamp TEXT,
            last_attempt_timestamp TEXT,
            last_check_status TEXT DEFAULT 'pending',
            last_check_error TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """)
        await self.execute("""
        CREATE TABLE IF NOT EXISTS update_notification_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            release_tag TEXT NOT NULL,
            destination_type TEXT NOT NULL,
            destination_id INTEGER NOT NULL,
            notified_at TEXT NOT NULL DEFAULT (datetime('now')),
            status TEXT NOT NULL,
            UNIQUE(release_tag, destination_type, destination_id)
        );
        """)

        await self.execute(
            """
            INSERT OR IGNORE INTO update_config (
                id, enabled, check_interval_hours, include_prereleases, running_version
            ) VALUES (1, 1, ?, ?, ?);
            """,
            (
                settings.update_check_interval_hours,
                int(settings.update_include_prereleases),
                settings.running_version,
            ),
        )
        await self.execute(
            "UPDATE update_config SET running_version = ? WHERE id = 1;",
            (settings.running_version,),
        )

    async def _load_enabled_channels(self) -> None:
        rows = await self.fetchall("SELECT channel_id FROM auto_translate_configs WHERE enabled = 1")
        self._enabled_channels = {row["channel_id"] for row in rows}

    def is_channel_enabled(self, channel_id: int) -> bool:
        return channel_id in self._enabled_channels

    def is_translated_message(self, message_id: int) -> bool:
        return message_id in self._known_translated_ids

    def track_translated_id(self, message_id: int) -> None:
        self._known_translated_ids.add(message_id)
        if len(self._known_translated_ids) > 10000:
            self._known_translated_ids = set(list(self._known_translated_ids)[-5000:])

    async def execute(self, query: str, params: tuple = ()) -> int:
        async with self._lock:
            def _run() -> int:
                with self._conn:
                    cur = self._conn.execute(query, params)
                    return cur.lastrowid or cur.rowcount
            return await asyncio.to_thread(_run)

    async def fetchone(self, query: str, params: tuple = ()) -> dict[str, Any] | None:
        async with self._lock:
            def _run() -> dict[str, Any] | None:
                cur = self._conn.execute(query, params)
                row = cur.fetchone()
                return dict(row) if row else None
            return await asyncio.to_thread(_run)

    async def fetchall(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        async with self._lock:
            def _run() -> list[dict[str, Any]]:
                cur = self._conn.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
            return await asyncio.to_thread(_run)

    async def set_channel_config(
        self,
        guild_id: int,
        channel_id: int,
        target_languages: list[str],
        output_mode: str = "text",
        sync_edits: bool = True,
        sync_deletes: bool = True,
        enabled: bool = True,
    ) -> None:
        langs_json = json.dumps([lang.lower().strip() for lang in target_languages])
        query = """
        INSERT INTO auto_translate_configs (
            channel_id, guild_id, target_languages, output_mode, sync_edits, sync_deletes, enabled, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(channel_id) DO UPDATE SET
            target_languages = excluded.target_languages,
            output_mode = excluded.output_mode,
            sync_edits = excluded.sync_edits,
            sync_deletes = excluded.sync_deletes,
            enabled = excluded.enabled,
            updated_at = datetime('now');
        """
        await self.execute(
            query,
            (
                channel_id,
                guild_id,
                langs_json,
                output_mode,
                int(sync_edits),
                int(sync_deletes),
                int(enabled),
            ),
        )
        if enabled:
            self._enabled_channels.add(channel_id)
        else:
            self._enabled_channels.discard(channel_id)

    async def get_channel_config(self, channel_id: int) -> dict[str, Any] | None:
        row = await self.fetchone("SELECT * FROM auto_translate_configs WHERE channel_id = ?", (channel_id,))
        if row:
            row["target_languages"] = json.loads(row["target_languages"])
            row["sync_edits"] = bool(row["sync_edits"])
            row["sync_deletes"] = bool(row["sync_deletes"])
            row["enabled"] = bool(row["enabled"])
        return row

    async def disable_channel(self, channel_id: int) -> None:
        await self.execute(
            "UPDATE auto_translate_configs SET enabled = 0, updated_at = datetime('now') WHERE channel_id = ?",
            (channel_id,),
        )
        self._enabled_channels.discard(channel_id)

    async def update_channel_languages(self, channel_id: int, target_languages: list[str]) -> None:
        langs_json = json.dumps([lang.lower().strip() for lang in target_languages])
        await self.execute(
            "UPDATE auto_translate_configs SET target_languages = ?, updated_at = datetime('now') WHERE channel_id = ?",
            (langs_json, channel_id),
        )

    async def update_channel_mode(self, channel_id: int, output_mode: str) -> None:
        await self.execute(
            "UPDATE auto_translate_configs SET output_mode = ?, updated_at = datetime('now') WHERE channel_id = ?",
            (output_mode, channel_id),
        )

    async def record_translation_message(
        self,
        source_message_id: int,
        source_channel_id: int,
        guild_id: int,
        source_author_id: int,
        translated_message_ids: list[int],
        detected_source_language: str,
        source_content_hash: str,
    ) -> None:
        for mid in translated_message_ids:
            self.track_translated_id(mid)

        query = """
        INSERT INTO translation_messages (
            source_message_id, source_channel_id, guild_id, source_author_id,
            translated_message_ids, detected_source_language, source_content_hash, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(source_message_id) DO UPDATE SET
            translated_message_ids = excluded.translated_message_ids,
            detected_source_language = excluded.detected_source_language,
            source_content_hash = excluded.source_content_hash,
            updated_at = datetime('now');
        """
        await self.execute(
            query,
            (
                source_message_id,
                source_channel_id,
                guild_id,
                source_author_id,
                json.dumps(translated_message_ids),
                detected_source_language,
                source_content_hash,
            ),
        )

    async def get_translation_message(self, source_message_id: int) -> dict[str, Any] | None:
        row = await self.fetchone(
            "SELECT * FROM translation_messages WHERE source_message_id = ?", (source_message_id,)
        )
        if row:
            row["translated_message_ids"] = json.loads(row["translated_message_ids"])
        return row

    async def delete_translation_message(self, source_message_id: int) -> None:
        await self.execute("DELETE FROM translation_messages WHERE source_message_id = ?", (source_message_id,))

    async def get_and_delete_batch_translations(self, source_message_ids: list[int]) -> list[dict[str, Any]]:
        if not source_message_ids:
            return []
        placeholders = ",".join("?" for _ in source_message_ids)
        rows = await self.fetchall(
            f"SELECT * FROM translation_messages WHERE source_message_id IN ({placeholders})",
            tuple(source_message_ids),
        )
        for r in rows:
            r["translated_message_ids"] = json.loads(r["translated_message_ids"])

        await self.execute(
            f"DELETE FROM translation_messages WHERE source_message_id IN ({placeholders})",
            tuple(source_message_ids),
        )
        return rows

    async def get_update_config(self) -> dict[str, Any]:
        row = await self.fetchone("SELECT * FROM update_config WHERE id = 1")
        if not row:
            await self.execute(
                "INSERT OR IGNORE INTO update_config (id, running_version) VALUES (1, ?)",
                (settings.running_version,),
            )
            row = await self.fetchone("SELECT * FROM update_config WHERE id = 1")
        data = dict(row)
        data["enabled"] = bool(data["enabled"])
        data["include_prereleases"] = bool(data["include_prereleases"])
        data["notify_owner"] = bool(data["notify_owner"])
        return data

    async def update_update_settings(self, **kwargs: Any) -> None:
        allowed = {
            "enabled",
            "check_interval_hours",
            "include_prereleases",
            "notification_channel_id",
            "notify_owner",
        }
        updates = []
        params = []
        for k, v in kwargs.items():
            if k in allowed:
                updates.append(f"{k} = ?")
                if isinstance(v, bool):
                    params.append(int(v))
                else:
                    params.append(v)
        if updates:
            updates.append("updated_at = datetime('now')")
            sql = f"UPDATE update_config SET {', '.join(updates)} WHERE id = 1"
            await self.execute(sql, tuple(params))

    async def record_update_check_success(self, release_dict: dict[str, Any]) -> None:
        query = """
        UPDATE update_config SET
            last_check_timestamp = datetime('now'),
            last_attempt_timestamp = datetime('now'),
            last_check_status = 'success',
            last_check_error = NULL,
            latest_release_tag = ?,
            latest_release_url = ?,
            latest_release_title = ?,
            latest_release_published_at = ?,
            latest_release_body = ?,
            updated_at = datetime('now')
        WHERE id = 1;
        """
        await self.execute(
            query,
            (
                release_dict.get("tag_name"),
                release_dict.get("html_url"),
                release_dict.get("name") or release_dict.get("tag_name"),
                release_dict.get("published_at"),
                release_dict.get("body") or "",
            ),
        )

    async def record_update_check_failure(self, status: str, error_message: str) -> None:
        query = """
        UPDATE update_config SET
            last_attempt_timestamp = datetime('now'),
            last_check_status = ?,
            last_check_error = ?,
            updated_at = datetime('now')
        WHERE id = 1;
        """
        await self.execute(query, (status, error_message))

    async def claim_notification(self, release_tag: str, destination_type: str, destination_id: int) -> bool:
        async with self._lock:
            def _claim() -> bool:
                try:
                    with self._conn:
                        self._conn.execute(
                            """
                            INSERT INTO update_notification_history (
                                release_tag, destination_type, destination_id, status
                            ) VALUES (?, ?, ?, 'pending')
                            """,
                            (release_tag, destination_type, destination_id),
                        )
                    return True
                except sqlite3.IntegrityError:
                    cur = self._conn.execute(
                        """
                        SELECT status FROM update_notification_history
                        WHERE release_tag = ? AND destination_type = ? AND destination_id = ?
                        """,
                        (release_tag, destination_type, destination_id),
                    )
                    row = cur.fetchone()
                    if row and row["status"] == "failed":
                        with self._conn:
                            self._conn.execute(
                                """
                                UPDATE update_notification_history SET status = 'pending'
                                WHERE release_tag = ? AND destination_type = ? AND destination_id = ?
                                """,
                                (release_tag, destination_type, destination_id),
                            )
                        return True
                    return False

            return await asyncio.to_thread(_claim)

    async def mark_notification_result(
        self, release_tag: str, destination_type: str, destination_id: int, status: str
    ) -> None:
        query = """
        UPDATE update_notification_history SET
            status = ?,
            notified_at = datetime('now')
        WHERE release_tag = ? AND destination_type = ? AND destination_id = ?;
        """
        await self.execute(query, (status, release_tag, destination_type, destination_id))

    async def set_last_notified_tag(self, release_tag: str) -> None:
        await self.execute(
            "UPDATE update_config SET last_notified_tag = ?, updated_at = datetime('now') WHERE id = 1;",
            (release_tag,),
        )

    async def close(self) -> None:
        async with self._lock:
            if self._conn:
                await asyncio.to_thread(self._conn.close)
                self._conn = None