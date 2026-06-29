from pathlib import Path

import pytest

from scripts.medical_bulk_import import ApiError, run_bulk_import


class DummyResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class DummyClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def request(self, method, url, headers=None, **kwargs):
        self.calls.append({"method": method, "url": url, "headers": headers, "kwargs": kwargs})
        if not self.responses:
            raise AssertionError("no more responses")
        next_item = self.responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item


def _ok(data):
    return DummyResponse(200, {"code": 0, "msg": "ok", "data": data})


def _err(code, msg):
    return DummyResponse(200, {"code": code, "msg": msg, "data": None})


@pytest.fixture
def sample_folder(tmp_path: Path):
    (tmp_path / "a.png").write_bytes(b"a")
    (tmp_path / "b.jpg").write_bytes(b"b")
    return tmp_path


def _members_payload(*items):
    return {"items": list(items)}


def test_resolve_subject_and_import_success(sample_folder: Path):
    client = DummyClient(
        [
            _ok({"family_id": 1}),
            _ok(
                _members_payload(
                    {"id": 1, "nickname": "saiy", "family_role": "admin", "status": "active"},
                    {"id": 2, "nickname": "小石榴", "family_role": "member", "status": "active"},
                )
            ),
            _ok(
                {
                    "draft_id": "d1",
                    "report_type": "blood",
                    "report_type_label": "血常规",
                    "report_date": "2026-06-01",
                    "hospital": "北京大学国际医院",
                    "metrics": [],
                }
            ),
            _ok({"report": {"id": 101}}),
            _ok(
                {
                    "draft_id": "d2",
                    "report_type": "blood",
                    "report_type_label": "血常规",
                    "report_date": "2026-06-02",
                    "hospital": None,
                    "metrics": [],
                }
            ),
            _ok({"report": {"id": 102}}),
        ]
    )

    report = run_bulk_import(
        client,
        folder=sample_folder,
        token="tok",
        subject_nickname="小石榴",
        base_url="http://192.168.1.200:8000",
        dry_run=False,
        limit=None,
    )

    assert report["subject_id"] == 2
    assert report["summary"] == {"total": 2, "success": 2, "duplicate_skipped": 0, "failed": 0}

    # verify hospital comes from OCR draft (second one is None)
    commit_calls = [c for c in client.calls if c["url"].endswith("/commit")]
    assert commit_calls[0]["kwargs"]["json"]["hospital"] == "北京大学国际医院"
    assert commit_calls[1]["kwargs"]["json"]["hospital"] is None


def test_duplicate_4090_is_skipped(sample_folder: Path):
    client = DummyClient(
        [
            _ok({"family_id": 1}),
            _ok(
                _members_payload(
                    {"id": 2, "nickname": "小石榴", "family_role": "member", "status": "active"},
                )
            ),
            _err(4090, "该检查单已存在，请勿重复上传"),
            _ok(
                {
                    "draft_id": "d2",
                    "report_type": "blood",
                    "report_type_label": "血常规",
                    "report_date": "2026-06-02",
                    "hospital": None,
                    "metrics": [],
                }
            ),
            _ok({"report": {"id": 102}}),
        ]
    )

    report = run_bulk_import(
        client,
        folder=sample_folder,
        token="tok",
        subject_nickname="小石榴",
        base_url="http://192.168.1.200:8000",
        dry_run=False,
        limit=None,
    )

    assert report["summary"] == {"total": 2, "success": 1, "duplicate_skipped": 1, "failed": 0}
    assert any(item.status == "duplicate_skipped" and item.api_code == 4090 for item in report["results"])


def test_subject_not_found_raises(sample_folder: Path):
    client = DummyClient(
        [
            _ok({"family_id": 1}),
            _ok(_members_payload({"id": 1, "nickname": "saiy", "family_role": "admin", "status": "active"})),
        ]
    )

    with pytest.raises(ValueError, match="未找到昵称"):
        run_bulk_import(
            client,
            folder=sample_folder,
            token="tok",
            subject_nickname="小石榴",
            base_url="http://192.168.1.200:8000",
            dry_run=False,
            limit=None,
        )


def test_subject_name_conflict_raises(sample_folder: Path):
    client = DummyClient(
        [
            _ok({"family_id": 1}),
            _ok(
                _members_payload(
                    {"id": 2, "nickname": "小石榴", "family_role": "member", "status": "active"},
                    {"id": 3, "nickname": "小石榴", "family_role": "member", "status": "active"},
                )
            ),
        ]
    )

    with pytest.raises(ValueError, match="昵称冲突"):
        run_bulk_import(
            client,
            folder=sample_folder,
            token="tok",
            subject_nickname="小石榴",
            base_url="http://192.168.1.200:8000",
            dry_run=False,
            limit=None,
        )


def test_dry_run_no_medical_write_calls(sample_folder: Path):
    client = DummyClient(
        [
            _ok({"family_id": 1}),
            _ok(_members_payload({"id": 2, "nickname": "小石榴", "family_role": "member", "status": "active"})),
        ]
    )

    report = run_bulk_import(
        client,
        folder=sample_folder,
        token="tok",
        subject_nickname="小石榴",
        base_url="http://192.168.1.200:8000",
        dry_run=True,
        limit=None,
    )

    assert report["planned"] == 2
    assert report["summary"] == {"total": 2, "success": 0, "duplicate_skipped": 0, "failed": 0}
    assert all("/api/medical/" not in c["url"] for c in client.calls)


def test_non_duplicate_api_error_marked_failed(sample_folder: Path):
    client = DummyClient(
        [
            _ok({"family_id": 1}),
            _ok(_members_payload({"id": 2, "nickname": "小石榴", "family_role": "member", "status": "active"})),
            _err(5001, "vision parse failed"),
            _ok(
                {
                    "draft_id": "d2",
                    "report_type": "blood",
                    "report_type_label": "血常规",
                    "report_date": "2026-06-02",
                    "hospital": None,
                    "metrics": [],
                }
            ),
            _ok({"report": {"id": 102}}),
        ]
    )

    report = run_bulk_import(
        client,
        folder=sample_folder,
        token="tok",
        subject_nickname="小石榴",
        base_url="http://192.168.1.200:8000",
        dry_run=False,
        limit=None,
    )

    assert report["summary"] == {"total": 2, "success": 1, "duplicate_skipped": 0, "failed": 1}
    failed = [item for item in report["results"] if item.status == "failed"]
    assert failed and failed[0].api_code == 5001
