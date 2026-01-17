"""路径构建工具"""
import os
from datetime import datetime
from typing import Optional


def build_task_path(task_type: str, date: datetime, filename: str) -> str:
    """构建任务存储路径"""
    year = date.strftime('%Y')
    month = date.strftime('%m')
    
    return os.path.join(task_type, year, month, filename)


def build_processed_path(original_path: str) -> str:
    """构建处理后文件的路径"""
    path_parts = original_path.split(os.sep)
    if len(path_parts) >= 3:
        task_type = path_parts[0]
        filename = path_parts[-1]
        
        now = datetime.now()
        year = str(now.year)
        month = f"{now.month:02d}"
        
        return os.path.join(task_type, "processed", year, month, filename)
    
    # 如果路径格式不符合预期，直接在原路径前面加上processed
    return os.path.join("processed", original_path)


def extract_date_from_path(file_path: str) -> Optional[datetime]:
    """从路径中提取日期信息"""
    path_parts = file_path.split(os.sep)
    
    for part in path_parts:
        # 查找类似 YYYYMMDD_HHMM 格式的部分
        if len(part) == 13 and part[8] == '_' and part[4] == part[7] == part[11] == part[12] == part[13] == '':
            try:
                date_part = part[:8]  # YYYYMMDD
                dt = datetime.strptime(date_part, '%Y%m%d')
                return dt
            except ValueError:
                continue
    
    return None