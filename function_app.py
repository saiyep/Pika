import azure.functions as func
import datetime
import json
import logging

app = func.FunctionApp()

@app.route(route="AddNumbers", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def AddNumbers(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        a = req_body.get('a')
        b = req_body.get('b')
        if a is None or b is None:
            return func.HttpResponse(
                json.dumps({'error': '参数 a 和 b 必须都提供'}),
                status_code=400,
                mimetype="application/json"
            )
        result = a + b
        return func.HttpResponse(
            json.dumps({'result': result}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="SubtractNumbers", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def SubtractNumbers(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        a = req_body.get('a')
        b = req_body.get('b')
        if a is None or b is None:
            return func.HttpResponse(
                json.dumps({'error': '参数 a 和 b 必须都提供'}),
                status_code=400,
                mimetype="application/json"
            )
        result = a - b
        return func.HttpResponse(
            json.dumps({'result': result}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="MultiplyNumbers", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def MultiplyNumbers(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        a = req_body.get('a')
        b = req_body.get('b')
        if a is None or b is None:
            return func.HttpResponse(
                json.dumps({'error': '参数 a 和 b 必须都提供'}),
                status_code=400,
                mimetype="application/json"
            )
        result = a * b
        return func.HttpResponse(
            json.dumps({'result': result}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500,
            mimetype="application/json"
        )
