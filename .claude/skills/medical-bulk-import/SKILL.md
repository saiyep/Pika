---
name: medical-bulk-import
description: 离线批量插入检查单：给目录、被检查人昵称和 token，按一图一报告逐张执行 draft→commit，自动处理重复跳过并输出汇总。
---

# Medical Bulk Import (离线批量插入检查单)

用于把本地目录下的检查单图片按 **一图一报告** 批量入库，减少手工重复录入。

## 目标

1. 标准化离线导入流程（成员解析、目录扫描、逐张导入、结果汇总）。
2. 复用现有两阶段接口：`report-drafts` → `commit`。
3. 遇到重复（`code=4090`）自动跳过并继续，不中断整批。

## 必填输入

- `folder`：本地图片目录。
- `subject_nickname`：被检查人昵称（用于解析 `subject_id`）。
- `token`：请求头 `X-Pika-Token`。

## 可选输入

- `base_url`：后端地址，默认 `http://192.168.1.200:8000`。
- `dry_run`：只做成员/文件预检查，不执行写入。
- `limit`：仅处理前 N 张图片（按排序后顺序）。

## 从图片提取并提交的信息（commit payload）

- `report_date`：报告日期（OCR 结果）。
- `report_type` / `report_type_label`：报告类别（OCR 结果）。
- `metrics[]`：指标数组（名称、值、单位、参考范围、异常标记）。
- `hospital`：医院（OCR 结果；若缺失则保持空值，后续人工编辑）。
- `subject_id`：通过昵称映射解析得到。

## 执行步骤

1. 调用 `/api/user/whoami` 与 `/api/user/members`，生成并打印成员映射表：
   - `user_id, nickname, family_id, family_role, is_active`
2. 用 `subject_nickname` 解析唯一且 active 的 `subject_id`。
   - 找不到或重名冲突直接停止，避免导错人。
3. 扫描目录（递归）并按文件名稳定排序。
4. 逐张处理：
   - `POST /api/medical/report-drafts`（单文件）
   - `POST /api/medical/report-drafts/{draft_id}/commit`
5. 汇总输出：`total/success/duplicate_skipped/failed` + 失败清单。

## 命令模板

```bash
cd backend
python scripts/medical_bulk_import.py \
  --folder "D:/path/to/reports" \
  --subject-nickname "小石榴" \
  --token "<X-Pika-Token>"
```

```bash
cd backend
python scripts/medical_bulk_import.py \
  --folder "D:/path/to/reports" \
  --subject-nickname "小石榴" \
  --token "<X-Pika-Token>" \
  --dry-run \
  --limit 5
```

## 红线

- 不覆盖医院为固定值；医院仅使用 OCR 结果（可为空）。
- 不绕过昵称解析直接写死 `subject_id`（除非调用方明确指定）。
- 不在导入中断时伪报成功；必须如实输出失败与跳过明细。