---
name: context7
description: Access up-to-date, version-specific library documentation and code examples via the Context7 API by Upstash
---

# Context7 Documentation API

Fetch current library documentation, API references, and code examples through the Context7 REST API. Eliminate hallucinated APIs by giving your LLM accurate, version-specific docs for any supported library.

## Overview

Context7 provides LLM-ready documentation context from 3,500+ libraries. Use it when you need:
- Up-to-date API references for popular libraries
- Version-specific code examples
- Current documentation that training data lacks
- Accurate function signatures and parameters

## Requirements

- Context7 API key (optional but recommended from https://context7.com/dashboard)
- `CONTEXT7_API_KEY` environment variable set (for higher rate limits)
- curl or HTTP client for API requests

## API Endpoints

```
https://context7.com/api/v2/libs/search    # Search for libraries
https://context7.com/api/v2/context        # Get documentation context
```

## Quick Start

### Using curl

**Search for a library:**
```bash
export CONTEXT7_API_KEY="your_api_key_here"

curl -G "https://context7.com/api/v2/libs/search" \
  -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  --data-urlencode "query=react"
```

**Get documentation context:**
```bash
curl -G "https://context7.com/api/v2/context" \
  -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  --data-urlencode "libraryId=/facebook/react" \
  --data-urlencode "query=useState hook"
```

**Load from .env file:**
```bash
source .env && curl -G "https://context7.com/api/v2/libs/search" \
  -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  --data-urlencode "query=fastapi"
```

### Using Python

```python
import requests
import os

api_key = os.environ.get("CONTEXT7_API_KEY", "")
base_url = "https://context7.com/api/v2"

headers = {}
if api_key:
    headers["Authorization"] = f"Bearer {api_key}"

# Search for libraries
response = requests.get(
    f"{base_url}/libs/search",
    headers=headers,
    params={"query": "react"}
)
libraries = response.json()

# Get documentation context
response = requests.get(
    f"{base_url}/context",
    headers=headers,
    params={
        "libraryId": "/facebook/react",
        "query": "useState hook example"
    }
)
context = response.json()
```

## API Methods

### Search Libraries

Find libraries by name with intelligent LLM-powered ranking.

**Endpoint:** `GET /api/v2/libs/search`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Library name to search for |
| `limit` | integer | No | Max results to return (default: 10) |

**Example:**
```bash
curl -G "https://context7.com/api/v2/libs/search" \
  --data-urlencode "query=python requests" \
  --data-urlencode "limit=5"
```

**Response:**
```json
{
  "results": [
    {
      "libraryId": "/psf/requests",
      "name": "requests",
      "description": "Python HTTP library",
      "version": "2.31.0"
    }
  ]
}
```

### Get Documentation Context

Retrieve LLM-reranked documentation snippets for a specific query.

**Endpoint:** `GET /api/v2/context`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `libraryId` | string | Yes | Context7-compatible library ID (e.g., `/facebook/react`) |
| `query` | string | Yes | Natural language query about the library |
| `limit` | integer | No | Number of snippets to return (default: 5) |

**Example:**
```bash
curl -G "https://context7.com/api/v2/context" \
  --data-urlencode "libraryId=/facebook/react" \
  --data-urlencode "query=useEffect cleanup function" \
  --data-urlencode "limit=3"
```

**Response:**
```json
{
  "context": [
    {
      "content": "useEffect(() => { const subscription = props.source.subscribe(); return () => { subscription.unsubscribe(); }; }, [props.source]);",
      "source": "https://react.dev/reference/react/useEffect",
      "score": 0.95
    }
  ]
}
```

## Common Use Cases

### Get Current API Documentation

```bash
curl -G "https://context7.com/api/v2/context" \
  -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  --data-urlencode "libraryId=/python/fastapi" \
  --data-urlencode "query=dependency injection"
```

### Find Library ID

```bash
curl -G "https://context7.com/api/v2/libs/search" \
  --data-urlencode "query=langchain python"
```

### Get Code Examples

```bash
curl -G "https://context7.com/api/v2/context" \
  -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  --data-urlencode "libraryId=/openai/openai-python" \
  --data-urlencode "query=streaming chat completion example"
```

### Verify Function Signatures

```bash
curl -G "https://context7.com/api/v2/context" \
  -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  --data-urlencode "libraryId=/numpy/numpy" \
  --data-urlencode "query=np.ndarray.shape property"
```

## Library ID Format

Library IDs follow the pattern `/org/project`:

| Library | Library ID |
|---------|------------|
| React | `/facebook/react` |
| Vue.js | `/vuejs/vue` |
| FastAPI | `/tiangolo/fastapi` |
| Pydantic | `/pydantic/pydantic` |
| LangChain | `/langchain-ai/langchain` |
| NumPy | `/numpy/numpy` |
| pandas | `/pandas-dev/pandas` |

Use the search endpoint to find the correct library ID for any library.

## Workflow

**Two-step process for documentation lookup:**

1. **Resolve library ID:**
   ```bash
   curl -G "https://context7.com/api/v2/libs/search" \
     --data-urlencode "query=library-name"
   ```

2. **Get context:**
   ```bash
   curl -G "https://context7.com/api/v2/context" \
     --data-urlencode "libraryId=/org/project" \
     --data-urlencode "query=your question"
   ```

## Error Handling

Common HTTP status codes:

| Code | Meaning | Solution |
|------|---------|----------|
| 200 | Success | - |
| 401 | Unauthorized | Check CONTEXT7_API_KEY |
| 404 | Library not found | Verify libraryId exists |
| 429 | Rate Limited | Wait and retry or use API key |
| 500 | Server Error | Retry or contact support |

## Rate Limits

- Without API key: Limited requests per IP
- With API key: Higher limits based on plan
- Free tier available at context7.com/dashboard

Check your usage at https://context7.com/dashboard

## Environment Setup

Add to your `.env` file:

```bash
CONTEXT7_API_KEY=your_api_key_here
```

Or export in your shell:

```bash
export CONTEXT7_API_KEY="your_api_key_here"
```

## Tips

1. **Always use specific queries:** `"useState initial value"` works better than `"react hooks"`
2. **Include version keywords:** Add version numbers if you need specific docs
3. **Check library coverage:** Not all libraries are indexed; search first
4. **Combine with web search:** Use Context7 for API details, Serper for broader context

## Troubleshooting

**No results returned:**
- Verify libraryId format is `/org/project`
- Check the library exists at context7.com
- Try broader search terms

**Outdated documentation:**
- Context7 indexes regularly from source
- Some libraries update faster than others
- Use specific version queries if available

**Rate limit errors:**
- Get a free API key for higher limits
- Implement request caching
- Batch related queries

## Related Links

- [Context7 Website](https://context7.com)
- [Dashboard](https://context7.com/dashboard)
- [GitHub](https://github.com/upstash/context7)
- [API Guide](https://context7.com/docs/api-guide)
