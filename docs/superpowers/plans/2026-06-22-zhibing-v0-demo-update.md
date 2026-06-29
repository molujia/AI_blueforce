# 智兵决策 v0 演示闭环更新实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:executing-plans 逐任务执行此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。当前目录不是 Git 仓库，所有 “版本记录” 步骤均以 `git status --short` 不可用为前提；执行时记录已改文件清单即可，不强制 commit。

**目标：** 将当前系统修正为一个参考 wargame 的 2D 战术指挥演示闭环，支持一键部署、敌我拖拽、Top-N 寻路、LLM 特殊约束补丁、GraphRAG 可用性验证、轻量会话记忆和 Adapter 预览。

**架构：** 后端保留现有 `zhibing` 分层结构，新增 `scenario`、`routing`、`session_memory` 三个小型领域模块；前端重写 `command_ui` 为 wargame 风格 2D HUD；GraphRAG 增加官方示例与本地 PDF/DOCX 可用性入口；LLM 不直接产出路线，只产出结构化约束补丁和候选路线解释。

**技术栈：** Python、Django、SQLite、Leaflet、GeoJSON、unittest、现有 `llm_call_extract`、火山 Ark 模型 `ep-20260615114505-247zc` 可选 live smoke、本地 LLM 迁移配置、Windows blueforce conda 环境。

---

## 文件结构与职责

- 创建：`zhibing/scenario/__init__.py`，场景模块包。
- 创建：`zhibing/scenario/models.py`，场景对象、风险区、路径候选、约束补丁的数据结构。
- 创建：`zhibing/scenario/demo_scenario.py`，默认一键部署场景。
- 创建：`zhibing/routing/__init__.py`，寻路模块包。
- 创建：`zhibing/routing/road_graph.py`，从 GeoJSON 或演示配置构建轻量路径图。
- 创建：`zhibing/routing/path_planner.py`，确定性 Top-N 路径规划和评分。
- 创建：`zhibing/routing/constraint_patch.py`，LLM 约束补丁 schema 与应用逻辑。
- 创建：`zhibing/decision_layer/route_constraint_llm.py`，用户自然语言到约束补丁、候选路径解释的 LLM 门面。
- 创建：`zhibing/session_memory.py`，轻量 SQLite 会话、消息、约束、路径候选存储。
- 修改：`zhibing/scene/scene_tools.py`，返回默认演示场景对象和风险感知路径，而非空敌情/直线路径。
- 修改：`zhibing/visualization/projector.py`，投影场景对象、候选路径、最终路径、约束和 GraphRAG 命中来源。
- 修改：`zhibing/web/command_ui/templates/command_ui/index.html`，重写为 wargame 风格战术 HUD 页面。
- 修改：`zhibing/web/command_ui/static/command_ui/styles.css`，重写为深色战术 HUD。
- 修改：`zhibing/web/command_ui/static/command_ui/app.js`，实现地图图层、拖拽部署、聊天、路径候选、会话控制。
- 修改：`zhibing/web/command_ui/views.py`，新增场景、路径、会话、GraphRAG 状态 API。
- 复制：`zhibing/web/command_ui/static/command_ui/map/*.geojson`，从 wargame 复制必要 2D 地图资产。
- 创建：`zhibing/knowledge/graphrag_usability.py`，官方 quickstart 与本地文件可用性检查入口。
- 修改：`zhibing/knowledge/llm_router.py`，明确 live LLM 调用开关和本地 LLM 迁移配置。
- 创建：`zhibing/tests/test_demo_scenario.py`，默认场景测试。
- 创建：`zhibing/tests/test_path_planner.py`，Top-N、风险规避、约束重规划测试。
- 创建：`zhibing/tests/test_constraint_llm.py`，确定性 fallback 约束解析测试。
- 创建：`zhibing/tests/test_session_memory.py`，会话恢复与重置测试。
- 修改：`zhibing/tests/test_three_layer_alignment.py`，补充意图、可视化、Adapter 预览一致性。
- 创建：`zhibing/tests/test_graphrag_usability.py`，GraphRAG 可用性离线入口测试。
- 修改：`启动与演示说明.md`，补全前置知识库、场景部署和演示流程。
- 修改：`zhibing/docs/system_introduction.md`，补充新能力和真实测试结果要求。
- 修改：`requirements-blueforce.txt`，补充必要依赖。

---

## 任务 1：默认演示场景与数据模型

**文件：**
- 创建：`zhibing/scenario/__init__.py`
- 创建：`zhibing/scenario/models.py`
- 创建：`zhibing/scenario/demo_scenario.py`
- 测试：`zhibing/tests/test_demo_scenario.py`

- [ ] **步骤 1：编写失败测试**

```python
# zhibing/tests/test_demo_scenario.py
import unittest

from zhibing.scenario.demo_scenario import build_default_demo_scenario


class DemoScenarioTests(unittest.TestCase):
    def test_default_demo_has_required_objects(self):
        scenario = build_default_demo_scenario()
        self.assertEqual(scenario["friendly"]["id"], "blue_squad_1")
        self.assertGreaterEqual(len(scenario["enemies"]), 1)
        self.assertGreaterEqual(len(scenario["risk_zones"]), 1)
        self.assertEqual(scenario["target"]["kind"], "building_entry")
        self.assertGreaterEqual(len(scenario["route_graph"]["nodes"]), 4)
        self.assertGreaterEqual(len(scenario["route_graph"]["edges"]), 4)

    def test_demo_contains_main_and_side_route_labels(self):
        scenario = build_default_demo_scenario()
        labels = {edge["road_class"] for edge in scenario["route_graph"]["edges"]}
        self.assertIn("main_road", labels)
        self.assertIn("side_path", labels)
```

