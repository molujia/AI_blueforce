# 智兵决策系统更新完善实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 补全智兵决策系统的前置知识注入、下层仿真接口边界、可配置 HITL 节点策略、2D 可视化中间层，以及“意图识别-可视化中间层-仿真底层”一致性测试。

**架构：** 保持现有四层边界：用户界面、LLM 决策层、VBS Adapter、VBS Engine。新增三个横向能力：GraphRAG 知识层在用户进入前构建并在运行时注入；可视化中间层接收上层任务投影和下层状态回传，使用 wargame 风格的 Leaflet 地图并与文本输出并列展示；接口所有权文档把智兵系统自实现工具、智兵到下层的请求、下层必须提供的 HTTP/socket 能力分开。

**技术栈：** Python 3.9+、标准库 unittest、OpenAI-compatible LLM、`llm_call_extract` 火山 Ark 测试模型 `ep-20260615114505-247zc`、本地 OpenWebUI/vLLM 迁移配置、Django + Leaflet 可视化参考、JSON Schema Draft 7、SQLite/PostgreSQL 可替换存储、GraphRAG 知识图谱抽取与检索服务。

---

## 需要用户确认的问题

1. **可视化中间层部署形态：** 默认计划是在本仓库新增一个轻量 Django app，并从 `C:\Users\22646\Desktop\wargame` 复制必要静态地图资产到本仓库；是否接受复制资产，而不是运行外部 `wargame` 项目作为依赖服务？
2. **GraphRAG 首批文档来源：** 默认计划支持用户上传目录或配置目录 `knowledge_corpus/`，并内置一个小型测试条例文件；真实条例文件是否已有固定路径？
3. **HITL 默认策略：** 默认计划允许 `RISK_POLICY_CHECK`、`BT_SELECTION_UNKNOWN`、`ENTER_DANGER_ZONE_CHECK`、`RULE_CONFLICT_CHECK`、`REPLAN_FAIL_GATE` 触发 HITL；禁止 `STATUS_POLL`、`EMERGENCY_CONTACT`、`LOCAL_AVOIDANCE` 触发 HITL。是否需要把“进入建筑/围剿准备”也默认设为必须人工确认？
4. **围剿任务范围：** 当前现有 BT registry 主要支持移动和编队。默认计划把“围剿”拆成：移动到建筑入口、等待/请求人工确认、进入前态势评估、向下层提交后续待实现 tactical task。下层真实攻击/搜索行为树未提供前，不模拟开火执行。是否符合你的安全边界？
5. **下层接口协议：** 默认计划同时文档化 HTTP 和 socket，但先实现 HTTP client + Mock transport。下层工程师是否偏向固定 HTTP REST，还是必须 socket 长连接？

## 文件结构与职责

- 创建：`zhibing/docs/lower_simulation_interface.md`
  - 给下层仿真工程师的单独交付文档，列出下层必须提供的接口、数据结构、返回码、状态回传频率和坐标规范。
- 创建：`zhibing/interfaces/interface_ownership.py`
  - 机器可读的接口所有权登记表，区分 `ZHIBING_OWNED`、`LOWER_SIM_REQUIRED`、`SHARED_PROTOCOL`。
- 创建：`zhibing/interfaces/simulation_contract.schema.json`
  - 下层接口返回数据的 JSON Schema 集合入口。
- 修改：`zhibing/LOWER_LAYER_CONTRACT.md`
  - 保留现有说明，但改为摘要并指向新的下层工程师文档。
- 创建：`zhibing/hitl/node_catalog.py`
  - 定义工作流节点类型、节点类别、是否默认允许 HITL、是否允许紧急跳过。
- 创建：`zhibing/hitl/hitl_policy.yaml`
  - 可配置 HITL 策略，运营人员可改哪些节点触发人工确认。
- 修改：`zhibing/hitl/interrupt_handler.py`
  - 从策略文件读取节点触发规则，不再用主观字符串判断。
- 创建：`zhibing/knowledge/llm_router.py`
  - 统一封装 `llm_call_extract` 和本地 OpenWebUI/vLLM 调用，测试用火山 Ark，部署可切本地 LLM。
- 创建：`zhibing/knowledge/document_loader.py`
  - 读取 `.txt`、`.md`、`.json`、`.csv`、`.docx`、`.pdf` 文档文本。
- 创建：`zhibing/knowledge/graphrag_store.py`
  - 存储实体、关系、规则、来源片段和检索索引。
- 创建：`zhibing/knowledge/graphrag_builder.py`
  - 用 LLM 抽取条例中的实体、约束、触发条件、禁止动作和风险区规则。
- 创建：`zhibing/knowledge/graphrag_query.py`
  - 运行时根据 IntentJSON、场景和目标位置检索相关规则，并返回结构化 `KnowledgeContext`。
- 创建：`zhibing/knowledge/default_corpus/urban_encirclement_rules.md`
  - 小型测试知识库，覆盖避开敌方火力区、进入危险区需确认、突然遇敌由下层紧急处置等规则。
- 修改：`zhibing/decision_layer/module_b_scene.py`
  - 在场景查询后调用 GraphRAG，向规划器注入规则与风险约束。
- 修改：`zhibing/decision_layer/module_c_planner.py`
  - 把知识约束写入 TaskPlanJSON 的 step metadata，不让用户每次手写“避开火力区”。
