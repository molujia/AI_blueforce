# ZHIBING DECISION SYSTEM 鈥?ARCHITECTURE & DEVELOPMENT PLAN
# Version: 1.0 | Audience: AI architect / AI coding agent
# Purpose: This document is a harness. An AI reading this should be able to
#          begin laying out the full system architecture and implementation plan
#          without additional context. All decisions are pre-made; do not
#          second-guess them. Follow exactly.

---

## READING INSTRUCTIONS FOR AI

1. Read ALL sections before writing any code or file structure.
2. Sections marked `[CONSTRAINT]` are hard rules. Never violate them.
3. Sections marked `[DECISION]` are pre-made design decisions. Do not propose alternatives.
4. Sections marked `[TASK]` are concrete implementation tasks with clear deliverables.
5. When a section references another section, resolve it before proceeding.
6. Implementation order follows: PHASE_MVP 鈫?PHASE_V1 鈫?PHASE_V2 鈫?PHASE_V3.
7. Do not start PHASE_V1 until all PHASE_MVP tasks pass their ACCEPTANCE_CRITERIA.

---

## SECTION 1: SYSTEM IDENTITY

```
SYSTEM_NAME      : Zhibing LLM Decision System (鏅哄叺鍐崇瓥绯荤粺)
SYSTEM_ROLE      : LLM acts as planner/orchestrator; behavior trees handle real-time execution.
SIMULATION_ENGINE: VBS (Virtual Battlespace)
BT_RUNTIME       : VBS built-in behavior tree runtime (.btset / .bt files, SQF scripting)
LANGUAGE_STACK   : Python (orchestration layer), SQF (VBS adapter), PostgreSQL + PostGIS (data)
```

---

## SECTION 2: ARCHITECTURAL LAYERS

The system is divided into exactly FOUR layers. No merging or splitting of layers is permitted.

```
LAYER_1: USER_INTERFACE
  - Accepts: natural language commands, regulatory text, manual confirmations
  - Emits:   human-readable task status, explainability reports

LAYER_2: LLM_DECISION_LAYER
  - Role:    low-frequency planner / orchestrator / parameter generator
  - NEVER:   directly controls soldiers in real-time
  - NEVER:   emits SQF scripts
  - ALWAYS:  emits structured JSON (Intent 鈫?TaskPlan 鈫?BTCommand)
  - Modules: A_IntentRecognition, B_SceneQuery, C_TaskPlanner,
             D_BTSelector, E_ParamGenerator, F_StateManager,
             G_Replanner, H_ExplainabilityLogger

LAYER_3: VBS_ADAPTER
  - Role:    translate structured JSON into SQF calls; collect and classify VBS status
  - Accepts: TaskSubmitRequest (JSON), StatusQueryRequest (JSON)
  - Emits:   TaskStatusResponse (JSON)
  - Internal steps: auth 鈫?queue 鈫?compile_to_sqf 鈫?loadBTSet 鈫?setBT 鈫?                    setBBVariable 鈫?receiveMessage 鈫?poll_status 鈫?classify_return

LAYER_4: VBS_ENGINE
  - Role:    high-frequency tactical execution
  - Handles: emergency avoidance locally (does NOT return to upper layer)
  - Returns: non-emergency failure codes to LAYER_3
  - BT files: grpSimpleMoveNoAuto, GrpMove, GrpMove2, grpFollowFormation
```

**Data flow:**
```
USER_INTERFACE
    鈫? natural language / reports
LAYER_2: LLM_DECISION_LAYER
    鈫? TaskSubmitRequest / StatusQueryRequest  (JSON over internal API)
LAYER_3: VBS_ADAPTER
    鈫? SQF function calls
LAYER_4: VBS_ENGINE
```

---

## SECTION 3: HARD CONSTRAINTS

```
[CONSTRAINT-01] LLM_NO_SQF_OUTPUT
  The LLM layer MUST NOT generate SQF scripts directly.
  LLM outputs structured JSON only. LAYER_3 compiles JSON 鈫?SQF.
  Rationale: prevent script injection, maintain auditability.

[CONSTRAINT-02] NO_MODIFY_RUNNING_BT
  A behavior tree that is RUNNING must not have its parameters or structure
  modified in place. The only valid update strategy:
    wait for LAYER_4 to return a safe update point
    (status 鈭?{WAIT_UPPER, SUCCEEDED, FAILED, ABORTED})
    then LAYER_2 submits a new TaskSubmitRequest.
  Rationale: blackboard variable consistency, VBS runtime stability.

[CONSTRAINT-03] CALL_BEFORE_GENERATE
  In PHASE_MVP and PHASE_V1, the LLM MUST NOT generate new .bt files.
  It may only select from the BT_REGISTRY.
  New BT generation is allowed only in PHASE_V2 and only via the
  BT_GENERATION_PIPELINE defined in SECTION 10.

[CONSTRAINT-04] SEPARATE_SUBMIT_AND_QUERY
  While a task is in state {CREATED, DISPATCHED, ACKED, RUNNING},
  LAYER_2 MUST NOT submit a new TaskSubmitRequest for the same actor.
  It may only issue StatusQueryRequests.
  Submitting a new task is only allowed after the current task reaches
  a terminal or interruptible state.

[CONSTRAINT-05] TIMEOUT_IS_UPPER_LAYER_RESPONSIBILITY
  LAYER_4 (VBS) does not judge timeouts.
  LAYER_2 computes dynamic timeouts using TIMEOUT_FORMULA (SECTION 8).
  Hard-coded timeout values (e.g. 300s) are forbidden.

[CONSTRAINT-06] COORDINATES_MUST_HAVE_FRAME
  No bare coordinate arrays like [40.24, 116.11, 120.0] anywhere in the system.
  Every coordinate object must include a `frame` field.
  Valid frames: "WGS84_LATLON_ALT" | "VBS_LOCAL_XYZ"
  Coordinate conversion is handled by a dedicated CoordService.
  Note: GeoJSON RFC 7946 uses [longitude, latitude] order 鈥?always be explicit.

[CONSTRAINT-07] EXPLAINABILITY_FROM_DAY_ONE
  Every BT selection, parameter source, node trace, and return code
  must be written to decision_log from PHASE_MVP onward.
  Explainability is not optional and must not be deferred to later phases.
```

---

## SECTION 4: BT REGISTRY

