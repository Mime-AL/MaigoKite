"""SQLite repository for Agent domain state."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationBusyError(ValueError):
    """A conversation with unfinished work cannot be moved or removed."""


class MessageConflictError(ValueError):
    """A submission key was reused for a different request."""


class MessageReplay(Exception):
    """Return an existing product task; never execute a submitted message twice."""

    def __init__(self, task: dict[str, Any]) -> None:
        self.task = task
        super().__init__(str(task["id"]))


class SQLiteRepository:
    TASK_STATUSES = {
        "created",
        "queued",
        "running",
        "waiting_approval",
        "retry_wait",
        "succeeded",
        "failed",
        "rejected",
        "expired",
        "cancelled",
        "timed_out",
        "interrupted",
    }
    TOOL_CALL_STATUSES = {
        "proposed",
        "waiting_approval",
        "running",
        "succeeded",
        "failed",
        "denied",
        "cancelled",
        "timed_out",
        "expired",
    }
    APPROVAL_STATUSES = {"pending", "consumed", "rejected", "expired"}

    def __init__(self, path: str | Path) -> None:
        raw = str(path)
        self.path = raw if raw == ":memory:" else str(Path(raw).expanduser().resolve())
        self._connection: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()

    async def open(self) -> None:
        if self._connection is not None:
            return
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS workspaces (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conversations (
              id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
              title TEXT NOT NULL, model_id TEXT NOT NULL DEFAULT '', permission_mode TEXT NOT NULL,
              response_mode TEXT NOT NULL DEFAULT 'balanced',
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS workspace_folders (
              id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
              name TEXT NOT NULL, root_path TEXT NOT NULL, created_at TEXT NOT NULL,
              UNIQUE(workspace_id, root_path)
            );
            CREATE TABLE IF NOT EXISTS workspace_memberships (
              workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
              user_id TEXT NOT NULL, role TEXT NOT NULL,
              PRIMARY KEY(workspace_id, user_id)
            );
            CREATE INDEX IF NOT EXISTS idx_conversations_workspace_updated
              ON conversations(workspace_id, updated_at DESC);
            CREATE TABLE IF NOT EXISTS messages (
              id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
              role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
              ON messages(conversation_id, created_at);
            CREATE TABLE IF NOT EXISTS user_preferences (
              workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
              subject_user_id TEXT NOT NULL, key TEXT NOT NULL, value_json TEXT NOT NULL,
              updated_at TEXT NOT NULL, PRIMARY KEY(workspace_id, subject_user_id, key)
            );
            CREATE TABLE IF NOT EXISTS workspace_settings (
              workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
              key TEXT NOT NULL, value_json TEXT NOT NULL, updated_at TEXT NOT NULL,
              PRIMARY KEY(workspace_id, key)
            );
            CREATE TABLE IF NOT EXISTS audit_events (
              id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, actor TEXT NOT NULL,
              action TEXT NOT NULL, resource TEXT NOT NULL, result TEXT NOT NULL,
              details_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, conversation_id TEXT NOT NULL,
              title TEXT NOT NULL, status TEXT NOT NULL, input_text TEXT NOT NULL DEFAULT '',
              last_error TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_workspace_updated
              ON tasks(workspace_id, updated_at DESC);
            CREATE TABLE IF NOT EXISTS task_events (
              id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, conversation_id TEXT NOT NULL,
              task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
              sequence INTEGER NOT NULL, event_type TEXT NOT NULL,
              payload_json TEXT NOT NULL, occurred_at TEXT NOT NULL,
              UNIQUE(conversation_id, sequence)
            );
            CREATE INDEX IF NOT EXISTS idx_task_events_conversation_sequence
              ON task_events(conversation_id, sequence);
            CREATE TABLE IF NOT EXISTS tool_calls (
              id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, conversation_id TEXT NOT NULL,
              task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE, tool_name TEXT NOT NULL,
              arguments_json TEXT NOT NULL, assistant_content TEXT NOT NULL DEFAULT '',
              continuation_json TEXT NOT NULL DEFAULT '{}',
              result_json TEXT, summary TEXT NOT NULL DEFAULT '', status TEXT NOT NULL,
              risk_level TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tool_calls_conversation_created
              ON tool_calls(conversation_id, created_at);
            CREATE TABLE IF NOT EXISTS approvals (
              id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, conversation_id TEXT NOT NULL,
              principal_id TEXT NOT NULL, task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
              tool_call_id TEXT NOT NULL UNIQUE REFERENCES tool_calls(id) ON DELETE CASCADE,
              arguments_hash TEXT NOT NULL, risk_level TEXT NOT NULL, status TEXT NOT NULL,
              version INTEGER NOT NULL, expires_at TEXT NOT NULL, created_at TEXT NOT NULL,
              decided_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_approvals_workspace_status
              ON approvals(workspace_id, status, created_at DESC);
            CREATE TABLE IF NOT EXISTS todos (
              id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, text TEXT NOT NULL,
              done INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS questions (
              id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, conversation_id TEXT NOT NULL,
              task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
              tool_call_id TEXT NOT NULL UNIQUE REFERENCES tool_calls(id) ON DELETE CASCADE,
              principal_id TEXT NOT NULL, title TEXT NOT NULL, options_json TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending', version INTEGER NOT NULL DEFAULT 1,
              answer TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_questions_workspace_status ON questions(workspace_id,status);
            CREATE TABLE IF NOT EXISTS task_inputs (
              id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
              content TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued', created_at TEXT NOT NULL,
              idempotency_key TEXT NOT NULL, UNIQUE(task_id,idempotency_key)
            );
            CREATE INDEX IF NOT EXISTS idx_todos_workspace_created
              ON todos(workspace_id, created_at);
            CREATE TABLE IF NOT EXISTS user_memories (
              id TEXT PRIMARY KEY,
              workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
              subject_user_id TEXT NOT NULL,
              category TEXT NOT NULL,
              content TEXT NOT NULL,
              source_type TEXT NOT NULL,
              source_id TEXT NOT NULL,
              confidence REAL NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_user_memories_subject_updated
              ON user_memories(workspace_id, subject_user_id, updated_at DESC);
            """
        )
        conversation_columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(conversations)").fetchall()
        }
        if "response_mode" not in conversation_columns:
            connection.execute("ALTER TABLE conversations ADD COLUMN response_mode TEXT NOT NULL DEFAULT 'balanced'")
        for column, definition in (("folder_id", "TEXT NOT NULL DEFAULT ''"), ("archived", "INTEGER NOT NULL DEFAULT 0")):
            if column not in conversation_columns:
                connection.execute(f"ALTER TABLE conversations ADD COLUMN {column} {definition}")
        tool_call_columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(tool_calls)").fetchall()}
        if "continuation_json" not in tool_call_columns:
            connection.execute("ALTER TABLE tool_calls ADD COLUMN continuation_json TEXT NOT NULL DEFAULT '{}'")
        approval_columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(approvals)").fetchall()}
        if "note" not in approval_columns:
            connection.execute("ALTER TABLE approvals ADD COLUMN note TEXT NOT NULL DEFAULT ''")
        task_columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(tasks)").fetchall()}
        for column, definition in (
            ("input_text", "TEXT NOT NULL DEFAULT ''"),
            ("last_error", "TEXT NOT NULL DEFAULT ''"),
            ("version", "INTEGER NOT NULL DEFAULT 1"),
            ("request_hash", "TEXT NOT NULL DEFAULT ''"),
        ):
            if column not in task_columns:
                connection.execute(f"ALTER TABLE tasks ADD COLUMN {column} {definition}")
        connection.execute(
            """UPDATE conversations SET permission_mode=CASE permission_mode
                 WHEN 'plan' THEN 'read_only'
                 WHEN 'manual' THEN 'read_only'
                 WHEN 'accept_edits' THEN 'workspace'
                 WHEN 'auto' THEN 'full_access'
                 ELSE permission_mode END
               WHERE permission_mode IN ('plan','manual','accept_edits','auto')"""
        )
        connection.commit()
        self._connection = connection
        await self.ensure_workspace("personal", "Personal", "personal")
        async with self._lock:
            connection.execute(
                "INSERT OR IGNORE INTO workspace_memberships(workspace_id,user_id,role) VALUES(?,?,?)",
                ("personal", "local-user", "owner"),
            )
            connection.commit()

    async def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None

    def _db(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("repository is not open")
        return self._connection

    async def ensure_workspace(self, workspace_id: str, name: str, kind: str) -> dict[str, Any]:
        if kind not in {"personal", "team"}:
            raise ValueError("workspace kind must be personal or team")
        now = _now()
        async with self._lock:
            self._db().execute(
                "INSERT OR IGNORE INTO workspaces(id,name,kind,created_at,updated_at) VALUES(?,?,?,?,?)",
                (workspace_id, name, kind, now, now),
            )
            self._db().commit()
        return {"id": workspace_id, "name": name, "kind": kind}

    async def create_conversation(
        self,
        workspace_id: str,
        title: str = "",
        model_id: str = "",
        permission_mode: str = "workspace",
        response_mode: str = "balanced",
        folder_id: str = "",
    ) -> dict[str, Any]:
        conversation_id = f"conv_{uuid.uuid4().hex}"
        now = _now()
        title = title.strip() or "新对话"
        async with self._lock:
            self._require_folder(workspace_id, folder_id)
            self._db().execute(
                """INSERT INTO conversations(
                     id,workspace_id,title,model_id,permission_mode,response_mode,created_at,updated_at,folder_id
                   ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (conversation_id, workspace_id, title, model_id, permission_mode, response_mode, now, now, folder_id),
            )
            self._db().commit()
        return await self.get_conversation(workspace_id, conversation_id)

    async def check_workspace_access(self, workspace_id: str, user_id: str) -> str | None:
        async with self._lock:
            row = (
                self._db()
                .execute(
                    "SELECT role FROM workspace_memberships WHERE workspace_id=? AND user_id=?",
                    (workspace_id, user_id),
                )
                .fetchone()
            )
        return None if row is None else str(row[0])

    async def list_conversations(self, workspace_id: str) -> list[dict[str, Any]]:
        async with self._lock:
            rows = (
                self._db()
                .execute(
                    """SELECT c.*, COUNT(m.id) AS message_count FROM conversations c
                   LEFT JOIN messages m ON m.conversation_id=c.id
                   WHERE c.workspace_id=? GROUP BY c.id ORDER BY c.updated_at DESC""",
                    (workspace_id,),
                )
                .fetchall()
            )
        return [dict(row) for row in rows]

    async def get_conversation(self, workspace_id: str, conversation_id: str) -> dict[str, Any]:
        async with self._lock:
            row = (
                self._db()
                .execute(
                    """SELECT c.*, COUNT(m.id) AS message_count FROM conversations c
                   LEFT JOIN messages m ON m.conversation_id=c.id
                   WHERE c.workspace_id=? AND c.id=? GROUP BY c.id""",
                    (workspace_id, conversation_id),
                )
                .fetchone()
            )
        if row is None:
            raise KeyError(conversation_id)
        return dict(row)

    def _require_folder(self, workspace_id: str, folder_id: str) -> None:
        if folder_id and self._db().execute(
            "SELECT id FROM workspace_folders WHERE workspace_id=? AND id=?", (workspace_id, folder_id),
        ).fetchone() is None:
            raise KeyError(folder_id)

    def _require_idle_conversation(self, workspace_id: str, conversation_id: str) -> None:
        active = self._db().execute(
            """SELECT id FROM tasks WHERE workspace_id=? AND conversation_id=?
               AND status IN ('created','queued','running','waiting_approval','retry_wait') LIMIT 1""",
            (workspace_id, conversation_id),
        ).fetchone()
        if active:
            raise ConversationBusyError("请先停止或完成此对话中的任务，再移动、归档或删除。")

    async def list_workspace_folders(self, workspace_id: str) -> list[dict[str, Any]]:
        async with self._lock:
            rows = self._db().execute(
                "SELECT id,name,root_path FROM workspace_folders WHERE workspace_id=? ORDER BY created_at",
                (workspace_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    async def get_workspace_folder(self, workspace_id: str, folder_id: str) -> dict[str, Any]:
        async with self._lock:
            row = self._db().execute(
                "SELECT id,name,root_path FROM workspace_folders WHERE workspace_id=? AND id=?",
                (workspace_id, folder_id),
            ).fetchone()
        if row is None:
            raise KeyError(folder_id)
        return dict(row)

    async def create_workspace_folder(self, workspace_id: str, name: str, root_path: str) -> dict[str, Any]:
        async with self._lock:
            self._db().execute(
                "INSERT OR IGNORE INTO workspace_folders(id,workspace_id,name,root_path,created_at) VALUES(?,?,?,?,?)",
                (f"folder_{uuid.uuid4().hex}", workspace_id, name, root_path, _now()),
            )
            self._db().commit()
            row = self._db().execute(
                "SELECT id,name,root_path FROM workspace_folders WHERE workspace_id=? AND root_path=?",
                (workspace_id, root_path),
            ).fetchone()
        assert row is not None
        return dict(row)

    async def delete_conversation(self, workspace_id: str, conversation_id: str) -> list[str]:
        async with self._lock:
            self._require_idle_conversation(workspace_id, conversation_id)
            task_ids = [str(row[0]) for row in self._db().execute(
                "SELECT id FROM tasks WHERE workspace_id=? AND conversation_id=?", (workspace_id, conversation_id),
            ).fetchall()]
            self._db().execute(
                "DELETE FROM tasks WHERE workspace_id=? AND conversation_id=?",
                (workspace_id, conversation_id),
            )
            cursor = self._db().execute(
                "DELETE FROM conversations WHERE workspace_id=? AND id=?",
                (workspace_id, conversation_id),
            )
            self._db().commit()
        if cursor.rowcount == 0:
            raise KeyError(conversation_id)
        return task_ids

    async def update_conversation_permission(
        self, workspace_id: str, conversation_id: str, permission_mode: str
    ) -> dict[str, Any]:
        async with self._lock:
            cursor = self._db().execute(
                "UPDATE conversations SET permission_mode=?,updated_at=? WHERE workspace_id=? AND id=?",
                (permission_mode, _now(), workspace_id, conversation_id),
            )
            self._db().commit()
        if cursor.rowcount == 0:
            raise KeyError(conversation_id)
        return await self.get_conversation(workspace_id, conversation_id)

    async def update_conversation_settings(
        self,
        workspace_id: str,
        conversation_id: str,
        *,
        model_id: str | None = None,
        response_mode: str | None = None,
        permission_mode: str | None = None,
        title: str | None = None,
        folder_id: str | None = None,
        archived: bool | None = None,
    ) -> dict[str, Any]:
        assignments: list[str] = []
        values: list[Any] = []
        for column, value in (
            ("model_id", model_id),
            ("response_mode", response_mode),
            ("permission_mode", permission_mode),
            ("title", title),
            ("folder_id", folder_id),
            ("archived", archived),
        ):
            if value is not None:
                assignments.append(f"{column}=?")
                values.append(value)
        if not assignments:
            return await self.get_conversation(workspace_id, conversation_id)
        assignments.append("updated_at=?")
        values.extend([_now(), workspace_id, conversation_id])
        async with self._lock:
            if folder_id is not None:
                self._require_folder(workspace_id, folder_id)
            if folder_id is not None or archived is not None:
                self._require_idle_conversation(workspace_id, conversation_id)
            cursor = self._db().execute(
                f"UPDATE conversations SET {','.join(assignments)} WHERE workspace_id=? AND id=?",
                values,
            )
            self._db().commit()
        if cursor.rowcount == 0:
            raise KeyError(conversation_id)
        return await self.get_conversation(workspace_id, conversation_id)

    async def replace_conversation_model(
        self, workspace_id: str, previous_model_id: str, replacement_model_id: str
    ) -> None:
        async with self._lock:
            self._db().execute(
                """UPDATE conversations SET model_id=?,updated_at=?
                   WHERE workspace_id=? AND model_id=?""",
                (replacement_model_id, _now(), workspace_id, previous_model_id),
            )
            self._db().commit()

    async def append_message(self, conversation_id: str, role: str, content: str) -> dict[str, Any]:
        if role not in {"system", "user", "assistant", "tool"}:
            raise ValueError("invalid message role")
        message = {
            "id": f"msg_{uuid.uuid4().hex}",
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "created_at": _now(),
        }
        async with self._lock:
            if role == "user":
                self._db().execute(
                    """UPDATE conversations SET title=? WHERE id=? AND title='新对话'
                       AND NOT EXISTS(SELECT 1 FROM messages WHERE conversation_id=?)""",
                    (content[:28], conversation_id, conversation_id),
                )
            self._db().execute(
                "INSERT INTO messages(id,conversation_id,role,content,created_at) VALUES(:id,:conversation_id,:role,:content,:created_at)",
                message,
            )
            self._db().execute("UPDATE conversations SET updated_at=? WHERE id=?", (_now(), conversation_id))
            self._db().commit()
        return message

    async def list_messages(self, conversation_id: str, limit: int = 100) -> list[dict[str, Any]]:
        limit = min(max(limit, 1), 500)
        async with self._lock:
            rows = (
                self._db()
                .execute(
                    "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at DESC LIMIT ?",
                    (conversation_id, limit),
                )
                .fetchall()
            )
        return [dict(row) for row in reversed(rows)]

    async def save_preference(self, workspace_id: str, user_id: str, key: str, value: Any) -> None:
        async with self._lock:
            self._db().execute(
                """INSERT INTO user_preferences VALUES(?,?,?,?,?)
                   ON CONFLICT(workspace_id,subject_user_id,key)
                   DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at""",
                (workspace_id, user_id, key, json.dumps(value, ensure_ascii=False), _now()),
            )
            self._db().commit()

    async def get_preference(self, workspace_id: str, user_id: str, key: str) -> Any | None:
        async with self._lock:
            row = (
                self._db()
                .execute(
                    "SELECT value_json FROM user_preferences WHERE workspace_id=? AND subject_user_id=? AND key=?",
                    (workspace_id, user_id, key),
                )
                .fetchone()
            )
        return None if row is None else json.loads(row[0])

    async def save_workspace_setting(self, workspace_id: str, key: str, value: Any) -> None:
        async with self._lock:
            self._db().execute(
                """INSERT INTO workspace_settings VALUES(?,?,?,?)
                   ON CONFLICT(workspace_id,key)
                   DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at""",
                (workspace_id, key, json.dumps(value, ensure_ascii=False), _now()),
            )
            self._db().commit()

    async def get_workspace_setting(self, workspace_id: str, key: str) -> Any | None:
        async with self._lock:
            row = (
                self._db()
                .execute(
                    "SELECT value_json FROM workspace_settings WHERE workspace_id=? AND key=?",
                    (workspace_id, key),
                )
                .fetchone()
            )
        return None if row is None else json.loads(row[0])

    async def record_audit(
        self, workspace_id: str, actor: str, action: str, resource: str, result: str, details: dict[str, Any]
    ) -> None:
        safe = {
            key: value for key, value in details.items() if "secret" not in key.lower() and "token" not in key.lower()
        }
        async with self._lock:
            self._db().execute(
                "INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?)",
                (
                    f"audit_{uuid.uuid4().hex}",
                    workspace_id,
                    actor,
                    action,
                    resource,
                    result,
                    json.dumps(safe, ensure_ascii=False, default=str),
                    _now(),
                ),
            )
            self._db().commit()

    async def list_audit_events(self, workspace_id: str, limit: int = 100) -> list[dict[str, Any]]:
        limit = min(max(limit, 1), 500)
        async with self._lock:
            rows = (
                self._db()
                .execute(
                    "SELECT * FROM audit_events WHERE workspace_id=? ORDER BY created_at DESC LIMIT ?",
                    (workspace_id, limit),
                )
                .fetchall()
            )
        return [dict(row) for row in rows]

    async def create_task_state(
        self,
        task_id: str,
        workspace_id: str,
        conversation_id: str,
        title: str,
        status: str,
        input_text: str = "",
    ) -> None:
        self._require_status(status, self.TASK_STATUSES, "task")
        now = _now()
        async with self._lock:
            conversation = self._db().execute(
                "SELECT archived FROM conversations WHERE workspace_id=? AND id=?", (workspace_id, conversation_id),
            ).fetchone()
            if conversation is None:
                raise KeyError(conversation_id)
            if conversation["archived"]:
                raise ConversationBusyError("请先恢复归档对话，再发送消息。")
            self._db().execute(
                """INSERT INTO tasks(
                     id,workspace_id,conversation_id,title,status,input_text,last_error,
                     version,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (task_id, workspace_id, conversation_id, title, status, input_text, "", 1, now, now),
            )
            self._db().commit()

    async def check_message_replay(self, workspace_id: str, task_id: str, request_hash: str) -> None:
        if not request_hash:
            return
        async with self._lock:
            row = self._db().execute(
                "SELECT * FROM tasks WHERE workspace_id=? AND id=?", (workspace_id, task_id),
            ).fetchone()
        if row is not None:
            if not hmac.compare_digest(str(row["request_hash"]), request_hash):
                raise MessageConflictError("Idempotency-Key was already used for a different message")
            raise MessageReplay(dict(row))

    async def start_chat_turn(
        self, task_id: str, workspace_id: str, conversation_id: str, prompt: str, request_hash: str = "",
    ) -> None:
        """Atomically admit one turn and append its user message (not an execution checkpoint).

        Keyed task IDs are deterministic at the API boundary. A committed admission
        survives a crash; resubmitting that key only returns its task, including an
        interrupted task. A new execution always needs a new submission key.
        """
        now = _now()
        async with self._lock:
            db = self._db()
            with db:
                existing = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
                if existing is not None:
                    if (existing["workspace_id"] != workspace_id or existing["conversation_id"] != conversation_id
                            or not request_hash or not hmac.compare_digest(existing["request_hash"], request_hash)):
                        raise MessageConflictError("submission conflicts with an existing task")
                    raise MessageReplay(dict(existing))
                conversation = db.execute(
                    "SELECT archived FROM conversations WHERE workspace_id=? AND id=?", (workspace_id, conversation_id),
                ).fetchone()
                if conversation is None:
                    raise KeyError(conversation_id)
                if conversation["archived"]:
                    raise ConversationBusyError("请先恢复归档对话，再发送消息。")
                active = db.execute(
                    """SELECT id FROM tasks WHERE workspace_id=? AND conversation_id=?
                       AND status IN ('created','queued','running','waiting_approval','retry_wait') LIMIT 1""",
                    (workspace_id, conversation_id),
                ).fetchone()
                if active is not None:
                    raise ConversationBusyError("conversation has unfinished work; finish or cancel it first")
                db.execute(
                    """INSERT INTO tasks(id,workspace_id,conversation_id,title,status,input_text,request_hash,
                       created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (task_id, workspace_id, conversation_id, prompt[:80] or "Agent task", "running", prompt,
                     request_hash, now, now),
                )
                db.execute(
                    "INSERT INTO messages(id,conversation_id,role,content,created_at) VALUES(?,?,?,?,?)",
                    (f"msg_{uuid.uuid4().hex}", conversation_id, "user", prompt, now),
                )
                db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))

    async def update_task_status(self, task_id: str, status: str, last_error: str = "") -> None:
        self._require_status(status, self.TASK_STATUSES, "task")
        async with self._lock:
            cursor = self._db().execute(
                """UPDATE tasks SET status=?,last_error=?,version=version+1,updated_at=?
                   WHERE id=?""",
                (status, last_error, _now(), task_id),
            )
            self._db().commit()
        if cursor.rowcount == 0:
            raise KeyError(task_id)

    async def get_task(self, workspace_id: str, task_id: str) -> dict[str, Any]:
        async with self._lock:
            row = (
                self._db()
                .execute("SELECT * FROM tasks WHERE workspace_id=? AND id=?", (workspace_id, task_id))
                .fetchone()
            )
        if row is None:
            raise KeyError(task_id)
        return dict(row)

    async def list_tasks(self, workspace_id: str, conversation_id: str = "", limit: int = 100) -> list[dict[str, Any]]:
        limit = min(max(limit, 1), 500)
        sql = "SELECT * FROM tasks WHERE workspace_id=?"
        params: list[Any] = [workspace_id]
        if conversation_id:
            sql += " AND conversation_id=?"
            params.append(conversation_id)
        sql += " ORDER BY updated_at DESC,id DESC LIMIT ?"
        params.append(limit)
        async with self._lock:
            rows = self._db().execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    async def latest_conversation_task(self, workspace_id: str, conversation_id: str) -> dict[str, Any] | None:
        """Creation order, not updated_at: a resumed old task is not a new turn."""
        async with self._lock:
            row = self._db().execute(
                "SELECT * FROM tasks WHERE workspace_id=? AND conversation_id=? ORDER BY created_at DESC,rowid DESC LIMIT 1",
                (workspace_id, conversation_id),
            ).fetchone()
        return dict(row) if row is not None else None

    async def append_task_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        task_id = str(payload.get("task_id") or "")
        conversation_id = str(payload.get("conversation_id") or "")
        if not task_id or not conversation_id:
            return dict(payload)
        occurred_at = _now()
        event_id = f"event_{uuid.uuid4().hex}"
        async with self._lock:
            task = (
                self._db()
                .execute(
                    "SELECT workspace_id FROM tasks WHERE id=? AND conversation_id=?",
                    (task_id, conversation_id),
                )
                .fetchone()
            )
            if task is None:
                return dict(payload)
            sequence_row = (
                self._db()
                .execute(
                    "SELECT COALESCE(MAX(sequence),0)+1 FROM task_events WHERE conversation_id=?",
                    (conversation_id,),
                )
                .fetchone()
            )
            sequence = int(sequence_row[0])
            event_payload = dict(payload)
            enriched = {
                **payload,
                "event_id": event_id,
                "sequence": sequence,
                "occurred_at": occurred_at,
            }
            self._db().execute(
                """INSERT INTO task_events(
                     id,workspace_id,conversation_id,task_id,sequence,event_type,payload_json,occurred_at
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    event_id,
                    str(task["workspace_id"]),
                    conversation_id,
                    task_id,
                    sequence,
                    event_type,
                    json.dumps(event_payload, ensure_ascii=False, default=str),
                    occurred_at,
                ),
            )
            self._db().commit()
        return enriched

    async def list_task_events(
        self,
        workspace_id: str,
        conversation_id: str,
        after_sequence: int = 0,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        limit = min(max(limit, 1), 1000)
        async with self._lock:
            rows = (
                self._db()
                .execute(
                    """SELECT * FROM task_events
                   WHERE workspace_id=? AND conversation_id=? AND sequence>?
                   ORDER BY sequence LIMIT ?""",
                    (workspace_id, conversation_id, max(after_sequence, 0), limit),
                )
                .fetchall()
            )
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            try:
                item["payload"] = json.loads(str(item.pop("payload_json")))
            except (TypeError, json.JSONDecodeError):
                item["payload"] = {}
            result.append(item)
        return result

    async def recover_interrupted_tasks(self) -> list[dict[str, Any]]:
        """Mark work without a safe continuation checkpoint as explicitly interrupted."""
        interrupted: list[dict[str, Any]] = []
        now = _now()
        async with self._lock:
            rows = (
                self._db()
                .execute(
                    """SELECT * FROM tasks
                   WHERE status IN ('created','queued','running','retry_wait')"""
                )
                .fetchall()
            )
            for row in rows:
                item = dict(row)
                self._db().execute(
                    """UPDATE tasks SET status='interrupted',last_error=?,version=version+1,
                       updated_at=? WHERE id=?""",
                    ("Agent Core restarted before a safe continuation checkpoint", now, item["id"]),
                )
                item.update({"status": "interrupted", "updated_at": now})
                interrupted.append(item)
            self._db().commit()
        return interrupted

    async def interrupt_ephemeral_approvals(self, tool_names: set[str]) -> list[dict[str, Any]]:
        """Close approvals whose continuation depends on process-local resources."""
        if not tool_names:
            return []
        placeholders = ",".join("?" for _ in tool_names)
        now = _now()
        reason = "Process-local tool session was lost during Agent Core shutdown"
        interrupted: list[dict[str, Any]] = []
        async with self._lock:
            rows = (
                self._db()
                .execute(
                    f"""SELECT DISTINCT t.* FROM tasks t
                    JOIN approvals a ON a.task_id=t.id
                    JOIN tool_calls c ON c.id=a.tool_call_id
                    WHERE t.status='waiting_approval' AND a.status='pending'
                      AND c.tool_name IN ({placeholders})""",
                    tuple(sorted(tool_names)),
                )
                .fetchall()
            )
            for row in rows:
                item = dict(row)
                self._db().execute(
                    """UPDATE tasks SET status='interrupted',last_error=?,version=version+1,
                       updated_at=? WHERE id=?""",
                    (reason, now, item["id"]),
                )
                self._db().execute(
                    """UPDATE approvals SET status='rejected',decided_at=?,version=version+1
                       WHERE task_id=? AND status='pending'""",
                    (now, item["id"]),
                )
                self._db().execute(
                    """UPDATE tool_calls SET status='cancelled',updated_at=?
                       WHERE task_id=? AND status='waiting_approval'""",
                    (now, item["id"]),
                )
                item.update({"status": "interrupted", "last_error": reason, "updated_at": now})
                interrupted.append(item)
            self._db().commit()
        return interrupted

    async def cancel_task(self, workspace_id: str, task_id: str) -> dict[str, Any]:
        now = _now()
        async with self._lock:
            row = (
                self._db()
                .execute("SELECT * FROM tasks WHERE workspace_id=? AND id=?", (workspace_id, task_id))
                .fetchone()
            )
            if row is None:
                raise KeyError(task_id)
            if str(row["status"]) in {"succeeded", "failed", "cancelled", "timed_out", "expired"}:
                return dict(row)
            self._db().execute(
                """UPDATE tasks SET status='cancelled',last_error='Cancelled by user',
                   version=version+1,updated_at=? WHERE id=?""",
                (now, task_id),
            )
            self._db().execute(
                """UPDATE approvals SET status='rejected',decided_at=?,version=version+1
                   WHERE task_id=? AND status='pending'""",
                (now, task_id),
            )
            self._db().execute(
                "UPDATE questions SET status='cancelled',version=version+1 WHERE task_id=? AND status='pending'",
                (task_id,),
            )
            self._db().execute(
                """UPDATE tool_calls SET status='cancelled',updated_at=?
                   WHERE task_id=? AND status IN ('proposed','waiting_approval','running')""",
                (now, task_id),
            )
            self._db().commit()
        return await self.get_task(workspace_id, task_id)

    async def create_tool_call(
        self,
        tool_call_id: str,
        workspace_id: str,
        conversation_id: str,
        task_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        assistant_content: str = "",
        continuation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _now()
        async with self._lock:
            self._db().execute(
                """INSERT INTO tool_calls(
                     id,workspace_id,conversation_id,task_id,tool_name,arguments_json,
                     assistant_content,continuation_json,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    tool_call_id,
                    workspace_id,
                    conversation_id,
                    task_id,
                    tool_name,
                    json.dumps(arguments, ensure_ascii=False, sort_keys=True),
                    assistant_content,
                    json.dumps(continuation or {}, ensure_ascii=False, sort_keys=True, default=str),
                    "proposed",
                    now,
                    now,
                ),
            )
            self._db().commit()
        return await self.get_tool_call(tool_call_id)

    async def get_tool_call(self, tool_call_id: str) -> dict[str, Any]:
        async with self._lock:
            row = self._db().execute("SELECT * FROM tool_calls WHERE id=?", (tool_call_id,)).fetchone()
        if row is None:
            raise KeyError(tool_call_id)
        return dict(row)

    async def request_question(
        self, workspace_id: str, conversation_id: str, task_id: str, tool_call_id: str,
        principal_id: str, title: str, options: list[dict[str, Any]],
    ) -> dict[str, Any]:
        async with self._lock:
            db = self._db()
            with db:
                db.execute(
                    """INSERT OR IGNORE INTO questions(id,workspace_id,conversation_id,task_id,
                       tool_call_id,principal_id,title,options_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (f"question_{uuid.uuid4().hex}", workspace_id, conversation_id, task_id,
                     tool_call_id, principal_id, title, json.dumps(options, ensure_ascii=False), _now()),
                )
                # Keep the existing task-status DTO compatible with the GUI;
                # question.requested distinguishes this wait from an approval.
                db.execute("UPDATE tasks SET status='waiting_approval',updated_at=?,version=version+1 WHERE id=?",
                           (_now(), task_id))
                db.execute("UPDATE tool_calls SET status='waiting_approval',updated_at=? WHERE id=?",
                           (_now(), tool_call_id))
                row = db.execute("SELECT * FROM questions WHERE tool_call_id=?", (tool_call_id,)).fetchone()
        return dict(row)

    async def get_question(self, workspace_id: str, question_id: str) -> dict[str, Any]:
        async with self._lock:
            row = self._db().execute("SELECT * FROM questions WHERE workspace_id=? AND id=?",
                                     (workspace_id, question_id)).fetchone()
        if row is None:
            raise KeyError(question_id)
        return dict(row)

    async def list_questions(self, workspace_id: str, conversation_id: str = "") -> list[dict[str, Any]]:
        async with self._lock:
            rows = self._db().execute(
                """SELECT q.* FROM questions q JOIN tasks t ON t.id=q.task_id
                   WHERE q.workspace_id=? AND q.status='pending' AND t.status='waiting_approval'
                     AND (?='' OR q.conversation_id=?) ORDER BY q.created_at LIMIT 500""",
                (workspace_id, conversation_id, conversation_id),
            ).fetchall()
        return [dict(row) for row in rows]

    async def task_questions(self, workspace_id: str, task_id: str) -> list[dict[str, Any]]:
        async with self._lock:
            rows = self._db().execute("SELECT * FROM questions WHERE workspace_id=? AND task_id=?",
                                      (workspace_id, task_id)).fetchall()
        return [dict(row) for row in rows]

    async def submit_task_input(self, workspace_id: str, task_id: str, content: str,
                                idempotency_key: str) -> dict[str, Any]:
        if not content.strip() or len(content) > 10000 or not idempotency_key or len(idempotency_key) > 128:
            raise ValueError("content and an idempotency key (up to 128 characters) are required")
        async with self._lock:
            db = self._db()
            with db:
                task = db.execute("SELECT status FROM tasks WHERE workspace_id=? AND id=?",
                                  (workspace_id, task_id)).fetchone()
                if task is None:
                    raise KeyError(task_id)
                existing = db.execute("SELECT * FROM task_inputs WHERE task_id=? AND idempotency_key=?",
                                      (task_id, idempotency_key)).fetchone()
                if existing is not None:
                    if existing["content"] != content.strip():
                        raise ValueError("idempotency key was already used for another message")
                    return dict(existing)
                if task["status"] != "running":
                    raise ValueError("task is not running; resolve its pending interaction or send a new turn")
                count = db.execute("SELECT COUNT(*) FROM task_inputs WHERE task_id=? AND status='queued'", (task_id,)).fetchone()[0]
                if count >= 20:
                    raise ValueError("too many pending messages")
                item = {"id": f"input_{uuid.uuid4().hex}", "task_id": task_id, "content": content.strip(),
                        "status": "queued", "created_at": _now()}
                db.execute(
                    "INSERT INTO task_inputs(id,task_id,content,status,created_at,idempotency_key) VALUES(?,?,?,?,?,?)",
                    (item["id"], task_id, item["content"], item["status"], item["created_at"], idempotency_key),
                )
        return item

    async def task_inputs(self, workspace_id: str, task_id: str, *, pending: bool = False) -> list[dict[str, Any]]:
        await self.get_task(workspace_id, task_id)
        async with self._lock:
            rows = self._db().execute(
                """SELECT i.*,t.status AS task_status FROM task_inputs i JOIN tasks t ON t.id=i.task_id
                   WHERE t.workspace_id=? AND i.task_id=? AND (?=0 OR i.status='queued')
                   ORDER BY i.created_at,i.id LIMIT 500""", (workspace_id, task_id, int(pending)),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            task_status = item.pop("task_status")
            if item["status"] == "queued" and task_status not in {"running", "waiting_approval"}:
                item["status"] = "not_consumed"
            if not pending or item["status"] == "queued":
                result.append(item)
        return result

    async def consume_task_inputs(self, workspace_id: str, task_id: str, message_ids: set[str]) -> list[dict[str, Any]]:
        consumed = []
        async with self._lock:
            db = self._db()
            with db:
                rows = db.execute(
                    """SELECT i.*,t.conversation_id FROM task_inputs i JOIN tasks t ON t.id=i.task_id
                       WHERE t.workspace_id=? AND i.task_id=? AND i.status='queued'""",
                    (workspace_id, task_id),
                ).fetchall()
                for row in rows:
                    if row["id"] not in message_ids:
                        continue
                    db.execute("UPDATE task_inputs SET status='consumed' WHERE id=?", (row["id"],))
                    db.execute("INSERT OR IGNORE INTO messages VALUES(?,?,?,?,?)",
                               (row["id"], row["conversation_id"], "user", row["content"], row["created_at"]))
                    consumed.append({**dict(row), "status": "consumed"})
        return consumed

    async def answer_question(self, workspace_id: str, question_id: str, principal_id: str,
                              answer: str, version: int) -> dict[str, Any]:
        if not answer.strip() or len(answer) > 10000:
            raise ValueError("answer must contain 1 to 10000 characters")
        async with self._lock:
            db = self._db()
            with db:
                row = db.execute(
                    """SELECT q.*,t.status AS task_status FROM questions q JOIN tasks t ON t.id=q.task_id
                       WHERE q.workspace_id=? AND q.id=?""", (workspace_id, question_id),
                ).fetchone()
                if row is None:
                    raise KeyError(question_id)
                if row["principal_id"] != principal_id:
                    raise PermissionError("question belongs to another principal")
                if row["status"] != "pending" or row["version"] != version or row["task_status"] != "waiting_approval":
                    raise ValueError("question is no longer pending or its version changed")
                db.execute("UPDATE questions SET answer=?,status='answered',version=version+1 WHERE id=?",
                           (answer.strip(), question_id))
                db.execute("UPDATE tasks SET status='running',updated_at=?,version=version+1 WHERE id=?",
                           (_now(), row["task_id"]))
                db.execute(
                    "INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?)",
                    (f"audit_{uuid.uuid4().hex}", workspace_id, principal_id, "question.answered",
                     question_id, "answered", json.dumps({"version": version}, ensure_ascii=False), _now()),
                )
                # Visible history must also retain answers if a later run imports
                # product messages instead of a successfully completed checkpoint.
                db.execute("INSERT INTO messages(id,conversation_id,role,content,created_at) VALUES(?,?,?,?,?)",
                           (f"answer_{question_id}", row["conversation_id"], "user",
                            f"{row['title']}\n{answer.strip()}", _now()))
        return await self.get_question(workspace_id, question_id)

    async def inspect_task(self, workspace_id: str, task_id: str) -> dict[str, Any]:
        """Read one bounded GUI snapshot, scoped to the authenticated workspace.

        No runtime continuation or checkpoint is exposed. All queries run under
        the repository lock, so the projection cursor belongs to this snapshot.
        """
        async with self._lock:
            db = self._db()
            task = db.execute("SELECT * FROM tasks WHERE workspace_id=? AND id=?",
                              (workspace_id, task_id)).fetchone()
            if task is None:
                raise KeyError(task_id)
            calls = db.execute(
                """SELECT id,task_id,tool_name,arguments_json,result_json,summary,status,
                          risk_level,created_at,updated_at FROM tool_calls
                   WHERE workspace_id=? AND task_id=? ORDER BY created_at,id LIMIT 51""",
                (workspace_id, task_id),
            ).fetchall()
            approvals = db.execute(
                """SELECT a.*,t.tool_name,t.arguments_json FROM approvals a
                   JOIN tool_calls t ON t.id=a.tool_call_id
                   WHERE a.workspace_id=? AND a.task_id=? ORDER BY a.created_at LIMIT 51""",
                (workspace_id, task_id),
            ).fetchall()
            events = db.execute(
                """SELECT event_type,payload_json,sequence FROM task_events
                   WHERE workspace_id=? AND task_id=? AND event_type IN
                     ('plan.updated','context.updated','file.changed','message.completed','task.completed','task.succeeded')
                   ORDER BY sequence DESC LIMIT 101""",
                (workspace_id, task_id),
            ).fetchall()
            last_sequence = db.execute("SELECT COALESCE(MAX(sequence),0) FROM task_events WHERE task_id=?",
                                       (task_id,)).fetchone()[0]
            questions = db.execute("SELECT id,tool_call_id,title,options_json,status,version,answer FROM questions WHERE task_id=?",
                                   (task_id,)).fetchall()
        projection: dict[str, Any] = {
            "plan": None, "context": None, "changes": [], "summary": None,
            "questions": [{**{key: row[key] for key in row.keys() if key != "options_json"},
                           "options": json.loads(row["options_json"])} for row in questions],
            "truncated": len(calls) > 50 or len(approvals) > 50 or len(events) > 100,
        }
        for event in reversed(events[:100]):
            payload = json.loads(event["payload_json"])
            if event["event_type"] == "plan.updated":
                projection["plan"] = payload.get("items")
            elif event["event_type"] == "context.updated":
                projection["context"] = payload
            elif event["event_type"] == "file.changed":
                projection["changes"].append(payload)
            elif event["event_type"] == "message.completed":
                projection["summary"] = payload.get("content")
            elif event["event_type"] in {"task.succeeded", "task.completed"} and payload.get("summary") is not None:
                projection["summary"] = payload.get("summary")
        # Bound the wire snapshot independently of the number of rows. Large
        # evidence remains in event history; truncation is explicit to callers.
        remaining = 900_000
        def bounded(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            nonlocal remaining
            accepted = []
            for item in items:
                size = len(json.dumps(item, ensure_ascii=False).encode("utf-8"))
                if size > remaining:
                    projection["truncated"] = True
                    continue
                remaining -= size
                accepted.append(item)
            return accepted
        tool_calls = bounded([dict(row) for row in calls[:50]])
        approval_values = bounded([self._approval_value(row) for row in approvals[:50]])
        projection["changes"] = bounded(projection["changes"])
        projection["questions"] = bounded(projection["questions"])
        return {"task": dict(task), "tool_calls": tool_calls, "approvals": approval_values,
                "projection": projection, "last_sequence": int(last_sequence)}

    async def list_command_calls(self, workspace_id: str, conversation_id: str = "") -> list[dict[str, Any]]:
        async with self._lock:
            rows = self._db().execute(
                """SELECT c.*,t.status AS task_status FROM tool_calls c JOIN tasks t ON t.id=c.task_id
                   WHERE c.workspace_id=? AND c.tool_name IN ('exec_command','bash')
                     AND (?='' OR c.conversation_id=?) ORDER BY c.created_at DESC LIMIT 100""",
                (workspace_id, conversation_id, conversation_id),
            ).fetchall()
        return [dict(row) for row in rows]

    async def update_tool_call(
        self,
        tool_call_id: str,
        status: str,
        *,
        risk_level: str = "",
        arguments: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        summary: str = "",
    ) -> None:
        self._require_status(status, self.TOOL_CALL_STATUSES, "tool call")
        async with self._lock:
            self._db().execute(
                """UPDATE tool_calls SET status=?,risk_level=CASE WHEN ?='' THEN risk_level ELSE ? END,
                   arguments_json=COALESCE(?,arguments_json),
                   result_json=COALESCE(?,result_json),summary=CASE WHEN ?='' THEN summary ELSE ? END,
                   updated_at=? WHERE id=?""",
                (
                    status,
                    risk_level,
                    risk_level,
                    None
                    if arguments is None
                    else json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    None if result is None else json.dumps(result, ensure_ascii=False, default=str),
                    summary,
                    summary,
                    _now(),
                    tool_call_id,
                ),
            )
            self._db().commit()

    async def create_approval(
        self,
        workspace_id: str,
        conversation_id: str,
        principal_id: str,
        task_id: str,
        tool_call_id: str,
        arguments: dict[str, Any],
        risk_level: str,
        ttl_minutes: int = 15,
    ) -> dict[str, Any]:
        approval_id = f"approval_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc)
        normalized = json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        arguments_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        async with self._lock:
            self._db().execute(
                """INSERT INTO approvals(
                   id,workspace_id,conversation_id,principal_id,task_id,tool_call_id,
                   arguments_hash,risk_level,status,version,expires_at,created_at,decided_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    approval_id,
                    workspace_id,
                    conversation_id,
                    principal_id,
                    task_id,
                    tool_call_id,
                    arguments_hash,
                    risk_level,
                    "pending",
                    1,
                    (now + timedelta(minutes=ttl_minutes)).isoformat(),
                    now.isoformat(),
                    None,
                ),
            )
            self._db().execute(
                """UPDATE tool_calls SET status='waiting_approval',risk_level=?,arguments_json=?,updated_at=?
                   WHERE id=?""",
                (risk_level, normalized, now.isoformat(), tool_call_id),
            )
            self._db().execute(
                """UPDATE tasks SET status='waiting_approval',version=version+1,updated_at=?
                   WHERE id=?""",
                (now.isoformat(), task_id),
            )
            self._db().commit()
        return await self.get_approval(workspace_id, approval_id)

    @staticmethod
    def _approval_value(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["arguments"] = json.loads(item.pop("arguments_json"))
        return item

    async def get_approval(self, workspace_id: str, approval_id: str) -> dict[str, Any]:
        async with self._lock:
            row = (
                self._db()
                .execute(
                    """SELECT a.*,t.tool_name,t.arguments_json,t.assistant_content
                   FROM approvals a JOIN tool_calls t ON t.id=a.tool_call_id
                   WHERE a.workspace_id=? AND a.id=?""",
                    (workspace_id, approval_id),
                )
                .fetchone()
            )
        if row is None:
            raise KeyError(approval_id)
        return self._approval_value(row)

    async def list_approvals(
        self, workspace_id: str, conversation_id: str | None = None, status: str = "pending"
    ) -> list[dict[str, Any]]:
        query = """SELECT a.*,t.tool_name,t.arguments_json,t.assistant_content
                   FROM approvals a JOIN tool_calls t ON t.id=a.tool_call_id
                   WHERE a.workspace_id=? AND a.status=?"""
        params: list[Any] = [workspace_id, status]
        if conversation_id:
            query += " AND a.conversation_id=?"
            params.append(conversation_id)
        query += " ORDER BY a.created_at"
        async with self._lock:
            now = _now()
            expired = (
                self._db()
                .execute(
                    """SELECT id,task_id,tool_call_id FROM approvals
                   WHERE workspace_id=? AND status='pending' AND expires_at<=?""",
                    (workspace_id, now),
                )
                .fetchall()
            )
            for item in expired:
                self._db().execute(
                    "UPDATE approvals SET status='expired',decided_at=?,version=version+1 WHERE id=?",
                    (now, item["id"]),
                )
                self._db().execute(
                    "UPDATE tool_calls SET status='expired',updated_at=? WHERE id=?",
                    (now, item["tool_call_id"]),
                )
                self._db().execute(
                    """UPDATE tasks SET status='timed_out',last_error='Approval expired',
                       version=version+1,updated_at=? WHERE id=?""",
                    (now, item["task_id"]),
                )
                self._db().execute(
                    "INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?)",
                    (
                        f"audit_{uuid.uuid4().hex}",
                        workspace_id,
                        "system",
                        "approval.expired",
                        item["id"],
                        "expired",
                        "{}",
                        now,
                    ),
                )
            if expired:
                self._db().commit()
            rows = self._db().execute(query, params).fetchall()
        return [self._approval_value(row) for row in rows]

    async def decide_approval(
        self, workspace_id: str, approval_id: str, principal_id: str, decision: str, version: int,
        note: str = "",
    ) -> dict[str, Any]:
        if decision not in {"allow", "deny"}:
            raise ValueError("decision must be allow or deny")
        if not isinstance(note, str) or len(note) > 2000:
            raise ValueError("approval note must not exceed 2000 characters")
        note = note.strip()
        now = datetime.now(timezone.utc)
        async with self._lock:
            row = (
                self._db()
                .execute(
                    "SELECT * FROM approvals WHERE workspace_id=? AND id=?",
                    (workspace_id, approval_id),
                )
                .fetchone()
            )
            if row is None:
                raise KeyError(approval_id)
            item = dict(row)
            if item["principal_id"] != principal_id:
                raise PermissionError("approval belongs to another principal")
            if item["status"] != "pending":
                raise ValueError("approval has already been decided")
            if int(item["version"]) != version:
                raise ValueError("approval version conflict")
            task = self._db().execute(
                "SELECT status FROM tasks WHERE workspace_id=? AND id=?", (workspace_id, item["task_id"]),
            ).fetchone()
            if task is None or task["status"] != "waiting_approval":
                raise ValueError("task is no longer waiting for approval")
            call = (
                self._db()
                .execute("SELECT arguments_json FROM tool_calls WHERE id=?", (item["tool_call_id"],))
                .fetchone()
            )
            current_hash = (
                "" if call is None else hashlib.sha256(str(call["arguments_json"]).encode("utf-8")).hexdigest()
            )
            if not hmac.compare_digest(str(item["arguments_hash"]), current_hash):
                self._db().execute(
                    "UPDATE approvals SET status='rejected',decided_at=?,version=version+1 WHERE id=?",
                    (now.isoformat(), approval_id),
                )
                self._db().execute(
                    "UPDATE tool_calls SET status='denied',updated_at=? WHERE id=?",
                    (now.isoformat(), item["tool_call_id"]),
                )
                self._db().execute(
                    """UPDATE tasks SET status='failed',last_error='Approval arguments changed',
                       version=version+1,updated_at=? WHERE id=?""",
                    (now.isoformat(), item["task_id"]),
                )
                self._db().commit()
                raise PermissionError("approval arguments no longer match the proposed tool call")
            if datetime.fromisoformat(item["expires_at"]) <= now:
                self._db().execute(
                    "UPDATE approvals SET status='expired',decided_at=?,version=version+1 WHERE id=?",
                    (now.isoformat(), approval_id),
                )
                self._db().execute(
                    "UPDATE tool_calls SET status='expired',updated_at=? WHERE id=?",
                    (now.isoformat(), item["tool_call_id"]),
                )
                self._db().execute(
                    """UPDATE tasks SET status='timed_out',last_error='Approval expired',
                       version=version+1,updated_at=? WHERE id=?""",
                    (now.isoformat(), item["task_id"]),
                )
                self._db().commit()
                raise ValueError("approval has expired")
            approval_status = "consumed" if decision == "allow" else "rejected"
            call_status = "running" if decision == "allow" else "denied"
            task_status = "running" if decision == "allow" else "cancelled"
            with self._db() as db:
                db.execute(
                    "UPDATE approvals SET status=?,decided_at=?,note=?,version=version+1 WHERE id=?",
                    (approval_status, now.isoformat(), note, approval_id),
                )
                db.execute(
                    "UPDATE tool_calls SET status=?,updated_at=? WHERE id=?",
                    (call_status, now.isoformat(), item["tool_call_id"]),
                )
                db.execute(
                    "UPDATE tasks SET status=?,version=version+1,updated_at=? WHERE id=?",
                    (task_status, now.isoformat(), item["task_id"]),
                )
                if decision == "deny":
                    # Rejection ends this turn, not just the visible review
                    # card. No sibling proposal may remain actionable later.
                    db.execute(
                        """UPDATE approvals SET status='rejected',decided_at=?,version=version+1
                           WHERE task_id=? AND status='pending'""",
                        (now.isoformat(), item["task_id"]),
                    )
                    db.execute(
                        """UPDATE tool_calls SET status='cancelled',updated_at=? WHERE task_id=?
                           AND status IN ('proposed','waiting_approval','running')""",
                        (now.isoformat(), item["task_id"]),
                    )
                    db.execute(
                        "UPDATE questions SET status='cancelled',version=version+1 WHERE task_id=? AND status='pending'",
                        (item["task_id"],),
                    )
                # Decision and audit commit (or roll back) together.
                db.execute(
                    "INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?)",
                    (f"audit_{uuid.uuid4().hex}", workspace_id, principal_id, "approval.decided",
                     approval_id, "approved" if decision == "allow" else "denied",
                     json.dumps({"tool_call_id": item["tool_call_id"], "note": note,
                                 "version": version, "arguments_hash": item["arguments_hash"]},
                                ensure_ascii=False), now.isoformat()),
                )
        return await self.get_approval(workspace_id, approval_id)

    @staticmethod
    def _require_status(status: str, allowed: set[str], resource: str) -> None:
        if status not in allowed:
            raise ValueError(f"invalid {resource} status: {status}")

    async def list_todos(self, workspace_id: str) -> list[dict[str, Any]]:
        async with self._lock:
            rows = (
                self._db()
                .execute("SELECT * FROM todos WHERE workspace_id=? ORDER BY created_at,id", (workspace_id,))
                .fetchall()
            )
        return [{**dict(row), "done": bool(row["done"])} for row in rows]

    async def add_todo(self, workspace_id: str, text: str) -> list[dict[str, Any]]:
        now = _now()
        async with self._lock:
            self._db().execute(
                "INSERT INTO todos VALUES(?,?,?,?,?,?)",
                (f"todo_{uuid.uuid4().hex}", workspace_id, text, 0, now, now),
            )
            self._db().commit()
        return await self.list_todos(workspace_id)

    async def update_todo(
        self, workspace_id: str, todo_id: str, text: str | None = None, done: bool | None = None
    ) -> list[dict[str, Any]]:
        updates: list[str] = []
        params: list[Any] = []
        if text is not None:
            updates.append("text=?")
            params.append(text)
        if done is not None:
            updates.append("done=?")
            params.append(1 if done else 0)
        if not updates:
            raise ValueError("text or done is required for update")
        updates.append("updated_at=?")
        params.extend([_now(), workspace_id, todo_id])
        async with self._lock:
            cursor = self._db().execute(f"UPDATE todos SET {','.join(updates)} WHERE workspace_id=? AND id=?", params)
            self._db().commit()
        if cursor.rowcount == 0:
            raise KeyError(todo_id)
        return await self.list_todos(workspace_id)

    async def clear_todos(self, workspace_id: str) -> list[dict[str, Any]]:
        async with self._lock:
            self._db().execute("DELETE FROM todos WHERE workspace_id=?", (workspace_id,))
            self._db().commit()
        return []

    async def get_user_memory(self, workspace_id: str, subject_user_id: str, memory_id: str) -> dict[str, Any]:
        async with self._lock:
            row = (
                self._db()
                .execute(
                    """SELECT * FROM user_memories
                   WHERE workspace_id=? AND subject_user_id=? AND id=?""",
                    (workspace_id, subject_user_id, memory_id),
                )
                .fetchone()
            )
        if row is None:
            raise KeyError(memory_id)
        return dict(row)

    async def list_user_memories(
        self, workspace_id: str, subject_user_id: str, query: str = "", limit: int = 100
    ) -> list[dict[str, Any]]:
        limit = min(max(limit, 1), 500)
        sql = """SELECT * FROM user_memories
                 WHERE workspace_id=? AND subject_user_id=?"""
        params: list[Any] = [workspace_id, subject_user_id]
        normalized_query = query.strip().lower()
        if normalized_query:
            escaped = normalized_query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            sql += " AND lower(content) LIKE ? ESCAPE '\\'"
            params.append(f"%{escaped}%")
        sql += " ORDER BY updated_at DESC,id LIMIT ?"
        params.append(limit)
        async with self._lock:
            rows = self._db().execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    async def upsert_user_memory(
        self,
        workspace_id: str,
        subject_user_id: str,
        *,
        memory_id: str = "",
        category: str,
        content: str,
        source_type: str = "user",
        source_id: str = "",
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        now = _now()
        creating = not memory_id
        if creating:
            memory_id = f"memory_{uuid.uuid4().hex}"
        async with self._lock:
            try:
                if creating:
                    self._db().execute(
                        """INSERT INTO user_memories(
                             id,workspace_id,subject_user_id,category,content,source_type,
                             source_id,confidence,created_at,updated_at
                           ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                        (
                            memory_id,
                            workspace_id,
                            subject_user_id,
                            category,
                            content,
                            source_type,
                            source_id,
                            confidence,
                            now,
                            now,
                        ),
                    )
                else:
                    cursor = self._db().execute(
                        """UPDATE user_memories
                           SET category=?,content=?,confidence=?,updated_at=?
                           WHERE workspace_id=? AND subject_user_id=? AND id=?""",
                        (
                            category,
                            content,
                            confidence,
                            now,
                            workspace_id,
                            subject_user_id,
                            memory_id,
                        ),
                    )
                    if cursor.rowcount == 0:
                        raise KeyError(memory_id)
                self._db().execute(
                    "INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?)",
                    (
                        f"audit_{uuid.uuid4().hex}",
                        workspace_id,
                        subject_user_id,
                        "memory.created" if creating else "memory.updated",
                        memory_id,
                        "success",
                        json.dumps({"category": category}, ensure_ascii=False),
                        now,
                    ),
                )
                self._db().commit()
            except Exception:
                self._db().rollback()
                raise
        return await self.get_user_memory(workspace_id, subject_user_id, memory_id)

    async def delete_user_memory(self, workspace_id: str, subject_user_id: str, memory_id: str) -> None:
        async with self._lock:
            try:
                cursor = self._db().execute(
                    """DELETE FROM user_memories
                       WHERE workspace_id=? AND subject_user_id=? AND id=?""",
                    (workspace_id, subject_user_id, memory_id),
                )
                if cursor.rowcount == 0:
                    raise KeyError(memory_id)
                self._db().execute(
                    "INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?)",
                    (
                        f"audit_{uuid.uuid4().hex}",
                        workspace_id,
                        subject_user_id,
                        "memory.deleted",
                        memory_id,
                        "success",
                        "{}",
                        _now(),
                    ),
                )
                self._db().commit()
            except Exception:
                self._db().rollback()
                raise

    async def get_workspace_data_summary(self, workspace_id: str) -> dict[str, Any]:
        queries = {
            "conversation_count": "SELECT COUNT(*) FROM conversations WHERE workspace_id=?",
            "message_count": """SELECT COUNT(*) FROM messages m
                                JOIN conversations c ON c.id=m.conversation_id
                                WHERE c.workspace_id=?""",
            "memory_count": "SELECT COUNT(*) FROM user_memories WHERE workspace_id=?",
            "task_count": "SELECT COUNT(*) FROM tasks WHERE workspace_id=?",
            "audit_event_count": "SELECT COUNT(*) FROM audit_events WHERE workspace_id=?",
        }
        async with self._lock:
            result = {
                name: int(self._db().execute(query, (workspace_id,)).fetchone()[0]) for name, query in queries.items()
            }
        return {"storage_backend": "sqlite", **result}
