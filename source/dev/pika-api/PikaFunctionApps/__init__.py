"""Pika Life Automation Service - Main Entry Point"""
import logging
import json
import azure.functions as func
from .core.models import PikaRequest, PikaResponse
from .agents.master_agent import MasterAgent
from .core.exceptions import PikaException
from .core.security import validate_function_key


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """主函数入口"""
    logging.info('Pika Life Automation Service function processed a request.')
    
    try:
        # 获取请求数据
        req_body = req.get_json()
        
        # 创建Pika请求对象
        pika_request = PikaRequest(**req_body)
        
        # 初始化MasterAgent并处理请求
        master_agent = MasterAgent()
        result = await master_agent.process_request(pika_request)
        
        # 返回响应
        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"处理请求时发生错误: {str(e)}")
        
        error_response = PikaResponse(
            success=False,
            message="请求处理失败",
            error=str(e)
        ).model_dump()
        
        return func.HttpResponse(
            json.dumps(error_response, ensure_ascii=False, indent=2),
            status_code=500,
            mimetype="application/json"
        )