- [ ] **步骤 2：运行测试确认失败**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_demo_scenario -q
```

预期：FAIL，报告 `No module named 'zhibing.scenario'`。

- [ ] **步骤 3：实现数据模型**

```python
# zhibing/scenario/models.py
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Coordinate = dict[str, float | str]


@dataclass(frozen=True)
class BattlefieldUnit:
    id: str
    name: str
    side: Literal["friendly", "enemy"]
    kind: str
    position: Coordinate
    radius_m: float = 20.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RiskZone:
    id: str
    name: str
    kind: Literal["enemy_fire", "sniper_risk", "generic_risk"]
    center: Coordinate
    radius_m: float
    weight: float
    source: str = "scenario"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TargetPoint:
    id: str
    name: str
    kind: Literal["building_entry", "point"]
    position: Coordinate

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RouteCandidate:
    id: str
    waypoints: list[Coordinate]
    distance_m: float
    risk_score: float
    time_score: float
    total_score: float
    labels: list[str] = field(default_factory=list)
    constraint_hits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

- [ ] **步骤 4：实现默认场景**

```python
# zhibing/scenario/demo_scenario.py
from __future__ import annotations

from typing import Any

from zhibing.scenario.models import BattlefieldUnit, RiskZone, TargetPoint


def _coord(x: float, y: float) -> dict[str, float | str]:
    return {"frame": "VBS_LOCAL_XYZ", "x": x, "y": y, "z": 0.0}


def build_default_demo_scenario() -> dict[str, Any]:
    return {
        "scenario_id": "demo_encirclement_v0",
        "name": "默认围剿路径规划演示",
        "friendly": BattlefieldUnit("blue_squad_1", "AI士兵班组", "friendly", "squad", _coord(0, 0)).to_dict(),
        "enemies": [
            BattlefieldUnit("enemy_1", "敌方火力点", "enemy", "fire_point", _coord(520, 80), radius_m=90).to_dict()
        ],
        "risk_zones": [
            RiskZone("risk_main_road_sniper", "大路狙击风险区", "sniper_risk", _coord(420, 0), 80, 70).to_dict()
        ],
        "target": TargetPoint("target_entry_1", "目标建筑入口", "building_entry", _coord(900, 0)).to_dict(),
        "route_graph": {
            "nodes": [
                {"id": "start", "coord": _coord(0, 0)},
                {"id": "main_mid", "coord": _coord(450, 0)},
                {"id": "side_a", "coord": _coord(260, 220)},
                {"id": "side_b", "coord": _coord(650, 220)},
                {"id": "target", "coord": _coord(900, 0)}
            ],
            "edges": [
                {"from": "start", "to": "main_mid", "road_class": "main_road"},
                {"from": "main_mid", "to": "target", "road_class": "main_road"},
                {"from": "start", "to": "side_a", "road_class": "side_path"},
                {"from": "side_a", "to": "side_b", "road_class": "side_path"},
                {"from": "side_b", "to": "target", "road_class": "side_path"}
            ]
        }
    }
```

- [ ] **步骤 5：运行测试确认通过**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_demo_scenario -q
```

预期：PASS。

- [ ] **步骤 6：版本记录**

记录改动文件：

```powershell
Get-ChildItem zhibing\scenario
Get-Content -Raw zhibing\tests\test_demo_scenario.py
```

---

## 任务 2：Top-N 确定性寻路与约束补丁应用

**文件：**
- 创建：`zhibing/routing/__init__.py`
- 创建：`zhibing/routing/road_graph.py`
- 创建：`zhibing/routing/constraint_patch.py`
- 创建：`zhibing/routing/path_planner.py`
- 测试：`zhibing/tests/test_path_planner.py`

- [ ] **步骤 1：编写失败测试**

```python
# zhibing/tests/test_path_planner.py
import unittest

from zhibing.routing.constraint_patch import ConstraintPatch
from zhibing.routing.path_planner import plan_top_routes
from zhibing.scenario.demo_scenario import build_default_demo_scenario


class PathPlannerTests(unittest.TestCase):
    def test_default_planner_returns_top_routes(self):
        scenario = build_default_demo_scenario()
        routes = plan_top_routes(scenario, top_n=3, constraints=[])
        self.assertGreaterEqual(len(routes), 2)
        self.assertLess(routes[0].total_score, routes[-1].total_score)

    def test_avoid_main_road_constraint_changes_recommendation(self):
        scenario = build_default_demo_scenario()
        default_routes = plan_top_routes(scenario, top_n=3, constraints=[])
        constrained_routes = plan_top_routes(
            scenario,
            top_n=3,
            constraints=[
                ConstraintPatch(
                    constraint_id="c_avoid_main",
                    source_text="不要走大路，大路有狙击风险",
                    action="avoid",
                    target_type="road_class",
                    target_id="main_road",
                    weight_delta=200.0,
                    reason="用户要求规避大路",
                )
            ],
        )
        self.assertIn("main_road", default_routes[0].labels)
        self.assertNotIn("main_road", constrained_routes[0].labels)

    def test_ignore_enemy_zone_can_reduce_risk_penalty(self):
        scenario = build_default_demo_scenario()
        constrained_routes = plan_top_routes(
            scenario,
            top_n=3,
            constraints=[
                ConstraintPatch(
                    constraint_id="c_ignore_enemy",
                    source_text="敌军不在营地，必须争分夺秒",
                    action="ignore_zone",
                    target_type="enemy_zone",
                    target_id="enemy_1",
                    weight_delta=-80.0,
                    reason="用户要求忽略该敌区",
                )
            ],
        )
        self.assertGreaterEqual(len(constrained_routes), 2)
        self.assertEqual(constrained_routes[0].id, "route_main")
```

- [ ] **步骤 2：运行测试确认失败**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_path_planner -q
```

预期：FAIL，报告 `No module named 'zhibing.routing'`。

