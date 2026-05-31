import httpx

from app.core.exceptions import WeChatError
from app.settings import settings

JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


def code_to_openid(code: str) -> str:
    """Exchange a wx.login code for the user's openid via jscode2session."""
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
        raise WeChatError(f"wechat returned no openid: {data}")
    return openid
