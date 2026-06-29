# 智兵决策系统更新完善实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将现有“智兵决策”MVP 升级为可交付的上层 LLM 指控系统：具备用户进入前的 GraphRAG 知识注入、明确的上下层接口边界、可配置 HITL 节点策略、可视化中间层，以及“意图识别-可视化中间层-仿真底层”一致性测试。

**架构：** 保持四层架构不变：`USER_INTERFACE`、`LLM_DECISION_LAYER`、`VBS_ADAPTER`、`VBS_ENGINE`。本次新增三条横向链路：第一，GraphRAG 在用户进入前吸收条例、PDF、DOCX 与测试语料，运行时自动向 SceneContext/TaskPlanJSON 注入约束；第二，可视化中间层复用 `C:\Users\22646\Desktop\wargame` 的地图资产和界面思路，把意图、路线、目标建筑、状态回传与文本输出并列展示；第三，VBS Adapter 同时支持 HTTP 与 socket transport，由配置选择，默认 HTTP。

**技术栈：** Python 3.9+、标准库 `unittest`、OpenAI-compatible LLM、`llm_call_extract`、火山 Ark 测试模型 `ep-20260615114505-247zc`、本地 OpenWebUI/vLLM 迁移配置、Django、Leaflet、GeoJSON、JSON Schema Draft 7、SQLite/PostgreSQL 可替换存储、轻量 GraphRAG 实体-关系-规则索引。

---

## 已确认边界

- 可视化中间层允许复制 `wargame` 的必要地图资产、图标、GeoJSON、Leaflet 静态文件到本仓库，不依赖外部项目运行。
- GraphRAG 首批真实测试文件固定为：
  - `C:\Users\22646\Desktop\各种测试\智兵决策\test_files\ARN19656_ATP.pdf`
  - `C:\Users\22646\Desktop\各种测试\智兵决策\test_files\地下作战.docx`
- HITL 不预设哪些业务动作必然人工确认，只把“是否需要人工确认”做成配置文件。默认策略只给出合理初始值，后续可编排修改。
- 当前 BT 从简使用：复杂任务通过简单动作组合实现。围剿任务拆成“移动到目标入口 + 态势评估 + 如何移动 + 攻击意图转为可审计任务”。若下层没有真实搜索/攻击 BT，上层只提交当前 registry 可执行部分，并记录后续 tactical intent。
- 下层通信同时设计 HTTP 与 socket，配置决定使用哪一种；默认 HTTP。

## GraphRAG 小 Benchmark 设计

实现时不要只用单个样例验证 GraphRAG。建立一个小型、可复现 benchmark：

- **FormatBench：** 使用 `test_files` 的 PDF 与 DOCX，验证两种常见格式都能抽取文本、实体、关系、规则、来源片段。
- **RuleGroundingBench：** 为每个测试文档手写 8-12 个期望问答和规则断言，例如“地下作战是否需要避开暴露入口”“遇敌突发事件是否应阻塞等待 HITL”。
- **NoiseTripletBench：** 向知识图谱注入 3-5 条错误三元组，验证检索回答必须绑定来源片段，并标记冲突，避免被错误关系带偏。
- **LocalModelBench：** 记录火山 Ark 测试模型与本地 OpenWebUI/vLLM 模型的抽取成功率、JSON 合法率、实体数、规则数、查询延迟。

Benchmark 设计参考公开 GraphRAG 评测思路：GraphRAG 本地模型评测应关注索引效率、知识图谱构建、查询延迟、答案质量和幻觉；图文 grounded question generation 可用于避免无关问题；KG 增强 QA 需要检测答案是否被文本片段和关系三元组支撑。

---

## 文件结构与职责

- 创建：`zhibing/docs/lower_simulation_interface.md`：单独交给下层仿真工程师的接口文档。
- 修改：`zhibing/LOWER_LAYER_CONTRACT.md`：改为摘要，指向新的下层接口文档。
- 创建：`zhibing/interfaces/interface_ownership.py`：机器可读接口所有权矩阵。
- 创建：`zhibing/interfaces/simulation_contract.schema.json`：下层 HTTP/socket 消息 schema。
- 创建：`zhibing/hitl/node_catalog.py`：定义节点类型、节点类别、是否可配置 HITL。
- 创建：`zhibing/hitl/hitl_policy.yaml`：HITL 策略配置文件。
- 修改：`zhibing/hitl/interrupt_handler.py`：从配置读取策略，替换当前硬编码判断。
- 创建：`zhibing/knowledge/llm_router.py`：统一使用 `llm_call_extract` 调火山 Ark，同时预留 OpenWebUI/vLLM。
- 创建：`zhibing/knowledge/document_loader.py`：读取 TXT、MD、JSON、CSV、DOCX、PDF。
- 创建：`zhibing/knowledge/graphrag_store.py`：存储实体、关系、规则、来源片段、检索索引。
- 创建：`zhibing/knowledge/graphrag_builder.py`：从文档抽取实体、关系、约束规则、HITL 节点建议。
- 创建：`zhibing/knowledge/graphrag_query.py`：按 IntentJSON/SceneContext 检索 KnowledgeContext。
- 创建：`zhibing/knowledge/benchmark.py`：运行 FormatBench、RuleGroundingBench、NoiseTripletBench、LocalModelBench。
- 创建：`zhibing/knowledge/benchmarks/rule_grounding_cases.json`：小型人工断言集。
- 创建：`zhibing/knowledge/default_corpus/urban_encirclement_rules.md`：内置小型围剿/建筑接近测试语料。
- 修改：`zhibing/decision_layer/module_b_scene.py`：场景查询后注入 GraphRAG 知识。
- 修改：`zhibing/decision_layer/module_c_planner.py`：生成“移动到入口 + 态势评估 + 简化攻击意图”的多 step plan。
- 修改：`zhibing/decision_layer/module_e_param_gen.py`：对复杂任务只为当前可执行 BT 填参，未执行战术意图写入 metadata。
- 创建：`zhibing/visualization/schemas.py`：定义 `BattlefieldProjection`、单位、路线、目标、风险区、任务状态。
- 创建：`zhibing/visualization/projector.py`：把 IntentJSON、TaskPlanJSON、TaskSubmitRequest、TaskStatusResponse 映射为 2D 地图状态。
- 创建：`zhibing/visualization/map_assets.py`：记录从 `wargame` 复制的 Leaflet、GeoJSON、图标路径。
- 创建：`zhibing/web/...`：新增轻量 Django 可视化中间层。
- 创建：`zhibing/adapter/http_transport.py`：下层 HTTP transport。
- 创建：`zhibing/adapter/socket_transport.py`：下层 socket transport。
- 修改：`zhibing/config.py`：增加 transport、GraphRAG corpus、benchmark、visualization、LLM provider 配置。
- 修改：`zhibing/main.py`：暴露 intent、plan、projection、transport mode、HITL context。

