from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    msg: str = "ok"
    data: T | None = None

    @classmethod
    def ok(cls, data: Any = None) -> "ApiResponse":
        return cls(code=0, msg="ok", data=data)

    @classmethod
    def fail(cls, msg: str, code: int = 1, data: Any = None) -> "ApiResponse":
        return cls(code=code, msg=msg, data=data)
