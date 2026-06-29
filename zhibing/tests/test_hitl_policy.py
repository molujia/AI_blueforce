import unittest

from zhibing.hitl.interrupt_handler import HITLDecisionContext, HITLPolicy, check_hitl_required
from zhibing.hitl.node_catalog import NodeType, get_node_catalog


class HITLPolicyTests(unittest.TestCase):
    def test_policy_file_can_enable_encirclement_preparation(self) -> None:
        policy = HITLPolicy.from_dict({
            "nodes": {
                "ENCIRCLEMENT_PREP_CHECK": {
                    "hitl_allowed": True,
                    "require_hitl": True,
                    "allow_emergency_skip": False,
                }
            }
        })
        context = HITLDecisionContext(
            node_type=NodeType.ENCIRCLEMENT_PREP_CHECK,
            urgency="normal",
            trigger="CONFIGURED_HITL_NODE",
            actor={"type": "group", "id": "p_4"},
            proposed_action={"task_type": "encirclement_prepare"},
            risk_assessment="configured by policy",
        )
        self.assertIsNotNone(policy.evaluate(context))

    def test_emergency_contact_never_blocks_for_human_review_by_default(self) -> None:
        policy = HITLPolicy.default()
        context = HITLDecisionContext(
            node_type=NodeType.EMERGENCY_CONTACT,
            urgency="immediate",
            trigger="SUDDEN_CONTACT",
            actor={"type": "group", "id": "p_4"},
            proposed_action={"local_action": "avoid_or_take_cover"},
            risk_assessment="runtime emergency",
        )
        self.assertIsNone(policy.evaluate(context))

    def test_default_attack_policy_still_blocks_kinetic_action(self) -> None:
        interrupt = check_hitl_required({"intent": "group_attack", "actors": [{"type": "group", "id": "p_4"}]})
        self.assertIsNotNone(interrupt)

    def test_node_catalog_exposes_configurable_nodes(self) -> None:
        catalog = get_node_catalog()
        self.assertTrue(catalog["ENCIRCLEMENT_PREP_CHECK"]["hitl_configurable"])
        self.assertFalse(catalog["EMERGENCY_CONTACT"]["hitl_configurable"])


if __name__ == "__main__":
    unittest.main()