- 创建：`zhibing/visualization/schemas.py`
  - 定义 `BattlefieldProjection`、`VisualUnit`、`VisualRoute`、`VisualZone`、`VisualTaskState`。
- 创建：`zhibing/visualization/projector.py`
  - 把 IntentJSON、TaskPlanJSON、TaskSubmitRequest、TaskStatusResponse 映射为 2D 可视化状态。
- 创建：`zhibing/visualization/map_assets.py`
  - 管理从 `wargame` 参考项目复制来的瓦片、GeoJSON、图标路径和地图中心点。
- 创建：`zhibing/web/manage.py`
  - 可视化中间层 Django 入口。
- 创建：`zhibing/web/zhibing_web/settings.py`
  - Django 设置，静态资源路径指向本仓库。
- 创建：`zhibing/web/zhibing_web/urls.py`
  - Web 路由入口。
- 创建：`zhibing/web/command_ui/views.py`
  - 页面与 API：文本命令提交、投影状态查询、任务状态查询、HITL 审批。
- 创建：`zhibing/web/command_ui/templates/command_ui/index.html`
  - 参考 `wargame` 的地图 + 文本输入输出并列界面。
- 创建：`zhibing/web/command_ui/static/command_ui/app.js`
  - Leaflet 渲染逻辑：单位、目标建筑、路线、风险区、状态流。
- 创建：`zhibing/web/command_ui/static/command_ui/styles.css`
  - 精简版 wargame 风格，不直接使用旧项目巨型模板。
- 修改：`zhibing/main.py`
  - 暴露 `plan_only` 和 `run_user_command` 的投影结果，供 UI 并列显示。
- 创建：`zhibing/tests/test_interface_ownership.py`
  - 验证接口所有权文档与 registry 一致。
- 创建：`zhibing/tests/test_hitl_policy.py`
  - 验证可配置 HITL 节点允许/禁止逻辑。
- 创建：`zhibing/tests/test_graphrag_ingestion.py`
  - 用火山 Ark 或 fallback fixture 验证知识抽取结构。
- 创建：`zhibing/tests/test_visualization_projection.py`
  - 验证意图识别输出能正确落到地图投影。
- 创建：`zhibing/tests/test_command_visual_consistency.py`
  - 验证“用户命令-IntentJSON-TaskSubmitRequest-BattlefieldProjection”忠实一致。

---

### 任务 1：明确接口所有权与下层仿真交付文档

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
    def test_status_query_is_shared_protocol_and_query_task_is_lower_required(self):
        matrix = get_interface_matrix()
        self.assertEqual(matrix["StatusQueryRequest"]["owner"], "SHARED_PROTOCOL")
        self.assertEqual(matrix["query_task"]["owner"], "LOWER_SIM_REQUIRED")

    def test_scene_tools_are_zhibing_wrappers_not_lower_direct_calls(self):
        matrix = get_interface_matrix()
        self.assertEqual(matrix["Scene Query Tools"]["owner"], "ZHIBING_OWNED")
        self.assertIn("get_actor_state", matrix["Scene Query Tools"]["zhibing_functions"])
        self.assertIn("GET /actors/{actor_id}/state", matrix["Scene Query Tools"]["lower_dependencies"])
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest zhibing.tests.test_interface_ownership -q`

预期：FAIL，报错 `No module named 'zhibing.interfaces'`。

- [ ] **步骤 3：实现接口所有权登记表**

```python
# zhibing/interfaces/interface_ownership.py
from __future__ import annotations

from typing import Any


def get_interface_matrix() -> dict[str, dict[str, Any]]:
    return {
        "Scene Query Tools": {
            "owner": "ZHIBING_OWNED",
            "role": "Layer 2 tool facade. It validates inputs, enforces CoordService, caches facts, and calls lower sim or mock data.",
            "zhibing_functions": [
                "get_actor_state", "get_nearby_entities", "get_buildings",
                "get_building_entrances", "get_enemy_state", "get_weather",
                "route_plan", "estimate_move_time", "lookup_bt", "validate_bt_args",
                "query_obstacle", "get_passable_routes"
            ],
            "lower_dependencies": [
                "GET /actors/{actor_id}/state",
                "POST /entities/nearby",
                "POST /buildings/query",
                "GET /buildings/{building_id}/entrances",
                "POST /enemy/query",
                "GET /environment/weather",
                "POST /routes/plan",
                "GET /obstacles/{segment_id}"
            ],
        },
        "TaskSubmitRequest": {
            "owner": "SHARED_PROTOCOL",
            "role": "Zhibing emits it; lower simulation wrapper must accept the compiled SQF plan derived from it.",
        },
        "StatusQueryRequest": {
            "owner": "SHARED_PROTOCOL",
            "role": "Zhibing emits it; lower simulation wrapper must return TaskStatusResponse-compatible data.",
        },
        "submit_sqf_plan": {
            "owner": "LOWER_SIM_REQUIRED",
            "role": "Lower simulation wrapper executes loadBTSet, setBT, setBBVariable, receiveMessage.",
        },
        "query_task": {
            "owner": "LOWER_SIM_REQUIRED",
            "role": "Lower simulation wrapper returns runtime status, active node, position, progress, return code.",
        },
        "BattlefieldProjection": {
            "owner": "ZHIBING_OWNED",
            "role": "Visualization-only projection generated by Zhibing from intent, plan, and status.",
        },
    }
