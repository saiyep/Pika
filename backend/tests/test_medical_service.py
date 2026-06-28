import pytest

from app.core.user import service as user_service
from app.core.user.models import FamilyMembership, User
from app.modules.medical import service, vision
from app.modules.medical.models import (
    MedicalMetricAlias,
    MedicalMetricDictionary,
    MedicalReportMetricMap,
)


@pytest.fixture
def user(db_session):
    u = User(openid="test-openid", nickname="tester", role="admin", account_type="wechat", status="active")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    user_service.ensure_user_family(db_session, user=u)
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
    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))

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
    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))

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

    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))

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

    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))
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
    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))

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
    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))
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
    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))
    reparsed = service.reparse_report(db_session, report_id=report.id)

    assert reparsed.status == "parsed"
    assert len(reparsed.metrics) == 1
    assert reparsed.metrics[0].item_name == "WBC"
    assert reparsed.report_type == "blood"


def test_reparse_missing_report_returns_none(db_session):
    assert service.reparse_report(db_session, report_id=99999) is None


def test_hospital_falls_back_to_parsed_when_no_override(db_session, user, tmp_upload, monkeypatch):
    parsed = {**_FAKE_PARSED, "hospital": "北京协和医院"}
    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (parsed, "{}"))

    draft = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=None,
        files=[(b"\x89PNG\r\n\x1a\n h", "a.png", "image/png")], hospital_override=None,
    )
    assert draft["hospital"] == "北京协和医院"


def test_hospital_override_wins_over_parsed(db_session, user, tmp_upload, monkeypatch):
    parsed = {**_FAKE_PARSED, "hospital": "解析出的医院"}
    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (parsed, "{}"))

    draft = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=None,
        files=[(b"\x89PNG\r\n\x1a\n h2", "a.png", "image/png")], hospital_override="用户填的医院",
    )
    assert draft["hospital"] == "用户填的医院"


def test_parse_uses_subject_category_candidates(db_session, user, tmp_upload, monkeypatch):
    captured = {}

    spouse = User(openid="spouse-cate", nickname="爱人", role="member", account_type="wechat", status="active")
    db_session.add(spouse)
    db_session.commit()
    db_session.refresh(spouse)

    owner_m = user_service.get_active_membership(db_session, user_id=user.id)
    assert owner_m is not None
    db_session.add(FamilyMembership(family_id=owner_m.family_id, user_id=spouse.id, family_role="member", is_active=True))
    db_session.commit()

    categories = service.list_user_categories(db_session, user_id=spouse.id)
    blood = next((x for x in categories if x.category_key == "blood_routine"), None)
    assert blood is not None
    service.rename_user_category(
        db_session,
        user_id=spouse.id,
        category_id=blood.id,
        display_name="配偶血常规",
    )

    def fake_parse(_b, **kwargs):
        captured["candidates"] = kwargs.get("category_candidates")
        return _FAKE_PARSED, "{}"

    monkeypatch.setattr(vision, "parse_report_image", fake_parse)

    service.create_draft_from_images(
        db_session,
        uploader_id=user.id,
        subject_id=spouse.id,
        files=[(b"\x89PNG\r\n\x1a\n h3", "a.png", "image/png")],
        hospital_override="X",
    )

    assert captured["candidates"] is not None
    assert "配偶血常规" in captured["candidates"]


def test_is_lab_report_flag_passed_to_draft(db_session, user, tmp_upload, monkeypatch):
    parsed = {**_FAKE_PARSED, "is_lab_report": False, "metrics": []}
    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (parsed, "{}"))

    draft = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=None,
        files=[(b"\x89PNG\r\n\x1a\n notlab", "a.png", "image/png")], hospital_override="X",
    )
    assert draft["is_lab_report"] is False


def test_update_report_edits_header_and_metrics(db_session, user, tmp_upload, monkeypatch):
    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))
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
    mom = User(openid="mom-openid", nickname="妈妈", role="member", account_type="wechat", status="active")
    db_session.add(mom)
    db_session.commit()
    db_session.refresh(mom)

    owner_m = user_service.get_active_membership(db_session, user_id=user.id)
    assert owner_m is not None
    db_session.add(FamilyMembership(family_id=owner_m.family_id, user_id=mom.id, family_role="member", is_active=True))
    db_session.commit()

    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))
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
    mom = User(openid="mom2", nickname="妈妈", role="member", account_type="wechat", status="active")
    db_session.add(mom)
    db_session.commit()
    db_session.refresh(mom)

    owner_m = user_service.get_active_membership(db_session, user_id=user.id)
    assert owner_m is not None
    db_session.add(FamilyMembership(family_id=owner_m.family_id, user_id=mom.id, family_role="member", is_active=True))
    db_session.commit()

    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))
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


