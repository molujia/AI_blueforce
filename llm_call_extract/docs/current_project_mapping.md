# 与当前主项目的对应关系

这个独立包抽取自当前项目的 LLM 调用链路，但去掉了邮件业务、RAG、SOP、数据库、日志等非必要依赖。

## 主项目源码对应

- `src/aftersales_agent/agents/seed_chat_model.py`
  - 对应本包：`llm_client.py` 的 `SeedChatModel`、`SeedChatSession`、`LLMResponse`
  - 能力：OpenAI-compatible 调用、Responses API、Chat Completions API、图片输入、usage 统计、Responses 会话记忆。

- `src/aftersales_agent/agents/model_router.py`
  - 对应本包：`llm_client.py` 的 `ModelRouter`
  - 能力：读取 seed model 目录，为不同 task 选择不同模型，解析 provider/key/model 参数。

- `src/aftersales_agent/config.py`
  - 对应本包：`llm_client.py` 的 `Settings`
  - 能力：读取 YAML 配置、环境变量、代理配置。

- `configs/seed_models.yaml`
  - 对应本包：`configs/seed_models.yaml`
  - 能力：管理 OpenAI、火山 Ark 和其它 OpenAI-compatible 模型。

- `configs/agent_seed_models.yaml`
  - 对应本包：`configs/agent_seed_models.yaml`
  - 能力：为 `triage_extract`、`sop_workflow_analysis`、`reply_generation` 等 task 指定 seed model。

## 本包没有抽取的内容

- 邮件工单解析、SOP 节点选择、回复生成 prompt。
- RAG、库存查询、附件拉取、日志系统。
- FastAPI 服务和数据库。

这些内容不是“LLM 调用”本身。需要把本包接回业务系统时，只要调用：

```python
from llm_client import ModelRouter

router = ModelRouter()
model = router.get_chat_model("reply_generation")
response = model.invoke([
    {"role": "system", "content": "Return strict JSON only."},
    {"role": "user", "content": "Return JSON with key status."},
])
print(response.content)
```

需要会话记忆时：

```python
session = router.begin_session("sop_workflow_analysis")
session.invoke([{"role": "user", "content": "Remember marker ABC123."}])
response = session.invoke([{"role": "user", "content": "What marker did I provide?"}])
print(response.content)
```
