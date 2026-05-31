# Pika 家庭服务平台 — 医疗就诊辅助模块（POC）

## Context（为什么做这个）

用户的岳母经常去医院做检查（大到 X 光/核磁，小到血常规/肝功能），检查单和结果单据很多，难以追踪管理。目标是做一个**医疗检查记录追踪系统**：岳母用微信小程序上传检查结果照片 → 后端自动提取信息并结构化存储 → 随时在 dashboard 查看和按指标看趋势。

更大的定位：把它做成一个跑在家用 NAS（绿联 DH4300plus，Docker）上的**「家庭服务平台」**，可逐步扩展更多家庭模块；**医疗就诊辅助**是第一个模块。

**本次范围 = 局域网 POC**：在微信开发者工具 + 开发者本人手机预览下，连 NAS 局域网 IP，跑通「上传→存原图→GPT-4.5-mini 视觉解析→落库→小程序 dashboard 展示」全流程。公网 HTTPS 域名（给家人真机随时随地用）留作后续阶段，本次不实现。

**技术栈（已确认）**：Python + FastAPI + SQLite；解析用 Azure AI Foundry 上的 GPT-4.5-mini（vision）；前端原生微信小程序，内置 dashboard；趋势图用 ECharts 小程序版 `ec-canvas`。

**项目落地位置（已确认）**：复用现有 git 仓库 `D:\Documents\Projects\Pika`（远端 `git@github.com:saiyep/Pika.git`）。保留 .git 历史，清理旧的 Azure Functions 代码，在干净目录上重建为新项目。放弃 `Medical` 目录。

---

## 关键背景知识（微信小程序版本，已向用户科普）

- **个人 AppID** 免费注册即可，足够 POC（不能用微信支付，本项目不需要）。
- **开发版**连局域网 IP：微信开发者工具「详情→本地设置」勾选「不校验合法域名…」即可请求 `http://192.168.x.x:8000`。仅开发期 + 项目成员有效。
- 普通预览二维码**只有开发者本人能扫开**；家人要扫需加为「开发/体验成员」（个人小程序约 15 名成员够用），且只在你家 WiFi 内能连局域网 IP。
- **体验版/正式版强制 HTTPS 合法域名** → 给岳母随时随地真机用，必须等公网阶段。

---

## 贯穿原则：平台化、可逐步扩展

这是一个**会持续扩展的家庭服务平台**，医疗模块只是第一个最小可用版本。前后端设计都必须为扩展留好结构：

- **后端**：`core/`（平台公共能力，跨模块复用）+ `modules/<模块名>/`（各业务模块自包含）。新模块只在 `modules/` 下加目录、在 `main.py` 挂 router，不动已有模块。
- **数据库表名**：平台级表（如 users）放 core 用泛名；**模块业务表一律加模块前缀**（医疗模块 → `medical_` 前缀），避免未来模块间撞名。
- **小程序**：页面也按模块分组（`pages/medical/...`），首页做成可扩展的模块入口。
- **API 路径**：模块化前缀 `/api/medical/...`，未来 `/api/schedule/...` 等。

---

## 第 0 步：清理并重建 Pika 仓库（保留 git 历史）

工作目录 `D:\Documents\Projects\Pika`。

- **删除旧业务文件**：`source/ target/ test/ doc/ list_blobs.py test_qwen.py test_qwen_http.py test_qwen_simple.py`。
- **彻底删除旧 `CLAUDE.md`，从零写一份新的**（描述新的家庭服务平台 + 医疗模块架构，不保留任何旧 Azure/Notion 内容）。
- **保留**：`.git/`、`.venv/`、`.vscode/`。
- **重写 `.gitignore`**：换成 Python + 本项目用的忽略项，至少包含：
  ```
  __pycache__/
  *.py[cod]
  .venv/ venv/ env/
  .env
  backend/data/
  *.db
  miniprogram/node_modules/
  ```
- 把清理 + 新骨架作为一个**新 commit**（如 `chore: reset Pika to family-service platform`），不动远端历史。旧实现仍可通过历史 commit 找回。

---

## 第 1 步：后端骨架（平台 + 模块分层）

目录结构（核心）：