def test_medical_acl_actions(db_session, user):
    spouse = User(openid="spouse-openid", nickname="爱人", role="member", account_type="wechat", status="active")
    db_session.add(spouse)
    db_session.commit()
    db_session.refresh(spouse)

    owner_m = user_service.get_active_membership(db_session, user_id=user.id)
    assert owner_m is not None
    db_session.add(FamilyMembership(family_id=owner_m.family_id, user_id=spouse.id, family_role="member", is_active=True))
    db_session.commit()

    assert service.has_acl_action(db_session, actor_user_id=user.id, owner_user_id=user.id, action="view_report") is True
    assert service.has_acl_action(db_session, actor_user_id=spouse.id, owner_user_id=user.id, action="view_report") is True
    assert service.has_acl_action(db_session, actor_user_id=spouse.id, owner_user_id=user.id, action="upload_for_owner") is True
    assert service.has_acl_action(db_session, actor_user_id=spouse.id, owner_user_id=user.id, action="edit_report") is True
    assert service.has_acl_action(db_session, actor_user_id=spouse.id, owner_user_id=user.id, action="delete_report") is True

    service.set_acl_grant(
        db_session,
        owner_user_id=user.id,
        grantee_user_id=spouse.id,
        actions=["view_report", "upload_for_owner"],
    )

    assert service.has_acl_action(db_session, actor_user_id=spouse.id, owner_user_id=user.id, action="view_report") is True
    assert service.has_acl_action(db_session, actor_user_id=spouse.id, owner_user_id=user.id, action="upload_for_owner") is True
    assert service.has_acl_action(db_session, actor_user_id=spouse.id, owner_user_id=user.id, action="delete_report") is False


def test_metric_trend_marks_mixed_reference_ranges(db_session, user, tmp_upload, monkeypatch):
    from app.modules.medical import router

    parsed_a = {
        **_FAKE_PARSED,
        "metrics": [
            {
                "item_name": "WBC", "item_code": "WBC", "value_text": "11",
                "value_num": 11.0, "unit": "10^9/L", "ref_range": "4-9",
                "ref_low": 4.0, "ref_high": 9.0, "abnormal_flag": "high", "seq": 0,
            }
        ],
    }
    parsed_b = {
        **_FAKE_PARSED,
        "metrics": [
            {
                "item_name": "WBC", "item_code": "WBC", "value_text": "8",
                "value_num": 8.0, "unit": "10^9/L", "ref_range": "3.5-9.5",
                "ref_low": 3.5, "ref_high": 9.5, "abnormal_flag": "normal", "seq": 0,
            }
        ],
    }

    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (parsed_a if b.endswith(b"a") else parsed_b, "{}"))

    d1 = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=user.id,
        files=[(b"\x89PNG\r\n\x1a\n a", "a.png", "image/png")], hospital_override="医院A",
    )
    _commit(db_session, d1)

    d2 = service.create_draft_from_images(
        db_session, uploader_id=user.id, subject_id=user.id,
        files=[(b"\x89PNG\r\n\x1a\n b", "b.png", "image/png")], hospital_override="医院B",
    )
    _commit(db_session, d2)

    membership = user_service.get_active_membership(db_session, user_id=user.id)
    out = router.metric_trend(
        item_code="WBC",
        item_name=None,
        subject_id=user.id,
        db=db_session,
        user=user,
        membership=membership,
    )

    assert out.data is not None
    assert out.data.has_mixed_reference is True
    assert out.data.ref_low == 3.5
    assert out.data.ref_high == 9.5
    assert len(out.data.points) == 2
    assert out.data.points[0].value_text is not None
    assert out.data.points[0].ref_range is not None
    assert out.data.points[0].unit == "10^9/L"