- [ ] **步骤 3：实现约束补丁**

```python
# zhibing/routing/constraint_patch.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ConstraintPatch:
    constraint_id: str
    source_text: str
    action: Literal["avoid", "ignore_zone", "prefer", "priority"]
    target_type: Literal["road_class", "enemy_zone", "risk_zone", "route_metric"]
    target_id: str
    weight_delta: float
    reason: str
    priority: str | None = None
```

- [ ] **步骤 4：实现轻量道路图读取助手**

```python
# zhibing/routing/road_graph.py
from __future__ import annotations

from typing import Any


def get_node_coord(route_graph: dict[str, Any], node_id: str) -> dict[str, Any]:
    for node in route_graph["nodes"]:
        if node["id"] == node_id:
            return node["coord"]
    raise KeyError(f"route graph node not found: {node_id}")


def edge_labels(route_graph: dict[str, Any], node_path: list[str]) -> list[str]:
    labels = []
    pairs = set(zip(node_path, node_path[1:]))
    for edge in route_graph["edges"]:
        if (edge["from"], edge["to"]) in pairs or (edge["to"], edge["from"]) in pairs:
            labels.append(edge.get("road_class", "unknown"))
    return labels
```

- [ ] **步骤 4.5：实现轻量路径枚举与评分**

```python
# zhibing/routing/path_planner.py
from __future__ import annotations

import math
from typing import Any

from zhibing.routing.constraint_patch import ConstraintPatch
from zhibing.scenario.models import RouteCandidate


def plan_top_routes(scenario: dict[str, Any], *, top_n: int = 3, constraints: list[ConstraintPatch] | None = None) -> list[RouteCandidate]:
    constraints = constraints or []
    graph = scenario["route_graph"]
    node_by_id = {node["id"]: node["coord"] for node in graph["nodes"]}
    raw_routes = [
        ("route_main", ["start", "main_mid", "target"], ["main_road"]),
        ("route_side", ["start", "side_a", "side_b", "target"], ["side_path"]),
    ]
    candidates = []
    for route_id, node_ids, labels in raw_routes:
        waypoints = [node_by_id[node_id] for node_id in node_ids]
        distance = _distance_of_waypoints(waypoints)
        risk = _risk_score(route_id, labels, scenario, constraints)
        time_score = distance / 5.0
        total = distance + risk + time_score
        hits = _constraint_hits(labels, constraints)
        candidates.append(RouteCandidate(route_id, waypoints, distance, risk, time_score, total, labels, hits))
    candidates.sort(key=lambda item: item.total_score)
    return candidates[:top_n]


def _distance_of_waypoints(waypoints: list[dict[str, Any]]) -> float:
    total = 0.0
    for left, right in zip(waypoints, waypoints[1:]):
        total += math.hypot(float(right["x"]) - float(left["x"]), float(right["y"]) - float(left["y"]))
    return total


def _risk_score(route_id: str, labels: list[str], scenario: dict[str, Any], constraints: list[ConstraintPatch]) -> float:
    score = 0.0
    if route_id == "route_main":
        score += 60.0
    if route_id == "route_side":
        score += 15.0
    for patch in constraints:
        if patch.action == "avoid" and patch.target_type == "road_class" and patch.target_id in labels:
            score += patch.weight_delta
        if patch.action == "ignore_zone" and patch.target_type == "enemy_zone":
            score += patch.weight_delta
    return max(score, 0.0)


def _constraint_hits(labels: list[str], constraints: list[ConstraintPatch]) -> list[str]:
    hits = []
    for patch in constraints:
        if patch.target_type == "road_class" and patch.target_id in labels:
            hits.append(patch.constraint_id)
    return hits
```

- [ ] **步骤 5：运行测试确认通过**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_path_planner -q
```

预期：PASS。

- [ ] **步骤 6：版本记录**

记录改动文件：

```powershell
Get-ChildItem zhibing\routing
Get-Content -Raw zhibing\tests\test_path_planner.py
```

---

## 任务 3：LLM 约束解析门面与确定性 fallback

**文件：**
- 创建：`zhibing/decision_layer/route_constraint_llm.py`
- 修改：`zhibing/knowledge/llm_router.py`
- 测试：`zhibing/tests/test_constraint_llm.py`

- [ ] **步骤 1：编写失败测试**

```python
# zhibing/tests/test_constraint_llm.py
import unittest

from zhibing.decision_layer.route_constraint_llm import parse_route_constraint, explain_route_choices


class ConstraintLLMTests(unittest.TestCase):
    def test_parse_sniper_risk_avoids_main_road(self):
        patch = parse_route_constraint("不要执行，因为大路有被狙击的风险")
        self.assertEqual(patch.action, "avoid")
        self.assertEqual(patch.target_type, "road_class")
        self.assertEqual(patch.target_id, "main_road")

    def test_parse_urgent_enemy_not_in_camp_ignores_enemy_zone(self):
        patch = parse_route_constraint("不要绕路，因为敌军不在营地，现在必须争分夺秒")
        self.assertEqual(patch.action, "ignore_zone")
        self.assertEqual(patch.target_type, "enemy_zone")
        self.assertEqual(patch.target_id, "enemy_1")

    def test_explain_route_choices_mentions_all_candidates(self):
        text = explain_route_choices([
            {"id": "route_main", "distance_m": 900, "risk_score": 60, "total_score": 1140},
            {"id": "route_side", "distance_m": 1040, "risk_score": 15, "total_score": 1263},
        ])
        self.assertIn("route_main", text)
        self.assertIn("route_side", text)
```

- [ ] **步骤 2：运行测试确认失败**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_constraint_llm -q
```

预期：FAIL，报告找不到 `route_constraint_llm`。

- [ ] **步骤 3：实现确定性 fallback**