The BT_REGISTRY is a JSON file / database table that LAYER_2 queries to select behavior trees.
It is the single source of truth for what VBS can execute.

**Schema per entry:**
```json
{
  "bt_name": "<string>",
  "btset_path": "<absolute path to .btset file>",
  "scope": "group | soldier",
  "capabilities": ["<capability_tag>"],
  "required_args": [
    {"name": "<arg_name>", "type": "<sqf_type>", "description": "<string>"}
  ],
  "optional_args": [
    {"name": "<arg_name>", "type": "<sqf_type>", "default": "<value>"}
  ],
  "return_codes": ["SUCCESS", "UNREACHABLE", "SUBTASK_FAILED", "TIMEOUT", "..."],
  "safe_update_points": ["end", "upper_waiting_leaf", "SubTaskEnd"],
  "explainable_nodes": [
    {"node": "<node_name_in_bt>", "meaning": "<human_readable_description>"}
  ],
  "incompatible_with": ["<other_bt_name>"],
  "phase_available": "MVP"
}
```

**Initial registry entries (parsed from existing .bt files):**
```json
[
  {
    "bt_name": "grpSimpleMoveNoAuto",
    "scope": "group",
    "capabilities": ["group_move", "set_formation", "maintain_formation_direction"],
    "required_args": [
      {"name": "moveDest", "type": "array", "description": "destination coordinate object"},
      {"name": "formation", "type": "string", "description": "formation type identifier"}
    ],
    "optional_args": [],
    "return_codes": ["SUCCESS", "UNREACHABLE"],
    "safe_update_points": ["end"],
    "phase_available": "MVP"
  },
  {
    "bt_name": "GrpMove",
    "scope": "group",
    "capabilities": ["group_move", "set_speed", "set_formation", "dispatch_child_follow"],
    "required_args": [
      {"name": "movePos", "type": "array", "description": "destination coordinate object"},
      {"name": "speed", "type": "number", "description": "movement speed in m/s"}
    ],
    "optional_args": [
      {"name": "fmInfoTable", "type": "array", "default": []}
    ],
    "return_codes": ["SUCCESS", "UNREACHABLE", "SUBTASK_FAILED", "TIMEOUT"],
    "safe_update_points": ["end", "upper_waiting_leaf"],
    "explainable_nodes": [
      {"node": "BTArg init", "meaning": "reads movePos, speed, formation parameters from blackboard"},
      {"node": "move", "meaning": "executes group movement toward destination"},
      {"node": "adjust speed", "meaning": "adjusts member speeds based on formation distance"}
    ],
    "phase_available": "MVP"
  },
  {
    "bt_name": "GrpMove2",
    "scope": "group",
    "capabilities": ["group_move", "individual_destinations", "set_speed"],
    "required_args": [
      {"name": "movePosArr", "type": "array", "description": "array of coordinate objects, one per member"},
      {"name": "speed", "type": "number", "description": "movement speed"},
      {"name": "dir", "type": "number", "description": "facing direction in degrees"}
    ],
    "optional_args": [],
    "return_codes": ["SUCCESS", "SUBTASK_FAILED"],
    "safe_update_points": ["SubTaskEnd"],
    "phase_available": "MVP"
  },
  {
    "bt_name": "grpFollowFormation",
    "scope": "group",
    "capabilities": ["formation_follow"],
    "required_args": [],
    "optional_args": [],
    "return_codes": ["GrpMoveEnd"],
    "safe_update_points": ["message_driven"],
    "phase_available": "MVP"
  }
]
```

---

## SECTION 5: JSON PROTOCOL SCHEMAS

All inter-layer communication uses these schemas. Implement as JSON Schema (Draft 7).

### 5.1 CoordinateObject
```json
{
  "oneOf": [
    {
      "type": "object",
      "required": ["frame", "lat", "lon", "alt"],
      "properties": {
        "frame": {"const": "WGS84_LATLON_ALT"},
        "lat": {"type": "number"},
        "lon": {"type": "number"},
        "alt": {"type": "number"}
      }
    },
    {
      "type": "object",
      "required": ["frame", "x", "y", "z"],
      "properties": {
        "frame": {"const": "VBS_LOCAL_XYZ"},
        "x": {"type": "number"},
        "y": {"type": "number"},
        "z": {"type": "number"}
      }
    }
  ]
}
```

### 5.2 TaskSubmitRequest
```json
{
  "type": "object",
  "required": ["request_id", "session_id", "actor", "task", "timeout_policy", "callback_policy"],
  "properties": {
    "request_id":  {"type": "string"},
    "session_id":  {"type": "string"},
    "scenario_id": {"type": "string"},
    "actor": {
      "type": "object",
      "required": ["type", "id"],
      "properties": {
        "type": {"enum": ["group", "soldier"]},
        "id":   {"type": "string"}
      }
    },
    "task": {
      "type": "object",
      "required": ["task_type", "btset_path", "bt_name", "bt_scope", "bt_args"],
      "properties": {
        "task_type":   {"type": "string"},
        "btset_path":  {"type": "string"},
        "bt_name":     {"type": "string"},
        "bt_scope":    {"enum": ["group", "soldier"]},
        "bt_args":     {"type": "object"}
      }
    },
    "timeout_policy": {
      "type": "object",
      "required": ["expected_seconds", "hard_timeout_seconds", "stall_timeout_seconds"],
      "properties": {
        "expected_seconds":       {"type": "number"},
        "hard_timeout_seconds":   {"type": "number"},
        "stall_timeout_seconds":  {"type": "number"}
      }
    },
    "callback_policy": {
      "type": "object",
      "required": ["return_on"],
      "properties": {
        "return_on": {
          "type": "array",
          "items": {"enum": ["SUCCESS", "UNREACHABLE", "SUBTASK_FAILED", "PARAM_ERROR",
                             "BT_LOAD_ERROR", "ACTOR_NOT_FOUND", "WAIT_UPPER", "TIMEOUT"]}
        }
      }
    }
  }
}
```

### 5.3 StatusQueryRequest
```json
{
  "type": "object",
  "required": ["request_id", "session_id", "task_id"],
  "properties": {
    "request_id": {"type": "string"},
    "session_id": {"type": "string"},
    "task_id":    {"type": "string"},
    "query_fields": {
      "type": "array",
      "items": {"enum": ["task_status", "actor_position", "distance_to_goal",
                         "active_bt", "active_node", "last_return_code",
                         "progress_rate", "blocked_reason"]}
    }
  }
}
```

