from langgraph.graph import StateGraph, END
from app.schemas.document_schemas import ResearchState

from app.graph.subgraphs.research_graph import compiled_research_subgraph
from app.graph.subgraphs.scraping_graph import compiled_scraping_subgraph

async def invoke_research_subgraph_node(state: ResearchState) -> dict:
    """
    This node in the master graph is responsible for invoking the compiled research sub-graph.
    """

    subgraph_input = state.model_dump()

    try: 
        print(f"\n Invoking research sub-graph with input: {subgraph_input} \n")
        research_subgraph_final_state_dict = await compiled_research_subgraph.ainvoke(subgraph_input)
        

        return research_subgraph_final_state_dict

    except Exception as e:
        print(f"Master Graph: Error invoking research sub-graph: {e} ")
        import traceback
        traceback.print_exc()
        return {
            "status_message": f"Error during research sub-graph execution: {str(e)}",
            "error_message": f"Research Sub-Graph Error: {str(e)}"
        }

async def invoke_scraping_subgraph_node(state: ResearchState) -> dict:
    """
    This node in the master graph is responsible for invoking the compiled scraping sub-graph.
    """

    subgraph_input = state

    try:
        print(f"\n Invoking scraping sub-graph with input: {subgraph_input} \n")
        scraping_subgraph_final_state: ResearchState = await compiled_scraping_subgraph.ainvoke(subgraph_input)
        return scraping_subgraph_final_state
    
    except Exception as e:
        print(f"Master Graph: Error invoking scraping sub-graph: {e} ")
        import traceback
        traceback.print_exc()
        return {
            "status_message": f"Error during scraping sub-graph execution: {str(e)}",
            "error_message": f"Scraping Sub-Graph Error: {str(e)}"
        }


# Create the master orchestrator graph that combines all subgraphs.
master_workflow = StateGraph(ResearchState)

# Add nodes to the master workflow graph.
master_workflow.add_node("research_phase", invoke_research_subgraph_node)
master_workflow.add_node("scraping_phase", invoke_scraping_subgraph_node)

# Set entry point of the main graph
master_workflow.set_entry_point("research_phase")

# Define the conditional logic after research_phase
def should_scrape_references(state: ResearchState) -> str:
    """
    Decides if we need to run the scraping subgraph.
    """

    # Check for errors from the research phase first
    if state.error_message and "Research Sub-Graph Error" in state.error_message:
        return "end_due_to_error"

    if state.reference_urls and len(state.reference_urls) > 0:
        return "scraping_phase"
    else:
        return "end_no_urls"

master_workflow.add_conditional_edges(
    "research_phase",
    should_scrape_references,
    {
        "scraping_phase": "scraping_phase",
        "end_no_urls": END, 
        "end_due_to_error": END
    }
)

# After scraping_phase (if it runs), end the process with an END node.
master_workflow.add_edge("scraping_phase", END)

# Compile the master workflow into a runnable application.
compiled_master_orchestrator_graph = master_workflow.compile()

try:
    img_bytes = compiled_master_orchestrator_graph.get_graph(xray=True).draw_mermaid_png()
    with open("master_graph.png", "wb") as f:
        f.write(img_bytes)
except Exception as e:
    print(f"Could not generate graph visualization for iterative_research_subgraph")
