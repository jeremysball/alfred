# PRD #90: Multi-Provider LLM Support

**Status**: Draft  
**Priority**: High  
**Author**: Claude (Agent)  
**Created**: 2026-02-22  
**Related PRDs**: None

---

## Problem Statement

Alfred currently only supports Kimi as an LLM provider. Users cannot:
- Use other cloud providers (z.ai/Grok, OpenRouter)
- Run local models via Ollama
- Switch between multiple models/provider combinations
- Add new models without editing config files

This limits user choice and forces dependency on a single provider.

---

## Solution Overview

Implement a **multi-provider system** where:

1. **Provider + Model = Unique Selection**: Users configure pairs like "Grok 2 via z.ai" or "Claude via OpenRouter" as distinct, selectable models
2. **Modal UI for Everything**: All model selection and configuration happens through modal dialogs (not CLI flags or text commands alone)
3. **Graceful Error Handling**: Unavailable providers (e.g., Ollama not running) show dismissable modals, never crash

---

## Goals

1. **Multiple Providers**: Support z.ai, OpenRouter, and Ollama (in addition to existing Kimi)
2. **Flexible Model Configuration**: Users add models via config file or modal UI
3. **Runtime Model Switching**: Switch models mid-conversation via modal selector
4. **Graceful Degradation**: Provider errors show modals, don't crash the app
5. **Consistent UX**: All interactions use modal-based UI

---

## Non-Goals

1. **Auto-discovery of models**: Not scanning provider APIs for available models
2. **Model download/management**: Not managing Ollama model downloads
3. **Cost tracking per provider**: Not implementing usage/cost dashboards
4. **Provider failover**: Not auto-switching if one provider fails

---

## User Experience

### Model Selection Modal

User triggers model selector (keyboard shortcut or command):

```
┌─────────────────────────────────────────────────────┐
│  Select Model                                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│  > Grok 2 (z.ai)                        [current]   │
│    Claude 3.5 Sonnet (OpenRouter)                   │
│    Llama 3.2 (Ollama)                               │
│    Kimi K2                                           │
│                                                      │
│  [+ Add New Model]                    [Cancel]      │
└─────────────────────────────────────────────────────┘
```

### Add Model Modal

User clicks "Add New Model":

```
┌─────────────────────────────────────────────────────┐
│  Add New Model                                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Name:     [Claude 3.5 Sonnet        ]              │
│                                                      │
│  Provider: [OpenRouter        ▼]                    │
│                                                      │
│  Model:    [anthropic/claude-3.5-sonnet]            │
│                                                      │
│  API Key:  [••••••••••••••••••] [from env ▼]        │
│                                                      │
│  [Test Connection]    [Save]    [Cancel]            │
└─────────────────────────────────────────────────────┘
```

### Error Modal (Ollama Unavailable)

```
┌─────────────────────────────────────────────────────┐
│  ⚠️ Provider Unavailable                             │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Cannot connect to Ollama at:                       │
│  http://localhost:11434/v1                          │
│                                                      │
│  Make sure Ollama is running:                       │
│  $ ollama serve                                     │
│                                                      │
│                                [Switch Model] [OK]   │
└─────────────────────────────────────────────────────┘
```

---

## Technical Architecture

### Components

1. **`src/models/config.py`** — Model configuration storage and loading
2. **`src/models/provider.py`** — Extended provider implementations
3. **`src/models/registry.py`** — Model registry (available models)
4. **`src/models/selector.py`** — Modal selector UI component
5. **`src/models/manager.py`** — Add/edit/delete models UI

### Provider Implementations

All providers use OpenAI-compatible API:

| Provider | Base URL | Auth |
|----------|----------|------|
| z.ai | `https://api.x.ai/v1` | Bearer token |
| OpenRouter | `https://openrouter.ai/api/v1` | Bearer token |
| Ollama | `http://localhost:11434/v1` | None |
| Kimi | Existing | Existing |

### Configuration File

`data/models.json`:

```json
{
  "models": [
    {
      "id": "grok-2",
      "name": "Grok 2",
      "provider": "zai",
      "model": "grok-2",
      "api_key_env": "ZAI_API_KEY"
    },
    {
      "id": "claude-or",
      "name": "Claude 3.5 Sonnet",
      "provider": "openrouter",
      "model": "anthropic/claude-3.5-sonnet",
      "api_key_env": "OPENROUTER_API_KEY"
    },
    {
      "id": "llama-local",
      "name": "Llama 3.2",
      "provider": "ollama",
      "model": "llama3.2",
      "base_url": "http://localhost:11434/v1"
    }
  ],
  "default_model": "grok-2"
}
```

### CLI Integration

- **Startup**: `alfred --model "Llama 3.2"` (selects model by name or id)
- **In-chat**: `/model` opens modal selector
- **Config**: `alfred models add` opens add model modal
- **Config**: `alfred models list` shows configured models

### Telegram Integration

- `/model` — Opens inline keyboard selector
- `/models add` — Guided model addition flow
- `/models list` — List configured models

---

## Implementation Plan

### Milestone 1: Model Configuration System

**Goal**: Create the model configuration storage and loading system

**Tasks**:
- Create `data/models.json` schema and default template
- Implement `ModelConfig` dataclass with validation
- Implement `ModelRegistry` to load/save models
- Migrate existing Kimi config to new format (backward compatible)
- Add model config to `Config` class

