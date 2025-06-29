# WebFunctionCall
initial Azure function webservice to respond user's call

## 说明

本项目采用 Azure Functions Python v2 新模式（装饰器编程模型），所有函数均集中在 function_app.py 文件中进行注册和实现。

## AddNumbers 函数

- 路径：/api/AddNumbers
- 方法：POST
- Content-Type: application/json
- 请求参数：
  - a: 数字
  - b: 数字
- 返回：
  - result: a + b 的结果

### 示例

请求：
```json
{
  "a": 3,
  "b": 5
}
```

响应：
```json
{
  "result": 8
}
```
