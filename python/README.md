# MaigoKite 智能体核心

这是 MaigoKite 的 Python 后端包，FastAPI 与 AgentCore 在同一进程中运行。从仓库根目录启动：

```bash
PYTHONPATH=python .venv/bin/python -m agent.main run --config config/config.dev.yaml
```

依赖安装和解释器要求见 [开发指南](../docs/development/DevelopmentGuide.md)，核心运行边界见 [智能体运行时设计](../docs/design/AgentRuntime.md)，模型设置见 [配置指南](../docs/user-guide/Configuration.md)。

依赖只在仓库根 `pyproject.toml` / `uv.lock` 维护，`python/` 不再是独立安装项目。

聊天、工具调用与审批续接统一使用 LangChain create_agent / LangGraph。旧自研执行链和迁移开关已删除；验收范围见 [交付路线与状态](../docs/project/Roadmap.md)。
