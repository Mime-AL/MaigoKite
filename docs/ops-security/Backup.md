# NanamiGopher 备份恢复

## 概述

NanamiGopher 采用本地自动备份为主、可选加密云同步为辅的双轨备份策略，确保 SQLite 数据库、ChromaDB 向量库、用户配置及 Skill 数据在各类故障场景下均可恢复。所有备份数据使用 AES-256 加密存储。

---

## 1. 备份范围

### 1.1 备份组件清单

| 组件 | 存储类型 | 数据量级 | 重要性 | 备份频率 |
|------|----------|----------|--------|----------|
| SQLite 数据库 | 文件 (`data/nanamigopher.db`) | ~10-100MB | 核心 | 每小时 |
| ChromaDB 向量库 | 目录 (`data/chroma/`) | ~50MB-1GB | 重要 | 每天 |
| 用户配置 | 文件 (`config/users.yaml`) | ~1MB | 重要 | 每次变更时 |
| Skill 数据 | 目录 (`data/skills/`) | ~10-50MB | 一般 | 每天 |
| 日志归档 | 文件 (`/var/log/nanamigopher/*.gz`) | ~500MB | 合规 | 每周 |
| 安全审计日志 | 文件 (`/var/log/nanamigopher/audit.log`) | ~100MB | 合规 | 每周 |

### 1.2 各组件详细说明

#### SQLite 数据库

- 包含所有 Task 记录、对话历史、用户数据、工具调用日志。
- 备份时通过 WAL 模式确保一致性，无需停止服务。
- 关键表：`tasks`、`conversations`、`tool_calls`、`users`。

#### ChromaDB 向量库

- 包含知识库嵌入向量、语义检索索引。
- 数据量大但重建成本较低（可从原始文档重新嵌入）。
- 备份策略以节省存储空间为主。

#### 用户配置

- 包含用户偏好、权限设置、API 密钥配置（已加密）。
- 每次配置变更立即触发增量备份。

#### Skill 数据

- 包含已安装 Skill 的元数据、缓存数据、用户生成内容。
- Skill 本身可从仓库重新下载，仅备份用户自定义配置。

---

## 2. 备份策略

### 2.1 本地自动备份

默认启用本地自动备份，无需人工干预。

```yaml
backup:
  local:
    enabled: true
    schedule: "0 * * * *"          # 每小时执行
    retention_days: 30             # 保留 30 天
    max_backups: 720               # 最多 720 个备份文件
    compression: gzip              # gzip 压缩
    encryption: aes-256-gcm        # AES-256-GCM 加密
    storage_path: "/var/backups/nanamigopher/"
```

#### 备份流程

```
1. 锁写 SQLite（WAL checkpoint，毫秒级）
2. 复制 SQLite 文件 → backup-{timestamp}.db.enc
3. 打包 ChromaDB 目录 → chroma-backup-{timestamp}.tar.gz.enc
4. 打包用户配置 → config-backup-{timestamp}.tar.gz.enc
5. 打包 Skill 数据 → skills-backup-{timestamp}.tar.gz.enc
6. 合并为完整备份包 → full-backup-{timestamp}.tar.gz.enc
7. 清理超过保留期的旧备份
```

### 2.2 可选加密云同步

用户可选择将备份加密后同步至云端存储。

```yaml
backup:
  cloud:
    enabled: false
    provider: s3                    # 支持 s3 / oss / gcs
    endpoint: "https://storage.example.com"
    bucket: "nanamigopher-backups"
    region: "cn-north-1"
    sync_schedule: "0 2 * * *"      # 每天凌晨 2 点同步
    encryption_key_ref: "vault:backup/master-key"
    retention_days: 90              # 云端保留 90 天
```

#### 同步特性

- 仅同步增量变化，减少带宽消耗。
- 传输全程使用 HTTPS（TLS 1.3）。
- 云端存储与本地存储使用相同加密算法。
- 支持多区域冗余存储（高级功能）。

---

## 3. 恢复流程

### 3.1 单文件恢复

适用于仅需恢复个别文件（如误删某个配置文件）的场景。

```bash
# 列出可用备份
nanamigopher backup list

# 恢复单个文件
nanamigopher backup restore-file \
  --backup full-backup-20260721-0200.tar.gz.enc \
  --target config/users.yaml \
  --decrypt-key "your-decrypt-key"
```

**步骤：**
1. 选择目标备份文件。
2. 输入解密密钥。
3. 指定需要恢复的文件路径。
4. 系统验证文件完整性后写入目标位置。
5. 重启相关服务使配置生效。

### 3.2 全量恢复

适用于系统重装或大规模数据丢失场景。

```bash
# 全量恢复
nanamigopher backup restore-full \
  --backup full-backup-20260721-0200.tar.gz.enc \
  --decrypt-key "your-decrypt-key" \
  --target-dir /opt/nanamigopher
```

**步骤：**

