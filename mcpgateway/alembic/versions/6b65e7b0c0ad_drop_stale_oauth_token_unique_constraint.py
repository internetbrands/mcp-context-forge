# -*- coding: utf-8 -*-
"""Location: ./mcpgateway/alembic/versions/6b65e7b0c0ad_drop_stale_oauth_token_unique_constraint.py
Copyright 2026
SPDX-License-Identifier: Apache-2.0
Authors: Mihai Criveti

drop_stale_oauth_token_unique_constraint

Drop the legacy ``unique_gateway_user`` unique constraint on
``(gateway_id, user_id)`` left behind when migration
``14ac971cee42`` (add_user_context_to_oauth_tokens) shifted per-user
uniqueness to ``(gateway_id, app_user_email)`` without removing the
original constraint.

Leaving the stale constraint in place blocks any second ContextForge
user from authorising against a gateway whose OAuth provider returns
an organisation-scoped or otherwise non-per-user subject claim —
causing a UniqueViolation on the second user's callback.

See: https://github.com/IBM/mcp-context-forge/issues/5066

Revision ID: 6b65e7b0c0ad
Revises: e28566875fa4
Create Date: 2026-06-09 00:00:00.000000
"""

# Standard
from typing import Sequence, Union

# Third-Party
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "6b65e7b0c0ad"  # pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = "e28566875fa4"  # pragma: allowlist secret
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT_NAME = "unique_gateway_user"
_TABLE_NAME = "oauth_tokens"


def _unique_constraint_exists(conn: sa.engine.Connection, table: str, constraint: str) -> bool:
    """Return True if a named unique constraint exists on the given table."""
    dialect = conn.dialect.name.lower()
    if dialect == "postgresql":
        row = conn.execute(
            sa.text(
                "SELECT 1 FROM pg_constraint "
                "WHERE conrelid = :table::regclass AND conname = :name AND contype = 'u'"
            ),
            {"table": table, "name": constraint},
        ).fetchone()
        return row is not None
    if dialect == "sqlite":
        row = conn.execute(
            sa.text("SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = :name"),
            {"name": constraint},
        ).fetchone()
        return row is not None
    # Generic fallback via inspector
    inspector = sa.inspect(conn)
    for uc in inspector.get_unique_constraints(table):
        if uc.get("name") == constraint:
            return True
    return False


def upgrade() -> None:
    """Drop the stale unique_gateway_user constraint on (gateway_id, user_id)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if _TABLE_NAME not in inspector.get_table_names():
        return

    if not _unique_constraint_exists(conn, _TABLE_NAME, _CONSTRAINT_NAME):
        return

    dialect = conn.dialect.name.lower()
    if dialect == "sqlite":
        with op.batch_alter_table(_TABLE_NAME) as batch_op:
            batch_op.drop_constraint(_CONSTRAINT_NAME, type_="unique")
    else:
        op.drop_constraint(_CONSTRAINT_NAME, _TABLE_NAME, type_="unique")


def downgrade() -> None:
    """Re-add the legacy unique_gateway_user constraint on (gateway_id, user_id)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if _TABLE_NAME not in inspector.get_table_names():
        return

    dialect = conn.dialect.name.lower()
    if dialect == "sqlite":
        with op.batch_alter_table(_TABLE_NAME) as batch_op:
            batch_op.create_unique_constraint(_CONSTRAINT_NAME, ["gateway_id", "user_id"])
    else:
        op.create_unique_constraint(_CONSTRAINT_NAME, _TABLE_NAME, ["gateway_id", "user_id"])
