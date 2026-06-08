class PikaException(Exception):
    """Base business exception. code != 0 maps to a non-success ApiResponse."""

    code = 1
    msg = "error"

    def __init__(self, msg: str | None = None, code: int | None = None):
        if msg is not None:
            self.msg = msg
        if code is not None:
            self.code = code
        super().__init__(self.msg)


class NotFoundError(PikaException):
    code = 404
    msg = "not found"


class WeChatError(PikaException):
    code = 4001
    msg = "wechat login failed"


class VisionParseError(PikaException):
    code = 5001
    msg = "vision parse failed"


class DuplicateReportError(PikaException):
    code = 4090
    msg = "report already exists"