def test_list_reports_filters_multiple_hospitals(db_session, user, tmp_upload, monkeypatch):
    from app.modules.medical import router

    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))

    for hospital, content in [
        ("医院A", b"\x89PNG\r\n\x1a\n a"),
        ("医院B", b"\x89PNG\r\n\x1a\n b"),
        ("医院C", b"\x89PNG\r\n\x1a\n c"),
    ]:
        draft = service.create_draft_from_images(
            db_session,
            uploader_id=user.id,
            subject_id=user.id,
            files=[(content, f"{hospital}.png", "image/png")],
            hospital_override=hospital,
        )
        _commit(db_session, draft)

    membership = user_service.get_active_membership(db_session, user_id=user.id)
    out = router.list_reports(
        subject_id=user.id,
        report_type=None,
        hospital=["医院A", "医院C"],
        date_from=None,
        date_to=None,
        page=1,
        size=20,
        db=db_session,
        user=user,
        membership=membership,
    )

    assert out.data is not None
    assert {item.hospital for item in out.data.items} == {"医院A", "医院C"}
    assert out.data.total == 2


def test_medical_acl_requires_same_family(db_session, user):
    outsider = User(openid="outsider-openid", nickname="外人", role="member", account_type="wechat", status="active")
    db_session.add(outsider)
    db_session.commit()
    db_session.refresh(outsider)
    user_service.ensure_user_family(db_session, user=outsider)

    service.set_acl_grant(
        db_session,
        owner_user_id=user.id,
        grantee_user_id=outsider.id,
        actions=["view_report"],
    )
    assert service.has_acl_action(db_session, actor_user_id=outsider.id, owner_user_id=user.id, action="view_report") is False


def test_empty_acl_record_is_treated_as_default_allow(db_session, user):
    spouse = User(openid="spouse-empty-acl", nickname="爱人", role="member", account_type="wechat", status="active")
    db_session.add(spouse)
    db_session.commit()
    db_session.refresh(spouse)

    owner_m = user_service.get_active_membership(db_session, user_id=user.id)
    assert owner_m is not None
    db_session.add(FamilyMembership(family_id=owner_m.family_id, user_id=spouse.id, family_role="member", is_active=True))
    db_session.commit()

    grant = service.set_acl_grant(
        db_session,
        owner_user_id=user.id,
        grantee_user_id=spouse.id,
        actions=[],
    )
    assert set(grant.actions_json or []) == set(service.MEDICAL_ACTIONS)
    assert service.has_acl_action(db_session, actor_user_id=spouse.id, owner_user_id=user.id, action="view_report") is True
    assert service.has_acl_action(db_session, actor_user_id=spouse.id, owner_user_id=user.id, action="upload_for_owner") is True


def test_list_user_categories_auto_seeds_defaults(db_session, user):
    rows = service.list_user_categories(db_session, user_id=user.id)
    assert len(rows) == 5
    assert {r.category_key for r in rows} == {k for k, _, _ in service.MEDICAL_CATEGORY_DEFAULTS}


def test_category_rename_persists_for_user(db_session, user):
    from app.modules.medical import router

    membership = user_service.get_active_membership(db_session, user_id=user.id)
    assert membership is not None

    categories = service.list_user_categories(db_session, user_id=user.id)
    blood = next((x for x in categories if x.category_key == "blood_routine"), None)
    assert blood is not None

    body = router.CategoryUpdateIn(display_name="血常规重点")
    out = router.rename_category(
        category_id=blood.id,
        body=body,
        db=db_session,
        user=user,
        membership=membership,
    )

    assert out.data is not None
    target = next((x for x in out.data.items if x.id == blood.id), None)
    assert target is not None
    assert target.display_name == "血常规重点"


def test_category_rename_isolated_per_user(db_session, user):
    from app.modules.medical import router

    spouse = User(openid="cat-user", nickname="成员", role="member", account_type="wechat", status="active")
    db_session.add(spouse)
    db_session.commit()
    db_session.refresh(spouse)

    owner_m = user_service.get_active_membership(db_session, user_id=user.id)
    assert owner_m is not None
    spouse_m = FamilyMembership(family_id=owner_m.family_id, user_id=spouse.id, family_role="member", is_active=True)
    db_session.add(spouse_m)
    db_session.commit()

    user_cats = service.list_user_categories(db_session, user_id=user.id)
    spouse_cats = service.list_user_categories(db_session, user_id=spouse.id)
    user_blood = next((x for x in user_cats if x.category_key == "blood_routine"), None)
    spouse_blood = next((x for x in spouse_cats if x.category_key == "blood_routine"), None)
    assert user_blood is not None and spouse_blood is not None

    router.rename_category(
        category_id=user_blood.id,
        body=router.CategoryUpdateIn(display_name="A分类"),
        db=db_session,
        user=user,
        membership=owner_m,
    )

    out_spouse = router.rename_category(
        category_id=spouse_blood.id,
        body=router.CategoryUpdateIn(display_name="B分类"),
        db=db_session,
        user=spouse,
        membership=spouse_m,
    )

    spouse_target = next((x for x in out_spouse.data.items if x.id == spouse_blood.id), None)
    assert spouse_target is not None
    assert spouse_target.display_name == "B分类"


