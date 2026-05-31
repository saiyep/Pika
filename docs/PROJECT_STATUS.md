# Pika 项目状态与历史（接续上下文用）

> 这份文档让任何新的 Claude Code / 开发会话在 Pika 目录下能无缝续上。
> 配合根目录 `CLAUDE.md`（架构/约定/部署）一起读。

## 一句话现状

Pika 已从旧的 Azure Functions 健康数据项目**重置**为「家庭服务平台」，第一个模块「医疗就诊辅助」的 **POC 骨架已全部写好并本地验证通过**，已提交 commit `chore: reset Pika to family-service platform`。**还没在 NAS 上真正部署、没接真实 Azure key、小程序还没注册 AppID。**

## 项目背景（为什么做）

- 用户的岳母常去医院做检查（大检查 X光/核磁，小检查血常规/肝功能），单据多难追踪。
- 目标：岳母用微信小程序上传检查单照片 → 后端自动解析结构化 → dashboard 随时查看 + 按指标看趋势。
- 更大定位：跑在家用 NAS（绿联 DH4300plus，Docker）上的**家庭服务平台**，会持续扩展更多家庭模块；医疗是第一个。

## 已确定的技术栈与决策

- 后端 Python + FastAPI + SQLite；解析用 **Azure AI Foundry 的 GPT-4.5-mini（vision 视觉识别）**。
- 前端原生微信小程序，内置 dashboard。
- **趋势图用小程序原生 Canvas 2D 手绘**（折线+参考范围带+异常红点），**没用 ec-canvas/ECharts**——因为 ECharts 小程序版要 vendor 几百 KB 库文件，POC 阶段原生 canvas 零依赖即开即用。未来要更丰富交互再换。
- 平台分层：`backend/app/core/`（平台公共：用户身份、存储、db）+ `backend/app/modules/medical/`（业务）。
- **表名带模块前缀**：`medical_reports` / `medical_report_metrics`；`users` 是平台级共享表（core，泛名）。未来模块沿用 `<模块>_` 前缀。
- **POC 无权限**：全家共享可看可传，用微信 openid 只做「识别+显示谁传的」，不鉴权。
- **关键不变式：vision 解析失败也绝不丢原图**——report 仍落库 status=failed，原图照常保存，前端可重试。

## NAS / 环境关键信息

- 绿联 NAS DH4300plus，UGREENlink ID `dh4300plus-d2e0`，局域网 IP 约 `192.168.1.3`，带 Docker 可视化界面。
- **绿联 compose 坑**：部署时 `build.context` 必须用 `.`（相对当前目录），文件要放在绿联创建的共享目录里，否则报 "failed to read dockerfile"。
- **绿联 UGREENlink 不支持自定义端口映射**，只暴露管理端口（9999/9443）→ 自建服务端口无法靠 ug.link 公网访问。所以公网方案是后续阶段的难点。
- 已有容器：Hermes（连了微信 Clawbot，通过 Hermes 自带 gateway setup 扫码连微信）、kspeeder。
- Azure AI Foundry 上部署了 GPT-4.5-mini（支持 vision）。Hermes 当前也连的这个模型。

## 微信小程序版本约束（重要，决定 POC 能走多远）

- 个人 AppID 免费注册够用（不能用微信支付，本项目不需要）。
- **开发版**连局域网 IP：开发者工具「详情→本地设置」勾「不校验合法域名」即可请求 `http://192.168.1.3:8000`。仅开发期+项目成员有效。
- 普通预览二维码只有开发者本人能扫；家人要用需加为「开发/体验成员」（约 15 名），且只在你家 WiFi 内能连局域网 IP。
- **体验版/正式版强制 HTTPS 合法域名** → 给岳母随时随地真机用，必须等公网阶段。

## 已完成（本次会话）

1. 清理旧 Azure 代码，保留 .git 历史，重写 `.gitignore` 和 `CLAUDE.md`。
2. 后端 core 层：settings / db / models_base(User) / wechat(jscode2session) / storage / schemas_base / exceptions / deps / auth_router。
3. 医疗模块：models(MedicalReport/MedicalReportMetric) / schemas / prompts / vision(GPT-4.5-mini + JSON兜底+ref拆解+异常判定) / service(编排,不丢图) / router。
4. main.py 挂载、requirements.txt、Dockerfile、docker-compose.yml、.env.example。
5. 小程序：app/config/utils(request,auth) + 首页 + medical 下 upload/history/report-detail/metric-trend 五个页面。
6. **本地端到端验证通过**：上传（无 key 走失败兜底，原图仍落盘 `data/uploads/medical/2026/05/...`）、历史列表、详情、鉴权(无 token→401)、12 条路由注册成功。
7. 提交 commit。

## 待办（下次接着做）

1. **填真实凭据**：绿联 compose 的 environment 填 Azure（endpoint/key/api_version/deployment）+ 微信（AppID/Secret）；小程序 `miniprogram/config.js` 填 NAS 局域网 IP。
2. **注册微信小程序个人 AppID**，填进 `miniprogram/project.config.json`（当前是占位符 REPLACE_WITH_YOUR_APPID）。
3. **绿联部署后端**：Pika 目录放进绿联共享目录 → compose 部署（注意 build.context: . 的坑）→ 确认两个挂载点 `/volume1/Projects/Pika/data/uploads/medical` 和 `/volume1/Projects/Pika/data/db` 生效。
4. **开发者工具勾「不校验合法域名」**，连局域网 IP，拿真实血常规单测 vision 解析质量，不准就调 `backend/app/modules/medical/prompts.py` 或加后处理。
5. 把家人加为开发成员，在家 WiFi 内真机预览跑通全流程。
6. （后续阶段）公网 HTTPS 域名方案；更多检查类型；更多家庭模块。

## 验证命令（本地后端自测）

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # 或 source .venv/bin/activate
pip install -r requirements.txt
# 本地跑（路径用环境变量覆盖到本地 data/）
DATA_DIR=./data UPLOAD_DIR=./data/uploads/medical DB_PATH=./data/db/pika.db uvicorn app.main:app --reload
# 健康检查
curl http://127.0.0.1:8000/health
# 上传需要 X-Pika-Token（POC: token==openid），可先手动插一个 user 再测
```

## 关键文件位置

- 后端入口：`backend/app/main.py`
- vision 解析（调 prompt/兜底）：`backend/app/modules/medical/vision.py`、`prompts.py`
- 业务编排（不丢图逻辑）：`backend/app/modules/medical/service.py`
- 原图存储策略：`backend/app/core/storage.py`
- 部署：根目录 `Dockerfile`、`docker-compose.yml`
- 小程序后端地址配置：`miniprogram/config.js`
- 完整设计计划：`docs/IMPLEMENTATION_PLAN.md`
