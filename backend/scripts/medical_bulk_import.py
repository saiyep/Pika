from __future__ import annotations

import argparse
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".heic", ".heif"}


class ApiError(Exception):
    def __init__(self, message: str, *, api_code: int | None = None, http_status: int | None = None):
        super().__init__(message)
        self.api_code = api_code
        self.http_status = http_status


@dataclass
class ImportResult:
    file_path: str
    status: str
    message: str
    api_code: int | None = None
    report_id: int | None = None


@dataclass
class MemberRow:
    user_id: int
    nickname: str
    family_id: int | None
    family_role: str | None
    is_active: bool


def _request_api(
    client: Any,
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    **kwargs: Any,
) -> Any:
    resp = client.request(method=method, url=url, headers=headers, **kwargs)

    status_code = getattr(resp, "status_code", None)
    if status_code is None:
        raise ApiError("invalid response object")

    try:
        payload = resp.json()
    except Exception as exc:
        raise ApiError(f"response is not json (http {status_code})", http_status=status_code) from exc

    if not isinstance(payload, dict):
        raise ApiError(f"unexpected response payload (http {status_code})", http_status=status_code)

    code = payload.get("code")
    msg = payload.get("msg")
    data = payload.get("data")

    if status_code != 200:
        raise ApiError(str(msg or "http request failed"), api_code=code, http_status=status_code)

    if code != 0:
        raise ApiError(str(msg or "api request failed"), api_code=code, http_status=status_code)

    return data


def _fetch_member_rows(client: Any, *, base_url: str, headers: dict[str, str]) -> list[MemberRow]:
    whoami = _request_api(
        client,
        method="GET",
        url=f"{base_url}/api/user/whoami",
        headers=headers,
    )
    family_id = whoami.get("family_id") if isinstance(whoami, dict) else None

    member_out = _request_api(
        client,
        method="GET",
        url=f"{base_url}/api/user/members",
        headers=headers,
    )

    items = member_out.get("items") if isinstance(member_out, dict) else None
    if not isinstance(items, list):
        raise ValueError("/api/user/members 返回格式异常")

    rows: list[MemberRow] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        user_id = item.get("id")
        if not isinstance(user_id, int):
            continue
        rows.append(
            MemberRow(
                user_id=user_id,
                nickname=str(item.get("nickname") or ""),
                family_id=family_id,
                family_role=item.get("family_role"),
                is_active=str(item.get("status") or "").lower() == "active",
            )
        )

    return rows


def _resolve_subject_id(rows: list[MemberRow], nickname: str) -> int:
    exact_active = [r for r in rows if r.is_active and r.nickname == nickname]
    if len(exact_active) == 1:
        return exact_active[0].user_id
    if len(exact_active) > 1:
        conflict_ids = ", ".join(str(r.user_id) for r in exact_active)
        raise ValueError(f"昵称冲突（active 重名）: {nickname} -> {conflict_ids}")

    exact_all = [r for r in rows if r.nickname == nickname]
    if exact_all:
        raise ValueError(f"昵称 {nickname} 存在但均非 active，无法导入")

    raise ValueError(f"未找到昵称: {nickname}")