```

- [ ] **步骤 4：写下层工程师文档**

`zhibing/docs/lower_simulation_interface.md` 必须包含这些章节：

```markdown
# 下层仿真系统接口说明

## 1. 下层需要提供的能力总览
## 2. HTTP REST 接口
## 3. Socket 消息接口
## 4. TaskSubmitRequest / StatusQueryRequest 处理方式
## 5. Scene Query 下层依赖接口
## 6. TaskStatusResponse 返回字段
## 7. 节点追踪与 return_code 规范
## 8. 坐标系与 CoordService 约定
## 9. 错误码与重试建议
## 10. 最小联调案例
```

文档中明确：

- `Scene Query Tools` 是智兵系统实现的工具门面。
- `StatusQueryRequest` 是智兵和下层共同遵守的协议对象。
- 下层必须提供 actor、entity、building、route、weather、obstacle、task runtime 状态。
- 下层不负责上层 hard timeout 判定。
- 下层负责 VBS 行为树运行、实时局部避障、突发遇敌紧急处置。

- [ ] **步骤 5：运行测试验证通过**

运行：`python -m unittest zhibing.tests.test_interface_ownership -q`

预期：PASS。

- [ ] **步骤 6：Commit**

```bash
git add zhibing/interfaces zhibing/docs/lower_simulation_interface.md zhibing/LOWER_LAYER_CONTRACT.md zhibing/tests/test_interface_ownership.py
git commit -m "docs: define lower simulation interface ownership"
```

---

### 任务 2：建立可配置 HITL 节点目录与策略

**文件：**
- 创建：`zhibing/hitl/node_catalog.py`
- 创建：`zhibing/hitl/hitl_policy.yaml`
- 修改：`zhibing/hitl/interrupt_handler.py`
- 修改：`zhibing/main.py`
- 测试：`zhibing/tests/test_hitl_policy.py`

- [ ] **步骤 1：编写失败测试**

```python
import unittest

from zhibing.hitl.node_catalog import NodeType
from zhibing.hitl.interrupt_handler import HITLPolicy, HITLDecisionContext


