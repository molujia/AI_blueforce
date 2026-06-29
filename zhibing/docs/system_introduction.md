# 智兵决策系统介绍

## 1. 系统定位

智兵决策系统是面向 VBS 仿真环境的上层 LLM 指控系统。它负责把用户自然语言任务、预置条令知识、当前战场态势和下层行为树能力整合起来，生成可解释、可检查、可下发的任务计划。

当前系统包含上层 LLM 智兵决策层、GraphRAG 知识注入层、任务规划层、2D 可视化中间层、任务网关和 VBS Adapter。它不包含真实 VBS 仿真引擎、真实行为树运行时和真实 HTTP/socket 下层封装服务。下层工程师需要按 `zhibing/docs/lower_simulation_interface.md` 补齐真实仿真接口。

## 2. 完整系统功能

### 2.1 用户意图识别与任务拆解

系统接收用户文本命令，将其转化为结构化 IntentJSON。对复杂任务不会直接假设下层具备完整能力，而是按当前 BT registry 拆成可执行步骤与 pending intent。

例如“前往建筑内开展围剿”在当前 v0 中会被拆成：

1. 移动到目标建筑入口。
2. 态势评估。
3. 后续移动与攻击意图，等待下层补齐战术 BT。

当前下层可执行能力有限，因此实际提交以移动类行为树为主，后续战术意图保留在计划、可视化和解释日志中。

### 2.2 GraphRAG 知识注入

系统在用户进入前使用知识库吸收条令、PDF、DOCX 和内置规则语料，使“避开敌方火力区”“进入建筑前进行态势评估”等知识不依赖用户现场补充。

当前实现位于 `zhibing/knowledge`：

- `document_loader.py`：加载文本、DOCX、PDF 等文件。
- `graphrag_builder.py`：构建轻量 GraphRAG store。
- `graphrag_query.py`：按任务意图检索规则和来源片段。
- `graphrag_usability.py`：提供官方 quickstart 命令说明和本地文件可用性测试入口。
- `llm_router.py`：预留火山 Ark、OpenAI-compatible 和本地 LLM 迁移配置。

验收口径是可用性：官方 quickstart 命令可被列出，本地 `test_files/地下作战.docx` 与 `test_files/ARN19656_ATP.pdf` 能被加载、查询，并返回来源命中。官方 GraphRAG live quickstart 和 nano 模型测试没有自动执行，因为用户要求任何测试期 LLM 消耗都必须先估算成本并征得同意。

### 2.3 确定性寻路与 LLM 特殊约束

路径生成遵循“算法先行，LLM 修正约束”的边界：

1. 固定寻路算法先生成 Top-N 候选路径。
2. 算法按距离、风险、时间等指标评分。
3. 若路径分数接近，系统请求 LLM 解释每条路线优缺点，供用户选择。
4. 若用户输入特殊要求，LLM 只解析为结构化约束补丁，不直接生成路线坐标。
5. 路径规划器应用补丁重新评分，生成新推荐路线。

当前 v0 支持的典型约束包括：

- “不要走大路，大路有狙击风险”：解析为 `avoid road_class:main_road`，推荐绕行小路。
- “敌军不在营地，现在必须争分夺秒”：解析为 `ignore_zone enemy_zone:enemy_1` 和 `priority=time`，推荐更短路线。

### 2.4 wargame 风格 2D 可视化中间层

Web UI 参考 `C:\Users\22646\Desktop\wargame` 的 2D 地图和战术 HUD 设计。当前项目只保留 2D 地图，不使用真实地图图片；敌我单位也简化为我方一个班组单元、敌方一个火力点单元。

地图资产已复制进本仓库：

- `zhibing/web/command_ui/static/command_ui/map/roads.geojson`
- `zhibing/web/command_ui/static/command_ui/map/buildings.geojson`
- `zhibing/web/command_ui/static/command_ui/map/water.geojson`
- `zhibing/web/command_ui/static/command_ui/map/landhouse.geojson`

