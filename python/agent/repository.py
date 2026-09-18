"""SQLite repository for phase-one Agent domain state."""

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


class SQLiteRepository:
    TASK_STATUSES = {
        "created", "queued", "running", "waiting_approval", "retry_wait",
        "succeeded", "failed", "rejected", "expired", "cancelled", "timed_out",
    }
    TOOL_CALL_STATUSES = {
        "proposed", "waiting_approval", "running", "succeeded",
        "failed", "denied", "cancelled", "timed_out", "expired",
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
              title TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
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
            CREATE INDEX IF NOT EXISTS idx_todos_workspace_created
              ON todos(workspace_id, created_at);
            """
        )
        conversation_columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(conversations)").fetchall()
        }
        if "response_mode" not in conversation_columns:
            connection.execute(
                "ALTER TABLE conversations ADD COLUMN response_mode TEXT NOT NULL DEFAULT 'balanced'"
            )
        tool_call_columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(tool_calls)").fetchall()
        }
        if "continuation_json" not in tool_call_columns:
            connection.execute(
                "ALTER TABLE tool_calls ADD COLUMN continuation_json TEXT NOT NULL DEFAULT '{}'"
            )
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
        self, workspace_id: str, title: str = "", model_id: str = "", permission_mode: str = "workspace",
        response_mode: str = "balanced",
    ) -> dict[str, Any]:
        conversation_id = f"conv_{uuid.uuid4().hex}"
        now = _now()
        title = title.strip() or "新对话"
        async with self._lock:
            self._db().execute(
                """INSERT INTO conversations(
                     id,workspace_id,title,model_id,permission_mode,response_mode,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                (conversation_id, workspace_id, title, model_id, permission_mode, response_mode, now, now),
            )
            self._db().commit()
        return await self.get_conversation(workspace_id, conversation_id)

    async def check_workspace_access(self, workspace_id: str, user_id: str) -> str | None:
        async with self._lock:
            row = self._db().execute(
                "SELECT role FROM workspace_memberships WHERE workspace_id=? AND user_id=?",
                (workspace_id, user_id),
            ).fetchone()
        return None if row is None else str(row[0])

    async def list_conversations(self, workspace_id: str) -> list[dict[str, Any]]:
        async with self._lock:
            rows = self._db().execute(
                """SELECT c.*, COUNT(m.id) AS message_count FROM conversations c
                   LEFT JOIN messages m ON m.conversation_id=c.id
                   WHERE c.workspace_id=? GROUP BY c.id ORDER BY c.updated_at DESC""",
                (workspace_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    async def get_conversation(self, workspace_id: str, conversation_id: str) -> dict[str, Any]:
        async with self._lock:
            row = self._db().execute(
                """SELECT c.*, COUNT(m.id) AS message_count FROM conversations c
                   LEFT JOIN messages m ON m.conversation_id=c.id
                   WHERE c.workspace_id=? AND c.id=? GROUP BY c.id""",
                (workspace_id, conversation_id),
            ).fetchone()
        if row is None:
            raise KeyError(conversation_id)
        return dict(row)

    async def delete_conversation(self, workspace_id: str, conversation_id: str) -> None:
        async with self._lock:
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
        self, workspace_id: str, conversation_id: str, *, model_id: str | None = None,
        response_mode: str | None = None, permission_mode: str | None = None,
    ) -> dict[str, Any]:
        assignments: list[str] = []
        values: list[Any] = []
        for column, value in (
            ("model_id", model_id),
            ("response_mode", response_mode),
            ("permission_mode", permission_mode),
        ):
            if value is not None:
                assignments.append(f"{column}=?")
                values.append(value)
        if not assignments:
            return await self.get_conversation(workspace_id, conversation_id)
        assignments.append("updated_at=?")
        values.extend([_now(), workspace_id, conversation_id])
        async with self._lock:
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
        message = {"id": f"msg_{uuid.uuid4().hex}", "conversation_id": conversation_id, "role": role,
                   "content": content, "created_at": _now()}
        async with self._lock:
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
            rows = self._db().execute(
                "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at DESC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
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
            row = self._db().execute(
                "SELECT value_json FROM user_preferences WHERE workspace_id=? AND subject_user_id=? AND key=?",
                (workspace_id, user_id, key),
            ).fetchone()
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
            row = self._db().execute(
                "SELECT value_json FROM workspace_settings WHERE workspace_id=? AND key=?",
                (workspace_id, key),
            ).fetchone()
        return None if row is None else json.loads(row[0])

    async def record_audit(self, workspace_id: str, actor: str, action: str, resource: str,
                           result: str, details: dict[str, Any]) -> None:
        safe = {key: value for key, value in details.items() if "secret" not in key.lower() and "token" not in key.lower()}
        async with self._lock:
            self._db().execute(
                "INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?)",
                (f"audit_{uuid.uuid4().hex}", workspace_id, actor, action, resource, result,
                 json.dumps(safe, ensure_ascii=False, default=str), _now()),
            )
            self._db().commit()

    async def list_audit_events(self, workspace_id: str, limit: int = 100) -> list[dict[str, Any]]:
        limit = min(max(limit, 1), 500)
        async with self._lock:
            rows = self._db().execute(
                "SELECT * FROM audit_events WHERE workspace_id=? ORDER BY created_at DESC LIMIT ?",
                (workspace_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    async def create_task_state(
        self, task_id: str, workspace_id: str, conversation_id: str, title: str, status: str
    ) -> None:
        self._require_status(status, self.TASK_STATUSES, "task")
        now = _now()
        async with self._lock:
            self._db().execute(
                "INSERT INTO tasks VALUES(?,?,?,?,?,?,?)",
                (task_id, workspace_id, conversation_id, title, status, now, now),
            )
            self._db().commit()

    async def update_task_status(self, task_id: str, status: str) -> None:
        self._require_status(status, self.TASK_STATUSES, "task")
        async with self._lock:
            self._db().execute("UPDATE tasks SET status=?,updated_at=? WHERE id=?", (status, _now(), task_id))
            self._db().commit()

    async def create_tool_call(
        self, tool_call_id: str, workspace_id: str, conversation_id: str, task_id: str,
        tool_name: str, arguments: dict[str, Any], assistant_content: str = "",
        continuation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _now()
        async with self._lock:
            self._db().execute(
                """INSERT INTO tool_calls(
                     id,workspace_id,conversation_id,task_id,tool_name,arguments_json,
                     assistant_content,continuation_json,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (tool_call_id, workspace_id, conversation_id, task_id, tool_name,
                 json.dumps(arguments, ensure_ascii=False, sort_keys=True), assistant_content,
                 json.dumps(continuation or {}, ensure_ascii=False, sort_keys=True, default=str),
                 "proposed", now, now),
            )
            self._db().commit()
        return await self.get_tool_call(tool_call_id)

    async def get_tool_call(self, tool_call_id: str) -> dict[str, Any]:
        async with self._lock:
            row = self._db().execute("SELECT * FROM tool_calls WHERE id=?", (tool_call_id,)).fetchone()
        if row is None:
            raise KeyError(tool_call_id)
        return dict(row)

    async def update_tool_call(
        self, tool_call_id: str, status: str, *, risk_level: str = "",
        arguments: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None, summary: str = ""
    ) -> None:
        self._require_status(status, self.TOOL_CALL_STATUSES, "tool call")
        async with self._lock:
            self._db().execute(
                """UPDATE tool_calls SET status=?,risk_level=CASE WHEN ?='' THEN risk_level ELSE ? END,
                   arguments_json=COALESCE(?,arguments_json),
                   result_json=COALESCE(?,result_json),summary=CASE WHEN ?='' THEN summary ELSE ? END,
                   updated_at=? WHERE id=?""",
                (status, risk_level, risk_level,
                 None if arguments is None else json.dumps(
                     arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                 ),
                 None if result is None else json.dumps(result, ensure_ascii=False, default=str),
                 summary, summary, _now(), tool_call_id),
            )
            self._db().commit()

    async def create_approval(
        self, workspace_id: str, conversation_id: str, principal_id: str, task_id: str,
        tool_call_id: str, arguments: dict[str, Any], risk_level: str, ttl_minutes: int = 15
    ) -> dict[str, Any]:
        approval_id = f"approval_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc)
        normalized = json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        arguments_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        async with self._lock:
            self._db().execute(
                """INSERT INTO approvals VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (approval_id, workspace_id, conversation_id, principal_id, task_id, tool_call_id,
                 arguments_hash, risk_level, "pending", 1,
                 (now + timedelta(minutes=ttl_minutes)).isoformat(), now.isoformat(), None),
            )
            self._db().execute(
                """UPDATE tool_calls SET status='waiting_approval',risk_level=?,arguments_json=?,updated_at=?
                   WHERE id=?""",
                (risk_level, normalized, now.isoformat(), tool_call_id),
            )
            self._db().execute(
                "UPDATE tasks SET status='waiting_approval',updated_at=? WHERE id=?",
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
            row = self._db().execute(
                """SELECT a.*,t.tool_name,t.arguments_json,t.assistant_content
                   FROM approvals a JOIN tool_calls t ON t.id=a.tool_call_id
                   WHERE a.workspace_id=? AND a.id=?""",
                (workspace_id, approval_id),
            ).fetchone()
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
            expired = self._db().execute(
                """SELECT id,task_id,tool_call_id FROM approvals
                   WHERE workspace_id=? AND status='pending' AND expires_at<=?""",
                (workspace_id, now),
            ).fetchall()
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
                    "UPDATE tasks SET status='timed_out',updated_at=? WHERE id=?",
                    (now, item["task_id"]),
                )
                self._db().execute(
                    "INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?)",
                    (f"audit_{uuid.uuid4().hex}", workspace_id, "system", "approval.expired",
                     item["id"], "expired", "{}", now),
                )
            if expired:
                self._db().commit()
            rows = self._db().execute(query, params).fetchall()
        return [self._approval_value(row) for row in rows]

    async def decide_approval(
        self, workspace_id: str, approval_id: str, principal_id: str,
        decision: str, version: int
    ) -> dict[str, Any]:
        if decision not in {"allow", "deny"}:
            raise ValueError("decision must be allow or deny")
        now = datetime.now(timezone.utc)
        async with self._lock:
            row = self._db().execute(
                "SELECT * FROM approvals WHERE workspace_id=? AND id=?",
                (workspace_id, approval_id),
            ).fetchone()
            if row is None:
                raise KeyError(approval_id)
            item = dict(row)
            if item["principal_id"] != principal_id:
                raise PermissionError("approval belongs to another principal")
            if item["status"] != "pending":
                raise ValueError("approval has already been decided")
            if int(item["version"]) != version:
                raise ValueError("approval version conflict")
            call = self._db().execute(
                "SELECT arguments_json FROM tool_calls WHERE id=?", (item["tool_call_id"],)
            ).fetchone()
            current_hash = "" if call is None else hashlib.sha256(str(call["arguments_json"]).encode("utf-8")).hexdigest()
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
                    "UPDATE tasks SET status='failed',updated_at=? WHERE id=?",
                    (now.isoformat(), item["task_id"]),
                )
                self._db().commit()
                raise PermissionError("approval arguments no longer match the proposed tool call")
            if datetime.fromisoformat(item["expires_at"]) <= now:
                self._db().execute("UPDATE approvals SET status='expired',decided_at=?,version=version+1 WHERE id=?", (now.isoformat(), approval_id))
                self._db().execute("UPDATE tool_calls SET status='expired',updated_at=? WHERE id=?", (now.isoformat(), item["tool_call_id"]))
                self._db().execute("UPDATE tasks SET status='timed_out',updated_at=? WHERE id=?", (now.isoformat(), item["task_id"]))
                self._db().commit()
                raise ValueError("approval has expired")
            approval_status = "consumed" if decision == "allow" else "rejected"
            call_status = "running" if decision == "allow" else "denied"
            task_status = "running" if decision == "allow" else "cancelled"
            self._db().execute(
                "UPDATE approvals SET status=?,decided_at=?,version=version+1 WHERE id=?",
                (approval_status, now.isoformat(), approval_id),
            )
            self._db().execute(
                "UPDATE tool_calls SET status=?,updated_at=? WHERE id=?",
                (call_status, now.isoformat(), item["tool_call_id"]),
            )
            self._db().execute(
                "UPDATE tasks SET status=?,updated_at=? WHERE id=?",
                (task_status, now.isoformat(), item["task_id"]),
            )
            self._db().commit()
        return await self.get_approval(workspace_id, approval_id)

    @staticmethod
    def _require_status(status: str, allowed: set[str], resource: str) -> None:
        if status not in allowed:
            raise ValueError(f"invalid {resource} status: {status}")

    async def list_todos(self, workspace_id: str) -> list[dict[str, Any]]:
        async with self._lock:
            rows = self._db().execute(
                "SELECT * FROM todos WHERE workspace_id=? ORDER BY created_at,id", (workspace_id,)
            ).fetchall()
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
            cursor = self._db().execute(
                f"UPDATE todos SET {','.join(updates)} WHERE workspace_id=? AND id=?", params
            )
            self._db().commit()
        if cursor.rowcount == 0:
            raise KeyError(todo_id)
        return await self.list_todos(workspace_id)

    async def clear_todos(self, workspace_id: str) -> list[dict[str, Any]]:
        async with self._lock:
            self._db().execute("DELETE FROM todos WHERE workspace_id=?", (workspace_id,))
            self._db().commit()
        return []