### 5.4 TaskStatusResponse
```json
{
  "type": "object",
  "required": ["session_id", "task_id", "status"],
  "properties": {
    "session_id": {"type": "string"},
    "task_id":    {"type": "string"},
    "status": {
      "enum": ["CREATED", "DISPATCHED", "ACKED", "RUNNING",
               "WAIT_UPPER", "SUCCEEDED", "FAILED", "TIMEOUT", "ABORTED"]
    },
    "actor": {
      "type": "object",
      "properties": {
        "type":     {"enum": ["group", "soldier"]},
        "id":       {"type": "string"},
        "position": {"$ref": "#/definitions/CoordinateObject"}
      }
    },
    "bt_runtime": {
      "type": "object",
      "properties": {
        "bt_name":     {"type": "string"},
        "active_node": {"type": "string"},
        "node_path":   {"type": "array", "items": {"type": "string"}}
      }
    },
    "progress": {
      "type": "object",
      "properties": {
        "distance_to_goal_m":          {"type": "number"},
        "elapsed_seconds":             {"type": "number"},
        "estimated_remaining_seconds": {"type": "number"},
        "progress_rate_mps":           {"type": "number"}
      }
    },
    "return_code": {"type": ["string", "null"]},
    "error": {
      "type": ["object", "null"],
      "properties": {
        "class":            {"type": "string"},
        "message":          {"type": "string"},
        "position":         {"$ref": "#/definitions/CoordinateObject"},
        "blocked_segment":  {"type": "string"}
      }
    },
    "suggested_action": {
      "enum": ["REPLAN_ROUTE", "REASSIGN_TASK", "REQUEST_HUMAN", "HOLD_POSITION", null]
    }
  }
}
```

### 5.5 IntentJSON (LAYER_2 internal 鈥?Module A output)
```json
{
  "type": "object",
  "required": ["intent", "actors", "constraints"],
  "properties": {
    "intent":          {"type": "string", "description": "semantic intent tag, e.g. move_and_guard"},
    "actors": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "id"],
        "properties": {
          "type": {"enum": ["group", "soldier"]},
          "id":   {"type": "string"}
        }
      }
    },
    "destination": {
      "type": "object",
      "properties": {
        "type":          {"enum": ["absolute", "relative_direction", "entity_ref"]},
        "coord":         {"$ref": "#/definitions/CoordinateObject"},
        "direction":     {"enum": ["north", "south", "east", "west", "northeast",
                                   "northwest", "southeast", "southwest"]},
        "distance_m":    {"type": "number"},
        "entity_id":     {"type": "string"},
        "target_object": {"type": "string"}
      }
    },
    "movement_mode":   {"type": "string", "description": "e.g. 鎬ヨ鍐? 甯歌, 闅愯斀"},
    "post_action":     {"type": "string", "description": "e.g. guard, hold, retreat"},
    "constraints": {
      "type": "object",
      "properties": {
        "avoid_enemy":        {"type": "boolean"},
        "maintain_formation": {"type": "boolean"},
        "allow_replan":       {"type": "boolean"}
      }
    }
  }
}
```

### 5.6 TaskPlanJSON (LAYER_2 internal 鈥?Module C output)
```json
{
  "type": "object",
  "required": ["mission_id", "plan"],
  "properties": {
    "mission_id": {"type": "string"},
    "plan": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["step_id", "task_type", "actor", "bt", "args", "timeout_policy"],
        "properties": {
          "step_id":     {"type": "string"},
          "task_type":   {"type": "string"},
          "actor":       {"type": "object"},
          "depends_on":  {"type": "array", "items": {"type": "string"},
                          "description": "list of step_ids that must SUCCEED before this step starts"},
          "bt": {
            "type": "object",
            "required": ["btset_path", "bt_name"],
            "properties": {
              "btset_path": {"type": "string"},
              "bt_name":    {"type": "string"}
            }
          },
          "args":           {"type": "object"},
          "timeout_policy": {"type": "object"}
        }
      }
    }
  }
}
```

---

## SECTION 6: TASK STATE MACHINE

Implement as a state machine class `TaskStateMachine`. One instance per task_instance record.

```
States:
  CREATED       鈫?initial state on task record creation
  DISPATCHED    鈫?TaskSubmitRequest sent to LAYER_3
  ACKED         鈫?LAYER_3 confirmed loadBTSet succeeded
  RUNNING       鈫?VBS behavior tree is executing
  WAIT_UPPER    鈫?BT returned to upper waiting leaf; safe to submit new task
  SUCCEEDED     鈫?BT completed successfully
  FAILED        鈫?BT returned non-recoverable failure
  TIMEOUT       鈫?LAYER_2 computed timeout exceeded
  ABORTED       鈫?manually stopped or compensation task triggered

Transitions:
  CREATED     鈫?DISPATCHED     : on TaskSubmitRequest sent
  DISPATCHED  鈫?ACKED          : on LAYER_3 ACK
  DISPATCHED  鈫?FAILED         : on BT_LOAD_ERROR | ACTOR_NOT_FOUND | PARAM_ERROR
  ACKED       鈫?RUNNING        : on VBS execution start confirmed
  RUNNING     鈫?WAIT_UPPER     : on BT returning WAIT_UPPER return code
  RUNNING     鈫?SUCCEEDED      : on BT returning SUCCESS
  RUNNING     鈫?FAILED         : on BT returning UNREACHABLE | SUBTASK_FAILED
  RUNNING     鈫?TIMEOUT        : on LAYER_2 timeout condition met (see SECTION 8)
  WAIT_UPPER  鈫?DISPATCHED     : on new TaskSubmitRequest for same actor
  TIMEOUT     鈫?ABORTED        : after replan attempt fails or is rejected
  FAILED      鈫?ABORTED        : after diagnosis decides no replan possible

Guard (enforced by state machine):
  RUNNING 鈫?new TaskSubmitRequest is FORBIDDEN (implements CONSTRAINT-04)
```

---

## SECTION 7: DATABASE SCHEMA

Use PostgreSQL + PostGIS. All tables in schema `zhibing`.

