# NanamiGopher 安全架构

> **状态**：Current
> **最后核验**：2026-09-14
> **权威范围**：系统威胁模型、身份、凭证、网络和事件响应

工具风险等级、权限模式和审批见 [Tool Permission](../agent-capabilities/security/tool-permission.md)，本文不维护第二份权限矩阵。

## 1. 信任边界

```text
不可信输入
├── 用户/API请求
├── 上传文档与检索内容
├── 模型输出
├── Tool/MCP结果
└── 第三方 Skill包与进程

可信执行边界
├── Gateway认证与AccessPolicy
├── Agent Core ToolPolicy
├── Sandbox/hard-deny
├── CredentialProvider
└── 不可变审计事件
```

任何内容被模型读取后仍保持原信任级别；检索或 ToolResult 不能提升为系统指令。

## 2. 身份与 Workspace

- 桌面模式使用本地设备/用户身份适配器。
- 服务器模式使用经验证的 OIDC/JWT。
- Gateway 验证 issuer、audience、expiry、算法和签名密钥。
- 所有资源访问经过 Workspace Membership 检查。
- 外部客户端不能声明可信 principal。
- 服务间 gRPC 使用服务身份并限制网络可达性。

## 3. 工具与审批

- Gateway AccessPolicy 和 Python ToolPolicy 均需通过。
- 未知 capability 默认拒绝。
- L5逐次审批，hard-deny不能由用户确认覆盖。
- Approval绑定参数 hash、资源范围、主体、任务和有效期。
- Native 与 MCP Tool 使用相同政策入口和审计要求。

## 4. Skill与MCP

- 第三方 Skill按不受信代码处理。
- 安装前验证 manifest、内容 hash、来源、依赖和能力请求。
- MCP子进程使用最小环境、独立工作目录和资源限制。
- 文件和网络范围按 SkillGrant控制。
- 不自动执行未经验证包的入口命令。

## 5. 凭证

| 环境 | Provider |
|---|---|
| 桌面 | Keychain / DPAPI / libsecret |
| 服务器 | Vault / KMS / Secret Manager |
| 显式 fallback | 使用强KDF和认证加密的本地文件 |

- 数据库只保存 Credential Reference 和元数据。
- Skill只获得明确声明且已批准的凭证。
- Secret不进入日志、Memory、向量索引或API响应。
- 撤销凭证后相关运行实例必须刷新或停止。

## 6. 网络与客户端

- 外部接口使用 HTTPS/WSS。
- CORS、WebSocket Origin 和重定向采用显式 allowlist。
- Agent Core、数据库和向量服务不暴露公网。
- Electron启用 context isolation、sandbox、webSecurity，禁用 renderer Node能力。
- 外部链接通过受控系统浏览器打开。

## 7. 数据保护

- Workspace是默认隔离边界。
- 日志和审计字段经过结构化脱敏。
- 派生索引继承源数据的访问范围和删除策略。
- 备份先压缩后认证加密，密钥与备份分离。
- 数据导出和删除产生审计事件。

## 8. 安全事件

事件至少包括：认证失败、跨Workspace访问、hard-deny、审批绕过、Secret访问、Skill校验失败、沙箱逃逸、异常批量操作。

响应流程：

```text
检测 → 限制影响 → 撤销会话/凭证/Grant
→ 保存证据 → 通知负责人/用户 → 修复 → 复盘
```

## 9. 验收

- [ ] 身份、Workspace和服务边界明确。
- [ ] 权限矩阵只引用Tool Permission。
- [ ] Secret值不在业务数据库。
- [ ] MCP进程不继承完整环境。
- [ ] WebSocket与REST执行相同访问控制。
- [ ] 数据删除能传播到派生索引和备份策略。