**Validation**:
- Unit test: Load models.json, verify parsing
- Unit test: Save new model, verify persistence
- Test: Existing Kimi config still works (migration)

### Milestone 2: Provider Implementations

**Goal**: Implement z.ai, OpenRouter, and Ollama providers

**Tasks**:
- Create `ZAIProvider` using OpenAI SDK
- Create `OpenRouterProvider` using OpenAI SDK
- Create `OllamaProvider` using OpenAI SDK
- Update `LLMFactory` to support all providers
- Add connection testing method to `LLMProvider`

**Validation**:
- Unit test: Each provider constructs correct API client
- Integration test: Connect to each provider (mocked or real)
- Test: Ollama unavailable returns graceful error, not exception

### Milestone 3: Model Selector Modal (CLI)

**Goal**: Modal UI for selecting models in CLI

**Tasks**:
- Create `ModelSelector` component using prompt_toolkit
- Bind to keyboard shortcut (e.g., Ctrl-M or F2)
- Implement `/model` command to open selector
- Show current model indicator in status line
- Handle model switch mid-conversation

**Validation**:
- Manual test: Open selector, switch model, verify switch
- Test: Switch preserves conversation context
- Test: Status line shows correct model name

### Milestone 4: Add Model Modal (CLI)

**Goal**: Modal UI for adding/editing models in CLI

**Tasks**:
- Create `ModelManager` component for add/edit/delete
- Form fields: name, provider (dropdown), model ID, API key source
- Implement "Test Connection" button
- Validate required fields before save
- Add to selector modal as [+ Add New Model] option

**Validation**:
- Manual test: Add new model via modal, verify it appears in selector
- Test: Test Connection fails gracefully for bad credentials
- Test: Required field validation works

### Milestone 5: Error Modals

**Goal**: Graceful error handling with modal UI

**Tasks**:
- Create `ErrorModal` component
- Catch provider connection errors at runtime
- Show error modal with provider-specific help
- "Switch Model" button opens model selector
- "OK" dismisses modal, returns to prompt

**Validation**:
- Test: Ollama not running shows error modal, doesn't crash
- Test: Invalid API key shows error modal
- Test: Switch Model from error modal works

### Milestone 6: Telegram Integration

**Goal**: Model selection and management via Telegram

**Tasks**:
- Implement `/model` inline keyboard selector
- Implement `/models add` guided flow
- Implement `/models list` command
- Handle errors with inline message (not modal)

**Validation**:
- Manual test: Switch models via Telegram
- Manual test: Add model via Telegram flow
- Test: Error messages are user-friendly

### Milestone 7: Documentation

**Goal**: Document new multi-provider system

**Tasks**:
- Update README.md with provider setup instructions
- Document `data/models.json` schema
- Add inline help in modals (tooltips, hints)

**Validation**:
- Documentation covers all three providers
- Example configs for each provider

---

## Testing Strategy

### Unit Tests

1. **Model Config**:
   ```python
   def test_load_models_json():
       registry = ModelRegistry("data/models.json")
       assert len(registry.models) >= 1
   
   def test_save_new_model():
       registry = ModelRegistry()
       registry.add(ModelConfig(id="test", provider="ollama", ...))
       assert registry.get("test") is not None
   ```

2. **Provider Factory**:
   ```python
   def test_factory_creates_zai_provider():
       config = Config(default_llm_provider="zai", ...)
       provider = LLMFactory.create(config)
       assert isinstance(provider, ZAIProvider)
   ```

### Integration Tests

1. **Provider Connection**:
   ```python
   async def test_ollama_connection_unavailable():
       provider = OllamaProvider(base_url="http://localhost:9999")
       result = await provider.test_connection()
       assert result.success is False
       assert "Ollama is not running" in result.error_message
   ```

### Manual Testing Checklist

- [ ] Add z.ai model via modal, verify connection
- [ ] Add OpenRouter model via modal, verify connection
- [ ] Add Ollama model via modal, verify connection (with Ollama running)
- [ ] Switch between models mid-conversation
- [ ] Trigger Ollama error (stop Ollama), verify error modal
- [ ] Dismiss error modal, continue with different model
- [ ] Add model via Telegram
- [ ] Switch model via Telegram

---

## Success Criteria

1. **Provider Support**: All three providers (z.ai, OpenRouter, Ollama) work correctly
2. **Model Management**: Users can add, select, and switch models via modal UI
3. **No Crashes**: Provider errors show modals, never crash the application
4. **Telegram Parity**: Core model selection works via Telegram
5. **Documentation**: Clear setup instructions for each provider

---

## Open Questions

1. **API Key Storage**: Store in models.json or always reference env vars? (Recommend: env vars for security)
2. **Default Models**: Should Alfred ship with pre-configured defaults for each provider?
3. **Model Icons**: Use provider icons in selector for visual distinction?

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-22 | Provider + Model = unique selection | User wants explicit control over which model from which provider |
| 2026-02-22 | Modal UI for everything | Consistent UX, no CLI flag juggling |
| 2026-02-22 | Error modals, not crashes | Graceful degradation, user can switch and continue |
| 2026-02-22 | OpenAI SDK for all providers | All support OpenAI-compatible API, reduces code duplication |

---

## Related Links

- GitHub Issue: #90
- Current Implementation: `src/llm.py`, `src/config.py`
