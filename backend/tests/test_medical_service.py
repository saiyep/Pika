import pytest

from app.core.user.models import User
from app.modules.medical import service, vision


@pytest.fixture
def user(db_session):
    u = User(openid="test-openid", nickname="tester")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def tmp_upload(monkeypatch, tmp_path):
    # Redirect image storage to a temp dir so tests don't touch real uploads.
    from app.core import storage
    monkeypatch.setattr(storage.settings, "upload_dir", str(tmp_path))
    return tmp_path


_FAKE_PARSED = {
    "is_lab_report": True,
    "report_type": "blood",
    "report_type_label": "血常规",
    "report_date": "2026-05-01",
    "hospital": None,
    "metrics": [
        {
            "item_name": "WBC", "item_code": "WBC", "value_text": "11",
            "value_num": 11.0, "unit": "10^9/L", "ref_range": "4-9",
            "ref_low": 4.0, "ref_high": 9.0, "abnormal_flag": "high", "seq": 0,
        }
    ],
}


def test_draft_then_commit_persists_report(db_session, user, tmp_upload, monkeypatch):
    monkeypatch.setattr(vision, "parse_report_image", lambda b: (_FAKE_PARSED, "{}"))

    draft = service.create_draft_from_images(
        db_session,
        uploader_id=user.id,
        subject_id=None,
        files=[(b"\x89PNG\r\n\x1a\n fake", "a.png", "image/png")],
        hospital_override="北京协和医院",
    )
    assert draft["status"] == "parsed"
    assert draft["report_type"] == "blood"
    assert len(draft["metrics"]) == 1

    report = service.commit_draft(
        db_session,
        draft_id=draft["draft_id"],
        report_type=draft["report_type"],
        report_type_label=draft["report_type_label"],
        report_date=draft["report_date"],
        hospital=draft["hospital"],
        metrics=draft["metrics"],
    )

    assert report.id is not None
    assert report.hospital == "北京协和医院"
    assert report.status == "parsed"
    assert report.image_paths and len(report.image_paths) == 1
    assert report.image_path == report.image_paths[0]
    assert len(report.metrics) == 1
    assert report.metrics[0].item_name == "WBC"
    assert report.metrics[0].abnormal_flag == "high"


def test_multi_image_draft_keeps_all_paths(db_session, user, tmp_upload, monkeypatch):
    monkeypatch.setattr(vision, "parse_report_image", lambda b: (_FAKE_PARSED, "{}"))

    draft = service.create_draft_from_images(
        db_session,
        uploader_id=user.id,
        subject_id=None,
        files=[
            (b"\x89PNG\r\n\x1a\n one", "1.png", "image/png"),
            (b"\xff\xd8\xff two", "2.jpg", "image/jpeg"),
        ],
        hospital_override="某医院",
    )
    assert len(draft["image_paths"]) == 2


def test_vision_failure_marks_failed_but_keeps_image(db_session, user, tmp_upload, monkeypatch):
    def boom(_b):
        raise RuntimeError("azure down")

    monkeypatch.setattr(vision, "parse_report_image", boom)

    draft = service.create_draft_from_images(
        db_session,
        uploader_id=user.id,
        subject_id=None,
        files=[(b"\x89PNG\r\n\x1a\n fake", "a.png", "image/png")],
        hospital_override="X",
    )

    # Image is still saved; draft is marked failed with no metrics.
    assert draft["status"] == "failed"
    assert draft["metrics"] == []
    assert len(draft["image_paths"]) == 1


def test_commit_missing_draft_raises(db_session):
    with pytest.raises(ValueError):
        service.commit_draft(
            db_session,
            draft_id="does-not-exist",
            report_type="blood",
            report_type_label=None,
            report_date=None,
            hospital=None,
            metrics=[],
        )


