"""
PostgreSQL access for conversations and messages.
Uses DATABASE_URL or POSTGRES_* env vars for connection.
"""

import os
from typing import Any, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

DEFAULT_TOP_K = 20


def _get_connection_params():
    url = os.getenv("DATABASE_URL")
    if url:
        return {"dsn": url}
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "karb"),
        "user": os.getenv("POSTGRES_USER", "karb"),
        "password": os.getenv("POSTGRES_PASSWORD", "karb"),
    }


def get_connection():
    """Return a new connection. Caller must close it."""
    params = _get_connection_params()
    if "dsn" in params:
        return psycopg2.connect(params["dsn"], cursor_factory=RealDictCursor)
    return psycopg2.connect(cursor_factory=RealDictCursor, **params)


def load_messages(
    conversation_id: str,
    top_k: int = DEFAULT_TOP_K,
) -> List[dict]:
    """
    Load the most recent messages for a conversation (newest last for turn_history).
    Returns list of dicts with keys: role, content, created_at (oldest first).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT role, content, created_at
                FROM (
                  SELECT role, content, created_at
                  FROM message
                  WHERE conversation_id = %s
                  ORDER BY created_at DESC
                  LIMIT %s
                ) sub
                ORDER BY created_at ASC
                """,
                (conversation_id, top_k),
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def insert_message(
    conversation_id: str,
    role: str,
    content: str,
    *,
    ambiguous: bool = False,
    bot_trace: Optional[List[dict]] = None,
) -> Optional[str]:
    """
    Insert a message. Returns the new message id (UUID string) or None on error.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if role == "assistant":
                cur.execute(
                    """
                    INSERT INTO message (conversation_id, role, content, ambiguous, bot_trace)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id::text
                    """,
                    (
                        conversation_id,
                        role,
                        content,
                        ambiguous,
                        psycopg2.extras.Json(bot_trace) if bot_trace else None,
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO message (conversation_id, role, content)
                    VALUES (%s, %s, %s)
                    RETURNING id::text
                    """,
                    (conversation_id, role, content),
                )
            row = cur.fetchone()
            conn.commit()
            return row["id"] if row else None
    except Exception:
        conn.rollback()
        return None
    finally:
        conn.close()


def messages_to_turn_history(messages: List[dict]) -> List[str]:
    """Convert DB message rows to turn_history strings: 'User: ...' or 'Assistant: ...'."""
    out = []
    for m in messages:
        role = (m.get("role") or "user").lower()
        content = (m.get("content") or "").strip()
        if role == "user":
            out.append(f"User: {content}")
        else:
            out.append(f"Assistant: {content}")
    return out


# ---------------------------------------------------------------------------
# Users (auth)
# ---------------------------------------------------------------------------


def create_user(
    username: str, password_hash: str, email: Optional[str] = None
) -> Optional[str]:
    """Create a user. Returns id (UUID string) or None on conflict/error."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app_user (username, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id::text
                """,
                (username.strip(), email.strip() if email else None, password_hash),
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"] if row else None
    except Exception:
        conn.rollback()
        return None
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[dict]:
    """Return user row (id, username, email, password_hash, created_at) or None."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id::text, username, email, password_hash, created_at FROM app_user WHERE username = %s",
                (username.strip(),),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Return user row (id, username, email, created_at; no password_hash) or None."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id::text, username, email, created_at FROM app_user WHERE id = %s",
                (user_id.strip(),),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


def create_conversation(user_id: str, name: Optional[str] = None) -> Optional[str]:
    """Create a conversation for the user. Returns conversation id or None."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversation (user_id, name)
                VALUES (%s, %s)
                RETURNING id::text
                """,
                (user_id.strip(), name.strip() if name else None),
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"] if row else None
    except Exception:
        conn.rollback()
        return None
    finally:
        conn.close()


def get_conversation(conversation_id: str, user_id: str) -> Optional[dict]:
    """Return conversation row if it belongs to user_id, else None."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, user_id::text, name, created_at, rating, rated_at::text
                FROM conversation
                WHERE id = %s AND user_id = %s
                """,
                (conversation_id.strip(), user_id.strip()),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def list_conversations(user_id: str, limit: int = 100) -> List[dict]:
    """Return conversations for the user, newest first. Keys: id, user_id, name, created_at, rating, rated_at."""
    limit = min(max(1, limit), 500)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, user_id::text, name, created_at, rating, rated_at::text
                FROM conversation
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id.strip(), limit),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_conversation_rating(conversation_id: str, user_id: str, rating: int) -> bool:
    """Set conversation rating (1-5). Returns True if updated."""
    if not (1 <= rating <= 5):
        return False
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE conversation
                SET rating = %s, rated_at = now()
                WHERE id = %s AND user_id = %s
                """,
                (rating, conversation_id.strip(), user_id.strip()),
            )
            conn.commit()
            return cur.rowcount > 0
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Messages (get, rate)
# ---------------------------------------------------------------------------


def get_message_with_conversation(message_id: str) -> Optional[dict]:
    """Return message row plus conversation user_id for ownership check."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT m.id::text, m.conversation_id::text, m.role, m.content,
                       m.created_at, m.ambiguous, m.bot_trace, m.rating, m.rated_at,
                       c.user_id::text AS conversation_user_id
                FROM message m
                JOIN conversation c ON c.id = m.conversation_id
                WHERE m.id = %s
                """,
                (message_id.strip(),),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def get_latest_messages(conversation_id: str, limit: int = 2) -> List[dict]:
    """Return the latest messages (newest last)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, conversation_id::text, role, content, created_at::text,
                       ambiguous, bot_trace, rating, rated_at::text
                FROM message
                WHERE conversation_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (conversation_id.strip(), limit),
            )
            rows = cur.fetchall()
            # Oldest first for [user_msg, assistant_msg]
            return [dict(r) for r in reversed(rows)]
    finally:
        conn.close()


def list_messages(conversation_id: str, limit: int = 100) -> List[dict]:
    """Return messages for a conversation, oldest first (id, conversation_id, role, content, created_at, ambiguous, bot_trace, rating, rated_at)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, conversation_id::text, role, content, created_at::text,
                       ambiguous, bot_trace, rating, rated_at::text
                FROM message
                WHERE conversation_id = %s
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (conversation_id.strip(), limit),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_message_rating(message_id: str, user_id: str, rating: int) -> bool:
    """Set message rating (1-5). Message must be assistant and in user's conversation."""
    if not (1 <= rating <= 5):
        return False
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE message m
                SET rating = %s, rated_at = now()
                FROM conversation c
                WHERE m.conversation_id = c.id AND c.user_id = %s
                  AND m.id = %s AND m.role = 'assistant'
                """,
                (rating, user_id.strip(), message_id.strip()),
            )
            conn.commit()
            return cur.rowcount > 0
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()