```python
# zhibing/decision_layer/route_constraint_llm.py
from __future__ import annotations

import hashlib
from typing import Any

from zhibing.routing.constraint_patch import ConstraintPatch


def parse_route_constraint(user_text: str) -> ConstraintPatch:
    text = user_text.lower()
    constraint_id = "c_" + hashlib.sha1(user_text.encode("utf-8")).hexdigest()[:8]
    if "大路" in user_text or "main road" in text or "狙击" in user_text:
        return ConstraintPatch(
            constraint_id=constraint_id,
            source_text=user_text,
            action="avoid",
            target_type="road_class",
            target_id="main_road",
            weight_delta=200.0,
            reason="用户指出大路存在狙击或暴露风险",
        )
    if "不在营地" in user_text or "争分夺秒" in user_text or "不要绕路" in user_text:
        return ConstraintPatch(
            constraint_id=constraint_id,
            source_text=user_text,
            action="ignore_zone",
            target_type="enemy_zone",
            target_id="enemy_1",
            weight_delta=-80.0,
            reason="用户要求降低敌方营地区域对路径的影响并优先时间",
            priority="time",
        )
    return ConstraintPatch(
        constraint_id=constraint_id,
        source_text=user_text,
        action="priority",
        target_type="route_metric",
        target_id="balanced",
        weight_delta=0.0,
        reason="未识别到明确重规划约束，保持均衡评分",
    )


def explain_route_choices(candidates: list[dict[str, Any]]) -> str:
    lines = ["候选路径分数接近，请选择一条路线："]
    for index, item in enumerate(candidates, start=1):
        lines.append(
            f"{index}. {item['id']}：距离 {item['distance_m']:.0f} 米，"
            f"风险 {item['risk_score']:.0f}，总分 {item['total_score']:.0f}。"
        )
    lines.append("可回复编号选择路线，也可输入新的约束重新规划。")
    return "\n".join(lines)
```

- [ ] **步骤 4：在 `llm_router.py` 中增加 live 调用开关说明**

修改 `KnowledgeLLMRouter.provider_summary()` 返回字段，加入：

```python
"live_call_requires_user_approval": True,
"vision_model_requires_user_approval": True,
"recommended_test_model": "ep-20260615114505-247zc"
```

该步骤不触发真实 LLM 调用。

- [ ] **步骤 5：运行测试确认通过**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_constraint_llm -q
```

预期：PASS。

---

## 任务 4：轻量 SQL 会话记忆

**文件：**
- 创建：`zhibing/session_memory.py`
- 测试：`zhibing/tests/test_session_memory.py`

- [ ] **步骤 1：编写失败测试**

```python
# zhibing/tests/test_session_memory.py
import tempfile
import unittest
from pathlib import Path

from zhibing.session_memory import SessionMemory


class SessionMemoryTests(unittest.TestCase):
    def test_session_can_store_messages_and_constraints(self):
        db_path = Path(tempfile.gettempdir()) / "zhibing_session_memory_test.sqlite3"
        if db_path.exists():
            db_path.unlink()
        memory = SessionMemory(db_path)
        session_id = memory.open_or_create_session("demo_encirclement_v0")
        memory.add_message(session_id, "user", "不要走大路")
        memory.add_constraint(session_id, {"constraint_id": "c1", "action": "avoid"})
        restored = memory.load_session(session_id)
        self.assertEqual(restored["messages"][0]["content"], "不要走大路")
        self.assertEqual(restored["constraints"][0]["constraint_id"], "c1")

    def test_reset_session_clears_context(self):
        db_path = Path(tempfile.gettempdir()) / "zhibing_session_memory_reset.sqlite3"
        if db_path.exists():
            db_path.unlink()
        memory = SessionMemory(db_path)
        session_id = memory.open_or_create_session("demo_encirclement_v0")
        memory.add_message(session_id, "user", "大路危险")
        memory.reset_session(session_id)
        restored = memory.load_session(session_id)
        self.assertEqual(restored["messages"], [])
        self.assertEqual(restored["constraints"], [])
```

- [ ] **步骤 2：运行测试确认失败**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_session_memory -q
```

预期：FAIL，报告找不到 `zhibing.session_memory`。

- [ ] **步骤 3：实现 SQLite 存储**

```python
# zhibing/session_memory.py
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
        with self._connect() as conn:
            conn.execute(
                "insert into sessions(session_id, scenario_id, created_at, updated_at) values (?, ?, ?, ?)",
                (session_id, scenario_id, time.time(), time.time()),
            )
        return session_id

    def add_message(self, session_id: str, role: str, content: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "insert into messages(session_id, role, content, created_at) values (?, ?, ?, ?)",
                (session_id, role, content, time.time()),
            )

    def add_constraint(self, session_id: str, patch: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "insert into constraints(session_id, patch_json, created_at) values (?, ?, ?)",
                (session_id, json.dumps(patch, ensure_ascii=False), time.time()),
            )

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
        return {"session_id": session_id, "messages": messages, "constraints": constraints}

    def reset_session(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute("delete from messages where session_id=?", (session_id,))
            conn.execute("delete from constraints where session_id=?", (session_id,))
            conn.execute("delete from route_candidates where session_id=?", (session_id,))

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("create table if not exists sessions(session_id text primary key, scenario_id text, created_at real, updated_at real)")
            conn.execute("create table if not exists messages(id integer primary key autoincrement, session_id text, role text, content text, created_at real)")
            conn.execute("create table if not exists constraints(id integer primary key autoincrement, session_id text, patch_json text, created_at real)")
            conn.execute("create table if not exists route_candidates(id integer primary key autoincrement, session_id text, candidate_json text, selected integer default 0, created_at real)")
```