```
Pika/
├── docker-compose.yml          # 绿联部署入口；build.context: .
├── Dockerfile                  # python:3.11-slim → uvicorn app.main:app
├── .env.example                # Azure / 微信 凭据样例（真实 .env 不入库）
├── CLAUDE.md                   # 重写为新平台说明
├── backend/
│   ├── requirements.txt        # fastapi uvicorn[standard] sqlalchemy pydantic pydantic-settings openai httpx python-multipart pillow
│   ├── app/
│   │   ├── main.py             # FastAPI 实例，挂载各模块 router，CORS，启动建表
│   │   ├── settings.py         # pydantic-settings 读环境变量
│   │   ├── core/               # 平台公共能力（不依赖 modules）
│   │   │   ├── db.py           # SQLAlchemy engine/SessionLocal/Base/get_db
│   │   │   ├── models_base.py  # User 表 + TimestampMixin
│   │   │   ├── deps.py         # 当前用户解析（从 header 取 token/openid）
│   │   │   ├── wechat.py       # wx.login code→openid（jscode2session）
│   │   │   ├── storage.py      # 原图落盘：路径生成/命名/保存/读取
│   │   │   ├── schemas_base.py # 统一响应 ApiResponse
│   │   │   └── exceptions.py
│   │   └── modules/
│   │       └── medical/        # 医疗模块（可依赖 core）
│   │           ├── router.py   # /api/medical/* 端点
│   │           ├── models.py   # MedicalReport / MedicalReportMetric
│   │           ├── schemas.py
│   │           ├── service.py  # 编排：存图→调 vision→落库
│   │           ├── vision.py   # Azure GPT-4.5-mini vision 调用 + JSON 兜底
│   │           └── prompts.py  # vision prompt 模板
│   └── data/                   # 运行期数据（git 忽略），分两个挂载点
│       ├── db/pika.db          # SQLite（单独挂载）
│       └── uploads/            # 原图（单独挂载）
└── miniprogram/                # 微信小程序（页面按模块分组）
```

**分层原则**：`core/` 不依赖 `modules/`；新模块只需在 `modules/` 下新建目录并在 `main.py` 挂载 router。

---

## 第 2 步：数据库 schema（SQLite，设计成通用）

**`users`**（core，平台级，故用泛名）：`id` / `openid`(UNIQUE) / `nickname`（如「岳母」「我」）/ `role` / `created_at`

> **users 表意图（微信登录如何识别用户）**：微信小程序 `wx.login()` 拿到临时 `code` → 后端用 `code + AppID + AppSecret` 调微信 `jscode2session` 换回该用户的 `openid`（微信给的、该用户在本小程序内唯一且不变的身份ID）。后端把 openid 存进 users 表，下次该用户登录就能认出「这是谁」，从而标记「谁上传的」、dashboard 显示「看谁的检查」。`nickname` 由用户首次进入时填写或授权获取微信昵称。**POC 不做权限**，全家共享可见可传，users 表只用于「识别 + 显示」，不用于鉴权。这是平台级表，未来所有模块共用同一套家庭成员。

**`medical_reports`**（医疗模块·检查单主表，加 `medical_` 前缀避免未来撞名）：`id` / `uploader_id`(FK users) / `subject_id`(FK users, 可空，留「这单是谁的体检」扩展) / `report_type`(如 blood_routine/unknown) / `report_type_label`(如「血常规」) / `report_date`(可空) / `image_path`(原图相对路径) / `status`(uploaded/parsing/parsed/failed) / `raw_json`(vision 原始返回留档) / `created_at`

**`medical_report_metrics`**（医疗模块·指标明细，一对多）：`id` / `report_id`(FK medical_reports, CASCADE) / `item_name`(「白细胞计数」) / `item_code`(「WBC」, 跨单趋势对齐用) / `value_text`(应对「阴性」「+」) / `value_num`(数值, 画图用) / `unit` / `ref_range`(原文「3.5-9.5」) / `ref_low` / `ref_high` / `abnormal_flag`(high/low/normal/unknown) / `seq`

索引：`medical_reports(subject_id, report_type, report_date)`、`medical_report_metrics(report_id, item_code)`。

设计要点：`value_text`+`value_num` 双字段兼容定性结果；`item_code` 是跨多张单子聚合趋势的关键。**未来扩展新模块的表，沿用 `<模块>_` 前缀规范。**

---

## 第 3 步：API 接口（FastAPI）

统一响应 `{"code":0,"msg":"ok","data":{...}}`；身份用登录拿到的 token（POC 阶段 token 可直接=openid，请求带 `header: X-Pika-Token`）。

