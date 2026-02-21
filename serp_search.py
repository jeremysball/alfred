#!/usr/bin/env python3
"""
SerpAPI Search Example
======================
Perform Google searches programmatically using SerpAPI.

Installation:
    pip install serpapi

Get API Key:
    Sign up at https://serpapi.com to get your free API key
"""

import os
import json
from serpapi import GoogleSearch

# Configuration
SERP_API_KEY = os.getenv("SERP_API_KEY", "YOUR_API_KEY_HERE")


def search_google(query: str, **kwargs) -> dict:
    """
    Perform a Google search using SerpAPI.
    
    Args:
        query: Search query string
        **kwargs: Additional parameters (location, language, num_results, etc.)
    
    Returns:
        dict: Search results from SerpAPI
    """
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERP_API_KEY,
        "num": kwargs.get("num_results", 10),
    }
    
    # Add optional parameters
    if "location" in kwargs:
        params["location"] = kwargs["location"]
    if "language" in kwargs:
        params["hl"] = kwargs["language"]
    if "safe" in kwargs:
        params["safe"] = kwargs["safe"]
    
    search = GoogleSearch(params)
    results = search.get_dict()
    
    return results


def extract_organic_results(results: dict) -> list:
    """
    Extract organic search results.
    
    Returns:
        List of result dictionaries with title, link, and snippet
    """
    organic_results = results.get("organic_results", [])
    
    extracted = []
    for result in organic_results:
        extracted.append({
            "position": result.get("position"),
            "title": result.get("title"),
            "link": result.get("link"),
            "snippet": result.get("snippet"),
            "displayed_link": result.get("displayed_link")
        })
    
    return extracted


def extract_featured_snippet(results: dict) -> dict:
    """Extract featured snippet if present."""
    answer_box = results.get("answer_box")
    if answer_box:
        return {
            "title": answer_box.get("title"),
            "snippet": answer_box.get("snippet"),
            "link": answer_box.get("link")
        }
    return None


def extract_related_questions(results: dict) -> list:
    """Extract 'People Also Ask' questions."""
    related = results.get("related_questions", [])
    return [
        {
            "question": q.get("question"),
            "snippet": q.get("snippet"),
            "link": q.get("link")
        }
        for q in related
    ]


def extract_images(results: dict) -> list:
    """Extract image results if available."""
    images = results.get("images_results", [])
    return [
        {
            "title": img.get("title"),
            "thumbnail": img.get("thumbnail"),
            "original": img.get("original"),
            "source": img.get("source")
        }
        for img in images[:10]  # Limit to first 10
    ]


def print_results(results: dict, verbose: bool = False):
    """Pretty print search results."""
    
    # Featured Snippet
    snippet = extract_featured_snippet(results)
    if snippet:
        print("\n" + "="*60)
        print("📌 FEATURED SNIPPET")
        print("="*60)
        print(f"Title: {snippet['title']}")
        print(f"Snippet: {snippet['snippet']}")
        print(f"Link: {snippet['link']}")
    
    # Organic Results
    print("\n" + "="*60)
    print("🌐 ORGANIC RESULTS")
    print("="*60)
    
    organic = extract_organic_results(results)
    for i, result in enumerate(organic, 1):
        print(f"\n{i}. {result['title']}")
        print(f"   Link: {result['link']}")
        print(f"   Snippet: {result['snippet']}")
    
    # Related Questions
    questions = extract_related_questions(results)
    if questions:
        print("\n" + "="*60)
        print("❓ PEOPLE ALSO ASK")
        print("="*60)
        for q in questions:
            print(f"\nQ: {q['question']}")
            print(f"A: {q['snippet']}")
    
    # Verbose: Raw JSON
    if verbose:
        print("\n" + "="*60)
        print("📄 RAW RESULTS (JSON)")
        print("="*60)
        print(json.dumps(results, indent=2))


# ============================================================
# EXAMPLES
# ============================================================

def example_basic_search():
    """Basic search example."""
    print("\n🔍 Example: Basic Search")
    print("-" * 60)
    
    results = search_google(
        query="Python programming language",
        num_results=5
    )
    
    print_results(results)


def example_local_search():
    """Local search with location."""
    print("\n🔍 Example: Local Search")
    print("-" * 60)
    
    results = search_google(
        query="best pizza restaurants",
        location="New York, NY",
        num_results=5
    )
    
    # Extract local results if available
    local_results = results.get("local_results", [])
    if local_results:
        print("\n📍 Local Results:")
        for place in local_results[:5]:
            print(f"  • {place.get('title')}")
            print(f"    Rating: {place.get('rating')} ({place.get('reviews')} reviews)")
            print(f"    Address: {place.get('address')}")
            print()
    else:
        print_results(results)


def example_news_search():
    """Search for news articles."""
    print("\n🔍 Example: News Search")
    print("-" * 60)
    
    results = search_google(
        query="latest technology news",
        num_results=5
    )
    
    # Extract news results
    news_results = results.get("news_results", [])
    if news_results:
        print("\n📰 News Results:")
        for article in news_results[:5]:
            print(f"\n  • {article.get('title')}")
            print(f"    Source: {article.get('source')}")
            print(f"    Date: {article.get('date')}")
            print(f"    Link: {article.get('link')}")
    else:
        print_results(results)


def example_shopping_search():
    """Search for shopping results."""
    print("\n🔍 Example: Shopping Search")
    print("-" * 60)
    
    results = search_google(
        query="wireless headphones",
        num_results=5
    )
    
    # Extract shopping results
    shopping = results.get("shopping_results", [])
    if shopping:
        print("\n🛍️ Shopping Results:")
        for item in shopping[:5]:
            print(f"\n  • {item.get('title')}")
            print(f"    Price: {item.get('price')}")
            print(f"    Rating: {item.get('rating')} stars")
            print(f"    Source: {item.get('source')}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import sys
    
    # Check if API key is set
    if SERP_API_KEY == "YOUR_API_KEY_HERE":
        print("⚠️  Warning: Please set your SERP_API_KEY!")
        print("   Get one at: https://serpapi.com")
        print("   Set it as environment variable: export SERP_API_KEY='your_key'")
        print("\n   Continuing with example output...\n")
    
    # Run examples
    example_basic_search()
    example_local_search()
    example_news_search()
    example_shopping_search()
    
    # Command line usage
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"\n🔍 Custom Search: '{query}'")
        print("-" * 60)
        results = search_google(query, num_results=10)
        print_results(results)
