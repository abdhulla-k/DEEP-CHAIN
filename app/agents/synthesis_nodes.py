from app.schemas.document_schemas import ResearchState
from typing import Dict, List, Any
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings

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



async def synthesize_information_node(state: ResearchState) -> Dict[str, Any]:
    """
    Synthesizes information from web search results and scraped reference texts
    into a consolidated knowledge base.
    """
    if not llm:
        return {
            "consolidated_information": "LLM not available for synthesis.",
            "status_message": "Synthesis skipped: LLM not initialized.",
            "error_message": "SYNTHESIS_LLM_ERROR"
        }


    # Collect the necessary information from the state
    initial_topic = state.initial_topic
    search_results = state.raw_search_results
    reference_texts = state.extracted_text_from_references

    formatted_input_parts = []

    if search_results:
        search_snippets_text = "\n\n".join(
            [
                f"Source (Search Query: '{res.get('query', 'N/A')}'):\n{res.get('content_summary', 'No snippet available.')}"
                for res in search_results if res.get('content_summary')
            ]
        )
        if search_snippets_text.strip():
            formatted_input_parts.append(
                f"Information from Web Search Snippets: \n{search_snippets_text}"
            )

    if reference_texts:
        scraped_content_text = "\n\n".join(
            [
                f"Source (Reference URL: {ref.get('url', 'N/A')}, Title: '{ref.get('title', 'N/A')}'):\n{ref.get('extracted_text', 'No text extracted.')}"
                for ref in reference_texts if ref.get('extracted_text') 
            ]
        )
        if scraped_content_text.strip():
            formatted_input_parts.append(
                f"Information from Scraped Reference URLs: \n{scraped_content_text}"
            )

    if not formatted_input_parts:
        print("No relevant information found to synthesize.")

        return {
            "consolidated_information": "No information gathered from previous steps to synthesize.",
            "status_message": "Synthesis complete: No input information.",
        }

    full_context_for_llm = "\n\n".join(formatted_input_parts)
    
    # Limit the context length if necessary
    if len(full_context_for_llm) > 30000:
        full_context_for_llm = full_context_for_llm[:30000]

    system_prompt = (
        "You are an expert research assistant and information synthesizer. "
        "Your task is to review the provided information, which comes from web search snippets and content scraped from specific URLs. "
        "Based on this information, create a comprehensive, coherent, and de-duplicated summary that is highly relevant to the 'Original Topic'. "
        "Focus on extracting and organizing key facts, arguments, data points, and important concepts. "
        "The goal is to produce a structured knowledge base that can be used by another AI to write a detailed document. "
        "Do not add information that is not present in the provided texts. "
        "If the provided information is contradictory, point it out. "
        "Organize the output logically, perhaps using markdown for structure if appropriate (e.g., headings for different aspects of the topic if they emerge from the content)."
    )

    human_prompt_template = (
        "Original Topic: {topic}\n\n"
        "Collected Information to Synthesize:\n"
        "-------------------------------------\n"
        "{context}\n"
        "-------------------------------------\n\n"
        "Please synthesize the above information thoroughly, keeping the original topic in mind. "
        "Produce a clean, consolidated text. If no relevant information is found for the topic in the provided context, state that clearly."
    )

    # LangChain prompt structure
    from langchain_core.prompts import ChatPromptTemplate
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_prompt_template)
    ])

    # Create the chain and invoke the LLM
    try:
        synthesis_chain = prompt | llm
        
        llm_response = await synthesis_chain.ainvoke({
            "topic": initial_topic,
            "context": full_context_for_llm
        })
        
        # The response from ChatGoogleGenerativeAI is an AIMessage
        synthesized_text = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

        if not synthesized_text.strip():
            synthesized_text = "LLM returned no synthesized text."
        else:
            print(f"\n\nSynthesis Node: \nLLM synthesis successful. Output length (chars): {len(synthesized_text)}\n\n")

        return {
            "consolidated_information": synthesized_text,
            "status_message": "Information synthesis complete.",
            "error_message": None
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "consolidated_information": f"Error during synthesis: {str(e)}",
            "status_message": "Synthesis failed due to an error.",
            "error_message": f"SYNTHESIS_LLM_INVOCATION_ERROR: {str(e)}"
        }