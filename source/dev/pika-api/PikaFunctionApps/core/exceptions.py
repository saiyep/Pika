"""自定义异常定义"""


class PikaException(Exception):
    """Pika服务基础异常类"""
    pass


class AuthenticationError(PikaException):
    """认证错误"""
    pass


class ValidationError(PikaException):
    """验证错误"""
    pass


class ProcessingError(PikaException):
    """处理错误"""
    pass


class StorageError(PikaException):
    """存储错误"""
    pass


class VisionError(PikaException):
    """视觉识别错误"""
    pass


class NotionError(PikaException):
    """Notion操作错误"""
    pass