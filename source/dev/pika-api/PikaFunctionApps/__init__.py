import azure.functions as func
import logging
import json
import asyncio
from .agents.master_agent import MasterAgent


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function entry point for Pika life automation service
    Handles both structured and natural language requests
    Authentication handled by Azure Functions (authLevel: "function")
    """
    logging.info('Pika function processed a request.')

    try:
        # Parse request body
        req_body = req.get_json()
        
        # Initialize and run MasterAgent
        master_agent = MasterAgent()
        response = await master_agent.process_request(req_body)
        
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            status_code=500,
            mimetype="application/json"
        )