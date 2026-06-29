# 配置说明

## 1. 供应商配置：`configs/seed_models.yaml`

`providers` 定义供应商公共参数：

```yaml
providers:
  volcengine_ark:
    api: responses
    base_url: https://ark.cn-beijing.volces.com/api/v3
    api_key_secret: ark_api_key
    api_key_env: ARK_API_KEY
```

关键字段：

- `api`：`responses` 或 `chat_completions`。
- `base_url`：OpenAI 或 OpenAI-compatible 服务地址。
- `api_key_secret`：从 `configs/secrets.local.yaml` 读取的 key 名。
- `api_key_env`：环境变量名。
- `tools`：Responses API 工具列表。没有工具就填 `[]`。

## 2. Seed model 目录：`configs/seed_models.yaml`

`seed_models` 定义可选择的模型：

```yaml
seed_models:
  volc_multimodal:
    provider: volcengine_ark
    model_alias: volc_multimodal
    model_name: ep-20260615114505-247zc
    supports_vision: true
    max_output_tokens: 3000
```

关键字段：

- `provider`：指向上面的供应商。
- `model_name`：真实 API 模型名或 endpoint id。
- `supports_vision`：文档标记，代码不会强行校验。
- `max_output_tokens`：默认最大输出长度，可被 task 覆盖。

## 3. Agent/task 模型选择：`configs/agent_seed_models.yaml`

不同任务可以选择不同 seed model：

```yaml
tasks:
  triage_extract:
    seed_model: volc_text
    temperature: 0
    response_format: json_object

  reply_generation:
    seed_model: volc_multimodal
    temperature: 0.2
    response_format: json_object
```

关键字段：

- `seed_model`：引用 `seed_models.yaml` 里的模型 id。
- `temperature`：覆盖模型默认温度。
- `max_output_tokens`：覆盖模型默认最大输出。
- `response_format: json_object`：请求 JSON 对象输出。

## 4. 密钥配置：`configs/secrets.local.yaml`

从 `configs/secrets.example.yaml` 复制：

```yaml
ark_api_key: "你的火山 Ark key"
openai_api_key: "你的 OpenAI key"
```

也可以用环境变量：

- `ARK_API_KEY`
- `OPENAI_API_KEY`

## 5. 代理配置

如需代理：

```yaml
http_proxy: "http://127.0.0.1:7897"
https_proxy: "http://127.0.0.1:7897"
```

或使用环境变量 `HTTP_PROXY` / `HTTPS_PROXY`。

## 6. 增加新的火山模型

只需要在 `seed_models.yaml` 增加一个模型：

```yaml
seed_models:
  my_new_ark_model:
    provider: volcengine_ark
    model_alias: my_new_ark_model
    model_name: 你的模型名或 endpoint id
    supports_vision: true
    max_output_tokens: 3000
    tools: []
```

然后在 `agent_seed_models.yaml` 中选择它：

```yaml
tasks:
  reply_generation:
    seed_model: my_new_ark_model
```
