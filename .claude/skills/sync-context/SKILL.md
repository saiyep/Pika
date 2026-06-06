---
name: sync-context
description: 同步更新 Pika 项目的记忆与文档。当用户说要"更新memory/文档/上下文""记录最新进展""同步状态"时使用。会把本次会话的关键进展（决策、部署、测试结果、范围变化、下一步）写入 auto-memory 与 docs/ 下的 md，并删除已过时内容。
---

# Sync Context (Pika)

把本次会话产生的**持久化进展**同步进记忆系统和项目文档。目标：下一个会话/开发者读了就能无缝续上，且不留过时信息。

## 何时用
- 用户说“更新 memory / 更新文档 / 同步上下文 / 记录进展 / 把这次的改动记下来”。
- 一个阶段性工作刚完成（部署成功、接口跑通、范围拍板、关键决策确定）。

## 同步范围（两类目标）

### A. Auto-memory（跨会话长期记忆）
目录：`C:\Users\saiy\.claude\projects\d--Documents-Projects-Pika\memory\`
- 索引文件 `MEMORY.md`：每条一行 `- [标题](file.md) — 一句话`，不要把正文写进索引。
- 各 memory 文件用 frontmatter（`name` / `description` / `metadata.type`），type 取 user/feedback/project/reference。
- **只存非代码可推导的信息**：项目背景、决策与原因、部署事实、外部资源、用户偏好、当前进展。不要存能从代码/git 直接读出的东西。

### B. 项目文档（仓库内，随代码走）
- `docs/PROJECT_STATUS.md` —— 当前真实状态、已完成、下一步、阻塞项。
- `docs/IMPLEMENTATION_PLAN.md` —— 当前执行范围与顺序。
- `CLAUDE.md` —— 架构/约定/命令（只在架构或规则变化时更新）。

## 执行步骤

1. **读现状**：先读 `MEMORY.md`、相关 memory 文件、`docs/PROJECT_STATUS.md`、`docs/IMPLEMENTATION_PLAN.md`，避免重复或冲突。
2. **提炼本次进展**：从对话里挑出值得长期保留的内容——
   - 新决策 + 为什么
   - 部署 / 配置 / 环境事实（如 NAS 路径、端口、验证结果）
   - 范围变化（新增需求、砍掉的需求）
   - 测试 / 验证结论
   - 明确的下一步
3. **更新 memory**：
   - 有对应文件就 Edit 更新；没有就新建并在 `MEMORY.md` 加一行索引。
   - 发现旧 memory 与现状冲突 → 直接改对或删除，不要保留错误信息。
4. **更新 md 文档**：
   - 把“已完成”从待办里移走；刷新“下一步/阻塞项”。
   - 删除已废弃的旧方案、旧术语、不再使用的逻辑描述（用户偏好：只留最新口径）。
5. **安全检查（强制）**：
   - 任何要写进**仓库文件**的内容都不得包含真实密钥（微信 AppSecret、Azure key）。
   - 真实密钥只存在于 NAS 的 `.env`，绝不写进 docs/CLAUDE.md/memory 仓库文件。
6. **简报**：结束时用 3-5 行说明改了哪些 memory 文件、哪些 md，以及当前“下一步”是什么。

## 注意
- memory 里的相对日期要转成绝对日期。
- 不要为了凑数写无意义条目；没有新进展就如实说明无需更新。
