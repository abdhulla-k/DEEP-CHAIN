from langgraph.graph import StateGraph, END
from app.schemas.document_schemas import ResearchState

from app.graph.subgraphs.research_graph import compiled_research_subgraph

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
        print(f"--- Master Graph: Error invoking research sub-graph: {e} ---")
        import traceback
        traceback.print_exc()
        return {
            "status_message": f"Error during research sub-graph execution: {str(e)}",
            "error_message": f"Research Sub-Graph Error: {str(e)}"
        }

master_workflow = StateGraph(ResearchState)

# Add nodes to the master workflow graph.
master_workflow.add_node("research_phase", invoke_research_subgraph_node)

# Set entry point of the main graph
master_workflow.set_entry_point("research_phase")

# Define the edges between nodes.
master_workflow.add_edge("research_phase", END)

# Compile the master workflow into a runnable application.
compiled_master_orchestrator_graph = master_workflow.compile()
