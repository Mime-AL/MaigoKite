# NanamiGopher 智能体核心

这是 NanamiGopher 的 Python 核心服务包。从仓库根目录启动：

```bash
PYTHONPATH=python .venv/bin/python -m agent.main run --config config/config.dev.yaml
```

依赖安装和解释器要求见 [开发指南](../docs/development/DevelopmentGuide.md)，核心运行边界见 [智能体运行时设计](../docs/design/AgentRuntime.md)，模型设置见 [配置指南](../docs/user-guide/Configuration.md)。

默认执行路径仍为 legacy；LangGraph 文件/技能路径需要显式启用临时迁移开关。