```sql
-- Session management
CREATE TABLE zhibing.sessions (
    session_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       TEXT NOT NULL,
    scenario_id   TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT now(),
    status        TEXT DEFAULT 'active'
);

-- Mission plans (one mission = multiple steps)
CREATE TABLE zhibing.mission_plans (
    mission_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    UUID REFERENCES zhibing.sessions,
    user_intent   TEXT,
    plan_json     JSONB,   -- full TaskPlanJSON
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- Individual task instances (one per plan step)
CREATE TABLE zhibing.task_instances (
    task_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id            UUID REFERENCES zhibing.mission_plans,
    session_id            UUID REFERENCES zhibing.sessions,
    step_id               TEXT,
    actor_type            TEXT,
    actor_id              TEXT,
    bt_name               TEXT,
    bt_args               JSONB,
    state                 TEXT DEFAULT 'CREATED',
    expected_finish_at    TIMESTAMPTZ,
    hard_timeout_at       TIMESTAMPTZ,
    stall_timeout_secs    INTEGER,
    last_status_at        TIMESTAMPTZ,
    last_position         JSONB,  -- CoordinateObject
    last_progress_rate    NUMERIC,
    created_at            TIMESTAMPTZ DEFAULT now()
);

-- Raw VBS requests sent
CREATE TABLE zhibing.vbs_requests (
    request_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id       UUID REFERENCES zhibing.task_instances,
    request_type  TEXT,  -- 'submit' | 'query'
    payload       JSONB,
    sent_at       TIMESTAMPTZ DEFAULT now()
);

-- Raw VBS responses received
CREATE TABLE zhibing.vbs_returns (
    return_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id    UUID REFERENCES zhibing.vbs_requests,
    task_id       UUID REFERENCES zhibing.task_instances,
    payload       JSONB,
    received_at   TIMESTAMPTZ DEFAULT now()
);

-- Scene snapshots at decision time
CREATE TABLE zhibing.scene_snapshots (
    snapshot_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id       UUID REFERENCES zhibing.task_instances,
    snapshot_data JSONB,
    captured_at   TIMESTAMPTZ DEFAULT now()
);

-- Explainability / decision log
CREATE TABLE zhibing.decision_logs (
    decision_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID REFERENCES zhibing.sessions,
    task_id             UUID REFERENCES zhibing.task_instances,
    user_intent         TEXT,
    intent_json         JSONB,
    selected_bt         TEXT,
    selection_reason    TEXT,
    parameters_sourced  JSONB,  -- {arg_name: {value: ..., source: ...}}
    bt_node_trace       JSONB,
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- Entity state store (synced from VBS)
CREATE TABLE zhibing.entity_states (
    entity_id     TEXT PRIMARY KEY,
    entity_type   TEXT,  -- 'group' | 'soldier' | 'vehicle' | 'enemy'
    position      GEOMETRY(PointZ, 4326),
    state_data    JSONB,
    updated_at    TIMESTAMPTZ DEFAULT now()
);

-- Geo store (buildings, roads, bridges 鈥?PostGIS)
CREATE TABLE zhibing.geo_objects (
    geo_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_type   TEXT,  -- 'building' | 'road' | 'bridge' | 'entrance' | 'obstacle' | 'exclusion_zone'
    geom          GEOMETRY NOT NULL,
    properties    JSONB,
    passable      BOOLEAN DEFAULT true,
    updated_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON zhibing.geo_objects USING GIST (geom);

-- BT Registry (mirror of JSON file, queryable via SQL)
CREATE TABLE zhibing.bt_registry (
    bt_name           TEXT PRIMARY KEY,
    btset_path        TEXT NOT NULL,
    scope             TEXT,
    capabilities      TEXT[],
    required_args     JSONB,
    optional_args     JSONB,
    return_codes      TEXT[],
    safe_update_points TEXT[],
    explainable_nodes JSONB,
    phase_available   TEXT,
    active            BOOLEAN DEFAULT true
);
```

---

## SECTION 8: TIMEOUT FORMULA

Implement in `TimeoutService`. Called during Module E (param generation) to populate `timeout_policy`.

```python
# All factors are floats. Default = 1.0 if data unavailable.

def compute_timeout(
    path_distance_m: float,
    base_speed_mps: float,
    terrain_factor: float,    # 1.0=flat road, 0.6=rough terrain, 0.4=water/steep
    weather_factor: float,    # 1.0=clear, 0.8=rain, 0.6=heavy rain/snow
    formation_factor: float,  # 1.0=no formation constraint, 0.85=line, 0.75=wedge
    threat_factor: float,     # 1.0=no threat, 0.7=under fire / evasion required
    load_bt_overhead_s: float = 5.0,
    formation_overhead_s: float = 10.0,
    safety_margin_s: float = 30.0
) -> dict:

    effective_speed = (base_speed_mps
                       * terrain_factor
                       * weather_factor
                       * formation_factor
                       * threat_factor)

    expected_s = (path_distance_m / effective_speed
                  + load_bt_overhead_s
                  + formation_overhead_s
                  + safety_margin_s)

    hard_timeout_s  = max(expected_s * 1.5, expected_s + 60)
    stall_timeout_s = max(60, expected_s * 0.2)

    return {
        "expected_seconds":      round(expected_s),
        "hard_timeout_seconds":  round(hard_timeout_s),
        "stall_timeout_seconds": round(stall_timeout_s)
    }

# LAYER_2 polls task status every POLL_INTERVAL_S = 10 seconds.
# Timeout check logic (run on every poll):
#   if now() > task.hard_timeout_at:
#       transition task to TIMEOUT
#   if (now() - task.last_meaningful_progress_at) > task.stall_timeout_secs:
#       transition task to TIMEOUT with reason = NO_PROGRESS
#   "meaningful progress" = distance_to_goal decreased by >= 5m since last check
```

---

## SECTION 9: SCENE QUERY TOOLS

Implement as Python functions with the following exact signatures.
These are the ONLY interfaces LAYER_2 uses to access scene data.
The LLM must call these tools; it must NOT guess or hallucinate scene data.