UI 包含：顶部状态栏、左侧部署和对象列表、中间 Leaflet 2D 地图、右侧聊天、路线候选、约束列表和 Adapter 预览。地图上的我方班组、敌方单元和目标入口支持拖拽，拖拽后可在对象列表中看到更新后的 VBS 本地坐标。v0 拖拽不持久化回后端。

### 2.5 轻量会话记忆

系统使用 SQLite 保存演示会话：用户消息、约束补丁、候选路线和当前推荐路线会保存在 session 中。页面重新加载时会恢复最近会话；点击“重置会话”会清空当前 session 的历史约束。

该能力用于保留聊天脚本中的会话思路：有记忆、可恢复、可重置。当前不承诺生产级持久化。

### 2.6 HITL 与下层接口边界

HITL 节点目录与策略配置位于 `zhibing/hitl`。哪些节点允许人工确认、哪些节点必须人工确认、紧急情况下是否跳过，均应由配置决定，而不是写死在主流程中。

下层仿真系统需要提供 actor、enemy、building、weather、route、obstacle、task runtime 等数据接口。智兵系统通过 Scene Query Tools 调用这些能力；当前离线环境使用 mock/demo 数据。

### 2.7 VBS Adapter 预览

Adapter 预览展示的是上层准备下发给下层的结构化任务，包括 actor、waypoints、约束和当前路线。当前本机没有真实 VBS 引擎，所以不会调用真实仿真；真实部署时默认 HTTP，也支持配置为 socket。

## 3. 系统使用流程

### 3.1 用户进入前

1. 运维或实验人员准备条令、PDF、DOCX 和内置规则语料。
2. 系统运行 GraphRAG 可用性检查，确认本地文件能建库和查询。
3. 系统加载 HITL 策略、BT registry 和下层接口配置。
4. 系统加载 wargame 2D GeoJSON 地图资产。
5. VBS 下层配置场景和实验内容，或由默认 demo 场景一键部署。

### 3.2 用户进入后

1. 用户打开 Web UI。
2. 点击“一键部署”加载默认围剿演示场景。
3. 系统显示我方班组、敌方火力点、风险区、目标入口和候选路线。
4. 用户可拖拽敌我和目标对象，观察 VBS 坐标变化。
5. 用户输入任务或路径约束。
6. 系统先用固定寻路算法生成/更新候选路线。
7. LLM 约束解析门面把特殊要求变成结构化补丁。
8. 路径规划器重评分并选择推荐路线。
9. 可视化、聊天解释、约束列表和 Adapter 预览同步更新。
10. 用户可重置会话，从无历史约束状态重新演示。

## 4. 演示案例说明

### 4.1 案例设定

现在用户已经完成了注册，登录进入系统，在 VBS 引擎中配置好了场景和实验内容：五名 AI 士兵要前往地图上的某个建筑内开展围剿任务。

在 v0 演示中，五名 AI 士兵被抽象为一个我方班组整体 `blue_squad_1`。地图上有目标建筑入口、敌方火力点和大路风险区。系统不直接生成完整围剿战术，而是先完成可验证的“路径规划 + LLM 特殊约束 + 可视化同步 + Adapter 预览”闭环。

### 4.2 理想演示流程

1. 打开 `http://127.0.0.1:8090/`。
2. 点击“一键部署”，看到我方班组、敌方火力点、目标入口和候选路径。
3. 观察默认候选路线：大路距离短，小路风险低。
4. 输入“不要走大路，大路有狙击风险”。
5. 系统解析出 `avoid main_road`，推荐路线切换为 `route_side`。
6. 点击“重置会话”。
7. 输入“敌军不在营地，现在必须争分夺秒”。
8. 系统解析出 `ignore_zone enemy_1`，推荐路线回到 `route_main`。
9. 查看右侧 Adapter 预览，确认 waypoints 与地图高亮路线一致。

## 5. 真实测试结果

以下结果均为本轮在 `blueforce` 环境中真实运行得到，不是杜撰。

### 5.1 依赖验证

命令：