def _scan_images(folder: Path, *, limit: int | None) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"目录不存在或不可用: {folder}")

    files = [
        p
        for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    files.sort(key=lambda p: str(p.relative_to(folder)).lower())

    if limit is not None and limit >= 0:
        files = files[:limit]

    return files


def _build_draft_payload(file_path: Path) -> tuple[list[tuple[str, tuple[str, bytes, str]]], dict[str, str]]:
    content = file_path.read_bytes()
    guessed = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    files = [("files", (file_path.name, content, guessed))]
    data: dict[str, str] = {}
    return files, data


def _format_member_table(rows: list[MemberRow]) -> str:
    headers = ["user_id", "nickname", "family_id", "family_role", "is_active"]
    lines = [
        "  ".join(headers),
        "  ".join(["-------", "--------", "---------", "-----------", "---------"]),
    ]
    for row in rows:
        lines.append(
            "  ".join(
                [
                    str(row.user_id),
                    row.nickname or "",
                    "" if row.family_id is None else str(row.family_id),
                    row.family_role or "",
                    "1" if row.is_active else "0",
                ]
            )
        )
    return "\n".join(lines)


def run_bulk_import(
    client: Any,
    *,
    folder: Path,
    token: str,
    subject_nickname: str,
    base_url: str,
    dry_run: bool,
    limit: int | None,
) -> dict[str, Any]:
    headers = {"X-Pika-Token": token}
    rows = _fetch_member_rows(client, base_url=base_url, headers=headers)
    subject_id = _resolve_subject_id(rows, subject_nickname)
    image_files = _scan_images(folder, limit=limit)

    if not image_files:
        raise ValueError("目录下没有可导入的图片")

    results: list[ImportResult] = []
    if dry_run:
        return {
            "rows": rows,
            "subject_id": subject_id,
            "planned": len(image_files),
            "results": results,
            "summary": {
                "total": len(image_files),
                "success": 0,
                "duplicate_skipped": 0,
                "failed": 0,
            },
        }

    for file_path in image_files:
        rel_path = str(file_path.relative_to(folder))
        try:
            files, data = _build_draft_payload(file_path)
            data["subject_id"] = str(subject_id)
            draft = _request_api(
                client,
                method="POST",
                url=f"{base_url}/api/medical/report-drafts",
                headers=headers,
                files=files,
                data=data,
            )
            draft_id = draft.get("draft_id") if isinstance(draft, dict) else None
            if not draft_id:
                raise ValueError("draft_id 缺失")

            commit_payload = {
                "subject_id": subject_id,
                "report_type": draft.get("report_type") or "unknown",
                "report_type_label": draft.get("report_type_label"),
                "report_date": draft.get("report_date"),
                "hospital": draft.get("hospital"),
                "metrics": draft.get("metrics") or [],
            }

            committed = _request_api(
                client,
                method="POST",
                url=f"{base_url}/api/medical/report-drafts/{draft_id}/commit",
                headers=headers,
                json=commit_payload,
            )
            report = committed.get("report") if isinstance(committed, dict) else None
            report_id = report.get("id") if isinstance(report, dict) else None
            results.append(
                ImportResult(
                    file_path=rel_path,
                    status="success",
                    message="ok",
                    report_id=report_id if isinstance(report_id, int) else None,
                )
            )
        except ApiError as exc:
            if exc.api_code == 4090:
                results.append(
                    ImportResult(
                        file_path=rel_path,
                        status="duplicate_skipped",
                        message=str(exc),
                        api_code=exc.api_code,
                    )
                )
            else:
                results.append(
                    ImportResult(
                        file_path=rel_path,
                        status="failed",
                        message=str(exc),
                        api_code=exc.api_code,
                    )
                )
        except Exception as exc:  # noqa: BLE001
            results.append(
                ImportResult(
                    file_path=rel_path,
                    status="failed",
                    message=str(exc),
                )
            )

    summary = {
        "total": len(results),
        "success": sum(1 for item in results if item.status == "success"),
        "duplicate_skipped": sum(1 for item in results if item.status == "duplicate_skipped"),
        "failed": sum(1 for item in results if item.status == "failed"),
    }
    return {
        "rows": rows,
        "subject_id": subject_id,
        "planned": len(image_files),
        "results": results,
        "summary": summary,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="离线批量插入检查单（一图一报告）")
    parser.add_argument("--folder", required=True, help="图片目录")
    parser.add_argument("--token", required=True, help="X-Pika-Token")
    parser.add_argument("--subject-nickname", required=True, help="被检查人昵称")
    parser.add_argument("--base-url", default="http://192.168.1.200:8000", help="后端地址")
    parser.add_argument("--dry-run", action="store_true", help="仅预检查，不写入")
    parser.add_argument("--limit", type=int, default=None, help="最多处理 N 张图片")
    return parser


def _print_report(report: dict[str, Any]) -> None:
    rows: list[MemberRow] = report["rows"]
    print("成员映射表:")
    print(_format_member_table(rows))
    print(f"解析 subject_id: {report['subject_id']}")
    print(f"待处理图片: {report['planned']}")

    if report["results"]:
        print("\n逐文件结果:")
        for item in report["results"]:
            code_text = f" (code={item.api_code})" if item.api_code is not None else ""
            rid_text = f" report_id={item.report_id}" if item.report_id is not None else ""
            print(f"- {item.file_path}: {item.status}{code_text} - {item.message}{rid_text}")

    summary = report["summary"]
    print("\n汇总:")
    print(
        f"total={summary['total']} success={summary['success']} "
        f"duplicate_skipped={summary['duplicate_skipped']} failed={summary['failed']}"
    )


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    base_url = str(args.base_url).rstrip("/")

    try:
        with httpx.Client(timeout=60.0) as client:
            report = run_bulk_import(
                client,
                folder=folder,
                token=args.token,
                subject_nickname=args.subject_nickname,
                base_url=base_url,
                dry_run=bool(args.dry_run),
                limit=args.limit,
            )
    except Exception as exc:  # noqa: BLE001
        print(f"执行失败: {exc}")
        return 1

    _print_report(report)
    if report["summary"]["failed"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
