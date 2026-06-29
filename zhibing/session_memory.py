"""Lightweight SQLite-backed conversation memory for the v0 demo."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class SessionMemory:
    def __init__(self, db_path: str | Path = "zhibing_session_memory.sqlite3") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def open_or_create_session(self, scenario_id: str) -> str:
        session_id = str(uuid.uuid4())
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                "insert into sessions(session_id, scenario_id, created_at, updated_at) values (?, ?, ?, ?)",
                (session_id, scenario_id, now, now),
            )
        return session_id

    def latest_session_id(self, scenario_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "select session_id from sessions where scenario_id=? order by updated_at desc limit 1",
                (scenario_id,),
            ).fetchone()
        return str(row[0]) if row else None

    def add_message(self, session_id: str, role: str, content: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "insert into messages(session_id, role, content, created_at) values (?, ?, ?, ?)",
                (session_id, role, content, time.time()),
            )
            self._touch(conn, session_id)

    def add_constraint(self, session_id: str, patch: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "insert into constraints(session_id, patch_json, created_at) values (?, ?, ?)",
                (session_id, json.dumps(patch, ensure_ascii=False), time.time()),
            )
            self._touch(conn, session_id)

    def add_route_candidates(self, session_id: str, candidates: list[dict[str, Any]], selected_route_id: str | None) -> None:
        with self._connect() as conn:
            conn.execute("delete from route_candidates where session_id=?", (session_id,))
            for candidate in candidates:
                conn.execute(
                    "insert into route_candidates(session_id, candidate_json, selected, created_at) values (?, ?, ?, ?)",
                    (
                        session_id,
                        json.dumps(candidate, ensure_ascii=False),
                        1 if candidate.get("id") == selected_route_id else 0,
                        time.time(),
                    ),
                )
            self._touch(conn, session_id)

    def load_session(self, session_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            messages = [
                {"role": row[0], "content": row[1]}
                for row in conn.execute("select role, content from messages where session_id=? order by id", (session_id,))
            ]
            constraints = [
                json.loads(row[0])
                for row in conn.execute("select patch_json from constraints where session_id=? order by id", (session_id,))
            ]
            candidates = [
                dict(json.loads(row[0]), selected=bool(row[1]))
                for row in conn.execute(
                    "select candidate_json, selected from route_candidates where session_id=? order by id",
                    (session_id,),
                )
            ]
        return {"session_id": session_id, "messages": messages, "constraints": constraints, "route_candidates": candidates}

    def reset_session(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute("delete from messages where session_id=?", (session_id,))
            conn.execute("delete from constraints where session_id=?", (session_id,))
            conn.execute("delete from route_candidates where session_id=?", (session_id,))
            self._touch(conn, session_id)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("create table if not exists sessions(session_id text primary key, scenario_id text, created_at real, updated_at real)")
            conn.execute("create table if not exists messages(id integer primary key autoincrement, session_id text, role text, content text, created_at real)")
            conn.execute("create table if not exists constraints(id integer primary key autoincrement, session_id text, patch_json text, created_at real)")
            conn.execute("create table if not exists route_candidates(id integer primary key autoincrement, session_id text, candidate_json text, selected integer default 0, created_at real)")

    def _touch(self, conn: sqlite3.Connection, session_id: str) -> None:
        conn.execute("update sessions set updated_at=? where session_id=?", (time.time(), session_id))

