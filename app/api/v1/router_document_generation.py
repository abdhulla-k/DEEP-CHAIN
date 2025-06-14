from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, List, Any

from app.schemas.document_schemas import ResearchState
from app.graph.research_graph import compiled_graph

router = APIRouter()

class GenerateQueriesRequest(BaseModel):
    topic: str

class GenerateQueriesResponse(BaseModel):
    initial_topic: str
    generated_queries: List[str]
    status_message: str
    error_message: str | None = None

@router.post(
    "/generate-queries", 
    response_model = GenerateQueriesResponse
)
async def generate_queries_endpoint(request_body: GenerateQueriesRequest):
    """
    Endpoint to generate search queries based on a given topic.
    Invokes a simple LangGraph workflow.
    """

    initial_input_for_graph = { "initial_topic": request_body.topic }

    try:
        final_graph_state_dict = await compiled_graph.ainvoke(initial_input_for_graph)

        generated_queries_list = final_graph_state_dict.get("generated_search_queries", [])
        if generated_queries_list is None:
            generated_queries_list = []

        response_data = GenerateQueriesResponse(
            initial_topic=final_graph_state_dict.get("initial_topic", request_body.topic),
            generated_queries=generated_queries_list,
            status_message=final_graph_state_dict.get("status_message", "Graph processing completed."),
            error_message=final_graph_state_dict.get("error_message")
        )

        return response_data

    except Exception as e:
        print(f"Error during graph invocation or processing: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
