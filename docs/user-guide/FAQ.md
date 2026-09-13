# NanamiGopher 常见问题

本文档汇总了用户在使用过程中最常遇到的问题及其解决方案。如果您没有找到答案，请参阅 [安装指南](./Installation.md) 或联系技术支持。

---

## 目录

1. [基础使用问题](#基础使用问题)
2. [工具使用问题](#工具使用问题)
3. [Skill 相关问题](#skill-相关问题)
4. [配置相关问题](#配置相关问题)
5. [性能相关问题](#性能相关问题)
6. [安全与隐私问题](#安全与隐私问题)
7. [故障排查](#故障排查)

---

## 基础使用问题

### Q1：如何开始与 NanamiGopher 对话？

在主界面的中间工作区底部，输入框中输入您的问题或指令，然后按 `Ctrl+Enter`（或 `Cmd+Enter` on macOS）发送。NanamiGopher 会根据您的问题和配置的权限模式，自动选择合适的工具来完成任务。

### Q2：如何新建对话？

- **快捷键**：按 `Ctrl+N`
- **菜单**：点击左侧导航栏中的"新建对话"按钮
- **右键**：在工作区标签栏右键点击，选择"新建对话"

每次新建对话都会创建一个独立的上下文环境，之前的对话记录不会互相干扰。

### Q3：如何切换模型？

- **快速切换**：按 `Ctrl+P` 打开快速切换面板，输入模型名称进行选择
- **设置面板**：进入 设置 > 模型配置，在下拉列表中选择目标模型
- **命令行**：
  ```bash
  nanamigopher models set-chat gpt-4o
  ```

切换模型后，新对话会使用选定的模型，已有对话不受影响。

### Q4：左侧/右侧导航栏不见了，如何找回？

- 左侧导航栏：按 `Ctrl+B` 切换显示/隐藏
- 右侧文件管理器：按 `Ctrl+Shift+F` 切换显示/隐藏
- 也可以在设置 > 界面 中配置默认显示状态

### Q5：如何查看我的对话历史？

点击左侧导航栏中的"归档"，可以浏览所有历史对话。您也可以使用"搜索"功能，通过关键词查找特定对话。

---

## 工具使用问题

### Q6：如何查看当前可用的工具？

NanamiGopher 在对话过程中会自动显示正在使用的工具。您也可以：

- 在设置面板中查看已启用的工具列表
- 使用命令行：
  ```bash
  nanamigopher tools list
  ```

Phase 1 支持的 10 个工具包括：`file_read`、`file_write`、`file_edit`、`bash`、`web_search`、`web_fetch`、`glob`、`grep`、`todo_write`、`sleep`。

### Q7：如何授权工具执行操作？

工具权限取决于您设置的权限模式：

- **Manual 模式**：每次工具调用前都会弹出确认对话框，您需要点击"允许"或"拒绝"
- **AcceptEdits 模式**：文件读写自动批准，其他操作仍需确认
- **Plan 模式**：不执行任何实际操作，仅生成计划
- **Auto 模式**：除 L5 级别的关键操作外，全部自动执行

您也可以单独调整每个工具的权限级别（设置 > 权限 > 工具分级）。

### Q8：工具执行失败了怎么办？

工具执行失败时，NanamiGopher 会在对话中显示错误信息。常见情况及解决方法：

| 错误类型 | 可能原因 | 解决方法 |
|----------|----------|----------|
| 文件读取失败 | 文件不存在或权限不足 | 检查文件路径，确认有读取权限 |
| Bash 超时 | 命令执行时间过长 | 缩短命令范围，或增加 timeout 配置 |
| 网页搜索失败 | 网络问题或搜索引擎不可用 | 检查网络，或切换搜索引擎 |
| Glob/Grep 无结果 | 搜索范围不对 | 检查搜索路径和过滤条件 |

查看详细错误日志：设置 > 诊断 > 查看日志。

### Q9：如何限制工具的使用范围？

通过配置工具白名单和黑名单：

1. 在 `config.yaml` 中设置 `tools.whitelist`
2. 或在设置面板中：设置 > 工具 > 工具白名单
3. 也可以针对特定工具配置 `allowed_commands` 和 `blocked_commands`

### Q10：todo_write 工具如何使用？

todo_write 工具允许您管理和追踪任务进度。在对话中直接描述任务即可，NanamiGopher 会自动维护任务列表。您也可以：

- 点击左侧导航栏的"定时任务"查看和管理任务
- 使用命令行：
  ```bash
  nanamigopher todo list          # 查看所有任务
  nanamigopher todo add "完成文档编写"
  nanamigopher todo done <任务ID>
  ```

---

## Skill 相关问题

### Q11：如何安装 Skill？

**图形界面安装**：
1. 点击左侧导航栏中的"Skill 管理"
2. 点击"安装 Skill"按钮
3. 输入 Skill 的 Git 仓库地址或本地路径
4. 点击确认安装

**命令行安装**：
```bash
# 从 Git 仓库安装
nanamigopher skills install https://github.com/user/my-skill

# 从本地目录安装
nanamigopher skills install /path/to/skill-dir
```

### Q12：如何卸载 Skill？

**图形界面**：
1. 进入"Skill 管理"
2. 找到要卸载的 Skill，点击"卸载"

**命令行**：
```bash
nanamigopher skills uninstall <skill-name>
```

### Q13：如何自定义 Skill？

每个 Skill 本质上是一个 MCP Server，您可以通过以下方式自定义：

1. **修改 SKILL.md**：在 Skill 目录中找到 `SKILL.md` 文件，编辑触发条件、参数说明和使用示例
2. **添加自定义逻辑**：Skill 目录中可以包含脚本、配置文件等，根据您的 MCP Server 实现方式添加
3. **创建新 Skill**：
   ```bash
   nanamigopher skills create my-custom-skill
   # 然后在生成的目录中编辑 SKILL.md 和实现代码
   ```

### Q14：Skill 加载失败怎么办？

常见原因和解决方法：

- **SKILL.md 格式错误**：检查文件格式是否符合规范
- **MCP Server 启动失败**：确认依赖已安装，环境变量已正确配置
- **端口冲突**：检查是否有其他程序占用了 MCP Server 的通信端口
- **查看日志**：设置 > 诊断 > 查看日志，搜索 "skill" 关键字

### Q15：如何管理多个 Skill 之间的冲突？

当多个 Skill 都可能响应同一请求时，可以通过设置优先级来解决：

```yaml
skills:
  priority_order:
    - "git-helper"
    - "code-review"
```

优先级高的 Skill 会先被尝试调用。

---

## 配置相关问题

### Q16：如何修改配置？

有三种方式：

1. **图形界面**：设置面板中逐项修改，自动保存到 `config.yaml`
2. **直接编辑**：编辑 `config.yaml` 文件，修改后重启应用生效
3. **命令行**：
   ```bash
   nanamigopher config set models.chat.model_name gpt-4o
   nanamigopher config get permissions.mode
   ```

### Q17：如何恢复默认配置？

```bash
# 命令行方式
nanamigopher config reset

# 手动方式
# 删除或重命名现有配置文件，然后重新启动应用
mv ~/.local/share/nanamigopher/config/config.yaml ~/.local/share/nanamigopher/config/config.yaml.old
# 重新启动 NanamiGopher，会自动生成默认配置文件
```

### Q18：配置修改后如何立即生效？

- 在图形界面中修改配置后，通常即时生效
- 直接编辑 `config.yaml` 后，需要重启应用
- 部分配置（如模型切换）可以热更新，无需重启

### Q19：如何备份和恢复配置？

```bash
# 备份配置
tar czf config-backup-$(date +%Y%m%d).tar.gz ~/.local/share/nanamigopher/config/

# 恢复配置
tar xzf config-backup-YYYYMMDD.tar.gz -C ~/.local/share/nanamigopher/
```

### Q20：如何在多台设备间同步配置？

NanamiGopher 支持通过云同步功能在多设备间同步配置（需要登录账户）。也可以在每台设备上手动复制 `config.yaml` 文件。

---

## 性能相关问题

### Q21：如何优化响应速度？

1. **选择更快的模型**：在设置 > 模型配置 中选择延迟更低的模型
2. **减少并发 Skill**：降低 `skills.max_concurrent_skills` 的值
3. **调整权限模式**：Plan 模式或 Auto 模式可以减少等待确认的时间
4. **清理缓存**：设置 > 存储 > 清理缓存
5. **关闭不必要的工具**：在工具配置中禁用不常用的工具
6. **使用本地模型**：对于简单任务，使用本地模型可以避免网络延迟

### Q22：内存占用过高怎么办？

**症状**：应用运行一段时间后内存持续增长，系统变慢。

**解决方法**：

1. **重启应用**：最简单有效的方式，会释放所有缓存
2. **减少对话数量**：关闭不需要的对话标签页
3. **清理向量数据库**：
   ```bash
   nanamigopher storage cleanup-vectors
   ```
4. **调整 Embedding 批处理大小**：在配置中减小 `models.embedding.batch_size`
5. **禁用 ChromaDB**（如果不使用搜索功能）：
   ```yaml
   storage:
     chromadb:
       enabled: false
   ```
6. **监控内存**：设置 > 诊断 > 资源监控，查看各组件的内存占用

### Q23：如何提高搜索响应速度？

1. 确保 ChromaDB 已启用并正确配置
2. 增加 `models.embedding.batch_size` 以提高向量化效率
3. 定期执行 `nanamigopher storage optimize-chroma` 进行索引优化
4. 减少向量数据库中存储的历史数据量

### Q24：磁盘空间不足怎么办？

1. **清理旧对话**：设置 > 存储 > 清理历史对话
2. **压缩向量数据**：
   ```bash
   nanamigopher storage compact-vectors
   ```
3. **清理 Skill 缓存**：设置 > Skill 管理 > 清理缓存
4. **迁移数据目录**：将 `storage.data_dir` 指向空间更大的磁盘分区

---

## 安全与隐私问题

### Q25：我的数据安全吗？

NanamiGopher 采用本地优先的设计原则：

- **数据存储**：SQLite 和 ChromaDB 均存储在本地，不上传到云端
- **凭证管理**：支持使用系统密钥链（Keychain/Credential Manager）或加密文件存储 API Key
- **网络隔离**：可选的沙箱模式可以限制应用的网路访问
- **审计日志**：所有操作均有记录，可随时审查

### Q26：能否完全离线使用？

可以。NanamiGopher 支持完全离线运行：

1. 使用本地模型（如通过 Ollama 部署的 LLM）
2. 禁用 `web_search` 和 `web_fetch` 工具
3. 设置 `security.network.allow_outbound: false`

### Q27：API Key 如何管理更安全？

推荐的凭证存储方式（按安全性排序）：

1. **系统密钥链**（推荐）：使用操作系统提供的安全存储
   ```yaml
   security:
     credentials:
       storage: keychain
   ```
2. **加密文件**：NanamiGopher 内置加密，需设置主密码
   ```yaml
   security:
     credentials:
       storage: encrypted-file
   ```
3. **环境变量**：不存储，仅从环境变量读取
   ```yaml
   security:
     credentials:
       storage: env
   ```

避免将 API Key 明文写在 `config.yaml` 中。

### Q28：如何防止工具执行危险操作？

1. 使用 **Plan 模式**：仅生成计划，不执行任何操作
2. 配置 **命令黑名单**：在 `tools.bash.blocked_commands` 中添加禁止的命令
3. 启用 **沙箱模式**：设置为 `network-isolated` 或 `full`
4. 限制 **L5 级别工具权限**：在权限配置中将 `l5_critical.auto_approve` 设为 `false`

### Q29：如何审查工具的历史操作？

查看审计日志：

```bash
# 查看最近的审计日志
nanamigopher audit log --last 50

# 导出审计日志
nanamigopher audit export --output audit-report.json
```

也可以在设置面板中：设置 > 安全 > 审计日志。

---

## 故障排查

### Q30：应用启动失败怎么办？

按以下步骤排查：

1. **检查日志文件**：
   - macOS：`~/Library/Logs/NanamiGopher/logs.log`
   - Windows：%APPDATA%\NanamiGopher\logs.log
   - Linux：~/.config/NanamiGopher/logs.log

2. **常见启动问题**：
   - 缺少依赖：查看日志中的错误信息，安装缺失的依赖
   - 端口冲突：确认 8080 和 8081 端口未被占用
   - 权限不足：确保数据目录有读写权限

3. **重置状态**：
   ```bash
   nanamigopher doctor
   ```
   该命令会自动检测并修复常见的配置问题。

### Q31：连接超时怎么办？

**症状**：模型调用或工具执行时出现超时错误。

**解决方法**：

1. **增加超时时间**：在配置中调整 `timeout` 参数
   ```yaml
   models:
     chat:
       timeout: 120    # 增加到 120 秒
   tools:
     web_search:
       timeout: 30
     web_fetch:
       timeout: 60
   ```
2. **检查网络**：确认网络连接正常
3. **更换模型提供商**：如果当前提供商响应慢，切换到其他模型
4. **使用本地模型**：对于频繁调用，考虑部署本地模型以减少网络延迟

### Q32：模型调用失败怎么办？

**症状**：发送消息后收到错误提示，如 "API key invalid"、"Rate limit exceeded" 等。

**排查步骤**：

1. **确认 API Key 有效**：
   ```bash
   nanamigopher models test-connection
   ```
2. **检查模型配额**：登录模型提供商的控制台，确认 API 额度充足
3. **查看错误详情**：设置 > 诊断 > 错误日志，复制完整错误信息
4. **尝试切换模型**：换一个模型测试是否是特定模型的问题
5. **检查 Base URL**：如果使用自定义端点，确认地址正确

### Q33：对话发送后无响应？

1. 检查网络是否正常
2. 确认模型配置是否正确
3. 查看权限模式是否为 Plan 模式（此模式不会返回实际结果）
4. 检查是否有长时间运行的工具在执行
5. 尝试重启应用

### Q34：文件管理器无法显示文件？

1. 确认当前工作区路径是否正确（设置 > 工作区）
2. 检查目录权限
3. 尝试刷新文件管理器（右键点击 > 刷新）
4. 在配置中检查 `glob` 和 `grep` 工具的过滤规则是否过于严格

### Q35：如何获取详细诊断信息？

```bash
# 运行全面诊断
nanamigopher doctor --verbose

# 导出诊断报告
nanamigopher doctor export --output diagnosis.json
```

诊断报告包含系统信息、配置状态、网络连接、存储健康度等详细信息，提交 Issue 时附上此报告可以帮助快速定位问题。

---

## 仍然遇到问题？

如果您在上述 FAQ 中找不到答案，请通过以下方式联系我们：

- **GitHub Issues**：[提交 Issue](https://github.com/your-org/nanamigopher/issues)
- **社区论坛**：[NanamiGopher Community](https://community.nanamigopher.dev)
- **电子邮件**：support@nanamigopher.dev

提交问题时，请附上 `nanamigopher doctor export` 生成的诊断报告，以便我们更快地帮您解决问题。
