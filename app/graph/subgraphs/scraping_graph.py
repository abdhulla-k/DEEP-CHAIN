from langgraph.graph import StateGraph, END

from app.schemas.document_schemas import ResearchState
from app.agents.scrapping_agent_nodes import (
    scrape_reference_urls_node
)

scrapping_workflow = StateGraph(ResearchState)

# Add nodes to the scrapping workflow
scrapping_workflow.add_node("scrape_reference_urls", scrape_reference_urls_node)

scrapping_workflow.set_entry_point("scrape_reference_urls")

# Define edges
scrapping_workflow.add_edge("scrape_reference_urls", END)

compiled_scraping_subgraph = scrapping_workflow.compile()
