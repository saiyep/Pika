---
name: start-bug
description: 用自然语言描述一个新 bug；该 skill 会先把它标准化成 ticket（含 backlog 行与必要的计划更新），而不是直接开始修代码。
---

# Start Bug (Pika)

用于把一个新的 bug / 回归问题转成 **可追踪的工作单元**，供后续 loop 使用。

## 目标
1. 把聊天中的 bug 描述沉淀成 `docs/tickets/TKT-xxx-*.md`。
2. 在 `docs/PROJECT_STATUS.md` 中登记 backlog 行。
3. 仅在影响共享范围/共享验收/跨 ticket 顺序时更新 `docs/IMPLEMENTATION_PLAN.md`。
4. 本 skill 只负责“建账”，不直接开始修产品代码。

## 必读
- `docs/PROJECT_STATUS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/tickets/README.md`
- `docs/tickets/TICKET_TEMPLATE.md`
- 现有 `docs/tickets/TKT-*.md`

## 红线
- 不跳过 ticket 直接开始修代码。
- 不把单 ticket 的长复现过程写回 `PROJECT_STATUS.md`。
- 不无意义地改 `IMPLEMENTATION_PLAN.md`；只有该 bug 暴露了共享范围、共享验收或跨 ticket 顺序变化时才改。
- 若已有明显对应 ticket，优先更新已有 ticket，而不是重复新建。

## 步骤
1. 先读 backlog 与 ticket 体系文件，确认是否已有对应 ticket。
2. 若 bug 描述不够可追踪，只做最少一轮澄清，补齐至少这些信息：
   - 现象是什么
   - 预期行为是什么
   - 影响面/严重度大概如何
   - 是否有明确复现场景
3. 若无现成 ticket，则：
   - 扫描 `docs/tickets/TKT-*.md` 现有编号；
   - 取下一个三位补零 ID，如 `TKT-009`；
   - 生成英文 slug 文件名：`TKT-xxx-英文slug.md`。
4. 用 `docs/tickets/TICKET_TEMPLATE.md` 建新 ticket，至少填完整：
   - 基本信息（`类型=bug`，默认 `状态=todo`）
   - 背景（现象、影响、当前原因判断）
   - 目标（恢复什么正确行为）
   - 非目标
   - 范围（修复范围 / 不做范围）
   - 方案备注（可写预期 vs 实际、风险）
   - 验收口径（按复现场景定义修好标准）
   - 部署影响
   - 初始 `Loop 记录`（建议 `loop 0`）
5. 在 `docs/PROJECT_STATUS.md` 的 active backlog 表中增加一行：
   - 优先级
   - 状态
   - ID
   - 标题
   - 明细路径
6. 仅当该 bug 影响共享范围/共享验收/跨 ticket 实施包时，再更新 `docs/IMPLEMENTATION_PLAN.md`。
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