```python
def get_actor_state(actor_id: str) -> dict:
    """Returns {id, type, position: CoordinateObject, health, status, current_bt, current_task_id}"""

def get_nearby_entities(position: dict, radius_m: float) -> list[dict]:
    """Returns list of entity_state dicts within radius_m of position"""

def get_buildings(area: dict) -> list[dict]:
    """area = CoordinateObject + radius_m. Returns [{id, type, geom_centroid, entrances, passable}]"""

def get_building_entrances(building_id: str) -> list[dict]:
    """Returns [{entrance_id, position: CoordinateObject, width_m, accessible}]"""

def get_enemy_state(area: dict) -> list[dict]:
    """Returns [{id, position, threat_level, last_seen_at}]"""

def get_weather() -> dict:
    """Returns {condition, weather_factor, visibility_m, wind_mps}"""

def route_plan(
    start: dict,          # CoordinateObject
    goal: dict,           # CoordinateObject
    constraints: dict     # {avoid_enemy: bool, avoid_obstacles: bool, max_detour_factor: float}
) -> dict:
    """Returns {waypoints: [CoordinateObject], total_distance_m, blocked_segments: [],
                passable: bool, estimated_time_s: float}
       Uses pgRouting under the hood."""

def estimate_move_time(route: dict, speed_mps: float, formation: str, weather: dict) -> dict:
    """Returns {expected_s, hard_timeout_s, stall_timeout_s} using TimeoutService"""

def lookup_bt(intent: str, actor_type: str) -> list[dict]:
    """Queries bt_registry by capability match. Returns ranked list of bt_registry entries."""

def validate_bt_args(bt_name: str, args: dict) -> dict:
    """Returns {valid: bool, errors: [str], warnings: [str]}"""

def query_obstacle(segment_id: str) -> dict:
    """Returns {passable, reason, last_updated_at}"""

def get_passable_routes(start: dict, goal: dict) -> list[dict]:
    """Returns list of route options sorted by estimated_time_s ascending"""
```

---

## SECTION 10: ERROR CLASSIFICATION

Errors are divided into 4 classes. Each class has a different handler.

```
CLASS_1: PRE_SUBMIT errors  (handled by LAYER_2 validation, never reach LAYER_3)
  MISSING_REQUIRED_ARG   鈫?auto-query scene tools to fill, or reject with explanation
  INVALID_COORDINATE     鈫?CoordService converts or rejects
  BT_SCOPE_MISMATCH      鈫?re-run lookup_bt with correct actor_type
  ARG_OUT_OF_RANGE       鈫?auto-clamp if safe, else reject
  UNAUTHORIZED           鈫?reject, log

CLASS_2: LOAD errors  (returned by LAYER_3 after SQF execution attempt)
  BT_LOAD_ERROR          鈫?task 鈫?FAILED; log btset_path; alert operator
  BT_NOT_FOUND           鈫?task 鈫?FAILED; suggest alternative from BT_REGISTRY
  ACTOR_NOT_FOUND        鈫?task 鈫?FAILED; refresh entity_states from VBS
  PARAM_ERROR            鈫?task 鈫?FAILED; validate_bt_args and retry once with corrected args

CLASS_3: EXECUTION failures  (returned by LAYER_4 via return codes)
  UNREACHABLE            鈫?REPLAN_ROUTE: call route_plan with avoid_obstacles=true;
                           submit new GrpMove with new waypoints
  SUBTASK_FAILED         鈫?query which sub-unit failed; split task or re-form group
  TARGET_LOST            鈫?re-query get_nearby_entities; rebind target; new task
  UNIT_STATUS_CHANGED    鈫?get_actor_state; reassign if unit is degraded

CLASS_4: TIMEOUT / NO_PROGRESS  (detected by LAYER_2 polling)
  TASK_TIMEOUT           鈫?log elapsed_seconds vs expected_seconds; attempt REPLAN_ROUTE
  NO_PROGRESS            鈫?query_obstacle on current position; check formation;
                           attempt speed/formation adjustment
  STALL_AT_OBSTACLE      鈫?deduce ROUTE_BLOCKED from position near known obstacle;
                           trigger CLASS_3.UNREACHABLE handler
```

---

## SECTION 11: REPLAN WORKFLOW

When a task enters TIMEOUT or FAILED with a recoverable error code:

```
STEP 1: snapshot current scene
  call get_actor_state(actor_id)
  call query_obstacle(nearest_segment)
  call get_enemy_state(area_around_actor)

STEP 2: diagnose failure
  if return_code == UNREACHABLE and position near known obstacle:
      diagnosis = ROUTE_BLOCKED
  elif return_code == NO_PROGRESS:
      diagnosis = STALL_OR_FORMATION_ISSUE
  elif return_code == SUBTASK_FAILED:
      diagnosis = SUBUNIT_UNREACHABLE

STEP 3: generate new plan
  if diagnosis == ROUTE_BLOCKED:
      new_route = route_plan(current_pos, original_goal,
                             constraints={avoid_obstacles: true, max_detour_factor: 2.0})
      if new_route.passable:
          submit new TaskSubmitRequest with bt_name=GrpMove, movePos=new_route.waypoints[-1]
      else:
          escalate to HUMAN_IN_THE_LOOP

  if diagnosis == STALL_OR_FORMATION_ISSUE:
      new_args = {speed: original_speed * 0.7, fmInfoTable: []}  # relax formation
      submit new TaskSubmitRequest with relaxed args

STEP 4: if replan fails twice 鈫?ABORTED
  compensation_task = {bt_name: "grpSimpleMoveNoAuto", args: {moveDest: original_start}}
  OR hold_position if no safe retreat

STEP 5: write replan event to decision_log
```

---

## SECTION 12: HUMAN IN THE LOOP

Implement using LangGraph `interrupt()` or equivalent mechanism.
HITL is REQUIRED (not optional) for the following trigger conditions:

```
TRIGGER_OPEN_FIRE         : any task with task_type containing "fire" or "attack"
TRIGGER_ENTER_DANGER_ZONE : destination is within a known threat zone (query Tactical Store)
TRIGGER_LOAD_UNKNOWN_BT   : bt_name not present in bt_registry.active = true
TRIGGER_REPLAN_FAIL_2X    : replan workflow has failed twice for same task
TRIGGER_RULE_CONFLICT     : task violates a constraint from regulatory corpus
```

HITL flow:
```
LAYER_2 raises interrupt 鈫?suspends task in WAIT_UPPER state
鈫?sends explanation to USER_INTERFACE:
    {trigger, actor, proposed_action, risk_assessment, decision_options: ["approve", "modify", "abort"]}
鈫?waits for human response (no timeout on HITL wait)
鈫?on "approve": resume task as planned
鈫?on "modify":  user provides modified IntentJSON; re-run from Module C
鈫?on "abort":   transition to ABORTED; run compensation task
```

