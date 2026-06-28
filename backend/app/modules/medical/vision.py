import base64
import json
import re

from openai import AzureOpenAI

from app.modules.medical.prompts import SYSTEM_PROMPT, build_user_prompt
from app.settings import settings

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_RANGE_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*[-~–]\s*(-?\d+(?:\.\d+)?)")


def _client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )


def _sniff_mime(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    if image_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return "image/jpeg"


def _data_url(image_bytes: bytes) -> str:
    mime = _sniff_mime(image_bytes)
    b64 = base64.b64encode(image_bytes).decode()
    return f"data:{mime};base64,{b64}"


def _loads_lenient(text: str) -> dict:
    """Parse JSON; if it fails, extract the first {...} block and retry."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _parse_range(ref_range: str | None) -> tuple[float | None, float | None]:
    if not ref_range:
        return None, None
    m = _RANGE_RE.search(ref_range)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


def _to_num(value: str | None) -> float | None:
    if value is None:
        return None
    m = _NUM_RE.search(str(value))
    return float(m.group(0)) if m else None


def _derive_flag(value_num, ref_low, ref_high, given) -> str:
    if given in ("high", "low", "normal", "unknown"):
        if given != "unknown":
            return given
    if value_num is None or ref_low is None or ref_high is None:
        return given or "unknown"
    if value_num < ref_low:
        return "low"
    if value_num > ref_high:
        return "high"
    return "normal"


def _normalize_metric(raw: dict, seq: int) -> dict | None:
    item_name = raw.get("item_name")
    if not item_name:
        return None
    value = raw.get("value")
    ref_range = raw.get("ref_range")
    ref_low, ref_high = _parse_range(ref_range)
    value_num = _to_num(value)
    return {
        "item_name": item_name,
        "item_code": raw.get("item_code"),
        "value_text": None if value is None else str(value),
        "value_num": value_num,
        "unit": raw.get("unit"),
        "ref_range": ref_range,
        "ref_low": ref_low,
        "ref_high": ref_high,
        "abnormal_flag": _derive_flag(value_num, ref_low, ref_high, raw.get("abnormal_flag")),
        "seq": seq,
    }


def parse_report_image(image_bytes: bytes, *, category_candidates: list[str] | None = None) -> tuple[dict, str]:
    """Call GPT-4.5-mini vision and return (parsed dict, raw model text).

    parsed = {report_type, report_type_label, report_date, metrics:[...normalized...]}.
    Also includes is_lab_report (bool) and hospital (str|None).
    Raises on hard failure (caller decides to mark report failed but keep image)."""
    resp = _client().chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_user_prompt(category_candidates)},
                    {"type": "image_url", "image_url": {"url": _data_url(image_bytes)}},
                ],
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    raw_text = resp.choices[0].message.content or ""
    data = _loads_lenient(raw_text)

    raw_metrics = data.get("metrics") or []
    metrics = []
    for i, m in enumerate(raw_metrics):
        norm = _normalize_metric(m, i)
        if norm:
            metrics.append(norm)

    parsed = {
        "is_lab_report": data.get("is_lab_report", True),
        "report_type": data.get("report_type") or "unknown",
        "report_type_label": data.get("report_type_label"),
        "report_date": data.get("report_date"),
        "hospital": data.get("hospital"),
        "metrics": metrics,
    }
    return parsed, raw_text
