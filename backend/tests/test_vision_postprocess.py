from app.modules.medical import vision
from app.modules.medical.prompts import build_user_prompt


class TestSniffMime:
    def test_png_magic(self):
        assert vision._sniff_mime(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16) == "image/png"

    def test_jpeg_magic(self):
        assert vision._sniff_mime(b"\xff\xd8\xff\xe0" + b"\x00" * 16) == "image/jpeg"

    def test_webp_magic(self):
        data = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 8
        assert vision._sniff_mime(data) == "image/webp"

    def test_gif_magic(self):
        assert vision._sniff_mime(b"GIF89a" + b"\x00" * 16) == "image/gif"

    def test_unknown_falls_back_to_jpeg(self):
        assert vision._sniff_mime(b"not-an-image") == "image/jpeg"

    def test_data_url_uses_sniffed_mime(self):
        # The bug that broke real uploads: PNG must not be labeled jpeg.
        url = vision._data_url(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        assert url.startswith("data:image/png;base64,")


class TestParseRange:
    def test_hyphen(self):
        assert vision._parse_range("4-9") == (4.0, 9.0)

    def test_tilde(self):
        assert vision._parse_range("3.5~5.5") == (3.5, 5.5)

    def test_en_dash(self):
        assert vision._parse_range("10–20") == (10.0, 20.0)

    def test_none_and_empty(self):
        assert vision._parse_range(None) == (None, None)
        assert vision._parse_range("") == (None, None)

    def test_unparseable(self):
        assert vision._parse_range("阴性") == (None, None)

    def test_negative_bounds(self):
        assert vision._parse_range("-2.0 - 3.0") == (-2.0, 3.0)


class TestToNum:
    def test_plain(self):
        assert vision._to_num("5.4") == 5.4

    def test_embedded_in_text(self):
        assert vision._to_num("约 12.3 mg") == 12.3

    def test_none(self):
        assert vision._to_num(None) is None

    def test_no_number(self):
        assert vision._to_num("阴性") is None


class TestDeriveFlag:
    def test_derives_high_when_unknown(self):
        assert vision._derive_flag(10, 4, 9, "unknown") == "high"

    def test_derives_low_when_unknown(self):
        assert vision._derive_flag(2, 4, 9, "unknown") == "low"

    def test_derives_normal_when_unknown(self):
        assert vision._derive_flag(6, 4, 9, "unknown") == "normal"

    def test_trusts_explicit_model_flag_over_numbers(self):
        # By design: an explicit high/low/normal from the model is kept as-is,
        # even if it disagrees with the numeric range.
        assert vision._derive_flag(6, 4, 9, "high") == "high"

    def test_missing_range_keeps_given(self):
        assert vision._derive_flag(6, None, None, "unknown") == "unknown"
        assert vision._derive_flag(6, None, None, None) == "unknown"

    def test_missing_value_keeps_given(self):
        assert vision._derive_flag(None, 4, 9, "unknown") == "unknown"


class TestNormalizeMetric:
    def test_full_metric_derives_flag(self):
        out = vision._normalize_metric(
            {"item_name": "WBC", "item_code": "WBC", "value": "11", "ref_range": "4-9", "unit": "10^9/L"},
            seq=0,
        )
        assert out["item_name"] == "WBC"
        assert out["value_num"] == 11.0
        assert out["ref_low"] == 4.0 and out["ref_high"] == 9.0
        assert out["abnormal_flag"] == "high"
        assert out["seq"] == 0

    def test_missing_item_name_returns_none(self):
        assert vision._normalize_metric({"value": "5"}, seq=0) is None

    def test_non_numeric_value_kept_as_text(self):
        out = vision._normalize_metric(
            {"item_name": "HBsAg", "value": "阴性", "ref_range": None}, seq=1
        )
        assert out["value_text"] == "阴性"
        assert out["value_num"] is None
        assert out["abnormal_flag"] == "unknown"

    def test_seq_is_passed_through(self):
        out = vision._normalize_metric({"item_name": "X", "value": "1"}, seq=7)
        assert out["seq"] == 7


class TestLoadsLenient:
    def test_clean_json(self):
        assert vision._loads_lenient('{"a": 1}') == {"a": 1}

    def test_json_wrapped_in_markdown(self):
        text = '```json\n{"report_type": "blood"}\n```'
        assert vision._loads_lenient(text) == {"report_type": "blood"}

    def test_json_with_prose_prefix(self):
        text = 'Here is the result: {"x": 2} hope it helps'
        assert vision._loads_lenient(text) == {"x": 2}


class TestBuildUserPrompt:
    def test_returns_default_prompt_without_candidates(self):
        out = build_user_prompt(None)
        assert '请先判断这张图是否为检查单' in out

    def test_includes_candidates_when_provided(self):
        out = build_user_prompt(['血常规', '肝肾功能'])
        assert '血常规、肝肾功能' in out
        assert '分类限定候选' in out
