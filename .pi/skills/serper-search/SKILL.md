---
name: serper-search
description: Google Search API via Serper.dev for web search, news, images, and knowledge graph results with high-quality structured data
---

# Serper Search API

Access Google Search programmatically through Serper.dev API. Get structured search results including organic listings, news, images, knowledge graph data, and more.

## Overview

Serper provides a fast, reliable API for Google Search with structured JSON responses. Use it when you need:
- Real-time web search results
- News articles and headlines
- Image search
- Knowledge graph information
- Related searches and questions

## Requirements

- Serper API key (from https://serper.dev/)
- `SERPER_API_KEY` environment variable set
- curl or HTTP client for API requests

## API Endpoint

```
POST https://google.serper.dev/search
```

## Quick Start

### Using curl

```bash
curl -X POST https://google.serper.dev/search \
  -H "X-API-KEY: $SERPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "your search query"
  }'
```

### Using Python

```python
import requests
import os

api_key = os.environ["SERPER_API_KEY"]
url = "https://google.serper.dev/search"

payload = {
    "q": "your search query",
    "num": 10
}

headers = {
    "X-API-KEY": api_key,
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)
results = response.json()
```

## Search Types

### Web Search (Default)

Search standard Google web results:

```bash
curl -X POST https://google.serper.dev/search \
  -H "X-API-KEY: $SERPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "Python async best practices",
    "num": 10,
    "page": 1
  }'
```

### News Search

Get current news articles:

```bash
curl -X POST https://google.serper.dev/news \
  -H "X-API-KEY: $SERPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "artificial intelligence 2025"
  }'
```

### Images Search

Search for images:

```bash
curl -X POST https://google.serper.dev/images \
  -H "X-API-KEY: $SERPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "mountain landscape"
  }'
```

## Request Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `q` | string | **Required.** Search query | - |
| `num` | integer | Number of results (max 100) | 10 |
| `page` | integer | Page number for pagination | 1 |
| `gl` | string | Country code (e.g., "us", "uk", "de") | "us" |
| `hl` | string | Language code (e.g., "en", "es", "fr") | "en" |
| `location` | string | Specific location for local search | - |
| `autocorrect` | boolean | Enable autocorrect | true |

## Response Structure

### Web Search Response

```json
{
  "searchParameters": {
    "q": "Python async best practices",
    "gl": "us",
    "hl": "en",
    "num": 10
  },
  "organic": [
    {
      "title": "Python Async/Await Tutorial",
      "link": "https://example.com/python-async",
      "snippet": "Learn the best practices for async/await in Python...",
      "position": 1
    }
  ],
  "knowledgeGraph": {
    "title": "Python",
    "type": "Programming Language",
    "description": "Python is a high-level programming language..."
  },
  "relatedSearches": [
    "python asyncio tutorial",
    "python async vs threading"
  ]
}
```

### News Search Response

```json
{
  "news": [
    {
      "title": "AI Breakthrough in 2025",
      "link": "https://example.com/news/ai-breakthrough",
      "snippet": "Scientists announce major advancement...",
      "date": "1 hour ago",
      "source": "Tech News Daily"
    }
  ]
}
```

### Images Search Response

```json
{
  "images": [
    {
      "title": "Beautiful Mountain",
      "imageUrl": "https://example.com/mountain.jpg",
      "link": "https://example.com/image-page",
      "source": "Example Site"
    }
  ]
}
```

## Common Use Cases

### Latest Technology News

```bash
curl -X POST https://google.serper.dev/news \
  -H "X-API-KEY: $SERPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q": "AI technology news 2025"}'
```

### Documentation Search

```bash
curl -X POST https://google.serper.dev/search \
  -H "X-API-KEY: $SERPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "site:docs.python.org asyncio"
  }'
```

### Stock/Financial Information

```bash
curl -X POST https://google.serper.dev/search \
  -H "X-API-KEY: $SERPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "TSLA stock price"
  }'
```

### Local Business Search

```bash
curl -X POST https://google.serper.dev/search \
  -H "X-API-KEY: $SERPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "best restaurants in San Francisco",
    "location": "San Francisco, CA"
  }'
```

### Academic Research

```bash
curl -X POST https://google.serper.dev/search \
  -H "X-API-KEY: $SERPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "machine learning paper filetype:pdf",
    "num": 20
  }'
```

## Search Tips

1. **Use site-specific searches**: `"site:github.com python projects"`
2. **Filter by filetype**: `"python tutorial filetype:pdf"`
3. **Exclude terms**: `"python -snake -monty"`
4. **Exact phrases**: `"\"async await\" python"`
5. **Date filtering**: Add "2024" or "2025" for recent results

## Error Handling

Common HTTP status codes:

| Code | Meaning | Solution |
|------|---------|----------|
| 200 | Success | - |
| 401 | Unauthorized | Check SERPER_API_KEY |
| 429 | Rate Limited | Wait and retry |
| 500 | Server Error | Retry or contact support |

## Quota and Limits

- Free tier: 100 searches/month
- Paid tiers: Higher limits available
- Rate limits vary by plan

Check your usage at https://serper.dev/dashboard

## Environment Setup

Add to your `.env` file:

```bash
SERPER_API_KEY=your_api_key_here
```

Or export in your shell:

```bash
export SERPER_API_KEY="your_api_key_here"
```

## Troubleshooting

**No results returned:**
- Check API key is valid
- Verify query is not empty
- Check rate limit status

**Unexpected results:**
- Try different query variations
- Use quotes for exact phrases
- Check `gl` and `hl` parameters

**Slow response:**
- Results are real-time from Google
- Complex queries may take longer
- Consider caching frequent searches

## Related Links

- [Serper Documentation](https://serper.dev/docs)
- [API Playground](https://serper.dev/playground)
- [Pricing](https://serper.dev/pricing)
