---
name: start-feature
description: 用自然语言描述一个新功能需求；该 skill 会先把它标准化成 ticket（含 backlog 行与必要的计划更新），而不是直接开始改代码。
---

# Start Feature (Pika)

用于把一个新的 feature 需求转成 **可追踪的工作单元**，供后续 loop 使用。

## 目标
1. 把聊天中的 feature 需求沉淀成 `docs/tickets/TKT-xxx-*.md`。
2. 在 `docs/PROJECT_STATUS.md` 中登记 backlog 行。
3. 仅在影响共享范围/共享验收/跨 ticket 顺序时更新 `docs/IMPLEMENTATION_PLAN.md`。
4. 本 skill 只负责“建账”，不直接开始实现产品代码。

## 必读
- `docs/PROJECT_STATUS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/tickets/README.md`
- `docs/tickets/TICKET_TEMPLATE.md`
- 现有 `docs/tickets/TKT-*.md`

## 红线
- 不跳过 ticket 直接开始改代码。
- 不把单 ticket 的长背景写回 `PROJECT_STATUS.md`。
- 不无意义地改 `IMPLEMENTATION_PLAN.md`；只有该 feature 影响全局范围、共享验收或跨 ticket 顺序时才改。
- 若已有明显对应 ticket，优先更新已有 ticket，而不是重复新建。

## 步骤
1. 先读 backlog 与 ticket 体系文件，确认是否已有对应 ticket。
2. 若需求描述过于模糊，只做最少一轮澄清，补齐至少这些信息：
   - 目标是什么
   - 为什么现在做
   - 优先级大概在哪一层（P0/P1/P2）
   - 非目标/边界是什么
3. 若无现成 ticket，则：
   - 扫描 `docs/tickets/TKT-*.md` 现有编号；
   - 取下一个三位补零 ID，如 `TKT-009`；
   - 生成英文 slug 文件名：`TKT-xxx-英文slug.md`。
4. 用 `docs/tickets/TICKET_TEMPLATE.md` 建新 ticket，至少填完整：
   - 基本信息（`类型=feature`，默认 `状态=todo`）
   - 背景
   - 目标
   - 非目标
   - 范围（要做 / 不做）
   - 方案备注
   - 验收口径
   - 部署影响
   - 初始 `Loop 记录`（建议 `loop 0`）
5. 在 `docs/PROJECT_STATUS.md` 的 active backlog 表中增加一行：
   - 优先级
   - 状态
   - ID
   - 标题
   - 明细路径
6. 仅当该 feature 影响共享范围/共享验收/跨 ticket 实施包时，再更新 `docs/IMPLEMENTATION_PLAN.md`。
7. 完成后只输出简短结论：
   - 新 ticket ID / 标题
   - 是否更新了 `PROJECT_STATUS.md`
   - 是否更新了 `IMPLEMENTATION_PLAN.md`
   - 建议下一步进入哪个 loop

## 输出要求
最终回复保持短，固定包含：
1. 新建/更新了哪个 ticket
2. backlog 是否已登记
3. `IMPLEMENTATION_PLAN.md` 是否改动
4. 下一步建议
