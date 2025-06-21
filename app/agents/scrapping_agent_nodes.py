from typing import Dict, List, Any
import asyncio
import httpx
from bs4 import BeautifulSoup

from app.schemas.document_schemas import ResearchState, ScrapedPage

# Helper function to fetch and parse
async def fetch_and_extract_content(url:str, client: httpx.AsyncClient) -> ScrapedPage:
    """Fetches a single URL and extracts basic info"""

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = await client.get(
            url, 
            timeout = 20.0, 
            headers = headers, 
            follow_redirects = True
        )
        response.raise_for_status()
        
        raw_html = response.text
        soup = BeautifulSoup(raw_html, "lxml")
        
        title_tag = soup.find("title")
        title = title_tag.string.strip() if title_tag else "N/A"
        
        return ScrapedPage(
            url = url, 
            content = raw_html, 
            title = title
        )

    except httpx.HTTPStatusError as e:
        print(f"Scraping Node: HTTP error fetching {url}: {e.response.status_code} - {e.response.reason_phrase}")
        return ScrapedPage(
            url = url,
            content = "",
            error = f"HTTP Error: {e.response.status_code} - {e.response.reason_phrase}"
        )
    
    except httpx.RequestError as e:
        print(f"Scraping Node: Request error fetching {url}: {e}")
        return ScrapedPage(
            url = url, 
            content = "", 
            error = f"Request Error: {e}"
        )
    
    except Exception as e:
        print(f"Scraping Node: General error fetching {url}: {e}")
        return ScrapedPage(
            url = url, 
            content = "", 
            error = f"General Error: {str(e)}"
        )

async def scrape_reference_urls_node(state: ResearchState) -> Dict[str, Any]:
    """
    Node to scrape content from user-provided reference URLs.
    Populates `scraped_content_from_references`.
    """

    urls_to_scrape = state.reference_urls

    # Make sure we have URLs to scrape
    if not urls_to_scrape:
        return {
            "scraped_content_from_references": [],
            "status_message": "No reference URLs to scrape."
        }

    # Initialize a list to hold the scraped pages
    scraped_pages: List[ScrapedPage] = []

    print(f"\n\nScraping Node: Starting to scrape \n\n{len(urls_to_scrape)} \nreference URLs...\n\n")
    # Use an async HTTP client to fetch all URLs concurrently
    async with httpx.AsyncClient() as client:
        tasks = [fetch_and_extract_content(url, client) for url in urls_to_scrape]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        scraped_pages.extend(results)
    
    
    successful_scrapes = sum(1 for page in scraped_pages if not page.error)
    failed_scrapes = len(scraped_pages) - successful_scrapes

    status_msg = f"Scraped {successful_scrapes}/{len(urls_to_scrape)} reference URLs."
    if failed_scrapes > 0:
        status_msg += f" {failed_scrapes} failed."


    print(f"\n\n scrapped contnet \n{scraped_pages}\n\n")
    return {
        "scraped_content_from_references": scraped_pages,
        "status_message": status_msg,
        "error_message": None 
    }