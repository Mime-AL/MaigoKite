# 工作日志：提示词安全审查

> 计划见 [plan.md](plan.md)。本文件按日期记录实际改动、验证结果和待办，不复制 [API 设计](../design/API.md) 的契约正文。

## 2026-10-12

### 方案阶段

- 评估可行性：仓库已有设置页与设置 API、LangGraph 审批/中断链路、前端任务继续/恢复入口，三块能力可复用。审查切点定在主模型每次真正发送前，不在 UI 或工具审批后补救。
- 确认边界：决策模型按工作区独立配置；阈值用 0-100；白名单按当前实际调用模型 ID 判断；审查失败保守拦截；复用现有暂停/继续链路，不建第二套审批系统。
- 计划用 engineering-docs 技能重写，收敛为“契约先行、请求构造库独立、runtime 只消费接口”的结构。
- 范围收敛：本批不动任何 UI，只输出前端可对接的接口、事件和类型，由前端组适配。

### 契约阶段

- `docs/design/API.md` 新增 `GET/PATCH /workspaces/{id}/settings/safety` 端点表单、字段与校验说明、`safety.reviewed` 事件约定、`capabilities.safety_review` 标志说明。
- 修正格式枚举：kev 是 jev 类的开源实现，枚举收敛为 `jev_like` 和 `laya`，不单独枚举 kev。
- 请求结构拆为 `state` 与 `question`：`state` 进入设置供自定义，留空用库内置默认值；`question` 由库根据审查输入生成。
- `docs/agent-capabilities/models/model-routing.md` 补决策模型独立配置与格式边界。

### Phase A（数据契约与持久化）✅

创建：
- `python/agent/safety/__init__.py` — 包入口。
- `python/agent/safety/config.py` — `safety.policy` 设置键、`safety.decision_model` 凭证引用、默认值（关闭 / `jev_like` / 阈值 75）、`normalize_safety_settings` 修复逻辑。
- `python/tests/test_safety_settings.py` — 8 个回归测试（仓库首个测试模块）。

修改：
- `python/agent/api/contracts.py` — `SafetySettings` DTO；`request_format` 用普通字符串，让端点能返回专用错误码。
- `python/agent/core.py` — `get_safety_settings` / `update_safety_settings`。
- `python/agent/api/settings.py` — 两个端点（owner_only）；格式错误抛 `APIError(400, "SAFETY_FORMAT_UNSUPPORTED")`；`api_key` 写入凭证存储不回显；写入记审计。
- `python/agent/api/app.py` — `capabilities.safety_review = true`。

### Phase B（前端契约，不含 UI）✅

- `web/src/api/client.ts` — `SafetySettings` / `SafetyRequestFormat` 类型与读写方法。
- `web/src/api/events.ts` — `SafetyReviewPayload` 类型（`safety.reviewed` 事件负载契约）。

### 验证记录

- 后端单测：`8 passed`（`python/tests/test_safety_settings.py`）。
- 导入烟测：`agent.api.contracts / agent.api.settings / agent.safety / agent.core` 导入正常，默认值与格式枚举正确。
- 前端类型检查：`web` 下 `npx vue-tsc --noEmit`，退出码 0。
- 未做端点 HTTP 联调，未运行真实决策模型验证（属于 Phase C/E）。

### 环境记录

- 本机无 `uv`；`.venv` 原本只有运行时依赖，已按开发指南 pip 分支补装 `pytest>=8`、`pytest-asyncio`。
- 测试命令：`$env:PYTHONPATH='python'; .\.venv\Scripts\python.exe -m pytest python/tests -q`。
- 系统 Python 是 miniconda 且缺 langchain；`agent/__init__.py` 急切导入 AgentCore，必须用 `.venv` 运行。

### 待办

- [x] Phase C：新增 `safety/request_builders.py`、`formats/jev_like.py`、`formats/laya.py` 和 `reviewer.py`；runtime 已接入前置切点、增量计算、白名单跳过、阈值判定及失败保守拦截。
- [x] Phase D：高风险审查复用现有结构化提问/恢复链路；结果落为 `safety.reviewed` 事件，继续或终止通过现有问题回答入口处理。
- [ ] Phase E：补审查场景测试、端点 HTTP 联调、文档收尾。
- [x] KEV 联调：`POST /v1/systemone` 已在本机 `127.0.0.1:8009` 验证，安全样例返回风险分值 0。
- [x] KEV score 校准：不再把 KEV 的 `score` 当作风险值。`jev_like` 现发送 `safe` /
  `dangerous` 两个 criterion，并读取 `legend` 对应的 `probabilities[dangerous]`，
  乘以 100 得到 0–100 `risk_score`；`risk_threshold` 保持 0–100。
- [x] LAYA 服务联调：`POST /predict` 已在本机 `127.0.0.1:8000` 验证；原单数 `question`
  载荷被 422 拒绝，已改为 `questions` 映射契约。检查点白名单、语言覆盖矩阵与服务端
  XPU 崩溃限制见 [plan](plan.md) 验证结果，`python/tests` 38 passed。
