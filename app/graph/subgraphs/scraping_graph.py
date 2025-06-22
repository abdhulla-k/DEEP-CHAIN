from langgraph.graph import StateGraph, END

from app.schemas.document_schemas import ResearchState
from app.agents.scrapping_agent_nodes import (
    scrape_reference_urls_node,
    extract_text_from_scraped_content_node
)

scrapping_workflow = StateGraph(ResearchState)

# Add nodes to the scrapping workflow
scrapping_workflow.add_node("scrape_reference_urls", scrape_reference_urls_node)
scrapping_workflow.add_node("extract_text_from_scraped_content", extract_text_from_scraped_content_node)

scrapping_workflow.set_entry_point("scrape_reference_urls")

# Define edges
scrapping_workflow.add_edge("scrape_reference_urls", "extract_text_from_scraped_content")
scrapping_workflow.add_edge("extract_text_from_scraped_content", END)

compiled_scraping_subgraph = scrapping_workflow.compile()

# Visualize the compiled scraping sub-graph
try:
    img_bytes = compiled_scraping_subgraph.get_graph(xray=True).draw_mermaid_png()
    with open("scraping_subgraph.png", "wb") as f:
        f.write(img_bytes)
except Exception as e:
    print(f"Could not generate graph visualization for scraping subgraph: {e}")