import azure.functions as func
import json
import logging
import os
import requests

app = func.FunctionApp()

# Configuration - these would typically be set as environment variables
AZURE_AI_ENDPOINT = os.environ.get("AZURE_AI_ENDPOINT", "")
AZURE_AI_KEY = os.environ.get("AZURE_AI_KEY", "")
MCP_SERVICES = {
    "weather": "https://mcp-weather-service.azurewebsites.net/api",
    "calendar": "https://mcp-calendar-service.azurewebsites.net/api",
    "news": "https://mcp-news-service.azurewebsites.net/api"
}

@app.route(route="pika", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def pika_assistant(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Pika personal assistant processed a request.')

    try:
        # Get the request body
        req_body = req.get_json()
        user_message = req_body.get('message')
        
        if not user_message:
            return func.HttpResponse(
                json.dumps({"error": "Please provide a 'message' in the request body"}),
                status_code=400,
                mimetype="application/json"
            )

        # Step 1: Forward to Azure AI GPT-4.1-nano for intent analysis
        intent = analyze_intent_with_azure_ai(user_message)
        
        if not intent:
            return func.HttpResponse(
                json.dumps({"error": "Failed to analyze intent"}),
                status_code=500,
                mimetype="application/json"
            )

        # Step 2: Call corresponding MCP service based on intent
        result = call_mcp_service(intent, req_body.get('parameters', {}))
        
        return func.HttpResponse(
            json.dumps({
                "intent": intent,
                "result": result
            }),
            status_code=200,
            mimetype="application/json"
        )
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON in request body"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"An error occurred: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="mcp/{service_name}", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def mcp_client(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('MCP client service called.')
    
    try:
        service_name = req.route_params.get('service_name')
        req_body = req.get_json()
        
        if service_name not in MCP_SERVICES:
            return func.HttpResponse(
                json.dumps({"error": f"Service '{service_name}' not found"}),
                status_code=404,
                mimetype="application/json"
            )
        
        # Call the MCP service
        result = call_mcp_service(service_name, req_body)
        
        return func.HttpResponse(
            json.dumps({
                "service": service_name,
                "result": result
            }),
            status_code=200,
            mimetype="application/json"
        )
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON in request body"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"An error occurred: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

def analyze_intent_with_azure_ai(message: str) -> str:
    """
    Analyze user intent using Azure AI GPT-4.1-nano
    In a real implementation, this would make an HTTP request to Azure AI
    """
    # This is a simplified implementation
    # A real implementation would call the Azure AI endpoint
    if "weather" in message.lower():
        return "weather"
    elif "calendar" in message.lower() or "schedule" in message.lower() or "meeting" in message.lower():
        return "calendar"
    elif "news" in message.lower() or "headline" in message.lower():
        return "news"
    else:
        return "general"

def call_mcp_service(service_name: str, parameters: dict) -> dict:
    """
    Call an MCP service based on the service name
    In a real implementation, this would make HTTP requests to actual MCP services
    """
    # This is a simplified implementation that simulates calling MCP services
    # A real implementation would call the actual MCP service endpoints
    
    if service_name == "weather":
        # Simulate weather service response
        return {
            "location": parameters.get("location", "Unknown"),
            "temperature": "22°C",
            "condition": "Partly cloudy"
        }
    elif service_name == "calendar":
        # Simulate calendar service response
        return {
            "events": [
                {"title": "Meeting with team", "time": "10:00 AM"},
                {"title": "Lunch with client", "time": "1:00 PM"}
            ]
        }
    elif service_name == "news":
        # Simulate news service response
        return {
            "headlines": [
                "Azure Functions update released",
                "New AI model shows promising results"
            ]
        }
    else:
        return {
            "message": f"General response to intent '{service_name}'",
            "details": parameters
        }