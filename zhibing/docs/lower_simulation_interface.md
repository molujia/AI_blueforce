# 下层仿真系统接口说明

本文档面向下层仿真系统工程师。智兵决策系统只实现上层 LLM 决策层、任务网关和 VBS Adapter；下层需要实现 VBS 仿真引擎、行为树运行时，以及 HTTP 或 socket 返回封装。

## 1. 下层必须提供什么

下层必须提供三类能力：

- 场景数据接口：actor、building、enemy、weather、route、obstacle 等实时或准实时数据。
- 任务运行接口：接收上层编译后的 SQF 调用序列，装载 BT，写入黑板变量，驱动 VBS/BT runtime。
- 状态返回接口：返回 task status、active node、node path、return code、进度、错误和建议动作。

`Scene Query Tools` 是智兵决策系统自己实现的工具门面；它会调用下层数据接口。`StatusQueryRequest`、`TaskSubmitRequest`、`TaskStatusResponse` 是上层和下层共同遵守的协议对象。

## 2. 默认 HTTP 接口

默认 transport 是 HTTP。建议端点如下：

- `POST /tasks/submit`：提交 `SubmitSQFPlan`。
- `POST /tasks/query`：提交 `StatusQueryRequest`，返回 `TaskStatusResponse`。
- `GET /actors/{actor_id}/state`：查询实体位置、生命值、姿态和编组状态。
- `POST /entities/nearby`：按中心点、半径、阵营和类型查询附近实体。
- `POST /buildings/query`：查询建筑物、房间、入口和可通行信息。
- `GET /buildings/{building_id}/entrances`：查询建筑入口坐标。
- `POST /enemy/query`：查询敌情。
- `GET /environment/weather`：查询天气、能见度和风况。
- `POST /routes/plan`：返回从起点到终点的可行路径。
- `GET /obstacles/{segment_id}`：查询障碍或阻断原因。

## 3. 可选 Socket 接口

socket 模式使用一行一个 JSON envelope：

```json
{"message_id":"uuid","message_type":"TASK_QUERY","payload":{"task_id":"task-id"}}
```

`message_type` 取值为 `TASK_SUBMIT`、`TASK_QUERY`、`TASK_STATUS`、`ACK`、`ERROR`。payload 与 HTTP 请求体保持一致。

## 4. Scene Query 依赖数据接口

上层会把 `get_actor_state`、`route_plan`、`get_building_entrances` 等工具暴露给决策层。下层不需要实现这些 Python 函数，但必须提供其依赖的数据能力。所有坐标必须是显式 frame 的对象，不允许裸数组作为协议数据。

## 5. 任务提交与状态查询

`SubmitSQFPlan` 示例：

```json
{
  "task_id": "task-uuid",
  "request": {"request_id": "request-uuid"},
  "sqf_statements": ["_status = loadBTSet \"CgfControl.btset\";"]
}
```

`StatusQueryRequest` 示例：

```json
{
  "request_id": "request-uuid",
  "session_id": "session-uuid",
  "task_id": "task-uuid",
  "query_fields": ["task_status", "actor_position", "active_node", "last_return_code"]
}
```

## 6. TaskStatusResponse 字段

下层返回至少包含：

- `session_id`
- `task_id`
- `status`: `ACKED`、`RUNNING`、`WAIT_UPPER`、`SUCCEEDED`、`FAILED`、`ABORTED` 或 `TIMEOUT`
- `actor`: type、id、position
- `bt_runtime`: bt_name、active_node、node_path
- `progress`: distance_to_goal_m、elapsed_seconds、estimated_remaining_seconds、progress_rate_mps
- `return_code`
- `error`
- `suggested_action`

## 7. active_node / node_path / return_code 规范

`active_node` 使用下层 BT runtime 当前节点名。`node_path` 从根节点到当前节点顺序排列。`return_code` 用稳定枚举表达任务结论或失败原因，例如 `SUCCESS`、`WAIT_UPPER`、`UNREACHABLE`、`SUBTASK_FAILED`、`BT_LOAD_ERROR`、`BT_NOT_FOUND`、`ACTOR_NOT_FOUND`、`PARAM_ERROR`。

## 8. 突发遇敌与局部避险责任

突发遇敌、局部避险、贴地运动规避等紧急动作必须由下层 VBS/BT runtime 本地处理，不应阻塞等待上层 HITL。下层可以在状态返回中报告 `EMERGENCY_CONTACT` 或 `LOCAL_AVOIDANCE` 事件，供上层解释、复盘或后续重规划。

## 9. 坐标协议

协议 JSON 中的坐标必须使用对象：

```json
{"frame":"VBS_LOCAL_XYZ","x":1000.0,"y":500.0,"z":0.0}
```

或：

```json
{"frame":"WGS84_LATLON_ALT","lat":40.0,"lon":116.0,"alt":120.0}
```

只有智兵决策系统的 SQF compiler 可以把坐标对象转换为 VBS 原生数组语法。

## 10. 最小联调案例

1. 上层提交 `GrpMove` 到 `p_4`，目标坐标为 `VBS_LOCAL_XYZ {x:1000,y:500,z:0}`。
2. 下层返回 `ACKED`。
3. 上层轮询状态。
4. 下层返回 `SUCCEEDED`、`return_code=SUCCESS`、actor.position 等于或接近目标点。
5. 若路径阻断，下层返回 `FAILED`、`return_code=UNREACHABLE`、`suggested_action=REPLAN_ROUTE`。