- `POST /api/auth/login` — body `{code, nickname?}`；后端调微信 jscode2session 换 openid，upsert users，返回 `{token, user}`。
- `POST /api/medical/reports` — multipart：`file`(图) + `report_date?` + `subject_id?`；存原图 → 调 vision 解析 → 写 medical_reports + medical_report_metrics → 返回 `{report, metrics}`。**解析失败仍落 medical_reports(status=failed)，绝不丢原图**。
- `GET /api/medical/reports?subject_id=&report_type=&page=&size=` — 历史列表（含 uploader_nickname、abnormal_count、缩略图入口）。
- `GET /api/medical/reports/{id}` — 单张详情（report + 全部 metrics）。
- `GET /api/medical/reports/{id}/image` — 返回原图二进制（StreamingResponse）。前端只通过此端点取图，不直接接触文件路径。
- `GET /api/medical/metrics/trend?item_code=&subject_id=` — 某指标按 report_date 升序的历史点 `[{report_date, value_num, abnormal_flag, report_id}]` + ref_low/ref_high，供画折线 + 参考范围带。
- `GET /api/medical/metrics/catalog?subject_id=` —（可选）指标字典，给趋势页做选择列表。

---

## 第 4 步：GPT-4.5-mini Vision 解析（modules/medical/vision.py）

- **库**：`openai` SDK 的 `AzureOpenAI` client。环境变量：`AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_API_VERSION` / `AZURE_OPENAI_DEPLOYMENT`（部署名）。**key 只在后端**。
- **调用**：图片 base64 → data URL，`chat.completions.create(model=deployment, messages=[system, user(text+image_url)], response_format={"type":"json_object"}, temperature=0)`。
- **Prompt 思路**（prompts.py）：「你是医学检验报告结构化助手，提取所有检查项目，**只输出 JSON 不要解释**，无法识别填 null 不要编造，日期 YYYY-MM-DD」+ 明确给出期望 JSON schema。
- **期望 JSON**：`{report_type, report_type_label, report_date, metrics:[{item_name, item_code, value, unit, ref_range, abnormal_flag}]}`。
- **兜底（关键，模型不可靠）**：①`json_object` 强制 JSON；②解析失败用正则抠 `{...}` 重试；③缺字段降级（metrics 缺→空列表，单条缺 item_name→跳过）；④后处理：正则拆 ref_range 成 ref_low/high，value 尝试转 value_num（转不了只存 value_text），按 value vs ref 校正 abnormal_flag；⑤原始返回存 `reports.raw_json`；⑥整体失败 status=failed，保留原图，前端可重试。

---

## 第 5 步：原图存储（core/storage.py）

- 容器内路径 `/app/data/uploads/medical/{YYYY}/{MM}/`（`medical` 是模块名层级，未来别的模块用 `uploads/<模块>/`；其下再按年月分目录）。
- compose 把 NAS 目录 `/volume1/Projects/Pika/data/uploads/medical` 映射到容器 `/app/data/uploads/medical`，原图长期保存在 NAS（SMB 可见）。
- 命名防冲突：`{YYYYMMDD_HHMMSS}_{uuid4前8位}.{ext}`，扩展名由 MIME/Pillow 探测、统一小写。
- 数据库存**相对路径**（`uploads/medical/2026/05/xxx.jpg`），绝对路径由 `settings.UPLOAD_DIR` 读取时拼接，便于迁移。

---

## 第 6 步：Docker 部署（绿联）

### 哪些数据需要 mount 到 NAS（重要）

容器可随时删除重建 → **任何重建后不能丢的数据都必须挂到 NAS 外部目录**。本项目需持久化两类，**分开挂载**（职责清晰、可分别备份）：

| 数据 | 容器内路径 | NAS 挂载 | 为什么 |
|------|-----------|----------|--------|
| **原图** | `/app/data/uploads/medical` | NAS `/volume1/Projects/Pika/data/uploads/medical` | 用户要求长期保存的 raw 图片，丢失无法恢复；按模块分目录、可单独备份 |
| **SQLite 库** | `/app/data/db` | NAS `/volume1/Projects/Pika/data/db` | 所有结构化记录，丢失全没；与原图分开便于单独备份/迁移 |
| 代码/依赖 | — | ❌ 不挂 | 打进镜像，重建时重新构建 |
| 凭据 | — | ❌ 不挂 | 走绿联 environment 注入（见下），不落盘不入库 |

绿联部署要点：compose 的 `build.context` 用 `.`，所有文件放在绿联创建的共享目录内（与本次 medical-test 验证一致）。

