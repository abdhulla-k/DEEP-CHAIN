from typing import Dict, List, Any
from app.schemas.document_schemas import ResearchState
from app.core.config import get_settings

# LLM and Tool Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from duckduckgo_search import DDGS
import time
import asyncio

settings = get_settings()

llm = None
if settings.GOOGLE_API_KEY and settings.GOOGLE_API_KEY != "API_KEY_PLACEHOLDER":
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.DEFAULT_LLM_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.3,
            convert_system_message_to_human=True
        )

    except Exception as e:
        print(f"Error initializing Google Generative AI LLM: {e}")
        llm = None
else:
    print("GOOGLE_API_KEY not found.")

search_tool = DuckDuckGoSearchRun()

# Node functions
async def generate_search_queries_node(state: ResearchState) -> Dict[str, Any]:
    """
    Node to generate specific search queries based on the initial topic using an LLM.
    Now considers critique_feedback if present.
    """
    
    # Make sure LLM is initialized
    if not llm:
        return {
            "status_message": "LLM not initialized; cannot generate search queries.",
            "error_message": "LLM_INITIALIZATION_FAILURE",
            "generated_search_queries": []
        }

    # Collect information from the state to generate queries
    initial_topic = state.initial_topic
    previous_critique = state.critique_feedback 
    
    # Prepare the system prompt
    prompt_text = (
        "You are a helpful research assistant. Your task is to generate 3 specific and effective "
        "search engine queries based on the given topic. Return only the queries, one per line, "
        "without any numbering or preamble."
    )

    # Generate prompt based on whether previous critique exists
    if previous_critique:
        prompt_text += (
            f"\n\nPrevious attempt's feedback: {previous_critique}\n"
            "Please generate NEW and IMPROVED queries based on this feedback to find better information. "
            "Avoid repeating previous failing query patterns."
        )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_text),
        ("human", "Topic: {topic}")
    ])
    
    # Create the chain with the prompt and LLM to generate search queries
    query_generation_chain = prompt | llm | StrOutputParser()

    try:
        generated_queries_str = await query_generation_chain.ainvoke({ "topic": initial_topic })

        # Split the generated queries by newlines and strip whitespace
        generated_queries = [
            q.strip() 
            for q in generated_queries_str.split("\n") 
            if q.strip()
        ]
        
        if not generated_queries or len(generated_queries) == 0:
            return {
                "generated_search_queries": [],
                "status_message": f"LLM returned no queries for topic: '{initial_topic[:50]}...'",
                "critique_feedback": "LLM failed to generate any queries. Consider re-evaluating topic or prompt.",
                "is_information_sufficient": False
            }
    
        print(f"\n\n--------------Generated Queries:\n{generated_queries_str}\n--------------\n\n")
        
        return {
            "generated_search_queries": generated_queries,
            "status_message": f"Generated {len(generated_queries)} search queries for topic: '{initial_topic[:50]}...'",
            "critique_feedback": None
        }
    
    except Exception as e:
        print(f"Error during search query generation: {e}")
        return {
            "status_message": "Error generating search queries.",
            "error_message": str(e),
            "generated_search_queries": []
        }


