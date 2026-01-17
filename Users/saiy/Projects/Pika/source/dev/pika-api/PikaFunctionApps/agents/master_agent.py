from pydantic_ai import Agent, tool  # 使用正确的导入方式，直接继承原生Agent类

class MasterAgent(Agent):
    # 系统提示词配置
    system_prompt = """
    你是一个健康数据自动化助手，负责解析用户意图并调度专业Agent执行任务。
    当前支持的任务包括：好轻APP体重数据录入、Notion笔记同步等。
    请根据用户请求选择合适的Agent进行处理。
    """
    
    @tool
    def route_to_health_metrics(self, request: PikaRequest) -> dict:
        # 路由逻辑
        pass
    
    @tool
    def route_to_notion_sync(self, request: PikaRequest) -> dict:
        # 路由逻辑
        pass