```yaml
services:
  pika-backend:
    build: { context: ., dockerfile: Dockerfile }
    container_name: pika-backend
    ports: ["8000:8000"]
    volumes:
      - /volume1/Projects/Pika/data/uploads/medical:/app/data/uploads/medical  # 原图，单独挂载
      - /volume1/Projects/Pika/data/db:/app/data/db                            # SQLite，单独挂载
    environment:                              # 凭据由绿联界面 environment 注入，不入 git
      - TZ=Asia/Shanghai
      - DATA_DIR=/app/data
      - UPLOAD_DIR=/app/data/uploads/medical
      - DB_PATH=/app/data/db/pika.db
      - WX_APPID=${WX_APPID}
      - WX_SECRET=${WX_SECRET}
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
      - AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION}
      - AZURE_OPENAI_DEPLOYMENT=${AZURE_OPENAI_DEPLOYMENT}
    restart: unless-stopped
```

`Dockerfile`：`python:3.11-slim` → 装 `backend/requirements.txt` → `COPY backend/ /app/` → `uvicorn app.main:app --host 0.0.0.0 --port 8000`。

**凭据注入方式（已确认）**：Azure key / 微信 AppSecret 等真实值**直接填在绿联 Docker compose 界面的 environment 字段**，不写进任何文件、不入 git。代码侧 `settings.py` 用 pydantic-settings 从环境变量读取。仓库里只放 `.env.example` 样例（占位符）。

---

## 第 7 步：微信小程序（miniprogram/）

- **注册**：mp.weixin.qq.com 个人主体注册，拿 AppID（计划执行时第一步引导）。
- **config.js**：集中放 `BASE_URL = 'http://192.168.1.3:8000'`（局域网 NAS IP）。
- **页面**（按模块分组，便于未来扩展）：`pages/index`（平台首页，做成可扩展的模块入口卡片）；医疗模块放 `pages/medical/` 下：`upload`（chooseMedia 拍照选图 → uploadFile）/ `history`（列表）/ `report-detail`（指标表 + 原图，异常红色高亮）/ `metric-trend`（选指标 → 趋势图）。未来新模块加 `pages/<模块>/`。
- **登录**：`app.js onLaunch` 里 `wx.login` 拿 code → POST `/api/auth/login` → token 存 `wx.setStorageSync`，后续请求带 `X-Pika-Token`（封装在 `utils/request.js`）。
- **上传**：`wx.uploadFile({url: BASE_URL+'/api/medical/reports', filePath, name:'file', formData:{report_date}})`。
- **趋势图**：`components/trend-chart/` 封装 `ec-canvas`（ECharts 小程序版），折线 + markArea 画参考范围带 + 异常点红色 markPoint。

---

## 实施顺序（依赖排序）

1. 清理 Pika，重建骨架，改 `.gitignore` + 重写 CLAUDE.md，新 commit。
2. core：settings → db → models_base(User) → wechat → storage。
3. medical：models → schemas → vision/prompts → service → router。
4. main.py 挂载，本地 `uvicorn` 跑通 login + 上传解析。
5. Dockerfile + compose，绿联部署，挂载 NAS 卷验证落图/落库。
6. 小程序：注册 AppID → auth → upload → history → detail → trend。

---

## 验证方式（端到端）

1. **后端本地**：`uvicorn app.main:app --reload`，用 `curl -F file=@血常规.jpg http://localhost:8000/api/medical/reports` 验证存图 + 解析 + 落库；查 db 文件和 uploads/medical/ 目录确认。
2. **NAS 部署**：绿联起容器后，局域网另一台机 `curl http://192.168.1.3:8000/api/medical/reports?...` 验证；SMB 进 NAS `/volume1/Projects/Pika/data/uploads/medical` 确认原图落盘、`/volume1/Projects/Pika/data/db` 确认库文件。
3. **小程序**：开发者工具勾「不校验合法域名」，连 `http://192.168.1.3:8000`，真机预览跑通「拍照上传 → 看到解析结果 → 历史列表 → 详情 → 某指标趋势图」。
4. **解析质量**：用几张真实血常规单测 vision 准确率，不准就调 prompt / 加后处理规则；确认失败单子原图不丢、可重试。

---

## 后续阶段（本次不做，仅备注）

- 公网 HTTPS 域名（让岳母真机随时随地用）：体验版/正式版的前置条件，方案到时再选（如备案域名 + 反代、或借 Hermes 已有网关）。
- 更多检查类型（肝功能、尿检等）：schema 已通用，主要靠 vision prompt 扩展。
- 更多家庭模块：在 `modules/` 下新增。