async def perform_search_node(state: ResearchState) -> Dict[str, Any]:
    """
    Node to perform web searches using DuckDuckGo for the generated queries.
    Includes small delays to be gentler.
    """
    
    # Make sure we have generated search queries
    queries = state.generated_search_queries
    
    if not queries:
        print("No search queries provided. Skipping search.")
        return {
            "status_message": "No search queries to perform search.",
            "raw_search_results": [],
            "error_message": "NO_SEARCH_QUERIES_PROVIDED"
        }


    all_results = []
    current_history = list(state.search_queries_history) 

    for i, query in enumerate(queries):
        if i > 0:
            # wait a bit between queries to avoid hitting rate limits
            await asyncio.sleep(4)

        try:
            # results = DDGS(timeout=20).text(
            #     query,
            #     max_results=10
            # )
            # print("\n\n\n\n\n results: \n")
            # print(results)
            # print("\n\n\n\n\n")

            # query_results_str = "\n".join(
            #     [f"{result['title']}: {result['body']}" for result in results if 'title' in result and 'body' in result]
            # )
            # if not query_results_str.strip():
            #     query_results_str = "No good DuckDuckGo search result was found for this query."

            # current_history.append({
            #     "query": query,
            #     "results_summary": query_results_str 
            # })
            # all_results.append({
            #     "query": query,
            #     "content_summary": query_results_str
            # })

            # Use the search tool perform the search
            query_results_str = search_tool.invoke(query)
            
            # Create a summary of the results to store in the state
            results_for_this_query = [{
                "query": query,
                "content_summary": query_results_str
            }]
            all_results.extend(results_for_this_query)
            
            current_history.append({
                "query": query,
                "results_summary": query_results_str 
            })
            
        except Exception as e:
            print(f"Error during search for query '{query}': {e}")

            all_results.append({
                "query": query,
                "error": str(e),
                "content_summary": f"Error searching for: {query}"
            })
            current_history.append({
                "query": query,
                "error": str(e)
            })

    print(f"\n\n\n\n------------------Search results: \n for {all_results} queries \n------------------\n")

    return {
        "raw_search_results": all_results, 
        "search_queries_history": current_history,
        "status_message": f"Performed search for {len(queries)} queries. Found {len(all_results)} result sets."
    }

async def evaluate_search_results_node(state: ResearchState) -> Dict[str, Any]:
    """
    Node to evaluate the quality and sufficiency of search results.
    Decides if more searching is needed.
    """
    
    # Start evaluation details
    current_results = state.raw_search_results
    search_iteration = state.iteration_count 
    max_search_iters = state.max_iterations

    sufficient_results_found = False
    feedback_for_requery = "Search results were insufficient. "
    
    # Re-querying if not current results found
    if not current_results:
        feedback_for_requery += "The search process did not return any results structure. Try broader or different queries."
        sufficient_results_found = False

    else:
        valid_content_count = 0
        problematic_queries_details = []

        # Evaluate each result set if it has useful content or errors
        for res_set in current_results: 
            query = res_set.get("query", "Unknown Query")
            content_summary = res_set.get("content_summary", "").lower()
            error_message = res_set.get("error")

            is_problematic = False
            if error_message:
                problematic_queries_details.append(f"Query '{query}' resulted in error: {error_message}")
                is_problematic = True

            elif not content_summary:
                problematic_queries_details.append(f"Query '{query}' returned an empty snippet.")
                is_problematic = True

            elif "no good duckduckgo search result was found" in content_summary:
                problematic_queries_details.append(f"Query '{query}' found no good DDG results.")
                is_problematic = True

            elif "ratelimit" in content_summary or "202 ratelimit" in content_summary :
                problematic_queries_details.append(f"Query '{query}' hit a rate limit.")
                is_problematic = True
            
            if not is_problematic:
                valid_content_count += 1

        if valid_content_count >= 1:
            sufficient_results_found = True
            if problematic_queries_details:
                pass
        else:
            feedback_for_requery += f"All queries resulted in no content, errors, or rate limits. Issues: {problematic_queries_details}. Consider rephrasing or broadening."
            sufficient_results_found = False

    # Check max iterations
    if search_iteration >= max_search_iters -1:
        if not sufficient_results_found:
            feedback_for_requery += " Max search iterations reached, proceeding with current results if any."

        # Force exit from loop by marking as sufficient if we reached max iterations
        sufficient_results_found = True

    updates = {
        "is_information_sufficient": sufficient_results_found,
        "critique_feedback": None if sufficient_results_found and not (search_iteration < max_search_iters -1 and not sufficient_results_found) else feedback_for_requery,
        "status_message": f"Search evaluation complete. Sufficient results: {sufficient_results_found}. Iteration: {search_iteration + 1}/{max_search_iters}"
    }

    if not sufficient_results_found and search_iteration < max_search_iters -1 :
        updates["iteration_count"] = search_iteration + 1 
        updates["generated_search_queries"] = [] 
        updates["raw_search_results"] = []
        
    else:
        # If we are stopping (either sufficient or max iterations reached),
        # ensure iteration_count reflects the final attempt count for clarity in state.
        updates["iteration_count"] = search_iteration + 1 
        print(f"Evaluation: Search loop ending. Final iteration count: {search_iteration + 1}.")


    return updates
