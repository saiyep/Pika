# TKT-012｜项目看板与 Ticket 管理基础设施

## 基本信息

- ID：`TKT-012`
- 类型：feature
- 优先级：P1
- 状态：todo
- 负责人：待定
- 关联阶段：项目基础设施 / 协作效率
- 关联入口：`docs/PROJECT_STATUS.md` 对应条目

## 背景

- 用户反馈 / 现象：当前 Pika 的 ticket / task / bug 都通过本地代码仓库 `docs/` 目录创建、维护和管理；查看进度、创建新 feature/bug、给 AI 读取更新都依赖手工编辑文档和本地 skill 流程。
- 当前原因判断：缺少一个面向项目管理的后台页面、结构化 API 和数据库模型来承接 ticket 看板、创建入口、附件和 AI 协作读写。
- 为什么现在做：随着 ticket 数量增加，单靠 Markdown 文件维护会变得难以浏览、筛选、创建和自动化更新；需要把项目管理能力产品化到 Pika 自身服务里。

## 目标

1. 在 Pika 后端服务中提供一个项目看板管理页面，用于查看每个 ticket / task / bug / feature 的进度、优先级、状态和详情。
2. 提供结构化 API，允许 AI 读取、创建和更新 ticket，减少直接改 Markdown 的脆弱性。
3. 增加创建 feature 和创建 bug 的页面入口，支持输入自然语言需求、选择优先级、类型、状态，并上传或粘贴截图。
4. 建立后端数据库模型，保存 ticket 元数据、正文、loop 记录、附件和与 `docs/tickets` 的关联关系。
5. 保留与现有 `docs/PROJECT_STATUS.md`、`docs/tickets/*.md` 工作流的兼容或同步路径。

## 非目标

1. 不在首版实现完整 Jira / Linear / GitHub Projects 级别的复杂项目管理能力。
2. 不接入多项目、多租户或外部团队协作体系。
3. 不让 AI 通过 API 执行任意文件系统写入；AI API 只能操作受控 ticket 数据结构。
4. 不在本 ticket 内重写现有所有 ticket 文档内容。
5. 不把业务用户的就医服务功能和项目管理后台混在同一个普通用户入口里。

## 范围

### 要做
- 设计 ticket / task / bug / feature 的基础数据模型，覆盖 ID、标题、类型、优先级、状态、负责人、阶段、正文、验收口径、部署影响、loop 记录、相关文件和附件。
- 设计附件能力，支持页面创建 feature/bug 时上传或粘贴截图，并与 ticket 关联。
- 提供项目看板页面，支持按状态、优先级、类型查看和筛选 ticket。
- 提供 ticket 详情页，展示背景、目标、范围、验收、loop 记录、附件和相关文件。
- 提供创建 feature、创建 bug 的表单入口，支持自然语言描述、截图、优先级、类型和初始状态。
- 提供 AI 可用的 API：列表查询、详情读取、创建 ticket、更新状态、追加 loop 记录、更新字段、上传/关联附件。
- 明确数据库与 `docs/tickets/*.md` 的同步策略：首版可选择导入现有 Markdown、生成 Markdown 快照，或以 DB 为主并保留导出能力。
- 加入权限与审计边界，至少限制为管理员或本地可信调用可操作项目管理 API。

### 不做
- 复杂工作流自动化、燃尽图、排期容量管理。
- 外部 OAuth、第三方项目管理工具同步。
- 自动让 AI 根据 ticket 直接改业务代码。
- 替代 Git 版本控制和代码 review 流程。

## 方案备注

- 涉及模块：后端数据库模型、Alembic migration、项目管理 API、管理端页面、附件存储、现有 docs/tickets 同步工具或适配层。
- 关键实现点：先定 source of truth（DB 主导、Markdown 主导或双向同步）；AI API 要结构化、幂等、可审计；截图附件不能进入不受控路径；页面要适合扫描和筛选。
- 风险 / 待确认：若 DB 与 Markdown 双写，容易出现冲突；需要先明确首版以哪一侧为准，以及是否仍要求每次创建 ticket 同步回 `docs/PROJECT_STATUS.md`。

## 验收口径

1. 管理页面能展示当前所有 ticket / task / bug / feature，并按状态、优先级、类型筛选。
2. 打开单个 ticket 能看到完整详情、loop 记录、附件和相关文件信息。
3. 页面上可以创建 feature 和 bug，填写需求描述、优先级，并上传或粘贴截图。
4. AI 可以通过受控 API 读取 ticket 列表/详情，并创建或更新 ticket 的结构化字段和 loop 记录。
5. 现有 `docs/tickets/*.md` 至少能被导入或映射到看板中，且不会丢失现有 ticket 信息。
6. 权限边界明确：非授权用户不能访问或修改项目管理数据。

## 部署影响

- 前端：需要，新增项目看板管理页面、详情页和创建 feature/bug 表单。
- 后端：需要，新增项目管理 API、服务层和附件处理。
- 数据库：需要，新增 ticket、loop 记录、附件等相关表，并由 Alembic 管理。
- 配置 / NAS：可能需要，若新增附件存储目录或管理后台访问配置。

## Loop 记录

### 2026-06-28 / loop 0
- 本轮目标：把“Pika 内置项目看板与 AI 可读写 ticket 管理”沉淀为基础设施 feature ticket。
- 已完成：明确页面、API、数据库、附件、AI 协作、docs 兼容和权限边界。
- 阻塞 / 问题：首版需要先决定 DB 与 Markdown 的 source of truth 和同步策略。
- 下一步：进入设计 loop，先画出数据模型、API 草案和 Markdown 导入/导出策略。

## 相关文件

- `docs/PROJECT_STATUS.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/tickets/README.md`
- `docs/tickets/TICKET_TEMPLATE.md`
- `backend/app/main.py`
- `backend/app/core/db.py`
- `backend/alembic/versions/`
- `miniprogram/` 或后续管理端前端入口
