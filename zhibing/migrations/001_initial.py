"""Initial PostgreSQL/PostGIS schema for Zhibing.

This file is migration-ready SQL text for Alembic integration. It is kept pure
Python so the MVP can be reviewed without requiring a live PostgreSQL server.
"""

INITIAL_SQL = """
CREATE SCHEMA IF NOT EXISTS zhibing;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS zhibing.sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS zhibing.mission_plans (
    mission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES zhibing.sessions,
    user_intent TEXT,
    plan_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS zhibing.task_instances (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID REFERENCES zhibing.mission_plans,
    session_id UUID REFERENCES zhibing.sessions,
    step_id TEXT,
    actor_type TEXT,
    actor_id TEXT,
    bt_name TEXT,
    bt_args JSONB,
    state TEXT DEFAULT 'CREATED',
    expected_finish_at TIMESTAMPTZ,
    hard_timeout_at TIMESTAMPTZ,
    stall_timeout_secs INTEGER,
    last_status_at TIMESTAMPTZ,
    last_position JSONB,
    last_progress_rate NUMERIC,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS zhibing.vbs_requests (
    request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES zhibing.task_instances,
    request_type TEXT,
    payload JSONB,
    sent_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS zhibing.vbs_returns (
    return_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES zhibing.vbs_requests,
    task_id UUID REFERENCES zhibing.task_instances,
    payload JSONB,
    received_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS zhibing.scene_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES zhibing.task_instances,
    snapshot_data JSONB,
    captured_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS zhibing.decision_logs (
    decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES zhibing.sessions,
    task_id UUID REFERENCES zhibing.task_instances,
    user_intent TEXT,
    intent_json JSONB,
    selected_bt TEXT,
    selection_reason TEXT,
    parameters_sourced JSONB,
    bt_node_trace JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS zhibing.entity_states (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT,
    position JSONB,
    geom geometry(Point, 4326),
    health NUMERIC,
    status TEXT,
    current_bt TEXT,
    current_task_id UUID,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS zhibing.bt_registry (
    bt_name TEXT PRIMARY KEY,
    registry_json JSONB NOT NULL,
    active BOOLEAN DEFAULT true,
    phase_available TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);
"""


def upgrade(op) -> None:
    op.execute(INITIAL_SQL)


def downgrade(op) -> None:
    op.execute("DROP SCHEMA IF EXISTS zhibing CASCADE;")