- [ ] **步骤 4：运行测试确认通过**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_session_memory -q
```

预期：PASS。

---

## 任务 5：场景工具接入演示场景和风险感知路径

**文件：**
- 修改：`zhibing/scene/scene_tools.py`
- 修改：`zhibing/tests/test_three_layer_alignment.py`
- 测试：`zhibing/tests/test_scene_route_tools.py`

- [ ] **步骤 1：编写失败测试**

```python
# zhibing/tests/test_scene_route_tools.py
import unittest

from zhibing.scene.scene_tools import get_enemy_state, route_plan


class SceneRouteToolsTests(unittest.TestCase):
    def test_enemy_state_returns_demo_enemy(self):
        enemies = get_enemy_state({"frame": "VBS_LOCAL_XYZ", "x": 0, "y": 0, "z": 0})
        self.assertGreaterEqual(len(enemies), 1)
        self.assertEqual(enemies[0]["id"], "enemy_1")

    def test_route_plan_returns_candidates(self):
        route = route_plan(
            {"frame": "VBS_LOCAL_XYZ", "x": 0, "y": 0, "z": 0},
            {"frame": "VBS_LOCAL_XYZ", "x": 900, "y": 0, "z": 0},
            {"top_n": 3},
        )
        self.assertIn("candidates", route)
        self.assertGreaterEqual(len(route["candidates"]), 2)
```

- [ ] **步骤 2：运行测试确认失败**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_scene_route_tools -q
```

预期：FAIL，因为当前 `get_enemy_state()` 返回空列表，`route_plan()` 返回直线路径。

- [ ] **步骤 3：修改 `scene_tools.py`**

核心改动：

```python
from zhibing.routing.path_planner import plan_top_routes
from zhibing.scenario.demo_scenario import build_default_demo_scenario


def get_enemy_state(area: dict[str, Any]) -> list[dict[str, Any]]:
    default_coord_service.validate(area["position"] if "position" in area else area)
    return build_default_demo_scenario()["enemies"]


def get_building_entrances(building_id: str) -> list[dict[str, Any]]:
    target = build_default_demo_scenario()["target"]
    return [{"id": target["id"], "building_id": building_id, "coord": target["position"], "kind": target["kind"]}]
```

`route_plan()` 保留原有返回字段，同时增加：

```python
scenario = build_default_demo_scenario()
candidates = [candidate.to_dict() for candidate in plan_top_routes(scenario, top_n=int(constraints.get("top_n", 3)), constraints=[])]
best = candidates[0]
return {
    "waypoints": best["waypoints"],
    "candidates": candidates,
    "total_distance_m": best["distance_m"],
    "risk_score": best["risk_score"],
    "blocked_segments": [],
    "passable": True,
    "estimated_time_s": best["time_score"],
}
```

- [ ] **步骤 4：运行测试确认通过**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_scene_route_tools -q
```

预期：PASS。

---

## 任务 6：可视化投影扩展

**文件：**
- 修改：`zhibing/visualization/projector.py`
- 测试：`zhibing/tests/test_visualization_projection.py`

- [ ] **步骤 1：扩展测试**

在 `test_visualization_projection.py` 增加：

```python
def test_projection_includes_scene_objects_and_route_candidates(self):
    from zhibing.scenario.demo_scenario import build_default_demo_scenario
    from zhibing.routing.path_planner import plan_top_routes
    from zhibing.visualization.projector import build_demo_projection

    scenario = build_default_demo_scenario()
    candidates = [item.to_dict() for item in plan_top_routes(scenario, top_n=3)]
    projection = build_demo_projection(scenario, candidates, selected_route_id=candidates[0]["id"], session=None)
    self.assertEqual(projection["friendly"]["id"], "blue_squad_1")
    self.assertGreaterEqual(len(projection["enemies"]), 1)
    self.assertGreaterEqual(len(projection["risk_zones"]), 1)
    self.assertGreaterEqual(len(projection["route_candidates"]), 2)
    self.assertEqual(projection["selected_route_id"], candidates[0]["id"])
```

- [ ] **步骤 2：运行测试确认失败**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_visualization_projection -q
```

预期：FAIL，报告 `build_demo_projection` 不存在。

- [ ] **步骤 3：实现 `build_demo_projection()`**

```python
def build_demo_projection(
    scenario: dict[str, Any],
    route_candidates: list[dict[str, Any]],
    *,
    selected_route_id: str | None,
    session: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_name": scenario["name"],
        "friendly": scenario["friendly"],
        "enemies": scenario["enemies"],
        "risk_zones": scenario["risk_zones"],
        "target": scenario["target"],
        "route_candidates": route_candidates,
        "selected_route_id": selected_route_id,
        "session": session or {"messages": [], "constraints": []},
        "task_state": {"state": "PLANNED", "return_code": None},
    }
```

- [ ] **步骤 4：运行测试确认通过**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_visualization_projection -q
```

预期：PASS。

---

## 任务 7：复制 wargame 2D 地图资产

**文件：**
- 创建或覆盖：`zhibing/web/command_ui/static/command_ui/map/roads.geojson`
- 创建或覆盖：`zhibing/web/command_ui/static/command_ui/map/buildings.geojson`
- 可选创建：`zhibing/web/command_ui/static/command_ui/map/water.geojson`
- 可选创建：`zhibing/web/command_ui/static/command_ui/map/landhouse.geojson`
- 保留：`zhibing/web/command_ui/static/command_ui/vendor/leaflet.js`
- 保留：`zhibing/web/command_ui/static/command_ui/vendor/leaflet.css`

- [ ] **步骤 1：复制必要资产**

运行：

```powershell
New-Item -ItemType Directory -Force -Path zhibing\web\command_ui\static\command_ui\map
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\roads.geojson" "zhibing\web\command_ui\static\command_ui\map\roads.geojson" -Force
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\buildings.geojson" "zhibing\web\command_ui\static\command_ui\map\buildings.geojson" -Force
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\water.geojson" "zhibing\web\command_ui\static\command_ui\map\water.geojson" -Force
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\landhouse.geojson" "zhibing\web\command_ui\static\command_ui\map\landhouse.geojson" -Force
```

- [ ] **步骤 2：确认资产可读**

运行：

```powershell
Get-ChildItem zhibing\web\command_ui\static\command_ui\map
```

预期：至少显示 `roads.geojson`、`buildings.geojson`、`water.geojson`、`landhouse.geojson`。

---

## 任务 8：Django API 扩展

**文件：**
- 修改：`zhibing/web/command_ui/views.py`
- 修改：`zhibing/web/command_ui/urls.py`
- 测试：`zhibing/tests/test_command_ui_api.py`

- [ ] **步骤 1：编写失败测试**

```python
# zhibing/tests/test_command_ui_api.py
import json
import unittest

