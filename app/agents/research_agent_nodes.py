from typing import Dict, List, Any
from app.schemas.document_schemas import ResearchState
from app.core.config import get_settings

# LLM and Tool Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

settings = get_settings()

llm = None
if settings.GOOGLE_API_KEY and settings.GOOGLE_API_KEY != "YOUR_FALLBACK_GOOGLE_API_KEY_IF_NOT_SET":
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.DEFAULT_LLM_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.3,
            convert_system_message_to_human=True
        )
        print("Google Generative AI LLM initialized successfully.")
    except Exception as e:
        print(f"Error initializing Google Generative AI LLM: {e}")
        llm = None
else:
    print("GOOGLE_API_KEY not found or is placeholder.")

search_tool = DuckDuckGoSearchRun()
print("DuckDuckGoSearchRun tool initialized.")

# Node functions
async def generate_search_queries_node(state: ResearchState) -> Dict[str, Any]:
    """
    Node to generate specific search queries based on the initial topic using an LLM.
    """

    if not llm:
        print("LLM not initialized. Skipping search query generation.")
        return {
            "status_message": "LLM not initialized; cannot generate search queries.",
            "error_message": "LLM_INITIALIZATION_FAILURE"
        }

    initial_topic = state.initial_topic
    print(f"Initial topic: {initial_topic}")

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are a helpful research assistant. Your task is to generate 3 specific and effective search engine 
            queries based on the given topic. Return only the queries, one per line, without any numbering or preamble.
            """
        ),
        ("human", "Topic: {topic}")
    ])
    
    query_generation_chain = prompt | llm | StrOutputParser()

    try:
        generated_queries_str = await query_generation_chain.ainvoke({"topic": initial_topic})
        generated_queries = [q.strip() for q in generated_queries_str.split("\n") if q.strip()]
        
        print(f"Generated queries: {generated_queries}")
        
        return {
            "generated_search_queries": generated_queries,
            "status_message": f"Generated {len(generated_queries)} search queries for topic: '{initial_topic[:50]}...'"
        }
    except Exception as e:
        print(f"Error during search query generation: {e}")
        return {
            "status_message": "Error generating search queries.",
            "error_message": str(e)
        }

