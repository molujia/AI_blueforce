# 智兵决策系统运行逻辑

本文描述更新后的上层 LLM 指控系统运行过程。本系统包含 LLM 智兵决策层、任务网关、VBS Adapter、GraphRAG 知识层和 2D 可视化中间层；不包含 VBS 仿真引擎、行为树运行时和下层 HTTP/socket return 封装。

## 1. 用户进入前

### 1.1 条例、PDF、DOCX、测试语料导入

系统启动前可调用 `zhibing.knowledge.document_loader` 读取 TXT、MD、JSON、CSV、DOCX、PDF。当前测试语料包括 `test_files/ARN19656_ATP.pdf` 和 `test_files/地下作战.docx`，内置语料位于 `zhibing/knowledge/default_corpus/urban_encirclement_rules.md`。

### 1.2 GraphRAG 构建与 Benchmark

`zhibing.knowledge.graphrag_builder` 将文档切成 source chunks，抽取实体、关系和规则，写入轻量图谱。运行时通过 `retrieve_knowledge()` 自动检索 KnowledgeContext。Benchmark 入口是 `zhibing.knowledge.benchmark.run_benchmarks()`，覆盖 FormatBench、RuleGroundingBench、NoiseTripletBench 和 LocalModelBench。LLM 抽取通道由 `zhibing.knowledge.llm_router` 预留，默认测试模型为火山 Ark `ep-20260615114505-247zc`，部署时可切换本地 OpenWebUI/vLLM。

### 1.3 BT Registry 加载

`zhibing/registry/bt_registry.json` 描述当前可用 BT。现阶段主要可执行能力是移动类 BT，例如 `GrpMove`、`grpSimpleMoveNoAuto`、`GrpMove2`。复杂任务不能假设下层已有复杂围剿 BT，必须拆成当前 registry 可执行的简单步骤和 pending tactical intent。

### 1.4 下层仿真场景同步

上层通过 `Scene Query Tools` 获取 actor、weather、route、building、enemy、obstacle 等信息。工具门面由智兵系统实现，真实数据接口由下层仿真系统提供，详见 `zhibing/docs/lower_simulation_interface.md`。

### 1.5 wargame 地图资产加载

可视化中间层复制 `wargame` 的 Leaflet、roads.geojson、buildings.geojson 和小队图标到 `zhibing/web/command_ui/static/command_ui`，运行时不依赖外部 wargame 服务。

## 2. 用户进入后

### 2.1 文本命令输入

用户在文本界面或 2D 可视化界面输入命令，例如命令 `p_4` 前往目标建筑入口开展围剿任务。

### 2.2 IntentJSON

`module_a_intent` 将自然语言转成结构化 IntentJSON。LLM 只能输出 JSON，不能输出 SQF。离线 fallback 会识别移动和围剿类命令，并保证坐标使用显式 frame。

### 2.3 KnowledgeContext

`module_b_scene` 在场景查询过程中调用 GraphRAG，检索诸如避开敌火力区、建筑入口前态势评估、突发遇敌本地处理等规则，将其写入 SceneContext 和 TaskPlanJSON。

### 2.4 SceneContext

SceneContext 包含 actor 状态、天气、路线、BT 候选和 KnowledgeContext。当前 mock scene 可离线运行；真实部署时这些数据来自下层仿真系统。

### 2.5 TaskPlanJSON

`module_c_planner` 生成完整 TaskPlanJSON。普通移动生成单步计划。围剿建筑生成三步：移动到建筑入口、态势评估、pending attack intent。只有第一步 `GrpMove` 标记为可提交 adapter。

### 2.6 BattlefieldProjection

`zhibing.visualization.projector.build_projection()` 将 intent、plan 和 status response 投影为 2D 地图状态，包含 units、routes、targets、zones、pending_intents 和 task_state。

### 2.7 TaskSubmitRequest

主流程从 TaskPlanJSON 中选取首个 `executable_by_adapter=true` 的步骤，构造 TaskSubmitRequest。此请求仍是结构化 JSON；SQF 只由 adapter 内部的确定性 compiler 生成。

### 2.8 HTTP/socket Adapter

`VBSAdapter` 默认用于离线测试时走 mock transport。真实部署可调用 `VBSAdapter.from_config()`，根据 `ZHIBING_LOWER_SIM_TRANSPORT` 选择 HTTP 或 socket。配置默认值是 HTTP，socket 可作为长连接通道。

### 2.9 StatusQueryRequest / TaskStatusResponse

提交后上层发起状态查询。下层返回任务状态、actor 位置、active node、node path、return code、进度和错误信息。突发遇敌和局部避险由下层本地处理，上层只接收事件和状态。

### 2.10 ExplainabilityLogger

解释模块记录 BT 选择原因、替代方案、参数来源和任务结果。UI 会并列展示文本解释、JSON 输出和地图投影。

## 3. 围剿任务如何由简单 BT 实现

围剿任务暂不生成复杂围剿脚本。系统将其拆为：

1. `group_move_to_building_entry`：用 `GrpMove` 移动到建筑入口。
2. `situation_assessment`：pending 上层/下层态势评估节点。
3. `attack_intent_pending_lower_bt`：记录移动与攻击意图，等待下层补齐战术 BT。

这保证上层不会命令下层执行不存在的 BT，同时用户可在可视化中看到任务意图与实际可执行步骤的差异。

## 4. HITL 节点策略如何配置

节点类型定义在 `zhibing/hitl/node_catalog.py`。是否允许 HITL、是否要求 HITL、紧急情况下是否跳过，由 `zhibing/hitl/hitl_policy.yaml` 控制。`EMERGENCY_CONTACT` 和 `LOCAL_AVOIDANCE` 默认不阻塞等待人工确认。

## 5. 下层仿真系统责任边界

下层负责 VBS 引擎、BT runtime、HTTP/socket return、真实场景数据接口、任务执行、active_node/node_path/return_code、突发遇敌与局部避险。上层负责意图识别、知识检索、计划、可视化投影、确定性 SQF 编译和解释记录。