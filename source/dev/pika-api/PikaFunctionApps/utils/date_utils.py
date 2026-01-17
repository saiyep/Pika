"""日期处理工具"""
from datetime import datetime, date
from typing import Union


def parse_date_string(date_str: str) -> date:
    """解析日期字符串为date对象"""
    if not date_str:
        return date.today()
    
    # 尝试多种日期格式
    formats = [
        '%Y-%m-%d',  # 2023-01-15
        '%Y/%m/%d',  # 2023/01/15
        '%d/%m/%Y',  # 15/01/2023
        '%d-%m-%Y',  # 15-01-2023
        '%Y%m%d',    # 20230115
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    # 如果所有格式都失败，返回今天的日期
    return date.today()


def format_date_for_path(input_date: Union[date, datetime]) -> str:
    """将日期格式化为路径友好的字符串 YYYYMMDD"""
    if isinstance(input_date, datetime):
        input_date = input_date.date()
    
    return input_date.strftime('%Y%m%d')