def test_delete_report_removes_row_metrics_and_files(db_session, user, tmp_upload, monkeypatch):
    import os

    from app.core import storage
    from app.modules.medical.models import MedicalReportMetric

    monkeypatch.setattr(vision, "parse_report_image", lambda b: (_FAKE_PARSED, "{}"))

    draft = service.create_draft_from_images(
        db_session,
        uploader_id=user.id,
        subject_id=None,
        files=[(b"\x89PNG\r\n\x1a\n fake", "a.png", "image/png")],
        hospital_override="X",
    )
    report = service.commit_draft(
        db_session,
        draft_id=draft["draft_id"],
        report_type=draft["report_type"],
        report_type_label=draft["report_type_label"],
        report_date=draft["report_date"],
        hospital=draft["hospital"],
        metrics=draft["metrics"],
    )
    report_id = report.id
    img_abs = storage.abs_path(report.image_paths[0])
    assert os.path.exists(img_abs)

    ok = service.delete_report(db_session, report_id=report_id)

    assert ok is True
    assert db_session.get(service.MedicalReport, report_id) is None
    assert db_session.query(MedicalReportMetric).filter_by(report_id=report_id).count() == 0
    assert not os.path.exists(img_abs)


def test_delete_missing_report_returns_false(db_session):
    assert service.delete_report(db_session, report_id=99999) is False


def _commit(db_session, draft):
    return service.commit_draft(
        db_session,
        draft_id=draft["draft_id"],
        report_type=draft["report_type"],
        report_type_label=draft["report_type_label"],
        report_date=draft["report_date"],
        hospital=draft["hospital"],
        metrics=draft["metrics"],
    )


def test_duplicate_upload_rejected_after_commit(db_session, user, tmp_upload, monkeypatch):
    from app.core.exceptions import DuplicateReportError

    monkeypatch.setattr(vision, "parse_report_image", lambda b: (_FAKE_PARSED, "{}"))
    img = (b"\x89PNG\r\n\x1a\n same-bytes", "a.png", "image/png")

    draft = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=None, files=[img], hospital_override="X"
    )
    _commit(db_session, draft)

    # Same image again -> rejected before saving/parsing.
    with pytest.raises(DuplicateReportError):
        service.create_draft_from_images(
            db_session, uploader_id=user.id, subject_id=None, files=[img], hospital_override="X"
        )


def test_different_images_not_rejected(db_session, user, tmp_upload, monkeypatch):
    monkeypatch.setattr(vision, "parse_report_image", lambda b: (_FAKE_PARSED, "{}"))

    d1 = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=None,
        files=[(b"\x89PNG\r\n\x1a\n one", "1.png", "image/png")], hospital_override="X",
    )
    _commit(db_session, d1)

    # A different image -> allowed.
    d2 = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=None,
        files=[(b"\x89PNG\r\n\x1a\n two", "2.png", "image/png")], hospital_override="X",
    )
    assert d2["status"] == "parsed"


def test_content_hash_is_order_independent(db_session, user, tmp_upload, monkeypatch):
    monkeypatch.setattr(vision, "parse_report_image", lambda b: (_FAKE_PARSED, "{}"))
    a = (b"\x89PNG\r\n\x1a\n aaa", "a.png", "image/png")
    b = (b"\xff\xd8\xff bbb", "b.jpg", "image/jpeg")

    draft = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=None, files=[a, b], hospital_override="X"
    )
    _commit(db_session, draft)

    # Same two images in reversed order -> same hash -> rejected.
    from app.core.exceptions import DuplicateReportError
    with pytest.raises(DuplicateReportError):
        service.create_draft_from_images(
            db_session, uploader_id=user.id, subject_id=None, files=[b, a], hospital_override="X"
        )


def test_reparse_recovers_failed_report(db_session, user, tmp_upload, monkeypatch):
    # First upload fails (Azure down) -> report committed with status=failed.
    def boom(_b):
        raise RuntimeError("azure down")

    monkeypatch.setattr(vision, "parse_report_image", boom)
    draft = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=None,
        files=[(b"\x89PNG\r\n\x1a\n fail-then-ok", "a.png", "image/png")], hospital_override="X",
    )
    report = _commit(db_session, draft)
    assert report.status == "failed"
    assert len(report.metrics) == 0

    # Azure recovers -> reparse fills metrics and flips status.
    monkeypatch.setattr(vision, "parse_report_image", lambda b: (_FAKE_PARSED, "{}"))
    reparsed = service.reparse_report(db_session, report_id=report.id)

    assert reparsed.status == "parsed"
    assert len(reparsed.metrics) == 1
    assert reparsed.metrics[0].item_name == "WBC"
    assert reparsed.report_type == "blood"


def test_reparse_missing_report_returns_none(db_session):
    assert service.reparse_report(db_session, report_id=99999) is None


