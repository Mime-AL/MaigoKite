# NanamiGopher 安装指南

欢迎使用 NanamiGopher！本指南将帮助您完成产品的安装与首次启动。

---

## 目录

1. [系统要求](#系统要求)
2. [Electron 桌面端安装](#electron-桌面端安装)
3. [开发环境搭建](#开发环境搭建)
4. [首次启动流程](#首次启动流程)
5. [常见问题排查](#常见问题排查)

---

## 系统要求

### 最低配置

| 项目 | 最低要求 | 推荐配置 |
|------|----------|----------|
| 操作系统 | macOS 12+ / Windows 10+ / Ubuntu 20.04+ | macOS 14+ / Windows 11 / Ubuntu 22.04+ |
| CPU | 双核 2.0 GHz | 四核 2.5 GHz 或以上 |
| 内存 | 4 GB | 8 GB 或以上 |
| 磁盘空间 | 2 GB 可用空间 | 5 GB 可用空间 |

### 网络要求

- 首次启动需要联网以下载依赖和验证许可证
- 若使用云端模型（OpenAI 等），需保持网络连接
- 支持完全离线运行（仅使用本地模型和工具）

---

## Electron 桌面端安装

NanamiGopher 提供跨平台的 Electron 桌面客户端，支持 macOS、Windows 和 Linux。

### macOS

#### 方法一：App Store（如有上架）

在 Mac App Store 搜索 "NanamiGopher" 并下载安装。

#### 方法二：DMG 安装包

1. 从官方发布页面下载最新版本的 `.dmg` 文件
2. 双击打开下载的 DMG 文件
3. 将 NanamiGopher 图标拖入 Applications 文件夹
4. 首次启动时，由于未经过 Apple 公证，您可能需要在 **系统设置 > 隐私与安全性** 中点击"仍要打开"
5. 启动应用并完成初始化向导

#### 方法三：Homebrew

```bash
brew install --cask nanamigopher
```

### Windows

1. 从官方发布页面下载最新版本的 `.exe` 安装程序
2. 双击运行安装程序
3. 按照安装向导提示完成安装
4. 如果 Windows SmartScreen 拦截了安装，请点击"更多信息" > "仍要运行"
5. 安装完成后，从桌面快捷方式启动 NanamiGopher

### Linux

#### Debian / Ubuntu

1. 从官方发布页面下载最新版本的 `.deb` 文件
2. 在终端中执行：

```bash
sudo dpkg -i nanamigopher_*.deb
sudo apt-get install -f  # 解决依赖问题
```

#### Fedora / RHEL

1. 从官方发布页面下载最新版本的 `.rpm` 文件
2. 在终端中执行：

```bash
sudo dnf install nanamigopher-*.rpm
```

#### AppImage（通用 Linux）

1. 从官方发布页面下载最新版本的 `.AppImage` 文件
2. 赋予执行权限：

```bash
chmod +x NanamiGopher-*.AppImage
```

3. 双击运行或通过终端启动：

```bash
./NanamiGopher-*.AppImage
```

---

## 开发环境搭建

如果您希望从源码构建或参与开发，请按以下步骤搭建环境。

### 前提条件

| 工具 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Go | 1.21 | 1.22+ |
| Python | 3.10 | 3.11+ |
| Node.js | 18 LTS | 20 LTS |
| pnpm | 8.x | 9.x |
| Git | 2.30+ | 最新稳定版 |

### 步骤一：安装 Go

```bash
# macOS
brew install go

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install golang-go

# Windows
# 从 https://go.dev/dl/ 下载安装程序
```

验证安装：

```bash
go version
```

### 步骤二：安装 Python

```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv

# Windows
# 从 https://www.python.org/downloads/ 下载安装，注意勾选 "Add to PATH"
```

验证安装：

```bash
python3 --version
pip3 --version
```

### 步骤三：安装 Node.js 和 pnpm

```bash
# 推荐使用 nvm 管理 Node.js 版本
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# 重启终端后执行：
nvm install 20
nvm use 20

# 安装 pnpm
npm install -g pnpm
```

验证安装：

```bash
node --version
pnpm --version
```

### 步骤四：克隆仓库并安装依赖

```bash
# 克隆仓库
git clone https://github.com/your-org/nanamigopher.git
cd nanamigopher

# 安装后端依赖（Go）
cd api-gateway
go mod download

# 安装 Agent Core 依赖（Python）
cd ../agent-core
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 安装前端依赖（Vue 3 + Vite）
cd ../../frontend
pnpm install
```

### 步骤五：配置环境变量

创建 `.env` 文件：

```bash
# API Gateway
API_GATEWAY_PORT=8080
AGENT_CORE_URL=http://localhost:8081

# 模型配置（按需填写）
OPENAI_API_KEY=your-api-key-here
EMBEDDING_MODEL=bge-m3

# 存储配置
DATA_DIR=./data
```

### 步骤六：启动开发服务器

```bash
# 终端 1：启动 API Gateway
cd api-gateway
go run cmd/server/main.go

# 终端 2：启动 Agent Core
cd agent-core
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8081

# 终端 3：启动前端开发服务器
cd frontend
pnpm dev
```

访问 `http://localhost:5173` 即可使用开发版本。

---

## 首次启动流程

### 桌面端首次启动

1. **欢迎页面**：启动 NanamiGopher 后，您将看到欢迎页面，展示产品概述和新手指引
2. **账户设置**（可选）：如需同步功能，请登录您的 NanamiGopher 账户；如不需要可跳过
3. **模型配置向导**：
   - 系统会自动检测您是否配置了 OpenAI API Key
   - 如未配置，默认使用本地 BGE-M3 Embedding 模型
   - 您可以在此阶段选择使用的 Chat Model
4. **权限模式选择**：
   - 系统会引导您选择一个初始权限模式（建议新手选择 Manual）
   - 您可以在后续随时在设置中修改
5. **数据目录确认**：
   - 系统会显示默认数据存储位置
   - 您可以更改为其他目录
6. **完成**：点击"开始使用"进入主界面

### 主界面概览

首次进入主界面后，您将看到三栏布局：

- **左侧导航栏**：包含总览、新建对话、搜索、定时任务、浏览器、包管理、Skill 管理、每日回顾、长期计划、归档、设置等功能入口
- **中间工作区**：AI 对话与任务执行的核心区域
- **右侧文件管理器**：显示当前工作区的文件和目录结构（默认收起）

> 提示：使用 `Ctrl+B` 切换左侧导航栏，使用 `Ctrl+Shift+F` 切换右侧文件管理器。

---

## 常见问题排查

### 应用无法启动

**症状**：双击图标后无任何反应，或闪退。

**解决方法**：

1. 检查系统是否满足最低配置要求
2. 查看日志文件：
   - macOS：`~/Library/Logs/NanamiGopher/logs.log`
   - Windows：%APPDATA%\NanamiGopher\logs.log
   - Linux：~/.config/NanamiGopher/logs.log
3. 尝试以管理员/超级用户身份运行
4. 重新下载安装包并重新安装

### 模型调用失败

**症状**：对话发送后无响应，或提示模型调用错误。

**解决方法**：

1. 确认 API Key 是否正确配置（设置 > 模型配置）
2. 检查网络连接是否正常
3. 确认模型服务是否可用（可访问对应服务商的状态页面）
4. 尝试切换到本地模型测试
5. 查看日志中的详细错误信息

### 数据存储异常

**症状**：对话记录丢失、搜索功能异常。

**解决方法**：

1. 确认数据存储目录有写入权限
2. 检查磁盘空间是否充足
3. 尝试手动备份并重建数据库：
   ```bash
   # 停止应用后执行
   cp -r ~/.local/share/nanamigopher/data ~/.local/share/nanamigopher/data.bak
   rm -rf ~/.local/share/nanamigopher/data
   # 重新启动应用
   ```

### 性能问题

**症状**：应用卡顿、响应缓慢。

**解决方法**：

1. 减少同时打开的对话数量
2. 关闭不必要的 Skill
3. 调整权限模式为更保守的设置（如 Plan 模式）
4. 检查是否有长时间运行的后台任务
5. 在设置中清理缓存数据

### 快捷键不生效

**症状**：`Ctrl+B` 或 `Ctrl+Shift+F` 没有切换侧边栏。

**解决方法**：

1. 确认快捷键未被其他应用程序占用
2. 在设置 > 快捷键 中检查并重新绑定
3. 尝试使用菜单栏中的对应命令

### 获取帮助

如果以上方法无法解决问题，请通过以下方式获取帮助：

- 提交 Issue：[GitHub Issues](https://github.com/your-org/nanamigopher/issues)
- 社区论坛：[NanamiGopher Community](https://community.nanamigopher.dev)
- 电子邮件：support@nanamigopher.dev
