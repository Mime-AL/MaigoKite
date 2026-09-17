# NanamiGopher 安装指南

> **状态**：Current
> **最后核验**：2026-09-14

## 1. 运行形态与就绪度

架构定义三种运行形态：

- 桌面模式：Electron 启动本地 Gateway 与 Agent Core。
- 开发模式：分别运行 Go、Python 和 Vue。
- 服务器模式：使用 Docker/Kubernetes，见 [Production](../deployment/Production.md)。

当前仓库尚未提供正式发布包；源码开发模式和 Electron 开发模式已经具备可验证入口，服务器发布仍属于 Planned。

## 2. 开发环境要求

- Go、Python、Node.js/npm 的版本以仓库模块配置和 CI 为准。
- 可选本地模型服务按 [Configuration](Configuration.md) 配置。
- 第三方模型需要对应 CredentialProvider 中的凭证。

## 3. 从源码启动

```bash
git clone <repository-url>
cd NanamiGopher

cd gateway
go mod download

cd ../python
python3 -m venv ../.venv
source ../.venv/bin/activate
python -m pip install -e '.[dev]'

cd ../web
npm install
```

安装完成后可从根目录启动：

```bash
make dev
```

该命令启动 Python gRPC Agent Core、Go Gateway 和 Vue。也可在 `web/` 执行 `npm run electron:dev`，由 Electron Supervisor 启动本地运行时。云模型名称在 `models.chat.default` 配置；对应 API Key 从环境或系统密钥环提供，不写入 YAML。

## 4. 首次启动目标流程

1. 系统创建或选择 Personal Workspace。
2. 配置本地模型或添加云模型凭证引用。
3. 选择权限模式；模式含义见 [Configuration](Configuration.md)。
4. 验证 Gateway、Agent Core、数据库和模型健康状态。

## 5. 故障定位

- 进程无法启动：检查运行配置、端口和子进程日志。
- Python 不可用：检查 gRPC health，而不是假设存在 HTTP `/health`。
- 模型不可用：检查 Provider endpoint、凭证引用和网络策略。
- 数据异常：不要手工复制活动 SQLite 文件，按 [Backup](../ops-security/Backup.md) 恢复。
- 详细开发环境见 [Environment](../development/Environment.md)。
