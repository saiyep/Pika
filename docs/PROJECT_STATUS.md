# Pika 项目状态（最新）

## 当前状态

- 主线阶段：体验版稳定性回归完成，进入下一轮能力升级准备。
- 已落地：趋势页改为单成员优先浏览；历史页默认本人 + 近 3 个月 + 医院结果联动筛选；上传页与权限设置页 UI/UX 已重构；登录/请求基础设施与版本校验也做了对应收口。
- 部署状态：后端已发布到 NAS，Alembic 版本 `d5a9e1c7b2f4`；本轮后端改动不需要重建数据库。

## 现场反馈评估（2026-06-25）

- 本轮反馈已拆成 ticket；全局只保留优先级与状态，总细节转移到 `docs/tickets/`。
- 当前 active backlog 以 P0 / P1 为主，每个 loop 尽量只推进一个 ticket。
- 已完成项“趋势图增加标准化网格刻度 + 新增数据表视图”不再单列 backlog，后续如需返工再新开 ticket。

## Backlog 总览（高层入口）

> 规则：`PROJECT_STATUS.md` 只做看板；单项背景、范围、验收、阻塞、loop 记录统一写到 `docs/tickets/*.md`。

### Active backlog（已建 ticket）

| 优先级 | 状态 | ID | 标题 | 明细 |
| --- | --- | --- | --- | --- |
| P0 | done | TKT-001 | 自动微信登录体验改造 | `docs/tickets/TKT-001-auto-wechat-login.md` |
| P0 | done | TKT-003 | 上传成功后导航回流优化 | `docs/tickets/TKT-003-post-submit-navigation.md` |
| P0 | done | TKT-004 | 就医权限默认未向家庭成员全开 | `docs/tickets/TKT-004-family-visibility-guidance.md` |
| P0 | done | TKT-005 | 扫码加入闭环真机验收 | `docs/tickets/TKT-005-invite-join-device-validation.md` |
| P0 | done | TKT-002 | 上传识别与提交自动重试反馈 | `docs/tickets/TKT-002-upload-retry-feedback.md` |
| P0 | done | TKT-003 | 上传成功后导航回流优化 | `docs/tickets/TKT-003-post-submit-navigation.md` |
| P0 | done | TKT-004 | 就医权限默认未向家庭成员全开 | `docs/tickets/TKT-004-family-visibility-guidance.md` |
| P0 | done | TKT-010 | 就医成员选择器 UI/UX 与权限联动统一 | `docs/tickets/TKT-010-unified-member-filter-ux.md` |
| P1 | todo | TKT-006 | 关注指标体系与医院自动识别主路径 | `docs/tickets/TKT-006-focus-metrics-and-hospital-recognition.md` |
| P1 | todo | TKT-007 | 检查单类别识别与关注指标联动 | `docs/tickets/TKT-007-report-category-recognition.md` |
| P1 | done | TKT-008 | 就医浏览体验真机验收与交互微调 | `docs/tickets/TKT-008-medical-browsing-device-polish.md` |
| P0 | done | TKT-009 | 趋势图点按缺少数值 tooltip | `docs/tickets/TKT-009-trend-point-tooltip.md` |

### 已完成 / 已验收

| 优先级 | 状态 | ID | 标题 | 明细 |
| --- | --- | --- | --- | --- |
| P0 | done | TKT-003 | 上传成功后导航回流优化 | `docs/tickets/TKT-003-post-submit-navigation.md` |
| P0 | done | TKT-004 | 就医权限默认未向家庭成员全开 | `docs/tickets/TKT-004-family-visibility-guidance.md` |
| P0 | done | TKT-005 | 扫码加入闭环真机验收 | `docs/tickets/TKT-005-invite-join-device-validation.md` |
| P0 | done | TKT-009 | 趋势图点按缺少数值 tooltip | `docs/tickets/TKT-009-trend-point-tooltip.md` |
| P0 | done | TKT-010 | 就医成员选择器 UI/UX 与权限联动统一 | `docs/tickets/TKT-010-unified-member-filter-ux.md` |

### 候选池（未升格成 active ticket）

- P2：AI 助手能力迭代。
- P2：更多报告类型适配与指标标准化词典完善。

进入 active backlog 前，先按 `docs/tickets/TICKET_TEMPLATE.md` 建 ticket，再回写到上表。
## 建议执行顺序（当前 P0）

### Loop 1
- `TKT-001` 自动微信登录体验改造

### Loop 2
- `TKT-002` 上传识别与提交自动重试反馈
- `TKT-003` 上传成功后导航回流优化

### Loop 3
- `TKT-004` 就医权限默认未向家庭成员全开

### Loop 4
- `TKT-010` 就医成员选择器 UI/UX 与权限联动统一

> 原则：P0 以串行为主；仅在同一用户流内（如上传链路）合并推进，避免多条 loop 同时改同一批页面和状态流。

## 关键约定（维持）

- `PROJECT_STATUS.md` 是全局高层入口；单项 backlog 明细写在 `docs/tickets/*.md`。
- 新会话先读 `PROJECT_STATUS.md`，再按当前目标跳转对应 ticket。
- 新 feature / bug 若会跨多个 loop，先按 `docs/tickets/TICKET_TEMPLATE.md` 建 ticket。
- `IMPLEMENTATION_PLAN.md` 只保留范围、共享验收口径、跨 ticket 实施包，不承载单项过程记录。
- DB 由 Alembic 管理；改 models 后 `alembic revision --autogenerate`。
- 改 backend 代码须 **rebuild**（重启不够）；改挂载须同步 NAS `docker-compose.yaml`。
- 流程：先 release→模拟器/真机验证→再 commit；push 前检查敏感公网标识不入仓库。
- 真实凭据只在 NAS `.env`，不入 git。
- 架构与运行约束见 `CLAUDE.md`。