---

### 任务 1：接口所有权与下层仿真接口文档

**文件：**
- 创建：`zhibing/interfaces/__init__.py`
- 创建：`zhibing/interfaces/interface_ownership.py`
- 创建：`zhibing/interfaces/simulation_contract.schema.json`
- 创建：`zhibing/docs/lower_simulation_interface.md`
- 修改：`zhibing/LOWER_LAYER_CONTRACT.md`
- 测试：`zhibing/tests/test_interface_ownership.py`

- [ ] **步骤 1：编写失败测试**

```python
import unittest

from zhibing.interfaces.interface_ownership import get_interface_matrix


class InterfaceOwnershipTests(unittest.TestCase):
    def test_shared_and_lower_interfaces_are_explicit(self):
        matrix = get_interface_matrix()
        self.assertEqual(matrix["StatusQueryRequest"]["owner"], "SHARED_PROTOCOL")
        self.assertEqual(matrix["TaskStatusResponse"]["owner"], "SHARED_PROTOCOL")
        self.assertEqual(matrix["submit_sqf_plan"]["owner"], "LOWER_SIM_REQUIRED")
        self.assertEqual(matrix["query_task"]["owner"], "LOWER_SIM_REQUIRED")

    def test_scene_tools_are_zhibing_facades_with_lower_dependencies(self):
        matrix = get_interface_matrix()
        scene = matrix["Scene Query Tools"]
        self.assertEqual(scene["owner"], "ZHIBING_OWNED")
        self.assertIn("get_actor_state", scene["zhibing_functions"])
        self.assertIn("GET /actors/{actor_id}/state", scene["lower_dependencies"])
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest zhibing.tests.test_interface_ownership -q`

预期：FAIL，报错 `No module named 'zhibing.interfaces'`。

- [ ] **步骤 3：实现接口所有权矩阵**

```python
# zhibing/interfaces/interface_ownership.py
from __future__ import annotations

from typing import Any


def get_interface_matrix() -> dict[str, dict[str, Any]]:
    return {
        "Scene Query Tools": {
            "owner": "ZHIBING_OWNED",
            "zhibing_functions": [
                "get_actor_state", "get_nearby_entities", "get_buildings",
                "get_building_entrances", "get_enemy_state", "get_weather",
                "route_plan", "estimate_move_time", "lookup_bt", "validate_bt_args",
                "query_obstacle", "get_passable_routes",
            ],
            "lower_dependencies": [
                "GET /actors/{actor_id}/state",
                "POST /entities/nearby",
                "POST /buildings/query",
                "GET /buildings/{building_id}/entrances",
                "POST /enemy/query",
                "GET /environment/weather",
                "POST /routes/plan",
                "GET /obstacles/{segment_id}",
            ],
        },
        "TaskSubmitRequest": {"owner": "SHARED_PROTOCOL"},
        "StatusQueryRequest": {"owner": "SHARED_PROTOCOL"},
        "TaskStatusResponse": {"owner": "SHARED_PROTOCOL"},
        "submit_sqf_plan": {"owner": "LOWER_SIM_REQUIRED"},
        "query_task": {"owner": "LOWER_SIM_REQUIRED"},
        "BattlefieldProjection": {"owner": "ZHIBING_OWNED"},
        "GraphRAG Knowledge Tools": {"owner": "ZHIBING_OWNED"},
        "VBS Runtime Emergency Handling": {"owner": "LOWER_SIM_REQUIRED"},
    }
```

- [ ] **步骤 4：创建下层接口 schema**

`zhibing/interfaces/simulation_contract.schema.json` 写入：

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "LowerSimulationContract",
  "definitions": {
    "SubmitSQFPlan": {
      "type": "object",
      "required": ["task_id", "request", "sqf_statements"],
      "properties": {
        "task_id": {"type": "string"},
        "request": {"type": "object"},
        "sqf_statements": {"type": "array", "items": {"type": "string"}}
      }
    },
    "SocketEnvelope": {
      "type": "object",
      "required": ["message_id", "message_type", "payload"],
      "properties": {
        "message_id": {"type": "string"},
        "message_type": {"enum": ["TASK_SUBMIT", "TASK_QUERY", "TASK_STATUS", "ACK", "ERROR"]},
        "payload": {"type": "object"}
      }
    }
  }
}
```

- [ ] **步骤 5：编写下层工程师文档**

`zhibing/docs/lower_simulation_interface.md` 必须包含：

```markdown
# 下层仿真系统接口说明

## 1. 下层必须提供什么
## 2. 默认 HTTP 接口
## 3. 可选 Socket 接口
## 4. Scene Query 依赖数据接口
## 5. 任务提交与状态查询
## 6. TaskStatusResponse 字段
## 7. active_node / node_path / return_code 规范
## 8. 突发遇敌与局部避障责任
## 9. 坐标协议
## 10. 最小联调案例
```

明确写入：`Scene Query Tools` 是智兵系统自己的工具门面；下层实现 actor、building、enemy、weather、route、obstacle、task runtime 数据接口；`StatusQueryRequest` 与 `TaskStatusResponse` 是共享协议；下层负责 VBS 运行、BT runtime、socket/HTTP return、突发遇敌本地处置。

- [ ] **步骤 6：运行测试验证通过**

运行：`python -m unittest zhibing.tests.test_interface_ownership -q`

预期：PASS。

- [ ] **步骤 7：Commit**

```bash
git add zhibing/interfaces zhibing/docs/lower_simulation_interface.md zhibing/LOWER_LAYER_CONTRACT.md zhibing/tests/test_interface_ownership.py
git commit -m "docs: define simulation interface ownership"
```

---

### 任务 2：配置化 HITL 节点体系

**文件：**
- 创建：`zhibing/hitl/node_catalog.py`
- 创建：`zhibing/hitl/hitl_policy.yaml`
- 修改：`zhibing/hitl/interrupt_handler.py`
- 测试：`zhibing/tests/test_hitl_policy.py`

- [ ] **步骤 1：编写失败测试**

```python
import unittest

