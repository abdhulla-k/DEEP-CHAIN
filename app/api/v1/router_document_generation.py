from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional

from app.graph.master_orchestrator_graph import compiled_master_orchestrator_graph

router = APIRouter()

class StartDocumentGenerationRequest(BaseModel):
    topic: str = Field(
        ...,
        description="The main topic for document generation.",
        example="The impact of AI on climate change"
    )
    reference_urls: List[str] = Field(
        default_factory=list, 
        description="Optional list of reference URLs provided by the user.",
        example = [
            "https://example.com/article1",
            "https://blog.example.com/post2"
        ]
    )

class DocumentGenerationResponse(BaseModel):
    message: str = Field(description = "Status message of the operation.")
    initial_topic: Optional[str] = None 
    generated_queries: Optional[List[str]] = None
    search_results_summary: Optional[List[Dict[str, Any]]] = None 
    error_message: Optional[str] = None


@router.post(
    "/document/generate",
    response_model = DocumentGenerationResponse
)
async def start_document_generation_endpoint(
    request_body: StartDocumentGenerationRequest,
):
    """
    Endpoint to start the multi-agent document generation process.
    Invokes the master orchestrator graph.
    """

    initial_input_for_master_graph = {
        "initial_topic": request_body.topic,
        "reference_urls": request_body.reference_urls,
    }

    try:
        # Invoke the Master Orchestrator Graph asynchronously
        final_master_graph_state_dict = await compiled_master_orchestrator_graph.ainvoke(
            initial_input_for_master_graph
        )

        generated_queries = final_master_graph_state_dict.get("generated_search_queries", [])
        raw_search_results = final_master_graph_state_dict.get("raw_search_results", [])
        
        search_summary = []
        if raw_search_results:
            for res_set in raw_search_results:
                query = res_set.get("query", "Unknown query")
                content = res_set.get("content_summary", res_set.get("error", "No content/error"))
                search_summary.append({
                    "query": query,
                    "summary_snippet": content[:150] + "..." if content and len(content) > 150 else content
                })

        response_data = DocumentGenerationResponse(
            message="Document generation process initiated and initial research phase completed.",
            initial_topic=final_master_graph_state_dict.get("initial_topic"),
            generated_queries=generated_queries if generated_queries else None,
            search_results_summary=search_summary if search_summary else None,
            error_message=final_master_graph_state_dict.get("error_message")
        )
        return response_data

    except Exception as e:
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during document generation: {str(e)}"
        )