| 步骤 | 操作 | 预计时间 | 注意事项 |
|------|------|----------|----------|
| 1 | 停止 NanamiGopher 服务 | 5s | 确保无写入操作 |
| 2 | 验证备份完整性 | 30s | SHA-256 校验 |
| 3 | 解密备份文件 | 10-60s | 取决于数据量 |
| 4 | 解压并恢复 SQLite | 10-30s | 自动执行 WAL 恢复 |
| 5 | 解压并恢复 ChromaDB | 30-120s | 大体积时较长 |
| 6 | 恢复用户配置 | 5s | |
| 7 | 恢复 Skill 数据 | 10-30s | |
| 8 | 启动 NanamiGopher 服务 | 10s | 自动检测数据一致性 |
| 9 | 验证恢复结果 | 30s | 运行自检脚本 |

### 3.3 灾难恢复

适用于数据中心级故障（硬件损坏、自然灾害等）。

```
1. 从异地备份源获取最新备份（云端或异地存储）
2. 在新环境中部署 NanamiGopher
3. 执行全量恢复流程
4. 验证数据完整性
5. 切换流量至新环境
6. 监控 24 小时确保稳定
```

**RTO（恢复时间目标）：** 4 小时
**RPO（恢复点目标）：** 1 小时

---

## 4. 备份加密

### 4.1 加密方案

| 项目 | 值 |
|------|-----|
| 算法 | AES-256-GCM |
| 密钥长度 | 256 位 |
| 密钥派生 | PBKDF2（100,000 次迭代） |
| 认证 | GCM 模式自带认证标签 |
| IV 长度 | 96 位 |

### 4.2 密钥管理

```
用户解密密钥
    │
    ├── 本地存储：用户设定的 master password
    │   └── 用于派生 AES 密钥（PBKDF2）
    │
    ├── 密钥管理服务：HashiCorp Vault / AWS KMS
    │   └── 企业级密钥托管
    │
    └── 环境变量：BACKUP_DECRYPT_KEY
        └── CI/CD 自动化恢复场景
```

### 4.3 加密流程

```
原始数据
    │
    ▼
AES-256-GCM 加密
    │
    ├── 生成随机 IV
    ├── 加密数据
    └── 生成认证标签（tag）
    │
    ▼
存储格式：[IV(12B)][tag(16B)][ciphertext(NB)]
    │
    ▼
gzip 压缩
    │
    ▼
备份文件（.enc）
```

### 4.4 密钥轮换

- 建议每 90 天轮换一次加密密钥。
- 轮换时对所有现有备份重新加密。
- 旧密钥保留至少 30 天以支持历史备份恢复。

---

## 5. 备份验证

### 5.1 自动验证

每次备份完成后自动执行完整性校验：

```yaml
backup:
  verify:
    enabled: true
    method: sha256              # SHA-256 校验和
    auto_restore_test: false     # 是否自动执行恢复演练
```

- 备份完成后立即计算 SHA-256 校验和。
- 校验和存储于独立文件 `backup-{timestamp}.sha256`。
- 校验失败时自动重试备份并告警。

### 5.2 定期恢复演练

建议每月执行一次恢复演练，验证备份可恢复性。

**演练流程：**

```bash
# 1. 创建临时恢复目录
mkdir -p /tmp/backup-restore-test

# 2. 从最新备份恢复至临时目录
nanamigopher backup restore-full \
  --backup $(nanamigopher backup list --latest) \
  --target-dir /tmp/backup-restore-test \
  --dry-run

# 3. 验证关键数据
nanamigopher backup verify \
  --target-dir /tmp/backup-restore-test \
  --check sqlite \
  --check chromadb \
  --check config

# 4. 清理测试数据
rm -rf /tmp/backup-restore-test
```

**验证检查项：**

| 检查项 | 说明 | 预期结果 |
|--------|------|----------|
| SQLite 完整性 | PRAGMA integrity_check | `ok` |
| Task 数量 | 对比备份前后 Task 数 | 一致 |
| 配置可读性 | 解析 YAML 配置文件 | 无语法错误 |
| 向量库索引 | ChromaDB health check | healthy |
| 加密验证 | 解密 + 校验和比对 | 通过 |

### 5.3 演练报告

恢复演练后自动生成报告：

```json
{
  "timestamp": "2026-07-21T03:00:00Z",
  "backup_file": "full-backup-20260721-0200.tar.gz.enc",
  "result": "passed",
  "checks": {
    "sqlite_integrity": "ok",
    "task_count_match": true,
    "config_valid": true,
    "vector_db_healthy": true,
    "encryption_verified": true
  },
  "duration_seconds": 45,
  "notes": "All checks passed"
}
```

---

## 附录

### 备份文件命名规范

```
{type}-backup-{YYYYMMDD}-{HHMM}.tar.gz.enc

示例：
  full-backup-20260721-0200.tar.gz.enc
  db-backup-20260721-1300.tar.gz.enc
  config-backup-20260721-1300.tar.gz.enc
```

### 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 备份失败 | 磁盘空间不足 | 清理旧备份或扩容磁盘 |
| 恢复失败 | 密钥错误 | 确认解密密钥正确性 |
| 恢复失败 | 备份损坏 | 使用 SHA-256 校验和验证，从上一版本恢复 |
| 云同步失败 | 网络中断 | 检查网络连接，手动触发同步 |
| 加密性能慢 | 数据量大 | 考虑使用硬件加速或增加服务器资源 |