class HITLPolicyTests(unittest.TestCase):
    def test_configurable_node_can_trigger_hitl(self):
        policy = HITLPolicy.from_dict({
            "nodes": {"ENTER_DANGER_ZONE_CHECK": {"hitl_allowed": True, "require_hitl": True}}
        })
        context = HITLDecisionContext(
            node_type=NodeType.ENTER_DANGER_ZONE_CHECK,
            urgency="normal",
            trigger="TRIGGER_ENTER_DANGER_ZONE",
            actor={"type": "group", "id": "p_4"},
            proposed_action={"task_type": "group_move"},
            risk_assessment="destination intersects known fire zone",
        )
        self.assertIsNotNone(policy.evaluate(context))

    def test_emergency_contact_cannot_block_for_hitl(self):
        policy = HITLPolicy.default()
        context = HITLDecisionContext(
            node_type=NodeType.EMERGENCY_CONTACT,
            urgency="immediate",
            trigger="TRIGGER_SUDDEN_ENEMY_CONTACT",
            actor={"type": "group", "id": "p_4"},
            proposed_action={"local_action": "take_cover"},
            risk_assessment="sudden contact must be handled locally",
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
    BT_SELECTION_UNKNOWN = "BT_SELECTION_UNKNOWN"
    FIRE_OR_ATTACK_AUTHORIZATION = "FIRE_OR_ATTACK_AUTHORIZATION"
    VISUALIZATION_PROJECTION = "VISUALIZATION_PROJECTION"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    TASK_SUBMISSION = "TASK_SUBMISSION"
    STATUS_POLL = "STATUS_POLL"
    REPLAN_DIAGNOSIS = "REPLAN_DIAGNOSIS"
    REPLAN_FAIL_GATE = "REPLAN_FAIL_GATE"
    EMERGENCY_CONTACT = "EMERGENCY_CONTACT"
    LOCAL_AVOIDANCE = "LOCAL_AVOIDANCE"
    EXPLANATION_QUERY = "EXPLANATION_QUERY"
```

- [ ] **步骤 4：实现策略读取和评估**

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
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            return cls.from_dict(data)
        return cls.from_dict({"nodes": {}})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HITLPolicy":
        return cls(nodes=dict(data.get("nodes") or {}))

    def evaluate(self, context: HITLDecisionContext) -> HITLInterrupt | None:
        node_config = self.nodes.get(context.node_type.value, {})
        if context.urgency == "immediate" and node_config.get("allow_emergency_skip", True):
            return None
        if not node_config.get("hitl_allowed", False):
            return None
        if not node_config.get("require_hitl", False):
            return None
        return HITLInterrupt(
            trigger=context.trigger,
            actor=context.actor,
            proposed_action=context.proposed_action,
            risk_assessment=context.risk_assessment,
        )
```

- [ ] **步骤 5：创建默认策略文件**

```yaml
# zhibing/hitl/hitl_policy.yaml
nodes:
  RULE_CONFLICT_CHECK:
    hitl_allowed: true
    require_hitl: true
    allow_emergency_skip: false
  ENTER_DANGER_ZONE_CHECK:
    hitl_allowed: true
    require_hitl: true
    allow_emergency_skip: false
  BT_SELECTION_UNKNOWN:
    hitl_allowed: true
    require_hitl: true
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

### 任务 3：引入 GraphRAG 知识注入与 LLM Router

**文件：**
- 创建：`zhibing/knowledge/__init__.py`
- 创建：`zhibing/knowledge/llm_router.py`
- 创建：`zhibing/knowledge/document_loader.py`
- 创建：`zhibing/knowledge/graphrag_store.py`
- 创建：`zhibing/knowledge/graphrag_builder.py`
- 创建：`zhibing/knowledge/graphrag_query.py`
- 创建：`zhibing/knowledge/default_corpus/urban_encirclement_rules.md`
- 修改：`zhibing/config.py`
- 修改：`zhibing/decision_layer/module_b_scene.py`
- 修改：`zhibing/decision_layer/module_c_planner.py`
- 测试：`zhibing/tests/test_graphrag_ingestion.py`

- [ ] **步骤 1：编写失败测试**

```python
import unittest

from zhibing.knowledge.document_loader import load_documents
from zhibing.knowledge.graphrag_builder import build_knowledge_graph
from zhibing.knowledge.graphrag_query import retrieve_knowledge_context


class GraphRAGIngestionTests(unittest.TestCase):
    def test_default_corpus_injects_avoid_fire_zone_rule(self):
        docs = load_documents(["zhibing/knowledge/default_corpus"])
        graph = build_knowledge_graph(docs, use_llm=False)
        context = retrieve_knowledge_context(
            graph,
            {
                "intent": "group_move",
                "actors": [{"type": "group", "id": "p_4"}],
                "destination": {"type": "absolute", "coord": {"frame": "VBS_LOCAL_XYZ", "x": 1000, "y": 500, "z": 0}},
                "constraints": {"avoid_enemy": False, "maintain_formation": True, "allow_replan": True},
            },
        )
        self.assertTrue(context["constraints"]["avoid_enemy_fire_zone"])
        self.assertIn("avoid_enemy_fire_zone", context["matched_rules"][0]["rule_id"])
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest zhibing.tests.test_graphrag_ingestion -q`

预期：FAIL，报错 `No module named 'zhibing.knowledge'`。

- [ ] **步骤 3：实现 LLM Router**

```python
# zhibing/knowledge/llm_router.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class KnowledgeLLMRouter:
    def __init__(self, task: str = "reply_generation") -> None:
        self.task = task

    def invoke_json(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        try:
            from llm_call_extract.llm_client import ModelRouter
            model = ModelRouter().get_chat_model(self.task)
            response = model.invoke(messages)
            return json.loads(response.content)
        except Exception as exc:
            raise RuntimeError(f"Knowledge LLM call failed: {exc}") from exc

    @staticmethod
    def local_deploy_notes() -> dict[str, str]:
        return {
            "test_vendor": "volcengine_ark / ep-20260615114505-247zc via llm_call_extract",
            "server_local": "OpenWebUI/vLLM OpenAI-compatible endpoint via env ZHIBING_LLM_BASE_URL and ZHIBING_LLM_MODEL",
        }
```

- [ ] **步骤 4：实现文档加载**

```python
# zhibing/knowledge/document_loader.py
from __future__ import annotations

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
            if file_path.suffix.lower() in {".txt", ".md", ".json", ".csv"}:
                docs.append(KnowledgeDocument(str(file_path), file_path.read_text(encoding="utf-8")))
            elif file_path.suffix.lower() == ".docx":
                import zipfile
                with zipfile.ZipFile(file_path) as archive:
                    xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
                docs.append(KnowledgeDocument(str(file_path), xml))
            elif file_path.suffix.lower() == ".pdf":
                docs.append(KnowledgeDocument(str(file_path), file_path.read_bytes().decode("utf-8", errors="ignore")))
    return docs
```

- [ ] **步骤 5：实现 GraphRAG store 与 fallback 抽取**

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
        if "火力区" in text or "fire zone" in text.lower():
            graph.entities.append({"id": "enemy_fire_zone", "type": "risk_zone", "name": "enemy fire zone"})
            graph.rules.append({
                "rule_id": "avoid_enemy_fire_zone",
                "condition": "movement destination or route intersects enemy fire zone",
                "action": "set constraints.avoid_enemy=true and route_plan avoid_enemy=true",
                "hitl_node": "ENTER_DANGER_ZONE_CHECK",
                "source": doc.source_path,
            })
        if "突然遇敌" in text or "sudden contact" in text.lower():
            graph.rules.append({
                "rule_id": "sudden_contact_local_emergency",
                "condition": "VBS runtime reports sudden enemy contact",
                "action": "lower layer handles immediate cover or avoidance without blocking HITL",
                "hitl_node": "EMERGENCY_CONTACT",
                "source": doc.source_path,
            })
    return graph
```

- [ ] **步骤 6：实现运行时检索**

```python
# zhibing/knowledge/graphrag_query.py
from __future__ import annotations

from typing import Any

from zhibing.knowledge.graphrag_store import KnowledgeGraph


def retrieve_knowledge_context(graph: KnowledgeGraph, intent_json: dict[str, Any]) -> dict[str, Any]:
    matched = []
    constraints = {"avoid_enemy_fire_zone": False, "requires_hitl_nodes": []}
    if "move" in intent_json.get("intent", "") or "group_move" == intent_json.get("intent"):
        for rule in graph.rules:
            if rule["rule_id"] == "avoid_enemy_fire_zone":
                matched.append(rule)
                constraints["avoid_enemy_fire_zone"] = True
                constraints["requires_hitl_nodes"].append(rule["hitl_node"])
    return {"matched_rules": matched, "constraints": constraints}
```

- [ ] **步骤 7：创建默认知识库**

```markdown
# Urban Encirclement Rules

执行建筑围剿、移动、接近目标建筑入口时，系统必须自动避开已知敌方火力区。用户不需要显式写出“避开敌方火力区”。

如果目标点或路线进入已知危险区，应在 ENTER_DANGER_ZONE_CHECK 节点请求 Human-in-the-loop。

如果 VBS 运行时突然遇敌，该事件属于 sudden contact。下层仿真系统应立即执行本地规避、隐蔽或短暂停止，不得阻塞等待 Human-in-the-loop。
```

- [ ] **步骤 8：把 GraphRAG 接入 Module B/C**

`module_b_scene.gather_scene()` 增加：

```python
from zhibing.knowledge.document_loader import load_documents
from zhibing.knowledge.graphrag_builder import build_knowledge_graph
from zhibing.knowledge.graphrag_query import retrieve_knowledge_context

docs = load_documents(["zhibing/knowledge/default_corpus"])
graph = build_knowledge_graph(docs, use_llm=False)
knowledge_context = retrieve_knowledge_context(graph, intent_json)
scene_context["knowledge_context"] = knowledge_context
```

`module_c_planner.create_single_step_plan()` 在 step 中增加：

```python
"knowledge_constraints": scene_context.get("knowledge_context", {}).get("constraints", {})
```

- [ ] **步骤 9：运行测试验证通过**

运行：`python -m unittest zhibing.tests.test_graphrag_ingestion -q`

预期：PASS。

- [ ] **步骤 10：火山 Ark 健康检查**

运行：

```powershell
$env:ARK_API_KEY=$env:ARK_API_KEY
python -c "from llm_call_extract.llm_client import ModelRouter; r=ModelRouter().get_chat_model('reply_generation').invoke([{'role':'user','content':'Return JSON {\"status\":\"ok\"}'}]); print(r.content)"
```

预期：输出 JSON，使用模型配置 `ep-20260615114505-247zc`。

- [ ] **步骤 11：Commit**

```bash
git add zhibing/knowledge zhibing/decision_layer/module_b_scene.py zhibing/decision_layer/module_c_planner.py zhibing/tests/test_graphrag_ingestion.py
git commit -m "feat: add graphrag knowledge injection"
```

---

### 任务 4：定义可视化投影数据模型

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
    def test_group_move_projection_contains_unit_route_and_target(self):
        projection = build_projection(
            intent_json={
                "intent": "group_move",
                "actors": [{"type": "group", "id": "p_4"}],
                "destination": {"type": "absolute", "coord": {"frame": "VBS_LOCAL_XYZ", "x": 1000, "y": 500, "z": 0}},
                "constraints": {"avoid_enemy": True, "maintain_formation": True, "allow_replan": True},
            },
            task_plan_json={
                "mission_id": "mission",
                "plan": [{
                    "step_id": "step_1",
                    "task_type": "group_move",
                    "actor": {"type": "group", "id": "p_4"},
                    "bt": {"btset_path": "CgfControl.btset", "bt_name": "GrpMove"},
                    "args": {"movePos": {"frame": "VBS_LOCAL_XYZ", "x": 1000, "y": 500, "z": 0}, "speed": 10},
                    "timeout_policy": {"expected_seconds": 145, "hard_timeout_seconds": 218, "stall_timeout_seconds": 60},
                }],
            },
            status_response=None,
        )
        self.assertEqual(projection["mission_id"], "mission")
        self.assertEqual(projection["units"][0]["id"], "p_4")
        self.assertEqual(projection["routes"][0]["task_type"], "group_move")
        self.assertEqual(projection["targets"][0]["coord"]["frame"], "VBS_LOCAL_XYZ")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest zhibing.tests.test_visualization_projection -q`

预期：FAIL，报错 `No module named 'zhibing.visualization'`。

- [ ] **步骤 3：实现投影 schema 和 projector**

```python
# zhibing/visualization/schemas.py
from __future__ import annotations

from typing import TypedDict, Any


class BattlefieldProjection(TypedDict):
    mission_id: str
    units: list[dict[str, Any]]
    routes: list[dict[str, Any]]
    targets: list[dict[str, Any]]
    zones: list[dict[str, Any]]
    task_state: dict[str, Any]
    textual_summary: str
```

```python
# zhibing/visualization/projector.py
from __future__ import annotations

from typing import Any

from zhibing.core.coord_service import default_coord_service


def build_projection(
    *,
    intent_json: dict[str, Any],
    task_plan_json: dict[str, Any],
    status_response: dict[str, Any] | None,
) -> dict[str, Any]:
    step = task_plan_json["plan"][0]
    actor = step["actor"]
    dest = step["args"].get("movePos") or step["args"].get("moveDest")
    if dest:
        default_coord_service.validate(dest)
    state = status_response["status"] if status_response else "PLANNED"
    return {
        "mission_id": task_plan_json["mission_id"],
        "units": [{
            "id": actor["id"],
            "type": actor["type"],
            "role": "assault_group" if actor["type"] == "group" else "soldier",
            "status": state,
            "position": (status_response.get("actor") or {}).get("position") if status_response else None,
        }],
        "routes": [{
            "id": f"{step['step_id']}_route",
            "task_type": step["task_type"],
            "bt_name": step["bt"]["bt_name"],
            "waypoints": [dest] if dest else [],
            "style": "planned" if state == "PLANNED" else "runtime",
        }],
        "targets": [{"id": "target_1", "kind": "building_or_point", "coord": dest}] if dest else [],
        "zones": [],
        "task_state": {"state": state, "return_code": status_response.get("return_code") if status_response else None},
        "textual_summary": f"{actor['id']} -> {step['task_type']} via {step['bt']['bt_name']}",
    }
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m unittest zhibing.tests.test_visualization_projection -q`

预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add zhibing/visualization zhibing/tests/test_visualization_projection.py
git commit -m "feat: add battlefield visualization projection"
```

---

### 任务 5：搭建 wargame 风格的 2D 可视化中间层

**文件：**
- 创建：`zhibing/web/manage.py`
- 创建：`zhibing/web/zhibing_web/__init__.py`
- 创建：`zhibing/web/zhibing_web/settings.py`
- 创建：`zhibing/web/zhibing_web/urls.py`
- 创建：`zhibing/web/command_ui/__init__.py`
- 创建：`zhibing/web/command_ui/views.py`
- 创建：`zhibing/web/command_ui/urls.py`
- 创建：`zhibing/web/command_ui/templates/command_ui/index.html`
- 创建：`zhibing/web/command_ui/static/command_ui/app.js`
- 创建：`zhibing/web/command_ui/static/command_ui/styles.css`
- 创建：`zhibing/web/command_ui/static/command_ui/vendor/leaflet.css`
- 创建：`zhibing/web/command_ui/static/command_ui/vendor/leaflet.js`
- 创建：`zhibing/web/command_ui/static/command_ui/map/roads.geojson`
- 创建：`zhibing/web/command_ui/static/command_ui/map/buildings.geojson`

- [ ] **步骤 1：创建 Django 最小入口**

```python
# zhibing/web/manage.py
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zhibing_web.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：配置 settings**

```python
# zhibing/web/zhibing_web/settings.py
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

- [ ] **步骤 3：实现页面和 API**

```python
# zhibing/web/command_ui/views.py
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
    projection = build_projection(
        intent_json=result.task_submit_request.get("intent_json", {}),
        task_plan_json={
            "mission_id": result.mission_id,
            "plan": [{
                "step_id": "step_1",
                "task_type": result.task_submit_request["task"]["task_type"],
                "actor": result.task_submit_request["actor"],
                "bt": {
                    "btset_path": result.task_submit_request["task"]["btset_path"],
                    "bt_name": result.task_submit_request["task"]["bt_name"],
                },
                "args": result.task_submit_request["task"]["bt_args"],
                "timeout_policy": result.task_submit_request["timeout_policy"],
            }],
        },
        status_response=result.task_status_response,
    )
    return JsonResponse({
        "state": result.state,
        "task_id": result.task_id,
        "explanation": result.explanation,
        "task_submit_request": result.task_submit_request,
        "task_status_response": result.task_status_response,
        "projection": projection,
    })
```

- [ ] **步骤 4：实现地图页面**

`index.html` 使用 wargame 的布局思想：左侧态势图层、中央地图、右侧文本指挥与解释。页面包含：

```html
<div id="map"></div>
<aside id="left-panel">
  <h2>态势图层</h2>
  <label><input type="checkbox" checked data-layer="units"> 单位</label>
  <label><input type="checkbox" checked data-layer="routes"> 路线</label>
  <label><input type="checkbox" checked data-layer="zones"> 风险区</label>
</aside>
<aside id="right-panel">
  <section id="chat-output"></section>
  <form id="command-form">
    <textarea id="command-input"></textarea>
    <button type="submit">下达</button>
  </form>
  <pre id="json-output"></pre>
</aside>
<script src="/static/command_ui/vendor/leaflet.js"></script>
<script src="/static/command_ui/app.js"></script>
```

- [ ] **步骤 5：实现前端投影渲染**

```javascript
async function submitCommand(text) {
  const response = await fetch("/api/command", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({message: text})
  });
  const data = await response.json();
  renderProjection(data.projection);
  document.getElementById("chat-output").textContent = data.explanation;
  document.getElementById("json-output").textContent = JSON.stringify(data.task_submit_request, null, 2);
}

function renderProjection(projection) {
  clearMissionLayers();
  projection.targets.forEach(drawTarget);
  projection.routes.forEach(drawRoute);
  projection.units.forEach(drawUnit);
  projection.zones.forEach(drawZone);
}
```

- [ ] **步骤 6：复制地图资产**

从 `C:\Users\22646\Desktop\wargame\wargame\static\wargame` 复制这些文件到本仓库：

- `lib/leaflet.js`
- `lib/leaflet.css`
- `roads.geojson`
- `buildings.geojson`
- 兵种图标：`攻势小队.png`、`侦察小队.png`、`保障小队.png`

复制命令：

```powershell
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\lib\leaflet.js" "zhibing\web\command_ui\static\command_ui\vendor\leaflet.js"
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\lib\leaflet.css" "zhibing\web\command_ui\static\command_ui\vendor\leaflet.css"
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\roads.geojson" "zhibing\web\command_ui\static\command_ui\map\roads.geojson"
Copy-Item "C:\Users\22646\Desktop\wargame\wargame\static\wargame\buildings.geojson" "zhibing\web\command_ui\static\command_ui\map\buildings.geojson"
```

- [ ] **步骤 7：运行开发服务器**

运行：

```powershell
python zhibing\web\manage.py runserver 127.0.0.1:8090
```

预期：打开 `http://127.0.0.1:8090/` 可看到地图、文本输入、输出解释。

- [ ] **步骤 8：Commit**

```bash
git add zhibing/web
git commit -m "feat: add 2d command visualization ui"
```

---

### 任务 6：打通主流程中的投影输出与 HITL 上下文

**文件：**
- 修改：`zhibing/main.py`
- 修改：`zhibing/decision_layer/module_a_intent.py`
- 修改：`zhibing/decision_layer/module_b_scene.py`
- 修改：`zhibing/decision_layer/module_c_planner.py`
- 修改：`zhibing/decision_layer/module_e_param_gen.py`
- 测试：`zhibing/tests/test_command_visual_consistency.py`

- [ ] **步骤 1：编写一致性测试**

```python
import unittest

from zhibing.main import ZhibingDecisionSystem
from zhibing.visualization.projector import build_projection


class CommandVisualConsistencyTests(unittest.TestCase):
    def test_command_destination_matches_task_request_and_projection(self):
        system = ZhibingDecisionSystem()
        result = system.run_user_command("让p_4群组以速度10移动到指定坐标 VBS_LOCAL_XYZ {x:1000, y:500, z:0}")
        request_dest = result.task_submit_request["task"]["bt_args"]["movePos"]
        projection = build_projection(
            intent_json=result.intent_json,
            task_plan_json=result.task_plan_json,
            status_response=result.task_status_response,
        )
        visual_dest = projection["targets"][0]["coord"]
        self.assertEqual(request_dest, visual_dest)
        self.assertEqual(projection["routes"][0]["bt_name"], result.task_submit_request["task"]["bt_name"])
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest zhibing.tests.test_command_visual_consistency -q`

预期：FAIL，因为 `MissionRunResult` 尚未暴露 `intent_json` 和 `task_plan_json`。

- [ ] **步骤 3：扩展 MissionRunResult**

```python
@dataclass
class MissionRunResult:
    session_id: str
    mission_id: str
    task_id: str
    state: str
    intent_json: dict[str, Any]
    task_plan_json: dict[str, Any]
    task_submit_request: dict[str, Any]
    task_status_response: dict[str, Any]
    decision_log_id: str
    explanation: str
    compiled_sqf: tuple[str, ...]
    replan_event: dict[str, Any] | None = None
```

在 `_result()` 中传入 `intent_json` 和 `task_plan_json`。

- [ ] **步骤 4：在 task submit request 中保留可视化追踪 metadata**

```python
submit_request["trace"] = {
    "intent_id": intent.get("intent"),
    "source": "LLM_DECISION_LAYER",
    "visualization_projection_expected": True,
}
```

- [ ] **步骤 5：运行一致性测试**

运行：`python -m unittest zhibing.tests.test_command_visual_consistency -q`

预期：PASS。

- [ ] **步骤 6：运行全量测试**

运行：`python -m unittest discover -s zhibing\tests -q`

预期：全部 PASS。

- [ ] **步骤 7：Commit**

```bash
git add zhibing/main.py zhibing/decision_layer zhibing/tests/test_command_visual_consistency.py
git commit -m "feat: expose mission trace for visualization consistency"
```

---

### 任务 7：完善下层 Mock 与真实 HTTP Transport 边界

**文件：**
- 创建：`zhibing/adapter/http_transport.py`
- 修改：`zhibing/adapter/vbs_adapter.py`
- 修改：`zhibing/config.py`
- 测试：`zhibing/tests/test_lower_http_transport.py`

- [ ] **步骤 1：编写 HTTP transport 测试**

```python
import unittest

from zhibing.adapter.http_transport import LowerSimHTTPTransport


class LowerHTTPTransportTests(unittest.TestCase):
    def test_builds_submit_payload(self):
        transport = LowerSimHTTPTransport(base_url="http://lower-sim.test")
        payload = transport.build_submit_payload(
            task_id="task",
            request={"request_id": "req"},
            sqf_statements=("loadBTSet \"CgfControl.btset\";",),
        )
        self.assertEqual(payload["task_id"], "task")
        self.assertEqual(payload["request"]["request_id"], "req")
        self.assertEqual(payload["sqf_statements"][0], "loadBTSet \"CgfControl.btset\";")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m unittest zhibing.tests.test_lower_http_transport -q`

预期：FAIL，报错 `No module named 'zhibing.adapter.http_transport'`。

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
        payload = self.build_submit_payload(task_id=plan.task_id, request=request, sqf_statements=plan.statements)
        return self._post_json("/tasks/submit", payload)

    def query_task(self, task_id: str, query_fields: list[str] | None = None) -> dict[str, Any]:
        return self._post_json("/tasks/query", {"task_id": task_id, "query_fields": query_fields or []})

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m unittest zhibing.tests.test_lower_http_transport -q`

预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add zhibing/adapter/http_transport.py zhibing/tests/test_lower_http_transport.py
git commit -m "feat: add lower simulation http transport"
```

---

### 任务 8：端到端测试“意图识别-可视化中间层-仿真底层”

**文件：**
- 创建：`zhibing/tests/test_three_layer_alignment.py`

- [ ] **步骤 1：编写三层一致性测试**

```python
import unittest

from zhibing.main import ZhibingDecisionSystem
from zhibing.visualization.projector import build_projection


class ThreeLayerAlignmentTests(unittest.TestCase):
    def test_intent_visual_and_adapter_are_aligned(self):
        system = ZhibingDecisionSystem()
        result = system.run_user_command("让p_4群组以速度10移动到指定坐标 VBS_LOCAL_XYZ {x:1000, y:500, z:0}")
        projection = build_projection(
            intent_json=result.intent_json,
            task_plan_json=result.task_plan_json,
            status_response=result.task_status_response,
        )

        request = result.task_submit_request
        self.assertEqual(request["actor"]["id"], projection["units"][0]["id"])
        self.assertEqual(request["task"]["bt_name"], projection["routes"][0]["bt_name"])
        self.assertEqual(request["task"]["bt_args"]["movePos"], projection["targets"][0]["coord"])
        self.assertIn("setBT", "\n".join(result.compiled_sqf))
        self.assertIn("setBBVariable", "\n".join(result.compiled_sqf))
```

- [ ] **步骤 2：运行测试验证通过**

运行：`python -m unittest zhibing.tests.test_three_layer_alignment -q`

预期：PASS。

- [ ] **步骤 3：增加不可达路线测试**

```python
def test_blocked_route_visual_state_matches_failed_status(self):
    system = ZhibingDecisionSystem()
    result = system.run_user_command("让p_4群组以速度10移动到指定坐标 VBS_LOCAL_XYZ {x:9000, y:500, z:0}")
    projection = build_projection(
        intent_json=result.intent_json,
        task_plan_json=result.task_plan_json,
        status_response=result.task_status_response,
    )
    self.assertEqual(result.state, "FAILED")
    self.assertEqual(projection["task_state"]["return_code"], "UNREACHABLE")
```

- [ ] **步骤 4：运行全量测试**

运行：`python -m unittest discover -s zhibing\tests -q`

预期：全部 PASS。

- [ ] **步骤 5：Commit**

```bash
git add zhibing/tests/test_three_layer_alignment.py
git commit -m "test: verify intent visual adapter alignment"
```

---

### 任务 9：更新运行逻辑文档

**文件：**
- 创建：`zhibing/docs/system_runtime_flow.md`
- 修改：`ZHIBING_SYSTEM_PLAN.md`

- [ ] **步骤 1：创建运行逻辑文档**

`zhibing/docs/system_runtime_flow.md` 必须包含：

```markdown
# 智兵决策系统运行逻辑

## 1. 用户进入前
### 1.1 知识库导入
### 1.2 GraphRAG 构建
### 1.3 BT Registry 加载
### 1.4 下层仿真场景同步
### 1.5 可视化地图资产加载

## 2. 用户进入后
### 2.1 文本命令输入
### 2.2 IntentJSON
### 2.3 KnowledgeContext
### 2.4 SceneContext
### 2.5 TaskPlanJSON
### 2.6 BattlefieldProjection
### 2.7 TaskSubmitRequest
### 2.8 StatusQueryRequest / TaskStatusResponse
### 2.9 ExplainabilityLogger

## 3. HITL 节点策略
## 4. 失败、重规划与紧急事件
## 5. 与下层仿真系统的责任边界
```

- [ ] **步骤 2：在计划文档中加入更新引用**

在 `ZHIBING_SYSTEM_PLAN.md` 的 SECTION 17 或末尾加入：

```markdown
Update documents:
- `zhibing/docs/lower_simulation_interface.md`
- `zhibing/docs/system_runtime_flow.md`
- `zhibing/hitl/hitl_policy.yaml`
```

- [ ] **步骤 3：Commit**

```bash
git add zhibing/docs/system_runtime_flow.md ZHIBING_SYSTEM_PLAN.md
git commit -m "docs: update full zhibing runtime flow"
```

---

## 自检清单

- [ ] 明确了 `Scene Query Tools` 是智兵系统自实现工具门面，下层只提供依赖数据接口。
- [ ] 明确了 `StatusQueryRequest` 是共享协议，下层必须返回 `TaskStatusResponse`。
- [ ] 有单独下层工程师交付文档：`zhibing/docs/lower_simulation_interface.md`。
- [ ] HITL 从主观触发改成节点类型 + YAML 策略配置。
- [ ] 紧急节点 `EMERGENCY_CONTACT` 和 `LOCAL_AVOIDANCE` 默认禁止阻塞式 HITL。
- [ ] 用户进入前的 GraphRAG 知识注入被纳入运行流程。
- [ ] GraphRAG 测试使用 `llm_call_extract`，配置兼容火山 Ark 和本地 OpenWebUI/vLLM。
- [ ] 可视化中间层以 wargame 的 Leaflet/GeoJSON 设计为参考，但在本仓库独立实现。
- [ ] 测试覆盖“意图识别-可视化中间层-仿真底层”三层一致性。
- [ ] 不修改 PHASE_MVP 禁止项：不让 LLM 生成 SQF，不生成新 `.bt` 文件。

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-06-20-zhibing-system-update.md`。两种执行方式：

**1. 子代理驱动（推荐）** - 每个任务调度一个新子代理，任务间进行审查，快速迭代。

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设检查点。

选择执行前，请先回答本计划开头的 5 个确认问题。
