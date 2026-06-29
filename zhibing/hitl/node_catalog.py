"""HITL node catalog and node categories."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NodeCategory(str, Enum):
    PRE_USER_BOOTSTRAP = "PRE_USER_BOOTSTRAP"
    DECISION_WORK = "DECISION_WORK"
    RISK_GATE = "RISK_GATE"
    DISPATCH = "DISPATCH"
    RUNTIME_OBSERVATION = "RUNTIME_OBSERVATION"
    LOCAL_EMERGENCY = "LOCAL_EMERGENCY"
    EXPLANATION = "EXPLANATION"


class NodeType(str, Enum):
    KNOWLEDGE_INGEST = "KNOWLEDGE_INGEST"
    SCENE_SYNC = "SCENE_SYNC"
    USER_COMMAND_INTAKE = "USER_COMMAND_INTAKE"
    INTENT_RECOGNITION = "INTENT_RECOGNITION"
    KNOWLEDGE_RETRIEVAL = "KNOWLEDGE_RETRIEVAL"
    SCENE_QUERY = "SCENE_QUERY"
    TASK_PLANNING = "TASK_PLANNING"
    BT_SELECTION = "BT_SELECTION"
    PARAM_GENERATION = "PARAM_GENERATION"
    RULE_CONFLICT_CHECK = "RULE_CONFLICT_CHECK"
    ENTER_DANGER_ZONE_CHECK = "ENTER_DANGER_ZONE_CHECK"
    BUILDING_ENTRY_PREP_CHECK = "BUILDING_ENTRY_PREP_CHECK"
    ENCIRCLEMENT_PREP_CHECK = "ENCIRCLEMENT_PREP_CHECK"
    FIRE_OR_ATTACK_AUTHORIZATION = "FIRE_OR_ATTACK_AUTHORIZATION"
    VISUALIZATION_PROJECTION = "VISUALIZATION_PROJECTION"
    TASK_SUBMISSION = "TASK_SUBMISSION"
    STATUS_POLL = "STATUS_POLL"
    REPLAN_DIAGNOSIS = "REPLAN_DIAGNOSIS"
    REPLAN_FAIL_GATE = "REPLAN_FAIL_GATE"
    EMERGENCY_CONTACT = "EMERGENCY_CONTACT"
    LOCAL_AVOIDANCE = "LOCAL_AVOIDANCE"
    EXPLANATION_QUERY = "EXPLANATION_QUERY"


@dataclass(frozen=True)
class NodeDefinition:
    node_type: NodeType
    category: NodeCategory
    hitl_configurable: bool
    description: str


NODE_CATALOG: dict[NodeType, NodeDefinition] = {
    NodeType.KNOWLEDGE_INGEST: NodeDefinition(NodeType.KNOWLEDGE_INGEST, NodeCategory.PRE_USER_BOOTSTRAP, False, "Ingest doctrine and test documents."),
    NodeType.SCENE_SYNC: NodeDefinition(NodeType.SCENE_SYNC, NodeCategory.PRE_USER_BOOTSTRAP, False, "Sync lower simulation scene data."),
    NodeType.USER_COMMAND_INTAKE: NodeDefinition(NodeType.USER_COMMAND_INTAKE, NodeCategory.DECISION_WORK, False, "Receive user command."),
    NodeType.INTENT_RECOGNITION: NodeDefinition(NodeType.INTENT_RECOGNITION, NodeCategory.DECISION_WORK, False, "Convert text to IntentJSON."),
    NodeType.KNOWLEDGE_RETRIEVAL: NodeDefinition(NodeType.KNOWLEDGE_RETRIEVAL, NodeCategory.DECISION_WORK, False, "Retrieve GraphRAG constraints."),
    NodeType.SCENE_QUERY: NodeDefinition(NodeType.SCENE_QUERY, NodeCategory.DECISION_WORK, False, "Collect scene context."),
    NodeType.TASK_PLANNING: NodeDefinition(NodeType.TASK_PLANNING, NodeCategory.DECISION_WORK, False, "Create TaskPlanJSON."),
    NodeType.BT_SELECTION: NodeDefinition(NodeType.BT_SELECTION, NodeCategory.DECISION_WORK, False, "Choose executable BT."),
    NodeType.PARAM_GENERATION: NodeDefinition(NodeType.PARAM_GENERATION, NodeCategory.DECISION_WORK, False, "Generate BT args."),
    NodeType.RULE_CONFLICT_CHECK: NodeDefinition(NodeType.RULE_CONFLICT_CHECK, NodeCategory.RISK_GATE, True, "Check conflict with doctrine or operator rules."),
    NodeType.ENTER_DANGER_ZONE_CHECK: NodeDefinition(NodeType.ENTER_DANGER_ZONE_CHECK, NodeCategory.RISK_GATE, True, "Check route through risk zone."),
    NodeType.BUILDING_ENTRY_PREP_CHECK: NodeDefinition(NodeType.BUILDING_ENTRY_PREP_CHECK, NodeCategory.RISK_GATE, True, "Check preparation before building entry."),
    NodeType.ENCIRCLEMENT_PREP_CHECK: NodeDefinition(NodeType.ENCIRCLEMENT_PREP_CHECK, NodeCategory.RISK_GATE, True, "Check encirclement preparation."),
    NodeType.FIRE_OR_ATTACK_AUTHORIZATION: NodeDefinition(NodeType.FIRE_OR_ATTACK_AUTHORIZATION, NodeCategory.RISK_GATE, True, "Authorize kinetic action."),
    NodeType.VISUALIZATION_PROJECTION: NodeDefinition(NodeType.VISUALIZATION_PROJECTION, NodeCategory.DECISION_WORK, False, "Build 2D projection."),
    NodeType.TASK_SUBMISSION: NodeDefinition(NodeType.TASK_SUBMISSION, NodeCategory.DISPATCH, False, "Submit executable task to lower layer."),
    NodeType.STATUS_POLL: NodeDefinition(NodeType.STATUS_POLL, NodeCategory.RUNTIME_OBSERVATION, False, "Poll task status."),
    NodeType.REPLAN_DIAGNOSIS: NodeDefinition(NodeType.REPLAN_DIAGNOSIS, NodeCategory.RUNTIME_OBSERVATION, False, "Diagnose failed task."),
    NodeType.REPLAN_FAIL_GATE: NodeDefinition(NodeType.REPLAN_FAIL_GATE, NodeCategory.RISK_GATE, True, "Ask for review before risky replanning."),
    NodeType.EMERGENCY_CONTACT: NodeDefinition(NodeType.EMERGENCY_CONTACT, NodeCategory.LOCAL_EMERGENCY, False, "Sudden contact handled locally by lower runtime."),
    NodeType.LOCAL_AVOIDANCE: NodeDefinition(NodeType.LOCAL_AVOIDANCE, NodeCategory.LOCAL_EMERGENCY, False, "Immediate local avoidance handled by lower runtime."),
    NodeType.EXPLANATION_QUERY: NodeDefinition(NodeType.EXPLANATION_QUERY, NodeCategory.EXPLANATION, False, "Explain decisions to the operator."),
}


def get_node_catalog() -> dict[str, dict[str, object]]:
    return {
        node.value: {
            "category": definition.category.value,
            "hitl_configurable": definition.hitl_configurable,
            "description": definition.description,
        }
        for node, definition in NODE_CATALOG.items()
    }
