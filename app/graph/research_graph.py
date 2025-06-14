from langgraph.graph import StateGraph, END
from app.schemas.document_schemas import ResearchState
from app.agents.research_agent_nodes import generate_search_queries_node

# Create a StatefulGraph instance with the ResearchState schema.
workflow = StateGraph(ResearchState)

# Add all nodes to the workflow graph.
workflow.add_node("query_generator", generate_search_queries_node)

# Define the entry point of the graph
workflow.set_entry_point("query_generator")

# Define the edges between nodes.
workflow.add_edge("query_generator", END)

# Compile the graph into a runnable application
compiled_graph = workflow.compile()