def test_hospital_falls_back_to_parsed_when_no_override(db_session, user, tmp_upload, monkeypatch):
    parsed = {**_FAKE_PARSED, "hospital": "北京协和医院"}
    monkeypatch.setattr(vision, "parse_report_image", lambda b: (parsed, "{}"))

    draft = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=None,
        files=[(b"\x89PNG\r\n\x1a\n h", "a.png", "image/png")], hospital_override=None,
    )
    assert draft["hospital"] == "北京协和医院"


def test_hospital_override_wins_over_parsed(db_session, user, tmp_upload, monkeypatch):
    parsed = {**_FAKE_PARSED, "hospital": "解析出的医院"}
    monkeypatch.setattr(vision, "parse_report_image", lambda b: (parsed, "{}"))

    draft = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=None,
        files=[(b"\x89PNG\r\n\x1a\n h2", "a.png", "image/png")], hospital_override="用户填的医院",
    )
    assert draft["hospital"] == "用户填的医院"


def test_is_lab_report_flag_passed_to_draft(db_session, user, tmp_upload, monkeypatch):
    parsed = {**_FAKE_PARSED, "is_lab_report": False, "metrics": []}
    monkeypatch.setattr(vision, "parse_report_image", lambda b: (parsed, "{}"))

    draft = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=None,
        files=[(b"\x89PNG\r\n\x1a\n notlab", "a.png", "image/png")], hospital_override="X",
    )
    assert draft["is_lab_report"] is False


def test_update_report_edits_header_and_metrics(db_session, user, tmp_upload, monkeypatch):
    monkeypatch.setattr(vision, "parse_report_image", lambda b: (_FAKE_PARSED, "{}"))
    draft = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=None,
        files=[(b"\x89PNG\r\n\x1a\n upd", "a.png", "image/png")], hospital_override="旧医院",
    )
    report = _commit(db_session, draft)

    updated = service.update_report(
        db_session,
        report_id=report.id,
        report_type="custom",
        report_type_label="自定义标签",
        report_date=None,
        hospital="新医院",
        metrics=[
            {"item_name": "WBC", "item_code": "WBC", "value_text": "15",
             "unit": "10^9/L", "ref_range": "4-9", "abnormal_flag": "unknown"}
        ],
    )

    assert updated.hospital == "新医院"
    assert updated.report_type_label == "自定义标签"
    assert len(updated.metrics) == 1
    # value re-derived from edited text: 15 > 9 -> high
    assert updated.metrics[0].value_num == 15.0
    assert updated.metrics[0].abnormal_flag == "high"


def test_update_missing_report_returns_none(db_session):
    assert service.update_report(
        db_session, report_id=99999, report_type="blood",
        report_type_label=None, report_date=None, hospital=None, metrics=[],
    ) is None


def test_subject_id_flows_draft_to_committed_report(db_session, user, tmp_upload, monkeypatch):
    # A second family member who is the subject of the report.
    mom = User(openid="mom-openid", nickname="妈妈")
    db_session.add(mom)
    db_session.commit()
    db_session.refresh(mom)

    monkeypatch.setattr(vision, "parse_report_image", lambda b: (_FAKE_PARSED, "{}"))
    draft = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=mom.id,
        files=[(b"\x89PNG\r\n\x1a\n subj", "a.png", "image/png")], hospital_override="X",
    )
    assert draft["subject_id"] == mom.id

    report = _commit(db_session, draft)
    # Report belongs to mom (subject), uploaded by user.
    assert report.subject_id == mom.id
    assert report.uploader_id == user.id


def test_list_filter_by_subject(db_session, user, tmp_upload, monkeypatch):
    mom = User(openid="mom2", nickname="妈妈")
    db_session.add(mom)
    db_session.commit()
    db_session.refresh(mom)

    monkeypatch.setattr(vision, "parse_report_image", lambda b: (_FAKE_PARSED, "{}"))
    # one report for user, one for mom
    for sid, img in [(user.id, b"\x89PNG\r\n\x1a\n me"), (mom.id, b"\x89PNG\r\n\x1a\n mom")]:
        d = service.create_draft_from_images(
            db_session, uploader_id=user.id, subject_id=sid,
            files=[(img, "a.png", "image/png")], hospital_override="X",
        )
        _commit(db_session, d)

    from app.modules.medical.models import MedicalReport
    mom_reports = db_session.query(MedicalReport).filter_by(subject_id=mom.id).all()
    assert len(mom_reports) == 1
    assert mom_reports[0].subject_id == mom.id