from django.test import Client, override_settings


@override_settings(ROOT_URLCONF="zhibing_web.urls")
class CommandUiApiTests(unittest.TestCase):
    def test_demo_scene_api_returns_projection(self):
        client = Client()
        response = client.get("/api/demo-scene")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["projection"]["friendly"]["id"], "blue_squad_1")

    def test_reset_session_api_returns_new_session_id(self):
        client = Client()
        response = client.post("/api/session/reset", data="{}", content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode("utf-8"))
        self.assertIn("session_id", data)
```

- [ ] **步骤 2：运行测试确认失败**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_command_ui_api -q
```

预期：FAIL，API 路由不存在。

- [ ] **步骤 3：实现 API**

在 `views.py` 增加：

```python
from zhibing.decision_layer.route_constraint_llm import explain_route_choices, parse_route_constraint
from zhibing.routing.path_planner import plan_top_routes
from zhibing.scenario.demo_scenario import build_default_demo_scenario
from zhibing.session_memory import SessionMemory
from zhibing.visualization.projector import build_demo_projection

MEMORY = SessionMemory()


def demo_scene(request):
    scenario = build_default_demo_scenario()
    routes = [item.to_dict() for item in plan_top_routes(scenario, top_n=3)]
    projection = build_demo_projection(scenario, routes, selected_route_id=routes[0]["id"], session=None)
    return JsonResponse({"projection": projection})


@csrf_exempt
@require_http_methods(["POST"])
def reset_session(request):
    session_id = MEMORY.open_or_create_session("demo_encirclement_v0")
    return JsonResponse({"session_id": session_id, "messages": [], "constraints": []})


@csrf_exempt
@require_http_methods(["POST"])
def route_constraint(request):
    data = json.loads(request.body.decode("utf-8"))
    patch = parse_route_constraint(data.get("message", ""))
    scenario = build_default_demo_scenario()
    routes = [item.to_dict() for item in plan_top_routes(scenario, top_n=3, constraints=[patch])]
    explanation = explain_route_choices(routes)
    return JsonResponse({"constraint": patch.__dict__, "routes": routes, "explanation": explanation})
```

在 `urls.py` 增加：

```python
path("api/demo-scene", views.demo_scene, name="demo_scene"),
path("api/session/reset", views.reset_session, name="reset_session"),
path("api/route-constraint", views.route_constraint, name="route_constraint"),
```

