# Pika Life Automation Service

基于双层智能Agent架构的个人生活自动化服务平台，第一期聚焦健康数据自动化录入。

## 架构设计

- **双层Agent架构**：上层MasterAgent（意图解析）+ 下层专业Agent（任务执行）
- **技术栈**：Python + Azure Functions + Pydantic-AI
- **部署模式**：HTTP触发器函数，authLevel: "function"

## 安全设计

- API认证：x-functions-key请求头
- 存储认证：storage_key参数传入
- 所有密钥通过环境变量管理

## 请求模式

支持结构化请求与自然语言请求两种输入格式

### 结构化请求示例

```json
{
  "mode": "structured",
  "task_type": "health_metrics",
  "parameters": {
    "storage_key": "{加密的存储密钥}",
    "blob_path": "data/health/2026/01/20260117_0830.png",
    "date": "2026-01-17"
  }
}
```

### 自然语言请求示例

```json
{
  "mode": "natural",
  "query": "我刚上传了今天早上的体重截图，在健康文件夹里，文件是8点半的那张，请处理一下",
  "parameters": {
    "storage_key": "{加密的存储密钥}",
    "date": "2026-01-17"
  }
}
```

## 部署说明

1. 创建Azure Function App：
   - 使用Python运行时
   - 选择合适的区域和定价层
   - 配置函数密钥

2. 配置环境变量（在Azure Portal中）：
   - `Pika_API_Key`: 业务逻辑API密钥
   - `OpenRouter_API_Key`: OpenRouter API密钥
   - `Notion_API_Key`: Notion API密钥
   - `Health_Metrics_Notion_DB_ID`: 健康数据Notion数据库ID
   - `Azure_Storage_Account_Name`: 存储账户名称 (如: pikastorage)
   - `Azure_Storage_Account_Key_default`: 存储账户密钥

3. 部署命令：
   ```bash
   func azure functionapp publish <function-app-name>
   ```

## 本地开发

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 启动本地开发服务器：
   ```bash
   func start
   ```

## API调用示例

```bash
curl -X POST https://<function-app-name>.azurewebsites.net/api/process \
  -H "x-functions-key: <function-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "structured",
    "task_type": "health_metrics",
    "parameters": {
      "storage_key": "encrypted_storage_key",
      "blob_path": "data/health/2026/01/20260117_0830.png",
      "date": "2026-01-17"
    }
  }'
```

## 项目结构

```
PikaFunctionApps/
├── __init__.py                    # Azure HTTP触发器主入口
├── function.json                  # Functions绑定配置
├── core/
│   ├── __init__.py
│   ├── config.py                   # 配置管理
│   ├── models.py                   # 数据模型
│   ├── exceptions.py               # 自定义异常
│   └── security.py                 # 安全验证工具
├── agents/
│   ├── __init__.py
│   ├── master_agent.py             # MasterAgent智能调度器
│   ├── base_agent.py               # Agent基类
│   └── health_metrics_agent.py     # 健康数据专业Agent
├── tools/
│   ├── __init__.py
│   ├── storage_tool.py             # Azure Storage操作
│   ├── vision_tool.py              # OpenRouter视觉模型
│   └── notion_tool.py              # Notion API操作
└── utils/
    ├── __init__.py
    ├── date_utils.py               # 日期处理工具
    ├── path_utils.py               # 路径构建工具
    └── validation.py               # 数据验证工具
```

## Azure Storage 结构

Azure Storage 容器名为 `filesystem`，文件路径结构如下：

```
filesystem/
├── data/
│   ├── health/{year}/{month}/{YYYYMMDD}_{HHMM}.png
│   ├── running/{year}/{month}/{YYYYMMDD}_{HHMM}.png
│   ├── swimming/{year}/{month}/{YYYYMMDD}_{HHMM}.png
│   └── temp/
└── {task_type}/processed/{year}/{month}/  # 处理完成后的文件
```