---

## SECTION 13: BT GENERATION PIPELINE (PHASE_V2 only)

This section MUST NOT be implemented in PHASE_MVP or PHASE_V1.

```
INPUT: regulatory text (鏉℃枃鏉′緥) or natural language BT specification

STEP 1: Rule Extraction (LLM)
  Output RuleJSON:
    {conditions: [], actions: [], exceptions: [], priorities: [], forbidden: []}

STEP 2: BT DSL Generation (LLM + Outlines JSON Schema constraint)
  Output BT_DSL_JSON:
    {tree_name, scope, type: "sequence|selector|parallel", children: [...]}
  Node types allowed in DSL:
    sequence | selector | parallel | condition | action | decorator
  Action names MUST map to VBS_SUPPORTED_ACTIONS whitelist (see below)

STEP 3: JSON Schema Validation
  Validate BT_DSL_JSON against bt_dsl.schema.json
  REJECT if any action not in VBS_SUPPORTED_ACTIONS

STEP 4: Node Mapping
  Map each action node to VBS internal action identifier
  Use bt_node_mapping_table.json (to be populated from VBS documentation)

STEP 5: Compile to .bt
  Output: {bt_name}.bt.json 鈥?VBS-loadable behavior tree file
  Compiler must be deterministic; same DSL always produces same .bt

STEP 6: Static Analysis (py_trees offline simulation)
  Check for: dead branches, unreachable leaves, missing return codes,
             infinite loops, blackboard variable access without init
  FAIL if any issue found; return to STEP 2 with error context

STEP 7: Sandbox Simulation
  Load .bt in VBS sandbox scene
  Run 3 test scenarios: normal path, blocked path, actor missing
  FAIL if unexpected return codes occur

STEP 8: Human Approval (HITL)
  Present to operator: {bt_name, dsl_summary, static_analysis_report, simulation_results}
  Only on "approve" 鈫?proceed to STEP 9

STEP 9: Register to BT_REGISTRY
  INSERT into zhibing.bt_registry with active=true
  Assign bt_version (semver), commit to bt_versions audit table
  Sync to BT_REGISTRY JSON file
```

VBS_SUPPORTED_ACTIONS whitelist (initial 鈥?expand as VBS documentation is reviewed):
```json
["move", "set_formation", "set_speed", "receive_message", "send_message",
 "hold_position", "report_unreachable_to_upper", "wait_for_message",
 "check_blackboard", "set_blackboard", "spawn_subtask", "wait_subtask_end"]
```

---

## SECTION 14: EXPLAINABILITY LOG FORMAT

Every call to Module D (BTSelector) MUST produce a decision_log entry.

```json
{
  "decision_id": "<uuid>",
  "session_id": "<uuid>",
  "task_id": "<uuid>",
  "user_intent": "<original natural language string>",
  "intent_json": { "<IntentJSON>" },
  "selected_bt": "<bt_name>",
  "selection_reason": "<one sentence: why this BT was selected over alternatives>",
  "alternatives_considered": [
    {"bt_name": "<name>", "rejected_reason": "<why rejected>"}
  ],
  "parameters_sourced": {
    "<arg_name>": {
      "value": "<value>",
      "source": "<how derived: scene_tool | user_input | default | inferred>"
    }
  },
  "bt_node_trace": [
    {"node": "<node_name>", "meaning": "<what it does in this context>"}
  ],
  "coord_conversions": [
    {"from": "<CoordinateObject>", "to": "<CoordinateObject>", "service": "CoordService"}
  ],
  "timestamp": "<ISO8601>"
}
```

Query pattern for operator ("Why did the soldier stop at the bridge?"):
```python
# LAYER_2 Module H answers natural language queries about past decisions
# by joining decision_logs + vbs_returns + scene_snapshots + task_instances
# and composing a natural language explanation.
```

---

## SECTION 15: TECH STACK

```
COMPONENT              TECHNOLOGY              NOTES
鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
LLM inference          vLLM (primary)          OpenAI-compatible API
                       Ollama (dev/test)        lighter, for iteration
Structured output      vLLM structured_outputs JSON Schema / grammar constraint
                       Outlines                additional constraint layer for BT DSL
Task state machine     LangGraph               persistent checkpoints, HITL interrupt
LLM tool integration   LangChain Tools         wraps SECTION 9 scene query functions
Relational DB          PostgreSQL 15+
Spatial data           PostGIS 3+              geo_objects, entity_states
Path planning          pgRouting               route_plan() backend
BT offline simulation  py_trees (Python)       PHASE_V2 static analysis only
Knowledge retrieval    RAG (Phase V1)          over bt_registry + scene knowledge
                       GraphRAG (Phase V3)     Microsoft GraphRAG for regulatory corpus
Task planning (V3)     Unified Planning (UP)   PDDL domain modeling
                       Fast Downward           PDDL planner backend
User interface         Open WebUI              Pipelines for tool integration
VBS adapter            custom Python+SQF       no existing solution; must be built
BT DSL compiler        custom Python           no existing solution; must be built
```

---

## SECTION 16: DEVELOPMENT PHASES

### PHASE_MVP

**Goal:** Natural language 鈫?call existing behavior tree 鈫?VBS executes 鈫?status returned 鈫?explanation logged.
**LLM generates new .bt:** FORBIDDEN.

Tasks (implement in this order):