```powershell
& "C:\Users\22646\miniconda3\envs\blueforce\python.exe" -c "import django, yaml, openai, docx, pypdf; print('deps-ok')"
```

输出：

```text
deps-ok
```

本轮曾发现 `python-docx` 缺失，已在 `blueforce` 中安装 `python-docx 1.2.0`、`pypdf 6.13.3` 和传递依赖 `lxml 6.1.1`。

### 5.2 重点闭环单元测试

命令：

```powershell
& "C:\Users\22646\miniconda3\envs\blueforce\python.exe" -m unittest zhibing.tests.test_demo_scenario zhibing.tests.test_path_planner zhibing.tests.test_constraint_llm zhibing.tests.test_session_memory zhibing.tests.test_scene_route_tools zhibing.tests.test_visualization_projection zhibing.tests.test_command_ui_api zhibing.tests.test_graphrag_usability zhibing.tests.test_three_layer_alignment -q
```

输出摘要：

```text
Ran 23 tests in 7.322s
OK
```

### 5.3 全量测试

命令：

```powershell
& "C:\Users\22646\miniconda3\envs\blueforce\python.exe" -m unittest discover -s zhibing\tests -q
```

输出摘要：

```text
Ran 52 tests in 10.095s
OK
```

### 5.4 Django 配置检查

命令：

```powershell
& "C:\Users\22646\miniconda3\envs\blueforce\python.exe" zhibing\web\manage.py check
```

输出：

```text
System check identified no issues (0 silenced).
```

### 5.5 首页 HTTP 冒烟

命令：

```powershell
curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8090/
```

输出：

```text
200
```

### 5.6 `/api/demo-scene` 冒烟

命令使用 Python 标准库访问本地服务，输出摘要：

```json
{
  "friendly": "blue_squad_1",
  "enemies": 1,
  "routes": 2,
  "selected": "route_side"
}
```

说明：本次查询时最近 session 中保留了“大路风险”约束，因此推荐路线为 `route_side`。如果需要回到无约束默认状态，应先点击“重置会话”。

### 5.7 大路狙击风险约束测试

请求内容：

```text
不要走大路，大路有狙击风险
```

真实返回摘要：

```json
{
  "constraint": {
    "action": "avoid",
    "target_type": "road_class",
    "target_id": "main_road",
    "weight_delta": 200.0,
    "reason": "用户指出大路存在狙击或暴露风险"
  },
  "selected": "route_side",
  "route0": "route_side",
  "labels0": ["side_path", "side_path", "side_path"],
  "explanation": "推荐 route_side：距离 1064 米，风险 15，标签 side_path、side_path、side_path。"
}
```

结论：用户特殊约束被正确解析为规避大路，推荐路线切换到小路。

### 5.8 争分夺秒约束测试

请求内容：

```text
敌军不在营地，现在必须争分夺秒
```

真实返回摘要：

```json
{
  "constraint": {
    "action": "ignore_zone",
    "target_type": "enemy_zone",
    "target_id": "enemy_1",
    "weight_delta": -80.0,
    "reason": "用户要求降低敌方营地区域对路径的影响并优先时间",
    "priority": "time"
  },
  "selected": "route_main",
  "route0": "route_main",
  "labels0": ["main_road", "main_road"],
  "explanation": "推荐 route_main：距离 900 米，风险 0，标签 main_road、main_road。"
}
```

结论：用户新的战术假设被正确转为忽略敌方区域影响，算法重新评分后选择最短大路。

## 6. 当前限制

- 当前没有真实 VBS 引擎，HTTP/socket 下层接口只完成上层契约、mock 和 Adapter 预览。
- 当前 LLM 约束解析使用 deterministic fallback，live LLM、nano 模型和视觉模型测试均需先征得用户同意。
- 拖拽部署在 v0 中不持久化回后端。
- 编号选择候选路线的持久化流程尚未实现；当前已具备路线解释和重新输入约束的流程。
- GraphRAG 官方 quickstart 未自动执行，因为它涉及安装和 LLM 成本；本地 DOCX/PDF 可用性已通过离线测试覆盖。