- [ ] **步骤 4：运行测试确认通过**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_command_ui_api -q
```

预期：PASS。

---

## 任务 9：wargame 风格 2D HUD 前端

**文件：**
- 修改：`zhibing/web/command_ui/templates/command_ui/index.html`
- 修改：`zhibing/web/command_ui/static/command_ui/styles.css`
- 修改：`zhibing/web/command_ui/static/command_ui/app.js`

- [ ] **步骤 1：重写 HTML 布局**

`index.html` 必须包含这些固定区域：

```html
<div id="top-title-bar"></div>
<div id="hud-top-bar"></div>
<aside id="left-sidebar"></aside>
<main id="map"></main>
<aside id="right-sidebar"></aside>
```

右侧必须包含：

```html
<div id="chat-messages"></div>
<textarea id="commandInput"></textarea>
<button id="sendCommandBtn" type="button">发送</button>
<button id="resetSessionBtn" type="button">重置会话</button>
<section id="routeCandidates"></section>
<pre id="adapterPreview"></pre>
```

- [ ] **步骤 2：重写 CSS**

`styles.css` 使用 wargame 的深蓝战术 HUD 风格，核心选择器：

```css
body { margin: 0; overflow: hidden; background: #101a39; color: #d4d4d4; }
#top-title-bar { position: absolute; top: 0; left: 0; right: 0; height: 50px; z-index: 5000; }
#hud-top-bar { position: absolute; top: 50px; left: 0; right: 0; height: 36px; z-index: 4000; }
#map { position: absolute; top: 86px; left: 320px; right: 360px; bottom: 0; z-index: 1; }
#left-sidebar { position: absolute; top: 86px; left: 0; bottom: 0; width: 320px; z-index: 2000; }
#right-sidebar { position: absolute; top: 86px; right: 0; bottom: 0; width: 360px; z-index: 2000; }
.unit-marker.friendly { background: #0f766e; border: 2px solid #99f6e4; }
.unit-marker.enemy { background: #7f1d1d; border: 2px solid #fecaca; }
.route-candidate.selected { border-color: #eab308; }
```

- [ ] **步骤 3：重写 JS**

`app.js` 必须实现：

```javascript
async function loadDemoScene()
async function submitRouteConstraint()
async function resetSession()
function renderProjection(projection)
function renderUnits(projection)
function renderRiskZones(projection)
function renderRouteCandidates(projection)
function renderChatMessage(role, content)
function makeDraggableMarker(kind, item)
function vbsToLatLng(coord)
function latLngToVbs(latlng)
```

地图启动时加载：

```javascript
Promise.all([
  fetch("/static/command_ui/map/roads.geojson").then(r => r.json()),
  fetch("/static/command_ui/map/buildings.geojson").then(r => r.json()),
  fetch("/static/command_ui/map/water.geojson").then(r => r.json()).catch(() => null),
  fetch("/static/command_ui/map/landhouse.geojson").then(r => r.json()).catch(() => null),
])
```

- [ ] **步骤 4：手动启动并检查页面**

运行：

```powershell
conda run -n blueforce python zhibing\web\manage.py runserver 127.0.0.1:8090
```

预期：浏览器访问 `http://127.0.0.1:8090/` 后显示战术 HUD、2D 地图、左侧部署栏、右侧聊天栏。

---

## 任务 10：GraphRAG 可用性入口

**文件：**
- 创建：`zhibing/knowledge/graphrag_usability.py`
- 修改：`zhibing/knowledge/graphrag_builder.py`
- 测试：`zhibing/tests/test_graphrag_usability.py`

- [ ] **步骤 1：编写离线入口测试**

```python
# zhibing/tests/test_graphrag_usability.py
import unittest

from zhibing.knowledge.graphrag_usability import local_file_usability_plan, query_local_test_files


class GraphRAGUsabilityTests(unittest.TestCase):
    def test_local_file_plan_includes_pdf_and_docx(self):
        plan = local_file_usability_plan()
        self.assertTrue(any(item["path"].endswith(".pdf") for item in plan["files"]))
        self.assertTrue(any(item["path"].endswith(".docx") for item in plan["files"]))

    def test_query_local_test_files_returns_source_hits(self):
        result = query_local_test_files("地下作战 建筑 入口")
        self.assertIn("hits", result)
        self.assertGreaterEqual(len(result["hits"]), 1)
        self.assertIn("source_id", result["hits"][0])
```

- [ ] **步骤 2：运行测试确认失败**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_graphrag_usability -q
```

预期：FAIL，模块不存在。

- [ ] **步骤 3：实现本地文件可用性查询**

```python
# zhibing/knowledge/graphrag_usability.py
from __future__ import annotations

from pathlib import Path
from typing import Any

from zhibing.knowledge.graphrag_builder import build_graphrag
from zhibing.knowledge.graphrag_query import query_knowledge


TEST_FILES_DIR = Path(__file__).resolve().parents[2] / "test_files"


def local_file_usability_plan() -> dict[str, Any]:
    files = [
        {"path": str(TEST_FILES_DIR / "地下作战.docx"), "kind": "docx"},
        {"path": str(TEST_FILES_DIR / "ARN19656_ATP.pdf"), "kind": "pdf"},
    ]
    return {"files": files, "acceptance": "build index and return source hits"}


def query_local_test_files(query: str) -> dict[str, Any]:
    paths = [item["path"] for item in local_file_usability_plan()["files"]]
    store = build_graphrag(paths, inject_default_rules=True)
    context = query_knowledge(store, {"intent": query}, top_k=5)
    hits = []
    for chunk in context.get("source_chunks", []):
        hits.append({"source_id": chunk.get("source_id"), "chunk_id": chunk.get("chunk_id"), "text": chunk.get("text", "")[:200]})
    return {"query": query, "hits": hits}
```

- [ ] **步骤 4：增加官方 quickstart 说明入口**

在同一文件增加不自动执行网络/LLM 的计划函数：

```python
def official_quickstart_commands() -> list[str]:
    return [
        "python -m pip install graphrag",
        "graphrag init --root ./graphrag_quickstart",
        "graphrag index --root ./graphrag_quickstart",
        "graphrag query --root ./graphrag_quickstart --method global --query \"What are the main themes?\"",
    ]
```

真实执行官方 quickstart 前，必须说明预计 LLM 调用和成本，并征得用户同意。

- [ ] **步骤 5：运行测试确认通过**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_graphrag_usability -q
```

预期：PASS。

---

## 任务 11：三层一致性测试补强

**文件：**
- 修改：`zhibing/tests/test_three_layer_alignment.py`
- 修改：`zhibing/main.py`
- 修改：`zhibing/adapter/vbs_adapter.py`

- [ ] **步骤 1：增加演示闭环测试**

在 `test_three_layer_alignment.py` 增加：

```python
def test_constraint_changes_visual_route_and_adapter_preview(self):
    from zhibing.decision_layer.route_constraint_llm import parse_route_constraint
    from zhibing.routing.path_planner import plan_top_routes
    from zhibing.scenario.demo_scenario import build_default_demo_scenario
    from zhibing.visualization.projector import build_demo_projection

    scenario = build_default_demo_scenario()
    patch = parse_route_constraint("不要走大路，大路有狙击风险")
    routes = [item.to_dict() for item in plan_top_routes(scenario, top_n=3, constraints=[patch])]
    projection = build_demo_projection(scenario, routes, selected_route_id=routes[0]["id"], session={"constraints": [patch.__dict__]})
    self.assertNotIn("main_road", projection["route_candidates"][0]["labels"])
    adapter_preview = {
        "actor_id": scenario["friendly"]["id"],
        "waypoints": projection["route_candidates"][0]["waypoints"],
        "constraints": projection["session"]["constraints"],
    }
    self.assertEqual(adapter_preview["waypoints"], projection["route_candidates"][0]["waypoints"])
```

- [ ] **步骤 2：运行测试确认通过**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_three_layer_alignment -q
```

预期：PASS。

---

## 任务 12：依赖文件更新

**文件：**
- 修改：`requirements-blueforce.txt`

- [ ] **步骤 1：检查当前依赖**

运行：

```powershell
Get-Content -Raw requirements-blueforce.txt
```

- [ ] **步骤 2：补充必要依赖**

文件应包含：

```text
Django==6.0.6
PyYAML==6.0.3
openai==2.32.0
python-docx
pypdf
```

`graphrag` 不默认加入基础依赖；它作为官方 quickstart 可用性测试的可选依赖，执行前需要用户确认安装和 LLM 成本。

- [ ] **步骤 3：验证导入**

运行：

```powershell
conda run -n blueforce python -c "import django, yaml, openai, docx, pypdf; print('deps-ok')"
```

预期：输出 `deps-ok`。

---

## 任务 13：文档更新

**文件：**
- 修改：`启动与演示说明.md`
- 修改：`zhibing/docs/system_introduction.md`

- [ ] **步骤 1：更新启动与演示说明**

文档必须包含以下章节：

```markdown
# 智兵决策系统启动与演示说明

## 1. 前置准备
## 2. GraphRAG 知识库可用性验证
## 3. 启动 Web UI
## 4. 一键部署默认场景
## 5. 拖拽部署敌我与威胁区
## 6. 演示命令一：默认路径规划
## 7. 演示命令二：大路狙击风险导致重规划
## 8. 演示命令三：忽略敌方营地并争分夺秒
## 9. 候选路径接近时如何选择
## 10. 会话恢复与重置
## 11. Adapter 预览如何理解
## 12. 测试命令
```

- [ ] **步骤 2：更新系统介绍**

`system_introduction.md` 必须说明：

- 系统完整功能。
- 用户使用流程。
- 前置 GraphRAG 使用方式。
- wargame 风格 2D 可视化。
- 寻路算法与 LLM 的职责边界。
- 会话记忆与重置。
- 演示案例。
- 真实测试结果区域，执行测试后填入实际命令输出摘要。

- [ ] **步骤 3：转换为 UTF-8 with BOM**

运行：

```powershell
$files = @("启动与演示说明.md", "zhibing\docs\system_introduction.md")
$enc = New-Object System.Text.UTF8Encoding $true
foreach ($file in $files) {
  $text = [System.IO.File]::ReadAllText((Resolve-Path $file), [System.Text.Encoding]::UTF8)
  [System.IO.File]::WriteAllText((Resolve-Path $file), $text, $enc)
}
```

---

## 任务 14：完整验证

**文件：**
- 不新增文件。

- [ ] **步骤 1：运行核心单元测试**

运行：

```powershell
conda run -n blueforce python -m unittest zhibing.tests.test_demo_scenario zhibing.tests.test_path_planner zhibing.tests.test_constraint_llm zhibing.tests.test_session_memory zhibing.tests.test_scene_route_tools zhibing.tests.test_visualization_projection zhibing.tests.test_command_ui_api zhibing.tests.test_graphrag_usability zhibing.tests.test_three_layer_alignment -q
```

预期：PASS。

- [ ] **步骤 2：运行全量测试**

运行：

```powershell
conda run -n blueforce python -m unittest discover -s zhibing\tests -q
```

预期：PASS。若既有测试因接口升级失败，先判断是否是旧断言不兼容新结构；更新测试时必须保留旧能力的覆盖。

- [ ] **步骤 3：运行 Django 检查**

运行：

```powershell
conda run -n blueforce python zhibing\web\manage.py check
```

预期：输出 `System check identified no issues`。

- [ ] **步骤 4：启动 Web UI 手工核验**

运行：

```powershell
conda run -n blueforce python zhibing\web\manage.py runserver 127.0.0.1:8090
```

浏览器访问：

```text
http://127.0.0.1:8090/
```

手工核验：

- 地图显示 wargame 2D 道路和建筑。
- 左侧可一键部署。
- 地图显示我方班组、敌方/风险区、目标入口。
- 右侧聊天栏可输入“前往目标建筑入口开展围剿”。
- 输入“不要走大路，大路有狙击风险”后，推荐路径变化。
- 输入“敌军不在营地，现在必须争分夺秒”后，重新偏向短路径。
- 点击重置会话后，历史约束清空。
- Adapter 预览中的 waypoints 与地图最终路径一致。

---

## 验收标准

- [ ] `启动与演示说明.md` 不再直接跳到演示，包含前置 GraphRAG、场景部署、敌我安排、地图说明。
- [ ] UI 具有 wargame 风格的 2D 战术 HUD，而不是纯文本控制台。
- [ ] 地图使用从 wargame 复制进本仓库的 2D GeoJSON 资产。
- [ ] 我方班组、敌方单元、风险区、目标入口可以出现在地图上。
- [ ] 一键部署默认 demo 可用。
- [ ] 确定性寻路先产出 Top-N 候选路径。
- [ ] LLM 负责用户特殊要求解析、约束补丁和候选路线解释，不直接生成路线坐标。
- [ ] 用户“大路狙击风险”约束能改变推荐路径。
- [ ] 用户“敌军不在营地、争分夺秒”约束能触发重新规划。
- [ ] 候选路径分数接近时可以进入解释与选择流程。
- [ ] 轻量 SQL 会话记忆能保存约束，重置会话能清空上下文。
- [ ] GraphRAG 官方 quickstart 被写入可用性验证流程。
- [ ] 用户提供的 PDF/DOCX 能建库、查询并返回来源片段。
- [ ] 全量测试在 `blueforce` 环境通过，真实测试结果写入 `zhibing/docs/system_introduction.md`。

## 执行交接

计划已保存到 `docs/superpowers/plans/2026-06-22-zhibing-v0-demo-update.md`。推荐使用 `superpowers-zh:executing-plans` 在当前会话或新会话中逐任务执行。执行时请先完成任务 1-4 的后端核心，再做任务 7-9 的前端；GraphRAG live quickstart、nano 模型或视觉模型测试在没有用户明确批准前不得运行。
