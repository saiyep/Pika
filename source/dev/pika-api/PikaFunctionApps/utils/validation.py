"""数据验证工具"""
from typing import Any, Dict
from ..core.exceptions import ValidationError


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """验证必需字段是否存在"""
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(f"缺少必需字段: {', '.join(missing_fields)}")


def validate_storage_path(path: str) -> bool:
    """验证存储路径格式"""
    if not path or not isinstance(path, str):
        return False
    
    # 检查路径格式是否符合预期 (task_type/year/month/filename)
    parts = path.split('/')
    if len(parts) < 3:
        return False
    
    task_type, year, month = parts[0], parts[1], parts[2]
    
    # 验证任务类型
    valid_task_types = ['health', 'running', 'swimming']
    if task_type not in valid_task_types:
        return False
    
    # 验证年份格式 (YYYY)
    if not (year.isdigit() and len(year) == 4):
        return False
    
    # 验证月份格式 (MM)
    if not (month.isdigit() and len(month) == 2 and 1 <= int(month) <= 12):
        return False
    
    return True


def validate_date_format(date_str: str) -> bool:
    """验证日期格式"""
    if not date_str or not isinstance(date_str, str):
        return False
    
    # 检查是否符合 YYYY-MM-DD 格式
    import re
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    return bool(re.match(pattern, date_str))


def clean_input(value: str) -> str:
    """清理输入值"""
    if not isinstance(value, str):
        return value
    
    # 去除首尾空白字符
    cleaned = value.strip()
    
    # 防止路径遍历攻击
    if '..' in cleaned:
        raise ValidationError("输入包含非法字符")
    
    return cleaned