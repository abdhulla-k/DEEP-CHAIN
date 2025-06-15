from langgraph.graph import StateGraph, END
from app.schemas.document_schemas import ResearchState
from app.agents.research_agent_nodes import (
    generate_search_queries_node,
    perform_search_node,
    evaluate_search_results_node # Import the new node
)

research_workflow = StateGraph(ResearchState)

# Add nodes to the research workflow
research_workflow.add_node("query_generator", generate_search_queries_node)
research_workflow.add_node("web_searcher", perform_search_node)
research_workflow.add_node("result_evaluator", evaluate_search_results_node)

# Define the entry point
research_workflow.set_entry_point("query_generator")

# Define edges
research_workflow.add_edge("query_generator", "web_searcher")
research_workflow.add_edge("web_searcher", "result_evaluator")

# Function to determine the next step based on search result evaluation
def should_continue_searching(state: ResearchState) -> str:
    """
    Determines the next step after search result evaluation.
    """

    if state.is_information_sufficient:
        # Create a custom name for the end node
        return "end_research_subgraph"
    else:
        return "query_generator"

# Add conditional edges based on the evaluation of search results
research_workflow.add_conditional_edges(
    "result_evaluator",
    should_continue_searching,
    {
        "query_generator": "query_generator",
        "end_research_subgraph": END          
    }
)

# Compile the research sub-graph
compiled_research_subgraph = research_workflow.compile()

# Visualize the compiled research sub-graph
try:
    img_bytes = compiled_research_subgraph.get_graph(xray=True).draw_mermaid_png()
    with open("iterative_research_subgraph.png", "wb") as f:
        f.write(img_bytes)
except Exception as e:
    print(f"Could not generate graph visualization for iterative_research_subgraph")