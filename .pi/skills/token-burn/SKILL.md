---
name: token-burn
description: Calculate total token usage from pi session JSONL files with beautiful emoji tables. Use when analyzing conversation history, tracking API costs, or auditing token consumption.
---

# 🔥 Token Burn

Calculate token usage from pi session JSONL files with beautiful visual output. Extracts actual token counts including cached tokens (cacheRead, cacheWrite) from message metadata.

![Token Burn Demo](assets/demo.png)

## ✨ Features

| Feature | Status | Emoji |
|---------|--------|-------|
| Beautiful emoji-enhanced tables | ✅ | 📊 |
| Stream large JSONL files | ✅ | 🌊 |
| Extract cached tokens | ✅ | 💾 |
| Model detection with icons | ✅ | 🤖 |
| Recursive directory processing | ✅ | 📁 |
| JSON output format | ✅ | 📋 |
| Cost estimation guidance | ✅ | 💰 |

## 🚀 Quick Start

```bash
cd /workspace/.pi/skills/token-burn

# 🔥 Run with default path (~/.pi/agent/sessions)
python3 src/token_burn.py

# 📄 Process specific session file
python3 src/token_burn.py ~/.pi/agent/sessions/--workspace--/2026-02-18.jsonl

# 📁 Process all sessions recursively
python3 src/token_burn.py ~/.pi/agent/sessions --recursive

# 📋 Output as JSON
python3 src/token_burn.py --json
```

## 📖 Usage Examples

### Default Session Analysis
```bash
# Analyzes ~/.pi/agent/sessions by default
python3 src/token_burn.py
```

**Output:**
```
🔥════════════════════════════════════════════════════════════════════🔥
║                    💰 TOKEN BURN REPORT 💰                         ║
🔥════════════════════════════════════════════════════════════════════🔥

╔════════════════════════════════════════════════════════════════════╗
║📊  Session Summary                                                 ║
╠════════════════════════════════════════════════════════════════════╣
║  📁 Files Processed              84                                ║
║  📄 Total Lines              11,561                                ║
║  💬 Messages w/ Usage         4,899                                ║
╚════════════════════════════════════════════════════════════════════╝
```

### JSON Output for Automation
```bash
python3 src/token_burn.py --json > token_report.json
```

## 📊 Output Format Details

### Model Emojis

| Provider | Emoji | Example Models |
|----------|-------|----------------|
| Kimi | 🌙 | kimi-coding/k2p5, kimi-k2-thinking |
| Claude | 🧠 | claude-4-sonnet, claude-opus-4 |
| OpenAI | 🤖 | o1, o3-mini, gpt-4o |
| Gemini | 💎 | gemini-2.0-flash-thinking |
| GLM/Zhipu | ⚡ | glm-4, glm-5 |
| DeepSeek | 🔮 | deepseek-r1, deepseek-reasoner |
| Qwen | 🐉 | qwen-qwq |
| Unknown | 🤖 | fallback for unrecognized models |

### Token Types

| Token Type | Emoji | Description |
|------------|-------|-------------|
| `input` | 📥 | Standard input tokens sent to API |
| `output` | 📤 | Generated output tokens from model |
| `cacheRead` | 💾 | Tokens read from cache (cheaper) |
| `cacheWrite` | 💿 | Tokens written to cache (one-time cost) |

## 💰 Cost Estimation with Search Skills

Token Burn integrates with search skills to estimate actual costs:

### Step 1: Get Token Counts
```bash
python3 src/token_burn.py
```

### Step 2: Search for Current Pricing

```bash
# For Claude/Anthropic models
serper-search "Anthropic Claude API pricing per token 2025"

# For OpenAI models  
serper-search "OpenAI o1 API pricing per million tokens 2025"

# For Kimi models
serper-search "Moonshot AI Kimi k2 API pricing 2025"
```

### Step 3: Calculate Estimated Cost

```
Model: kimi-coding/k2p5
Input tokens:      11,065,261
Output tokens:      1,082,103
Cache read:       239,416,576

Pricing (example):
- Input:   $0.50/1M
- Output:  $1.50/1M
- Cache read: $0.05/1M (usually much cheaper)

Cost = (11.07M × $0.50) + (1.08M × $1.50) + (239.42M × $0.05)
     = $5.54 + $1.62 + $11.97
     = $19.13
```

## 🔧 Advanced Usage

### Process Specific Workspace
```bash
python3 src/token_burn.py ~/.pi/agent/sessions/--workspace-alfred-- --recursive
```

### Filter by Date Range
```bash
find ~/.pi/agent/sessions -name "2026-02-18*.jsonl" -exec \
  python3 src/token_burn.py {} \;
```

## 🛠️ How It Works

1. **🌊 Streaming**: Reads JSONL files line-by-line without loading into memory
2. **🔍 Model Detection**: Extracts provider/model from message metadata  
3. **📊 Token Extraction**: Extracts `input`, `output`, `cacheRead`, `cacheWrite`
4. **🧮 Aggregation**: Sums tokens by model and calculates grand totals
5. **🎨 Beautiful Output**: Renders emoji-enhanced tables with smart formatting

## 🔗 Integration with Other Skills

| Skill | Use Case | Command Example |
|-------|----------|-----------------|
| serper-search | Find current API pricing | `serper-search "Claude API pricing 2025"` |
| writing-clearly | Document findings | Use for cost reports |

## 📝 License

MIT © 2025 Token Burn Project