def test_focus_metrics_create_update_delete(db_session, user):
    from app.modules.medical import router

    db_session.add(
        MedicalMetricDictionary(
            canonical_key="plt",
            canonical_name="血小板",
            canonical_unit="10^9/L",
            category_key="blood_routine",
            enabled=True,
        )
    )
    db_session.commit()

    dic = db_session.query(MedicalMetricDictionary).filter_by(canonical_key="plt").first()
    categories = service.list_user_categories(db_session, user_id=user.id)
    blood = next((x for x in categories if x.category_key == "blood_routine"), None)
    urine = next((x for x in categories if x.category_key == "urine_routine"), None)
    assert dic is not None and blood is not None and urine is not None

    out1 = router.create_focus_metric(
        body=router.FocusMetricUpsertIn(
            dictionary_id=dic.id,
            category_id=blood.id,
        ),
        db=db_session,
        user=user,
    )
    assert out1.data is not None
    assert len(out1.data.items) == 1
    assert out1.data.items[0].canonical_name == "血小板"
    assert out1.data.items[0].category_id == blood.id

    focus_id = out1.data.items[0].id
    out2 = router.update_focus_metric(
        focus_id=focus_id,
        body=router.FocusMetricUpdateIn(category_id=urine.id),
        db=db_session,
        user=user,
    )
    assert out2.data is not None
    assert out2.data.items[0].category_id == urine.id

    out3 = router.delete_focus_metric(focus_id=focus_id, db=db_session, user=user)
    assert out3.data is not None
    assert out3.data.items == []


def test_focus_metric_requires_existing_category(db_session, user):
    from app.modules.medical import router

    db_session.add(
        MedicalMetricDictionary(
            canonical_key="wbc",
            canonical_name="白细胞",
            canonical_unit="10^9/L",
            category_key="blood_routine",
            enabled=True,
        )
    )
    db_session.commit()

    dic = db_session.query(MedicalMetricDictionary).filter_by(canonical_key="wbc").first()
    assert dic is not None

    with pytest.raises(router.PikaException) as exc:
        router.create_focus_metric(
            body=router.FocusMetricUpsertIn(
                dictionary_id=dic.id,
                category_id=999999,
            ),
            db=db_session,
            user=user,
        )
    assert "category not found" in str(exc.value)


def test_bootstrap_creates_dictionary_and_alias(db_session, user, tmp_upload, monkeypatch):
    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))

    d1 = service.create_draft_from_images(
        db_session,
        uploader_id=user.id,
        subject_id=user.id,
        files=[(b"\x89PNG\r\n\x1a\n aa", "a.png", "image/png")],
        hospital_override="医院A",
    )
    service.commit_draft(
        db_session,
        draft_id=d1["draft_id"],
        report_type=d1["report_type"],
        report_type_label=d1["report_type_label"],
        report_date=d1["report_date"],
        hospital=d1["hospital"],
        metrics=d1["metrics"],
    )

    out = service.bootstrap_metric_dictionary(db_session, owner_user_id=user.id)
    assert out["dictionary_created"] >= 1
    assert out["alias_created"] >= 1

    dic = db_session.query(MedicalMetricDictionary).filter_by(canonical_key="wbc").first()
    assert dic is not None
    alias = db_session.query(MedicalMetricAlias).filter_by(owner_user_id=user.id, dictionary_id=dic.id, alias_name="WBC").first()
    assert alias is not None


