# Pika backlog / ticket 文档约定

## 目标

把仓库内的需求跟踪拆成两层：

1. `docs/PROJECT_STATUS.md`：只做全局看板，回答“现在最重要的事是什么”。
2. `docs/tickets/*.md`：一条 feature / bug 一个 ticket，回答“这一项具体要做什么、做到哪一步了”。
3. `docs/IMPLEMENTATION_PLAN.md`：只保留全局范围、共用验收口径、跨 ticket 的实施包。

这样后续每个 loop 都尽量只围绕一个 ticket 推进，避免把细节继续堆回 `PROJECT_STATUS.md`。

## 目录约定

- `docs/tickets/TICKET_TEMPLATE.md`：新 ticket 模板。
- `docs/tickets/TKT-xxx-*.md`：单项 feature / bug ticket。

当前不额外拆 `archive/` 目录；完成后的 ticket 仍留在这里，把状态改成 `done` 即可，方便回溯。

## 新开一个 feature / bug 的最小步骤

1. 复制 `TICKET_TEMPLATE.md`，按下一个编号创建新文件。
   - 文件名格式：`TKT-xxx-简短英文slug.md`
   - 例：`TKT-009-history-export.md`
2. 先补完整 `基本信息 / 背景 / 目标 / 范围 / 验收 / 部署影响`。
3. 在 `docs/PROJECT_STATUS.md` 的 backlog 总览里增加一行：
   - `ID`
   - `优先级`
   - `状态`
   - `标题`
   - `明细链接`
4. 如果这项工作会改变“当前范围、跨模块顺序、共用验收口径”，再更新 `docs/IMPLEMENTATION_PLAN.md`；如果只是单点实现细节，则只写 ticket，不扩写实施计划。
5. 后续每个 loop 的结论、阻塞、下一步，都优先写回对应 ticket 的“Loop 记录”。

## 什么时候必须先建 ticket

以下情况，进入 active backlog 前必须先建 ticket：

- 新功能
- 用户反馈形成的明确问题单
- 需要跨多次 loop 才能完成的改动
- 需要单独记录验收口径或部署影响的工作

以下情况可先不建 ticket：

- 纯一次性小修文案
- 已包含在某个进行中 ticket 里的子步骤
- 只改注释/格式且不会独立排期的改动

## 三份文档如何分工

### `PROJECT_STATUS.md`
- 保留当前阶段、部署状态、优先级总览。
- 每个 backlog 项只写一行摘要，不再堆实现细节。
- 作为新会话默认入口。

### `IMPLEMENTATION_PLAN.md`
- 保留当前范围、跨 ticket 的实施包、共享验收标准。
- 不重复记录单 ticket 的背景和过程。

### `docs/tickets/*.md`
- 记录单项背景、目标、非目标、范围、验收、进展、阻塞、部署影响。
- loop 结束时，优先更新这里。

## 状态建议

- `todo`：已立项，尚未开始
- `in_progress`：当前 loop 正在推进
- `blocked`：有明确阻塞
- `done`：验收完成
- `icebox`：暂缓，不进入当前阶段

## 维护原则

- `PROJECT_STATUS.md` 始终短。
- 单 ticket 文档允许详细，但只服务一个 tracked unit。
- 一个 loop 最好只主推一个 `in_progress` ticket；如同时推进多个，要在各自 ticket 里分别记进度。
- 完成 ticket 后，先更新 ticket 状态，再回写 `PROJECT_STATUS.md` 的总览状态。