from zhibing.hitl.node_catalog import NodeType
from zhibing.hitl.interrupt_handler import HITLDecisionContext, HITLPolicy


class HITLPolicyTests(unittest.TestCase):
    def test_policy_file_can_enable_encirclement_preparation(self):
        policy = HITLPolicy.from_dict({
            "nodes": {
                "ENCIRCLEMENT_PREP_CHECK": {
                    "hitl_allowed": True,
                    "require_hitl": True,
                    "allow_emergency_skip": False
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

    def test_emergency_contact_never_blocks_for_human_review_by_default(self):
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
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest zhibing.tests.test_hitl_policy -q`

预期：FAIL，报错 `cannot import name 'NodeType'`。

- [ ] **步骤 3：定义节点类型**

```python
# zhibing/hitl/node_catalog.py
from __future__ import annotations

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
```

- [ ] **步骤 4：实现策略类**

```python
# zhibing/hitl/interrupt_handler.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from zhibing.hitl.node_catalog import NodeType


@dataclass(frozen=True)
class HITLInterrupt:
    trigger: str
    actor: dict[str, str]
    proposed_action: dict[str, Any]
    risk_assessment: str
    decision_options: tuple[str, str, str] = ("approve", "modify", "abort")


@dataclass(frozen=True)
class HITLDecisionContext:
    node_type: NodeType
    urgency: str
    trigger: str
    actor: dict[str, str]
    proposed_action: dict[str, Any]
    risk_assessment: str


class HITLPolicy:
    def __init__(self, nodes: dict[str, dict[str, Any]]) -> None:
        self.nodes = nodes

    @classmethod
    def default(cls) -> "HITLPolicy":
        path = Path(__file__).with_name("hitl_policy.yaml")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
        return cls.from_dict(data or {})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HITLPolicy":
        return cls(nodes=dict(data.get("nodes") or {}))

    def evaluate(self, context: HITLDecisionContext) -> HITLInterrupt | None:
        cfg = self.nodes.get(context.node_type.value, {})
        if context.urgency == "immediate" and cfg.get("allow_emergency_skip", True):
            return None
        if not cfg.get("hitl_allowed", False):
            return None
        if not cfg.get("require_hitl", False):
            return None
        return HITLInterrupt(
            trigger=context.trigger,
            actor=context.actor,
            proposed_action=context.proposed_action,
            risk_assessment=context.risk_assessment,
        )
```

- [ ] **步骤 5：创建默认 HITL 配置**

```yaml
# zhibing/hitl/hitl_policy.yaml
nodes:
  RULE_CONFLICT_CHECK:
    hitl_allowed: true
    require_hitl: true
    allow_emergency_skip: false
  ENTER_DANGER_ZONE_CHECK:
    hitl_allowed: true
    require_hitl: false
    allow_emergency_skip: false
  BUILDING_ENTRY_PREP_CHECK:
    hitl_allowed: true
    require_hitl: false
    allow_emergency_skip: false
  ENCIRCLEMENT_PREP_CHECK:
    hitl_allowed: true
    require_hitl: false
    allow_emergency_skip: false
  FIRE_OR_ATTACK_AUTHORIZATION:
    hitl_allowed: true
    require_hitl: true
    allow_emergency_skip: false
  REPLAN_FAIL_GATE:
    hitl_allowed: true
    require_hitl: true
    allow_emergency_skip: false
  STATUS_POLL:
    hitl_allowed: false
    require_hitl: false
    allow_emergency_skip: true
  EMERGENCY_CONTACT:
    hitl_allowed: false
    require_hitl: false
    allow_emergency_skip: true
  LOCAL_AVOIDANCE:
    hitl_allowed: false
    require_hitl: false
    allow_emergency_skip: true
```

- [ ] **步骤 6：运行测试验证通过**

运行：`python -m unittest zhibing.tests.test_hitl_policy -q`

预期：PASS。

- [ ] **步骤 7：Commit**

```bash
git add zhibing/hitl zhibing/tests/test_hitl_policy.py
git commit -m "feat: add configurable hitl node policy"
```

---

### 任务 3：GraphRAG 文档加载、知识抽取与 Benchmark

**文件：**
- 创建：`zhibing/knowledge/__init__.py`
- 创建：`zhibing/knowledge/llm_router.py`
- 创建：`zhibing/knowledge/document_loader.py`
- 创建：`zhibing/knowledge/graphrag_store.py`
- 创建：`zhibing/knowledge/graphrag_builder.py`
- 创建：`zhibing/knowledge/graphrag_query.py`
- 创建：`zhibing/knowledge/benchmark.py`
- 创建：`zhibing/knowledge/default_corpus/urban_encirclement_rules.md`
- 创建：`zhibing/knowledge/benchmarks/rule_grounding_cases.json`
- 修改：`zhibing/config.py`
- 测试：`zhibing/tests/test_graphrag_ingestion.py`
- 测试：`zhibing/tests/test_graphrag_benchmark.py`

- [ ] **步骤 1：编写失败测试**

```python
import unittest

from zhibing.knowledge.document_loader import load_documents
from zhibing.knowledge.graphrag_builder import build_knowledge_graph
from zhibing.knowledge.graphrag_query import retrieve_knowledge_context


class GraphRAGIngestionTests(unittest.TestCase):
    def test_pdf_docx_and_default_corpus_are_loaded(self):
        docs = load_documents(["test_files", "zhibing/knowledge/default_corpus"])
        paths = {doc.source_path for doc in docs}
        self.assertTrue(any(path.endswith(".pdf") for path in paths))
        self.assertTrue(any(path.endswith(".docx") for path in paths))
        self.assertTrue(any("urban_encirclement_rules.md" in path for path in paths))

    def test_knowledge_context_injects_fire_zone_avoidance(self):
        docs = load_documents(["zhibing/knowledge/default_corpus"])
        graph = build_knowledge_graph(docs, use_llm=False)
        context = retrieve_knowledge_context(graph, {"intent": "group_move"})
        self.assertTrue(context["constraints"]["avoid_enemy_fire_zone"])
        self.assertIn("avoid_enemy_fire_zone", [r["rule_id"] for r in context["matched_rules"]])
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest zhibing.tests.test_graphrag_ingestion -q`

预期：FAIL，报错 `No module named 'zhibing.knowledge'`。

- [ ] **步骤 3：实现文档加载**

```python
# zhibing/knowledge/document_loader.py
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeDocument:
    source_path: str
    text: str


def load_documents(paths: list[str]) -> list[KnowledgeDocument]:
    docs: list[KnowledgeDocument] = []
    for raw in paths:
        path = Path(raw)
        files = list(path.rglob("*")) if path.is_dir() else [path]
        for file_path in files:
            if not file_path.is_file():
                continue
            suffix = file_path.suffix.lower()
            if suffix in {".txt", ".md", ".json", ".csv"}:
                docs.append(KnowledgeDocument(str(file_path), file_path.read_text(encoding="utf-8", errors="ignore")))
            elif suffix == ".docx":
                with zipfile.ZipFile(file_path) as archive:
                    xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
                text = re.sub(r"<[^>]+>", " ", xml)
                docs.append(KnowledgeDocument(str(file_path), text))
            elif suffix == ".pdf":
                raw_text = file_path.read_bytes().decode("latin-1", errors="ignore")
                docs.append(KnowledgeDocument(str(file_path), raw_text))
    return docs
```

- [ ] **步骤 4：实现 LLM Router**

```python
# zhibing/knowledge/llm_router.py
from __future__ import annotations

import json
from typing import Any


class KnowledgeLLMRouter:
    def __init__(self, task: str = "reply_generation") -> None:
        self.task = task

    def invoke_json(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        from llm_call_extract.llm_client import ModelRouter
        response = ModelRouter().get_chat_model(self.task).invoke(messages)
        return json.loads(response.content)

    @staticmethod
    def deployment_modes() -> dict[str, str]:
        return {
            "vendor_test": "llm_call_extract + volcengine Ark model ep-20260615114505-247zc",
            "server_local": "OpenWebUI or vLLM OpenAI-compatible endpoint configured by environment",
        }
```

- [ ] **步骤 5：实现 GraphRAG store、builder、query**

```python
# zhibing/knowledge/graphrag_store.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class KnowledgeGraph:
    entities: list[dict[str, Any]] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)
    rules: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
```

```python
# zhibing/knowledge/graphrag_builder.py
from __future__ import annotations

from zhibing.knowledge.document_loader import KnowledgeDocument
from zhibing.knowledge.graphrag_store import KnowledgeGraph


def build_knowledge_graph(docs: list[KnowledgeDocument], *, use_llm: bool = True) -> KnowledgeGraph:
    graph = KnowledgeGraph()
    for doc in docs:
        text = doc.text
        graph.sources.append({"path": doc.source_path, "chars": len(text)})
        lower = text.lower()
        if "火力区" in text or "fire zone" in lower:
            graph.entities.append({"id": "enemy_fire_zone", "type": "risk_zone", "name": "enemy fire zone"})
            graph.rules.append({
                "rule_id": "avoid_enemy_fire_zone",
                "condition": "route or destination intersects enemy fire zone",
                "action": "set avoid_enemy=true and route_plan avoid_enemy=true",
                "hitl_node": "ENTER_DANGER_ZONE_CHECK",
                "source": doc.source_path,
                "evidence": text[:500],
            })
        if "地下" in text or "subterranean" in lower:
            graph.entities.append({"id": "underground_operation", "type": "environment", "name": "underground operation"})
            graph.rules.append({
                "rule_id": "building_entry_requires_situation_assessment",
                "condition": "building or underground entry before encirclement",
                "action": "insert situation assessment step before attack intent",
                "hitl_node": "BUILDING_ENTRY_PREP_CHECK",
                "source": doc.source_path,
                "evidence": text[:500],
            })
        if "突然遇敌" in text or "sudden contact" in lower:
            graph.rules.append({
                "rule_id": "sudden_contact_local_emergency",
                "condition": "runtime sudden enemy contact",
                "action": "lower simulation handles immediate avoidance without HITL blocking",
                "hitl_node": "EMERGENCY_CONTACT",
                "source": doc.source_path,
                "evidence": text[:500],
            })
    return graph
```

```python
# zhibing/knowledge/graphrag_query.py
from __future__ import annotations

from typing import Any

from zhibing.knowledge.graphrag_store import KnowledgeGraph


def retrieve_knowledge_context(graph: KnowledgeGraph, intent_json: dict[str, Any]) -> dict[str, Any]:
    matched = []
    constraints = {"avoid_enemy_fire_zone": False, "requires_situation_assessment": False, "requires_hitl_nodes": []}
    intent = str(intent_json.get("intent", ""))
    for rule in graph.rules:
        if rule["rule_id"] == "avoid_enemy_fire_zone" and "move" in intent:
            matched.append(rule)
            constraints["avoid_enemy_fire_zone"] = True
            constraints["requires_hitl_nodes"].append(rule["hitl_node"])
        if rule["rule_id"] == "building_entry_requires_situation_assessment" and any(token in intent for token in ["encircle", "围剿", "attack"]):
            matched.append(rule)
            constraints["requires_situation_assessment"] = True
            constraints["requires_hitl_nodes"].append(rule["hitl_node"])
    return {"matched_rules": matched, "constraints": constraints}
```

- [ ] **步骤 6：创建默认语料和 benchmark cases**

`urban_encirclement_rules.md`：

```markdown
# Urban Encirclement Rules

执行建筑围剿、接近目标建筑入口或移动穿越暴露区域时，系统必须自动避开已知敌方火力区。用户不需要显式写出“避开敌方火力区”。

进入建筑或地下空间前，应插入态势评估步骤，确认入口、敌情、障碍和撤离路径。

如果 VBS 运行时突然遇敌，该事件属于 sudden contact。下层仿真系统应立即执行本地规避、隐蔽或短暂停止，不得阻塞等待 Human-in-the-loop。
```

`rule_grounding_cases.json`：

```json
[
  {"case_id": "avoid_fire_zone", "query_intent": {"intent": "group_move"}, "expected_rule_ids": ["avoid_enemy_fire_zone"]},
  {"case_id": "encirclement_assessment", "query_intent": {"intent": "encircle_building"}, "expected_rule_ids": ["building_entry_requires_situation_assessment"]}
]
```

- [ ] **步骤 7：实现 benchmark runner**

```python
# zhibing/knowledge/benchmark.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from zhibing.knowledge.document_loader import load_documents
from zhibing.knowledge.graphrag_builder import build_knowledge_graph
from zhibing.knowledge.graphrag_query import retrieve_knowledge_context


def run_rule_grounding_benchmark(cases_path: str = "zhibing/knowledge/benchmarks/rule_grounding_cases.json") -> dict[str, Any]:
    docs = load_documents(["test_files", "zhibing/knowledge/default_corpus"])
    graph = build_knowledge_graph(docs, use_llm=False)
    cases = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    passed = 0
    results = []
    for case in cases:
        context = retrieve_knowledge_context(graph, case["query_intent"])
        got = {rule["rule_id"] for rule in context["matched_rules"]}
        expected = set(case["expected_rule_ids"])
        ok = expected.issubset(got)
        passed += 1 if ok else 0
        results.append({"case_id": case["case_id"], "ok": ok, "expected": sorted(expected), "got": sorted(got)})
    return {"total": len(cases), "passed": passed, "results": results}
```

- [ ] **步骤 8：编写 benchmark 测试**

```python
import unittest

from zhibing.knowledge.benchmark import run_rule_grounding_benchmark


class GraphRAGBenchmarkTests(unittest.TestCase):
    def test_rule_grounding_benchmark_passes(self):
        report = run_rule_grounding_benchmark()
        self.assertEqual(report["passed"], report["total"])
```

- [ ] **步骤 9：运行测试验证通过**

运行：

```powershell
python -m unittest zhibing.tests.test_graphrag_ingestion -q
python -m unittest zhibing.tests.test_graphrag_benchmark -q
```

预期：全部 PASS。

- [ ] **步骤 10：火山 Ark LLM 健康检查**

运行：

```powershell
$env:ARK_API_KEY=$env:ARK_API_KEY
python -c "from llm_call_extract.llm_client import ModelRouter; r=ModelRouter().get_chat_model('reply_generation').invoke([{'role':'user','content':'Return JSON {\"status\":\"ok\"}'}]); print(r.content)"
```

预期：返回 JSON。该步骤验证测试期 vendor LLM 可用；服务器部署时改用本地 OpenWebUI/vLLM 配置。

- [ ] **步骤 11：Commit**

```bash
git add zhibing/knowledge zhibing/config.py zhibing/tests/test_graphrag_ingestion.py zhibing/tests/test_graphrag_benchmark.py
git commit -m "feat: add graphrag knowledge ingestion and benchmark"
```

---

### 任务 4：复杂任务拆解为简单 BT 可执行步骤

**文件：**
- 修改：`zhibing/decision_layer/module_a_intent.py`
- 修改：`zhibing/decision_layer/module_b_scene.py`
- 修改：`zhibing/decision_layer/module_c_planner.py`
- 修改：`zhibing/decision_layer/module_e_param_gen.py`
- 测试：`zhibing/tests/test_encirclement_decomposition.py`

- [ ] **步骤 1：编写失败测试**

```python
import unittest

from zhibing.decision_layer.module_a_intent import recognize_intent
from zhibing.decision_layer.module_b_scene import gather_scene
from zhibing.decision_layer.module_c_planner import create_task_plan


class EncirclementDecompositionTests(unittest.TestCase):
    def test_encirclement_decomposes_to_move_assess_and_attack_intent(self):
        intent = recognize_intent("命令p_4小组前往目标建筑入口开展围剿任务 VBS_LOCAL_XYZ {x:1000, y:500, z:0}", prefer_llm=False)
        scene = gather_scene(intent)
        plan = create_task_plan(intent, scene)
        task_types = [step["task_type"] for step in plan["plan"]]
        self.assertEqual(task_types[0], "group_move")
        self.assertIn("situation_assessment", task_types)
        self.assertIn("attack_intent_pending_lower_bt", task_types)
        self.assertEqual(plan["plan"][0]["bt"]["bt_name"], "GrpMove")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest zhibing.tests.test_encirclement_decomposition -q`

预期：FAIL，因为当前没有 `create_task_plan()` 多步规划函数。

- [ ] **步骤 3：扩展 intent fallback**

`module_a_intent.py` 中增加：

```python
if "围剿" in user_text or "encircle" in user_text.lower():
    intent["intent"] = "encircle_building"
    intent["post_action"] = "attack_intent"
```

- [ ] **步骤 4：实现 create_task_plan**

```python
# zhibing/decision_layer/module_c_planner.py
from __future__ import annotations

import uuid
from typing import Any


def create_task_plan(intent_json: dict[str, Any], scene_context: dict[str, Any]) -> dict[str, Any]:
    mission_id = str(uuid.uuid4())
    actor = intent_json["actors"][0]
    destination = intent_json["destination"]["coord"]
    if intent_json["intent"] == "encircle_building":
        return {
            "mission_id": mission_id,
            "plan": [
                {
                    "step_id": "step_1_move_to_entry",
                    "task_type": "group_move",
                    "actor": actor,
                    "depends_on": [],
                    "bt": {"btset_path": "CgfControl.btset", "bt_name": "GrpMove"},
                    "args": {"movePos": destination, "speed": float(intent_json.get("speed_mps", 5.0)), "fmInfoTable": []},
                    "timeout_policy": {},
                    "knowledge_constraints": scene_context.get("knowledge_context", {}).get("constraints", {}),
                },
                {
                    "step_id": "step_2_situation_assessment",
                    "task_type": "situation_assessment",
                    "actor": actor,
                    "depends_on": ["step_1_move_to_entry"],
                    "bt": {"btset_path": "", "bt_name": "NO_BT_UPPER_LAYER_ASSESSMENT"},
                    "args": {"query": ["enemy_state", "building_entrances", "obstacles"]},
                    "timeout_policy": {},
                },
                {
                    "step_id": "step_3_attack_intent_pending_lower_bt",
                    "task_type": "attack_intent_pending_lower_bt",
                    "actor": actor,
                    "depends_on": ["step_2_situation_assessment"],
                    "bt": {"btset_path": "", "bt_name": "PENDING_LOWER_TACTICAL_BT"},
                    "args": {"intent": "move_and_attack", "note": "current registry only executes movement BT"},
                    "timeout_policy": {},
                },
            ],
        }
    return create_single_step_plan(intent_json, scene_context["bt_candidates"][0], {}, {})
```

- [ ] **步骤 5：运行测试验证通过**

运行：`python -m unittest zhibing.tests.test_encirclement_decomposition -q`

预期：PASS。

- [ ] **步骤 6：Commit**

```bash
git add zhibing/decision_layer zhibing/tests/test_encirclement_decomposition.py
git commit -m "feat: decompose encirclement into executable simple steps"
```

---

### 任务 5：可视化投影模型

**文件：**
- 创建：`zhibing/visualization/__init__.py`
- 创建：`zhibing/visualization/schemas.py`
- 创建：`zhibing/visualization/projector.py`
- 测试：`zhibing/tests/test_visualization_projection.py`

- [ ] **步骤 1：编写失败测试**

```python
import unittest

from zhibing.visualization.projector import build_projection


class VisualizationProjectionTests(unittest.TestCase):
    def test_projection_contains_unit_route_target_and_pending_attack_intent(self):
        plan = {
            "mission_id": "mission",
            "plan": [
                {
                    "step_id": "step_1_move_to_entry",
                    "task_type": "group_move",
                    "actor": {"type": "group", "id": "p_4"},
                    "bt": {"btset_path": "CgfControl.btset", "bt_name": "GrpMove"},
                    "args": {"movePos": {"frame": "VBS_LOCAL_XYZ", "x": 1000, "y": 500, "z": 0}, "speed": 10},
                    "timeout_policy": {},
                },
                {
                    "step_id": "step_3_attack_intent_pending_lower_bt",
                    "task_type": "attack_intent_pending_lower_bt",
                    "actor": {"type": "group", "id": "p_4"},
                    "bt": {"btset_path": "", "bt_name": "PENDING_LOWER_TACTICAL_BT"},
                    "args": {"intent": "move_and_attack"},
                    "timeout_policy": {},
                },
            ],
        }
        projection = build_projection(intent_json={"intent": "encircle_building"}, task_plan_json=plan, status_response=None)
        self.assertEqual(projection["units"][0]["id"], "p_4")
        self.assertEqual(projection["routes"][0]["bt_name"], "GrpMove")
        self.assertEqual(projection["targets"][0]["coord"]["frame"], "VBS_LOCAL_XYZ")
        self.assertEqual(projection["pending_intents"][0]["task_type"], "attack_intent_pending_lower_bt")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest zhibing.tests.test_visualization_projection -q`

预期：FAIL，报错 `No module named 'zhibing.visualization'`。

- [ ] **步骤 3：实现 projector**

```python
# zhibing/visualization/projector.py
from __future__ import annotations

from typing import Any

from zhibing.core.coord_service import default_coord_service


def build_projection(*, intent_json: dict[str, Any], task_plan_json: dict[str, Any], status_response: dict[str, Any] | None) -> dict[str, Any]:
    units = []
    routes = []
    targets = []
    pending_intents = []
    for step in task_plan_json["plan"]:
        actor = step["actor"]
        if not any(unit["id"] == actor["id"] for unit in units):
            units.append({"id": actor["id"], "type": actor["type"], "status": status_response["status"] if status_response else "PLANNED"})
        dest = step["args"].get("movePos") or step["args"].get("moveDest")
        if dest:
            default_coord_service.validate(dest)
            routes.append({"id": step["step_id"], "task_type": step["task_type"], "bt_name": step["bt"]["bt_name"], "waypoints": [dest]})
            targets.append({"id": f"{step['step_id']}_target", "kind": "building_entry_or_point", "coord": dest})
        if step["bt"]["bt_name"].startswith("PENDING_"):
            pending_intents.append({"step_id": step["step_id"], "task_type": step["task_type"], "args": step["args"]})
    return {
        "mission_id": task_plan_json["mission_id"],
        "intent": intent_json.get("intent"),
        "units": units,
        "routes": routes,
        "targets": targets,
        "zones": [],
        "pending_intents": pending_intents,
        "task_state": {"state": status_response["status"] if status_response else "PLANNED", "return_code": status_response.get("return_code") if status_response else None},
    }
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m unittest zhibing.tests.test_visualization_projection -q`

预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add zhibing/visualization zhibing/tests/test_visualization_projection.py
git commit -m "feat: add battlefield projection model"
```

---

### 任务 6：复制 wargame 资产并搭建 2D 可视化中间层

**文件：**
- 创建：`zhibing/web/manage.py`
- 创建：`zhibing/web/zhibing_web/settings.py`
- 创建：`zhibing/web/zhibing_web/urls.py`
- 创建：`zhibing/web/command_ui/views.py`
- 创建：`zhibing/web/command_ui/urls.py`
- 创建：`zhibing/web/command_ui/templates/command_ui/index.html`
- 创建：`zhibing/web/command_ui/static/command_ui/app.js`
- 创建：`zhibing/web/command_ui/static/command_ui/styles.css`
- 复制：`zhibing/web/command_ui/static/command_ui/vendor/leaflet.js`
- 复制：`zhibing/web/command_ui/static/command_ui/vendor/leaflet.css`
- 复制：`zhibing/web/command_ui/static/command_ui/map/roads.geojson`
- 复制：`zhibing/web/command_ui/static/command_ui/map/buildings.geojson`
- 复制：`zhibing/web/command_ui/static/command_ui/icons/攻势小队.png`
- 复制：`zhibing/web/command_ui/static/command_ui/icons/侦察小队.png`
- 复制：`zhibing/web/command_ui/static/command_ui/icons/保障小队.png`

- [ ] **步骤 1：复制资产**

运行：

```powershell
New-Item -ItemType Directory -Force -Path zhibing\web\command_ui\static\command_ui\vendor,zhibing\web\command_ui\static\command_ui\map,zhibing\web\command_ui\static\command_ui\icons
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\lib\leaflet.js" "zhibing\web\command_ui\static\command_ui\vendor\leaflet.js"
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\lib\leaflet.css" "zhibing\web\command_ui\static\command_ui\vendor\leaflet.css"
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\roads.geojson" "zhibing\web\command_ui\static\command_ui\map\roads.geojson"
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\buildings.geojson" "zhibing\web\command_ui\static\command_ui\map\buildings.geojson"
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\攻势小队.png" "zhibing\web\command_ui\static\command_ui\icons\攻势小队.png"
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\侦察小队.png" "zhibing\web\command_ui\static\command_ui\icons\侦察小队.png"
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\保障小队.png" "zhibing\web\command_ui\static\command_ui\icons\保障小队.png"
```

- [ ] **步骤 2：实现 Django 最小服务**

`settings.py`：

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SECRET_KEY = "zhibing-dev-only"
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
ROOT_URLCONF = "zhibing_web.urls"
INSTALLED_APPS = ["django.contrib.staticfiles", "command_ui"]
MIDDLEWARE = []
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "command_ui" / "static"]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "command_ui" / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": []},
}]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

- [ ] **步骤 3：实现命令 API**

`views.py`：

```python
from __future__ import annotations

import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from zhibing.main import ZhibingDecisionSystem
from zhibing.visualization.projector import build_projection

SYSTEM = ZhibingDecisionSystem()


def index(request):
    return render(request, "command_ui/index.html")


@csrf_exempt
@require_http_methods(["POST"])
def command(request):
    data = json.loads(request.body.decode("utf-8"))
    result = SYSTEM.run_user_command(data["message"])
    projection = build_projection(intent_json=result.intent_json, task_plan_json=result.task_plan_json, status_response=result.task_status_response)
    return JsonResponse({
        "state": result.state,
        "task_id": result.task_id,
        "explanation": result.explanation,
        "task_submit_request": result.task_submit_request,
        "task_status_response": result.task_status_response,
        "projection": projection,
    })
```

- [ ] **步骤 4：实现页面和前端渲染**

`index.html` 必须包含地图、左侧图层、右侧文本输入输出。`app.js` 必须实现 `submitCommand()`、`renderProjection()`、`clearMissionLayers()`、`vbsToLatLng()`，并渲染单位、路线、目标和 pending intent。

- [ ] **步骤 5：运行开发服务器**

运行：`python zhibing\web\manage.py runserver 127.0.0.1:8090`

预期：`http://127.0.0.1:8090/` 显示地图、文本输入、输出解释和 JSON。

- [ ] **步骤 6：Commit**

```bash
git add zhibing/web
git commit -m "feat: add wargame-based 2d visualization ui"
```

---

### 任务 7：HTTP/socket 双 Transport

**文件：**
- 创建：`zhibing/adapter/http_transport.py`
- 创建：`zhibing/adapter/socket_transport.py`
- 修改：`zhibing/adapter/vbs_adapter.py`
- 修改：`zhibing/config.py`
- 测试：`zhibing/tests/test_lower_transports.py`

- [ ] **步骤 1：编写失败测试**

```python
import unittest

from zhibing.adapter.http_transport import LowerSimHTTPTransport
from zhibing.adapter.socket_transport import LowerSimSocketTransport


class LowerTransportTests(unittest.TestCase):
    def test_http_submit_payload_shape(self):
        transport = LowerSimHTTPTransport(base_url="http://lower-sim.test")
        payload = transport.build_submit_payload(task_id="task", request={"request_id": "req"}, sqf_statements=("line;",))
        self.assertEqual(payload["task_id"], "task")
        self.assertEqual(payload["sqf_statements"], ["line;"])

    def test_socket_envelope_shape(self):
        transport = LowerSimSocketTransport(host="127.0.0.1", port=9001)
        envelope = transport.build_envelope("TASK_QUERY", {"task_id": "task"})
        self.assertEqual(envelope["message_type"], "TASK_QUERY")
        self.assertEqual(envelope["payload"]["task_id"], "task")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest zhibing.tests.test_lower_transports -q`

预期：FAIL，报错缺少 transport 模块。

- [ ] **步骤 3：实现 HTTP transport**

```python
# zhibing/adapter/http_transport.py
from __future__ import annotations

import json
import urllib.request
from typing import Any

from zhibing.adapter.sqf_compiler import SQFCallPlan


class LowerSimHTTPTransport:
    def __init__(self, base_url: str, timeout_seconds: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def build_submit_payload(self, *, task_id: str, request: dict[str, Any], sqf_statements: tuple[str, ...]) -> dict[str, Any]:
        return {"task_id": task_id, "request": request, "sqf_statements": list(sqf_statements)}

    def submit_sqf_plan(self, plan: SQFCallPlan, request: dict[str, Any]) -> dict[str, Any]:
        return self._post_json("/tasks/submit", self.build_submit_payload(task_id=plan.task_id, request=request, sqf_statements=plan.statements))

    def query_task(self, task_id: str, query_fields: list[str] | None = None) -> dict[str, Any]:
        return self._post_json("/tasks/query", {"task_id": task_id, "query_fields": query_fields or []})

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(self.base_url + path, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
```

- [ ] **步骤 4：实现 socket transport**

```python
# zhibing/adapter/socket_transport.py
from __future__ import annotations

import json
import socket
import uuid
from typing import Any

from zhibing.adapter.sqf_compiler import SQFCallPlan


class LowerSimSocketTransport:
    def __init__(self, host: str, port: int, timeout_seconds: float = 20.0) -> None:
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds

    def build_envelope(self, message_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"message_id": str(uuid.uuid4()), "message_type": message_type, "payload": payload}

    def submit_sqf_plan(self, plan: SQFCallPlan, request: dict[str, Any]) -> dict[str, Any]:
        payload = {"task_id": plan.task_id, "request": request, "sqf_statements": list(plan.statements)}
        return self._send(self.build_envelope("TASK_SUBMIT", payload))

    def query_task(self, task_id: str, query_fields: list[str] | None = None) -> dict[str, Any]:
        return self._send(self.build_envelope("TASK_QUERY", {"task_id": task_id, "query_fields": query_fields or []}))

    def _send(self, envelope: dict[str, Any]) -> dict[str, Any]:
        data = (json.dumps(envelope) + "\n").encode("utf-8")
        with socket.create_connection((self.host, self.port), timeout=self.timeout_seconds) as conn:
            conn.sendall(data)
            response = conn.recv(1024 * 1024)
        return json.loads(response.decode("utf-8"))
```

- [ ] **步骤 5：配置 transport 选择**

`config.py` 增加：

```python
LOWER_SIM_TRANSPORT = os.getenv("ZHIBING_LOWER_SIM_TRANSPORT", "http")
LOWER_SIM_HTTP_BASE_URL = os.getenv("ZHIBING_LOWER_SIM_HTTP_BASE_URL", "http://127.0.0.1:9000")
LOWER_SIM_SOCKET_HOST = os.getenv("ZHIBING_LOWER_SIM_SOCKET_HOST", "127.0.0.1")
LOWER_SIM_SOCKET_PORT = int(os.getenv("ZHIBING_LOWER_SIM_SOCKET_PORT", "9001"))
```

- [ ] **步骤 6：运行测试验证通过**

运行：`python -m unittest zhibing.tests.test_lower_transports -q`

预期：PASS。

- [ ] **步骤 7：Commit**

```bash
git add zhibing/adapter zhibing/config.py zhibing/tests/test_lower_transports.py
git commit -m "feat: add configurable lower simulation transports"
```

---

### 任务 8：三层一致性测试

**文件：**
- 修改：`zhibing/main.py`
- 创建：`zhibing/tests/test_three_layer_alignment.py`

- [ ] **步骤 1：编写失败测试**

```python
import unittest

from zhibing.main import ZhibingDecisionSystem
from zhibing.visualization.projector import build_projection


class ThreeLayerAlignmentTests(unittest.TestCase):
    def test_move_command_aligns_intent_visual_and_adapter(self):
        system = ZhibingDecisionSystem()
        result = system.run_user_command("让p_4群组以速度10移动到指定坐标 VBS_LOCAL_XYZ {x:1000, y:500, z:0}")
        projection = build_projection(intent_json=result.intent_json, task_plan_json=result.task_plan_json, status_response=result.task_status_response)
        self.assertEqual(result.task_submit_request["actor"]["id"], projection["units"][0]["id"])
        self.assertEqual(result.task_submit_request["task"]["bt_args"]["movePos"], projection["targets"][0]["coord"])
        self.assertIn("setBT", "\n".join(result.compiled_sqf))
        self.assertIn("setBBVariable", "\n".join(result.compiled_sqf))

    def test_encirclement_projection_marks_pending_attack_intent(self):
        system = ZhibingDecisionSystem()
        result = system.run_user_command("命令p_4小组前往目标建筑入口开展围剿任务 VBS_LOCAL_XYZ {x:1000, y:500, z:0}")
        projection = build_projection(intent_json=result.intent_json, task_plan_json=result.task_plan_json, status_response=result.task_status_response)
        self.assertTrue(any(item["task_type"] == "attack_intent_pending_lower_bt" for item in projection["pending_intents"]))
```

- [ ] **步骤 2：扩展 `MissionRunResult`**

`zhibing/main.py` 的 dataclass 增加：

```python
intent_json: dict[str, Any]
task_plan_json: dict[str, Any]
projection: dict[str, Any] | None = None
```

确保 `_result()` 返回这些字段。

- [ ] **步骤 3：运行测试验证通过**

运行：`python -m unittest zhibing.tests.test_three_layer_alignment -q`

预期：PASS。

- [ ] **步骤 4：运行全量测试**

运行：`python -m unittest discover -s zhibing\tests -q`

预期：全部 PASS。

- [ ] **步骤 5：Commit**

```bash
git add zhibing/main.py zhibing/tests/test_three_layer_alignment.py
git commit -m "test: verify intent visualization adapter alignment"
```

---

### 任务 9：运行逻辑文档与计划同步

**文件：**
- 创建：`zhibing/docs/system_runtime_flow.md`
- 修改：`ZHIBING_SYSTEM_PLAN.md`

- [ ] **步骤 1：创建完整运行逻辑文档**

`zhibing/docs/system_runtime_flow.md` 必须包含：

```markdown
# 智兵决策系统运行逻辑

## 1. 用户进入前
### 1.1 条例、PDF、DOCX、测试语料导入
### 1.2 GraphRAG 构建与 Benchmark
### 1.3 BT Registry 加载
### 1.4 下层仿真场景同步
### 1.5 wargame 地图资产加载

## 2. 用户进入后
### 2.1 文本命令输入
### 2.2 IntentJSON
### 2.3 KnowledgeContext
### 2.4 SceneContext
### 2.5 TaskPlanJSON
### 2.6 BattlefieldProjection
### 2.7 TaskSubmitRequest
### 2.8 HTTP/socket Adapter
### 2.9 StatusQueryRequest / TaskStatusResponse
### 2.10 ExplainabilityLogger

## 3. 围剿任务如何由简单 BT 实现
## 4. HITL 节点策略如何配置
## 5. 下层仿真系统责任边界
```

- [ ] **步骤 2：更新总计划索引**

在 `ZHIBING_SYSTEM_PLAN.md` 末尾增加：

```markdown
## UPDATE DOCUMENTS

- `zhibing/docs/lower_simulation_interface.md`
- `zhibing/docs/system_runtime_flow.md`
- `zhibing/hitl/hitl_policy.yaml`
- `docs/superpowers/plans/2026-06-20-zhibing-system-update-v2.md`
```

- [ ] **步骤 3：Commit**

```bash
git add zhibing/docs/system_runtime_flow.md ZHIBING_SYSTEM_PLAN.md
git commit -m "docs: describe updated zhibing runtime flow"
```

---

## 验收标准

- [ ] `zhibing/docs/lower_simulation_interface.md` 可以直接交给下层仿真工程师。
- [ ] `Scene Query Tools`、`StatusQueryRequest`、`TaskStatusResponse` 的所有权清晰。
- [ ] HITL 触发完全由 `zhibing/hitl/hitl_policy.yaml` 配置控制。
- [ ] `EMERGENCY_CONTACT`、`LOCAL_AVOIDANCE` 默认不阻塞等待人工确认。
- [ ] GraphRAG 能读取 `test_files` 的 PDF 和 DOCX。
- [ ] GraphRAG benchmark 至少包含 FormatBench、RuleGroundingBench、NoiseTripletBench、LocalModelBench 的实现入口。
- [ ] 火山 Ark 测试链路可用，同时本地 OpenWebUI/vLLM 配置不需要改代码。
- [ ] 可视化中间层不依赖外部 `wargame` 服务运行，资产已复制到本仓库。
- [ ] 围剿任务能拆成“移动到入口 + 态势评估 + pending attack intent”。
- [ ] HTTP 和 socket transport 都有配置和测试；默认 HTTP。
- [ ] 三层一致性测试验证：命令目标、TaskSubmitRequest、地图投影目标一致。

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-06-20-zhibing-system-update-v2.md`。两种执行方式：

**1. 子代理驱动（推荐）** - 每个任务调度一个新子代理，任务间进行审查，快速迭代。

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设检查点。

推荐按任务 1 到任务 9 顺序执行。任务 1、2、3、7 是系统边界和平台基础；任务 4、5、6、8 是用户可见能力；任务 9 是交付文档闭环。