```
[TASK-MVP-01] Build BT_REGISTRY
  - Parse 4 existing .bt files: grpSimpleMoveNoAuto, GrpMove, GrpMove2, grpFollowFormation
  - Populate bt_registry table and JSON file using schema in SECTION 4
  - Output: bt_registry.json + DB table populated

[TASK-MVP-02] Implement JSON Schemas
  - Implement all schemas from SECTION 5 as JSON Schema Draft 7 files
  - Output: schemas/ directory with CoordinateObject, TaskSubmitRequest,
            StatusQueryRequest, TaskStatusResponse, IntentJSON, TaskPlanJSON

[TASK-MVP-03] Implement CoordService
  - WGS84_LATLON_ALT 鈫?VBS_LOCAL_XYZ conversion
  - Input validation: reject bare arrays, require frame field (CONSTRAINT-06)
  - Output: coord_service.py with unit tests covering edge cases

[TASK-MVP-04] Implement VBS Adapter (LAYER_3)
  - Functions: load_btset(), set_bt(), set_bb_variable(), send_message(), query_status()
  - JSON 鈫?SQF compiler: takes TaskSubmitRequest, emits SQF call sequence
  - Error classifier: maps VBS error responses to CLASS_2 error codes
  - Output: vbs_adapter.py, sqf_compiler.py

[TASK-MVP-05] Implement TaskStateMachine
  - All states and transitions from SECTION 6
  - Guard: RUNNING 鈫?new submit is FORBIDDEN (CONSTRAINT-04)
  - Output: task_state_machine.py with full transition unit tests

[TASK-MVP-06] Implement TimeoutService
  - compute_timeout() from SECTION 8
  - Polling loop with hard_timeout and stall_timeout checks
  - Output: timeout_service.py

[TASK-MVP-07] Create DB schema
  - All tables from SECTION 7
  - Migrations via Alembic
  - Output: migrations/001_initial.py

[TASK-MVP-08] Implement Scene Query Tools (minimal subset)
  - For MVP, implement only: get_actor_state, route_plan, lookup_bt, validate_bt_args
  - Remaining 9 tools stubbed (return empty/mock data)
  - Output: scene_tools.py

[TASK-MVP-09] Implement LLM Decision Layer (minimal)
  - Module A: IntentRecognition 鈥?prompt + JSON Schema constrained output 鈫?IntentJSON
  - Module B: SceneQuery 鈥?calls MVP scene tools
  - Module C: TaskPlanner 鈥?IntentJSON 鈫?TaskPlanJSON (single-step only for MVP)
  - Module D: BTSelector 鈥?queries bt_registry, selects best match
  - Module E: ParamGenerator 鈥?fills bt_args, calls TimeoutService, validates via validate_bt_args
  - Module H: ExplainabilityLogger 鈥?writes decision_log on every BT selection
  - Output: decision_layer/ package

[TASK-MVP-10] Integration: wire all layers
  - User input 鈫?Module A 鈫?B 鈫?C 鈫?D 鈫?E 鈫?TaskSubmitRequest 鈫?Adapter 鈫?VBS
  - Poll loop 鈫?StatusQueryRequest 鈫?Adapter 鈫?TaskStatusResponse 鈫?StateTransition
  - Output: main.py end-to-end flow

[TASK-MVP-11] MVP Acceptance Test
  - Input: "璁﹑_4缇ょ粍浠ラ€熷害10绉诲姩鍒版寚瀹氬潗鏍?VBS_LOCAL_XYZ {x:1000, y:500, z:0}"
  - Expected: task reaches SUCCEEDED, decision_log entry written, explanation retrievable
  - Input 2: same task but destination has no passable route
  - Expected: VBS returns UNREACHABLE, task transitions FAILED, replan triggered
```

ACCEPTANCE_CRITERIA for PHASE_MVP:
```
- All TASK-MVP-01 through TASK-MVP-11 pass
- CONSTRAINT-01 through CONSTRAINT-07 verifiable by code review
- decision_log entry created for every BT selection
- No bare coordinate arrays anywhere in codebase (grep check)
- TimeoutService uses formula from SECTION 8, not a hardcoded value
```

---

### PHASE_V1

**Goal:** Multi-step task plans, full error handling, replan workflow, HITL.
**Prerequisite:** PHASE_MVP ACCEPTANCE_CRITERIA all pass.

```
[TASK-V1-01] Complete Scene Query Tools
  - Implement remaining 9 tools from SECTION 9
  - Full PostGIS geo_objects data import for test scenario

[TASK-V1-02] Multi-step TaskPlanner
  - Module C: generate TaskPlanJSON with multiple steps and depends_on DAG
  - Step executor: resolves dependencies, dispatches steps sequentially or in parallel

[TASK-V1-03] Full Error Handler (all 4 classes from SECTION 10)
  - CLASS_1: pre-submit validation pipeline
  - CLASS_2: load error handling with retry/fallback
  - CLASS_3: execution failure handlers (UNREACHABLE, SUBTASK_FAILED, TARGET_LOST)
  - CLASS_4: timeout/stall detection and response

[TASK-V1-04] Replan Workflow
  - Full implementation of SECTION 11 replan steps 1鈥?
  - Double-fail 鈫?ABORTED with compensation task

[TASK-V1-05] HITL Integration
  - LangGraph interrupt() for all 5 TRIGGER conditions from SECTION 12
  - User interface for approve/modify/abort decision

[TASK-V1-06] Module F (StateManager) + Module G (Replanner)
  - StateManager: tracks all active tasks, monitors timeout, triggers replan
  - Replanner: implements SECTION 11

[TASK-V1-07] RAG over BT_REGISTRY
  - Embed bt_registry entries
  - Module D uses semantic search for BT selection in addition to capability tag match
```

---

### PHASE_V2

**Goal:** Regulatory text 鈫?new behavior tree generation pipeline.
**Prerequisite:** PHASE_V1 ACCEPTANCE_CRITERIA pass.

```
[TASK-V2-01] BT DSL specification
  - Define bt_dsl.schema.json with full node type coverage
  - Define VBS_SUPPORTED_ACTIONS whitelist (populate from VBS docs)
  - Define bt_node_mapping_table.json

[TASK-V2-02] BT DSL Generator (LLM + Outlines)
  - Prompt + grammar constraint 鈫?BT_DSL_JSON
  - Guaranteed valid JSON output via Outlines

[TASK-V2-03] BT Compiler (DSL 鈫?.bt)
  - Deterministic, pure function: same DSL 鈫?same .bt always
  - Validates all action names against VBS_SUPPORTED_ACTIONS

[TASK-V2-04] Static Analyzer (py_trees)
  - Offline simulation for dead branches, infinite loops, missing return codes

[TASK-V2-05] Sandbox simulation
  - VBS sandbox scene with 3 standard test cases
  - Automated pass/fail

[TASK-V2-06] BT version management
  - bt_versions audit table
  - Semver for each registered BT
  - Rollback capability

[TASK-V2-07] Full SECTION 13 pipeline integration
  - End-to-end: regulatory text input 鈫?BT registered in bt_registry
```

---

### PHASE_V3

**Goal:** PDDL planning, GraphRAG knowledge base, multi-unit coordination.
**Prerequisite:** PHASE_V2 ACCEPTANCE_CRITERIA pass.