def test_rebuild_metric_mappings_auto_matches_alias(db_session, user, tmp_upload, monkeypatch):
    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))

    d1 = service.create_draft_from_images(
        db_session,
        uploader_id=user.id,
        subject_id=user.id,
        files=[(b"\x89PNG\r\n\x1a\n bb", "b.png", "image/png")],
        hospital_override="医院A",
    )
    report = service.commit_draft(
        db_session,
        draft_id=d1["draft_id"],
        report_type=d1["report_type"],
        report_type_label=d1["report_type_label"],
        report_date=d1["report_date"],
        hospital=d1["hospital"],
        metrics=d1["metrics"],
    )

    dic = MedicalMetricDictionary(
        canonical_key="wbc",
        canonical_name="白细胞",
        canonical_unit="10^9/L",
        category_key="blood_routine",
        enabled=True,
    )
    db_session.add(dic)
    db_session.flush()
    db_session.add(
        MedicalMetricAlias(
            owner_user_id=user.id,
            dictionary_id=dic.id,
            alias_name="WBC",
            alias_unit="10^9/L",
            hospital_hint="医院A",
            report_type_hint=None,
            priority=100,
        )
    )
    db_session.commit()

    out = service.rebuild_metric_mappings(db_session, owner_user_id=user.id)
    assert out["mapped"] >= 1

    metric_id = report.metrics[0].id
    mapping = db_session.query(MedicalReportMetricMap).filter_by(report_metric_id=metric_id).first()
    assert mapping is not None
    assert mapping.match_status == "auto"
    assert mapping.dictionary_id == dic.id


def test_metric_trend_supports_dictionary_id(db_session, user, tmp_upload, monkeypatch):
    from app.modules.medical import router

    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))

    d1 = service.create_draft_from_images(
        db_session,
        uploader_id=user.id,
        subject_id=user.id,
        files=[(b"\x89PNG\r\n\x1a\n cc", "c.png", "image/png")],
        hospital_override="医院A",
    )
    report = service.commit_draft(
        db_session,
        draft_id=d1["draft_id"],
        report_type=d1["report_type"],
        report_type_label=d1["report_type_label"],
        report_date=d1["report_date"],
        hospital=d1["hospital"],
        metrics=d1["metrics"],
    )

    dic = MedicalMetricDictionary(
        canonical_key="wbc",
        canonical_name="白细胞",
        canonical_unit="10^9/L",
        category_key="blood_routine",
        enabled=True,
    )
    db_session.add(dic)
    db_session.flush()
    db_session.add(
        MedicalMetricAlias(
            owner_user_id=user.id,
            dictionary_id=dic.id,
            alias_name="WBC",
            alias_unit="10^9/L",
            hospital_hint="医院A",
            report_type_hint=None,
            priority=100,
        )
    )
    db_session.commit()

    service.rebuild_metric_mappings(db_session, owner_user_id=user.id)
    membership = user_service.get_active_membership(db_session, user_id=user.id)
    out = router.metric_trend(
        dictionary_id=dic.id,
        item_code=None,
        item_name=None,
        subject_id=user.id,
        db=db_session,
        user=user,
        membership=membership,
    )

    assert out.data is not None
    assert out.data.dictionary_id == dic.id
    assert out.data.category_key == "blood_routine"
    assert out.data.item_name == "白细胞"
    assert len(out.data.points) >= 1
    assert out.data.points[0].report_id == report.id


def test_metric_catalog_supports_mapped_and_category_filter(db_session, user, tmp_upload, monkeypatch):
    from app.modules.medical import router

    monkeypatch.setattr(vision, "parse_report_image", lambda b, **kwargs: (_FAKE_PARSED, "{}"))

    d1 = service.create_draft_from_images(
        db_session,
        uploader_id=user.id,
        subject_id=user.id,
        files=[(b"\x89PNG\r\n\x1a\n dd", "d.png", "image/png")],
        hospital_override="医院A",
    )
    service.commit_draft(
        db_session,
        draft_id=d1["draft_id"],
        report_type=d1["report_type"],
        report_type_label=d1["report_type_label"],
        report_date=d1["report_date"],
        hospital=d1["hospital"],
        metrics=d1["metrics"],
    )

    dic = MedicalMetricDictionary(
        canonical_key="wbc",
        canonical_name="白细胞",
        canonical_unit="10^9/L",
        category_key="blood_routine",
        enabled=True,
    )
    db_session.add(dic)
    db_session.flush()
    db_session.add(
        MedicalMetricAlias(
            owner_user_id=user.id,
            dictionary_id=dic.id,
            alias_name="WBC",
            alias_unit="10^9/L",
            hospital_hint="医院A",
            report_type_hint=None,
            priority=100,
        )
    )
    db_session.commit()

    service.rebuild_metric_mappings(db_session, owner_user_id=user.id)
    membership = user_service.get_active_membership(db_session, user_id=user.id)
    out = router.metric_catalog(
        subject_id=user.id,
        mapped=1,
        category_key="blood_routine",
        db=db_session,
        user=user,
        membership=membership,
    )

    assert out.data is not None
    assert len(out.data.items) >= 1
    assert out.data.items[0].dictionary_id == dic.id
    assert out.data.items[0].category_key == "blood_routine"

