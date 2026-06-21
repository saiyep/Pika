import base64
import io

import httpx
import qrcode

from app.core.exceptions import WeChatError
from app.settings import settings

JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


def code_to_openid(code: str) -> str:
    params = {
        "appid": settings.wx_appid,
        "secret": settings.wx_secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    try:
        resp = httpx.get(JSCODE2SESSION_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        raise WeChatError(f"wechat request failed: {e}")

    openid = data.get("openid")
    if not openid:
        raise WeChatError("wechat returned no openid")
    return openid


def invite_qrcode_data_url(*, code: str) -> str:
    payload = f"PIKA_INVITE:{code}"
    qr = qrcode.QRCode(box_size=10, border=3)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
