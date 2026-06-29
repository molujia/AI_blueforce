# LLM 调用独立抽取包

这个文件夹从当前邮件自动回复项目中抽取了 LLM 调用相关能力，目标是：只需要填写 API key 和模型名，就可以独立运行文本、多模态图片、会话记忆三类调用。

## 包含内容

- `llm_client.py`：独立的 OpenAI/OpenAI-compatible 调用封装，支持 Responses API、Chat Completions API、图片输入、JSON 输出格式、会话记忆。
- `configs/seed_models.yaml`：供应商和可选 seed model 目录。
- `configs/agent_seed_models.yaml`：为不同 task/agent 选择 seed model。
- `configs/secrets.example.yaml`：密钥填写模板。
- `examples/text_call.py`：文本调用示例。
- `examples/image_call.py`：图片/多模态调用示例。
- `examples/session_memory.py`：会话记忆示例。
- `docs/configuration.md`：配置说明。
- `docs/current_project_mapping.md`：与当前主项目源码的对应关系。

## 快速开始

1. 安装依赖：

```powershell
pip install -r requirements.txt
```

2. 复制密钥模板：

```powershell
Copy-Item configs\secrets.example.yaml configs\secrets.local.yaml
```

3. 在 `configs/secrets.local.yaml` 中填写密钥，例如：

```yaml
ark_api_key: "你的火山 Ark key"
openai_api_key: "你的 OpenAI key"
```

也可以不用 `secrets.local.yaml`，直接设置环境变量：

```powershell
$env:ARK_API_KEY="你的火山 Ark key"
$env:OPENAI_API_KEY="你的 OpenAI key"
```

4. 按需修改 `configs/seed_models.yaml` 中的 `model_name`，以及 `configs/agent_seed_models.yaml` 中每个 task 使用的 `seed_model`。

5. 运行示例：

```powershell
python examples\text_call.py --task triage_extract --prompt "Return JSON: what is 1+1?"
python examples\session_memory.py --task sop_workflow_analysis
python examples\image_call.py --task reply_generation --image C:\path\to\image.png --prompt "Describe this image in JSON."
```

## 最少需要改哪里

通常只需要改两个文件：

- `configs/secrets.local.yaml`：填写 key。
- `configs/seed_models.yaml`：填写或替换模型名。

如果要让不同 agent/task 使用不同模型，再改：

- `configs/agent_seed_models.yaml`

## 支持的供应商

默认配置里已经放了两类：

- OpenAI：`https://api.openai.com/v1`
- 火山 Ark：`https://ark.cn-beijing.volces.com/api/v3`

其它 OpenAI-compatible 供应商也可以照着 `volcengine_ark` 增加 provider。

## 注意

- 本包不包含真实密钥。
- 火山 Ark 示例默认走 `responses` API，与当前主项目保持一致。
- 如果模型不支持图片，不要把它选给 `reply_generation` 的图片示例。
