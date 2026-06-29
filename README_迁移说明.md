# 智兵决策系统迁移包说明

本目录是从原始工作区整理出的干净迁移包，用于搬迁、交付或在新机器上复现当前 v0 演示系统。

## 包含内容

- `zhibing/`：智兵决策系统主代码，包括决策层、GraphRAG、HITL、VBS Adapter、场景工具、寻路、可视化 Web UI、测试与地图资产。
- `docs/`：superpowers 规格与计划文档，便于追溯当前实现方案。
- `bt_examples/`：真实 VBS 行为树示例，用于下层行为树对照。
- `llm_call_extract/`：火山/OpenAI-compatible LLM 调用示例与配置参考。
- `test_files/`：GraphRAG 可用性测试使用的 DOCX/PDF 文件。
- `requirements-blueforce.txt`：当前迁移建议依赖。
- `启动与演示说明.md`：启动、部署、演示路径说明。
- `ZHIBING_SYSTEM_PLAN.md`：原始总体设计计划。
- `llm_migration_client.py` / `llm_migration_config.example.json`：本地测试与迁移后 LLM 调用方式示例。

## 未包含内容

- `.git/`、`.codex/`、`.agents/`：本机工作区/代理元数据，不属于系统迁移内容。
- `__pycache__/` 和 `.pyc`：Python 缓存文件，可由目标环境重新生成。
- `zhibing_session_memory.sqlite3`：v0 演示会话记忆库，搬迁时建议重新生成，避免携带旧会话约束。
- 旧压缩包或临时包目录。

## 推荐启动

```powershell
cd <迁移包目录>
conda create -n zhibing python=3.12 -y
conda activate zhibing
pip install -r requirements-blueforce.txt
python zhibing\web\manage.py runserver 127.0.0.1:8090
```

浏览器访问：

```text
http://127.0.0.1:8090/
```

## 推荐验证

```powershell
python -m unittest discover -s zhibing\tests -q
python zhibing\web\manage.py check
```

## 迁移注意

- 官方 GraphRAG quickstart 和 live LLM 测试可能产生网络与模型费用，运行前需要确认代理、模型和成本。
- 当前系统没有真实 VBS 引擎；下层仿真系统需按 `zhibing/docs/lower_simulation_interface.md` 实现 HTTP 或 socket 接口。
- 当前 v0 的拖拽部署不持久化回后端，主要用于演示和人工调整。