```
[TASK-V3-01] PDDL domain design
  - Define PDDL domain for military movement/guard/attack tasks
  - LLM generates PDDL problem from IntentJSON
  - Unified Planning (UP) + Fast Downward as solver

[TASK-V3-02] Action sequence 鈫?TaskPlanJSON compiler
  - PDDL action sequence 鈫?multi-step TaskPlanJSON

[TASK-V3-03] GraphRAG knowledge base
  - Ingest: regulatory corpus, BT documentation, historical task logs
  - Microsoft GraphRAG pipeline
  - Module B: use GraphRAG retrieval to augment scene query

[TASK-V3-04] Historical task memory
  - Embed past decision_logs
  - Module G: retrieve similar past failures 鈫?use historical replan strategy

[TASK-V3-05] Multi-unit coordination
  - Multi-actor task plans with cross-unit depends_on
  - Coordination state tracking per actor
```

---

## SECTION 17: FILE STRUCTURE

```
zhibing/
鈹溾攢鈹€ schemas/
鈹?  鈹溾攢鈹€ coordinate_object.schema.json
鈹?  鈹溾攢鈹€ task_submit_request.schema.json
鈹?  鈹溾攢鈹€ status_query_request.schema.json
鈹?  鈹溾攢鈹€ task_status_response.schema.json
鈹?  鈹溾攢鈹€ intent_json.schema.json
鈹?  鈹斺攢鈹€ task_plan_json.schema.json
鈹溾攢鈹€ registry/
鈹?  鈹溾攢鈹€ bt_registry.json                 # source of truth, synced to DB
鈹?  鈹斺攢鈹€ bt_node_mapping_table.json       # populated in PHASE_V2
鈹溾攢鈹€ core/
鈹?  鈹溾攢鈹€ coord_service.py
鈹?  鈹溾攢鈹€ timeout_service.py
鈹?  鈹溾攢鈹€ task_state_machine.py
鈹?  鈹斺攢鈹€ db.py                            # SQLAlchemy models + Alembic
鈹溾攢鈹€ adapter/
鈹?  鈹溾攢鈹€ vbs_adapter.py
鈹?  鈹斺攢鈹€ sqf_compiler.py
鈹溾攢鈹€ scene/
鈹?  鈹斺攢鈹€ scene_tools.py                   # all 13 tools from SECTION 9
鈹溾攢鈹€ decision_layer/
鈹?  鈹溾攢鈹€ module_a_intent.py
鈹?  鈹溾攢鈹€ module_b_scene.py
鈹?  鈹溾攢鈹€ module_c_planner.py
鈹?  鈹溾攢鈹€ module_d_bt_selector.py
鈹?  鈹溾攢鈹€ module_e_param_gen.py
鈹?  鈹溾攢鈹€ module_f_state_manager.py
鈹?  鈹溾攢鈹€ module_g_replanner.py
鈹?  鈹斺攢鈹€ module_h_explainability.py
鈹溾攢鈹€ hitl/
鈹?  鈹斺攢鈹€ interrupt_handler.py
鈹溾攢鈹€ bt_pipeline/                         # PHASE_V2 only
鈹?  鈹溾攢鈹€ rule_extractor.py
鈹?  鈹溾攢鈹€ dsl_generator.py
鈹?  鈹溾攢鈹€ bt_compiler.py
鈹?  鈹溾攢鈹€ static_analyzer.py
鈹?  鈹斺攢鈹€ bt_version_manager.py
鈹溾攢鈹€ migrations/
鈹?  鈹斺攢鈹€ 001_initial.py
鈹溾攢鈹€ tests/
鈹?  鈹溾攢鈹€ test_coord_service.py
鈹?  鈹溾攢鈹€ test_timeout_service.py
鈹?  鈹溾攢鈹€ test_state_machine.py
鈹?  鈹溾攢鈹€ test_vbs_adapter.py
鈹?  鈹斺攢鈹€ test_mvp_integration.py
鈹斺攢鈹€ main.py                              # entry point, wires all layers
```

---

## SECTION 18: IMPLEMENTATION RULES FOR AI

When implementing any component in this system, follow these rules:

```
RULE-1: Implement one TASK at a time. Do not start TASK-N+1 until TASK-N passes its tests.

RULE-2: Every function that accepts or produces coordinates MUST call CoordService.
        Never manipulate raw coordinate arrays directly.

RULE-3: Every call to VBS Adapter MUST go through TaskStateMachine.
        Never call adapter functions directly from decision_layer modules.

RULE-4: When writing prompts for LLM modules (A, C, D, E, G):
        - Include the relevant JSON Schema as a system prompt appendix
        - Use vLLM structured_outputs or Outlines to constrain output
        - Include at least 2 few-shot examples per module
        - Never rely on free-text parsing of LLM output

RULE-5: All database writes in task_instances, vbs_requests, vbs_returns
        must use transactions. No partial writes.

RULE-6: decision_log write happens BEFORE TaskSubmitRequest is sent to Adapter.
        If the task fails before submission, the log must still record the attempt.

RULE-7: When implementing error handlers (SECTION 10), start with CLASS_2 and CLASS_3.
        CLASS_1 and CLASS_4 can be simplified initially but must be complete in PHASE_V1.

RULE-8: Do not implement SECTION 13 (BT Generation Pipeline) in any PHASE_MVP file.
        Keep bt_pipeline/ directory empty until PHASE_V2 begins.

RULE-9: Test file naming: test_<module_name>.py.
        Every TASK must have at least one integration test in addition to unit tests.

RULE-10: All config values (btset paths, DB connection, poll intervals, LLM endpoint)
         go in config.py or environment variables. No hardcoded strings in logic files.
```

---

## END OF PLAN

# If you are an AI reading this:
# You now have everything needed to begin implementation.
# Start with SECTION 1 to confirm system identity, then proceed to PHASE_MVP TASK-MVP-01.
# Do not deviate from the schemas, constraints, or task order defined above.
# When in doubt, re-read the relevant SECTION before writing code.

## UPDATE DOCUMENTS

- `zhibing/docs/lower_simulation_interface.md`
- `zhibing/docs/system_runtime_flow.md`
- `zhibing/hitl/hitl_policy.yaml`
- `docs/superpowers/plans/2026-06-20-zhibing-system-update-v2.md`