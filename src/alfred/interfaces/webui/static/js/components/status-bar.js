/**
 * Status Bar Web Component
 *
 * Usage: <status-bar model="kimi-latest" queue="0" streaming="false"></status-bar>
 *
 * Attributes:
 *   - model: Current LLM model name
 *   - inputtokens: Input token count
 *   - outputtokens: Output token count
 *   - cachedtokens: Cache read token count
 *   - reasoningtokens: Reasoning/thinking token count
 *   - contexttokens: Current context usage
 *   - contextwindowtokens: Total context window size
 *   - queue: Number of queued messages
 *   - streaming: Whether LLM is generating (true/false)
 */
class StatusBar extends HTMLElement {
  constructor() {
    super();
    this._model = "";
    this._inputTokens = 0;
    this._outputTokens = 0;
    this._cachedTokens = 0;
    this._reasoningTokens = 0;
    this._contextTokens = 0;
    this._contextWindowTokens = 0;
    this._queue = 0;
    this._streaming = false;
    this._throbberIndex = 0;
    this._throbberInterval = null;
  }

  static get observedAttributes() {
    return [
      "model",
      "inputtokens",
      "outputtokens",
      "cachedtokens",
      "reasoningtokens",
      "contexttokens",
      "contextwindowtokens",
      "queue",
      "streaming",
    ];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue === newValue) return;

    switch (name) {
      case "model":
        this._model = newValue || "";
        break;
      case "inputtokens":
        this._inputTokens = parseInt(newValue, 10) || 0;
        break;
      case "outputtokens":
        this._outputTokens = parseInt(newValue, 10) || 0;
        break;
      case "cachedtokens":
        this._cachedTokens = parseInt(newValue, 10) || 0;
        break;
      case "reasoningtokens":
        this._reasoningTokens = parseInt(newValue, 10) || 0;
        break;
      case "contexttokens":
        this._contextTokens = parseInt(newValue, 10) || 0;
        break;
      case "contextwindowtokens":
        this._contextWindowTokens = parseInt(newValue, 10) || 0;
        break;
      case "queue":
        this._queue = parseInt(newValue, 10) || 0;
        break;
      case "streaming":
        this._streaming = newValue === "true";
        this._handleStreamingChange();
        break;
    }
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  disconnectedCallback() {
    this._stopThrobber();
  }

  _handleStreamingChange() {
    if (this._streaming) {
      this._startThrobber();
    } else {
      this._stopThrobber();
    }
  }

  _startThrobber() {
    if (this._throbberInterval) return;

    const throbberChars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
    this._throbberIndex = 0;

    this._throbberInterval = setInterval(() => {
      this._throbberIndex = (this._throbberIndex + 1) % throbberChars.length;
      const throbberEl = this.querySelector(".throbber");
      if (throbberEl) {
        throbberEl.textContent = throbberChars[this._throbberIndex];
      }
    }, 80);
  }

  _stopThrobber() {
    if (this._throbberInterval) {
      clearInterval(this._throbberInterval);
      this._throbberInterval = null;
    }
  }

  _render() {
    const throbberChar = this._streaming ? "⠋" : "";
    const streamingClass = this._streaming ? "streaming" : "";
    const queueClass = this._queue > 0 ? "has-queue" : "";

    // Format token display
    const tokensDisplay = this._formatTokens();
    const queueMarkup =
      this._queue > 0
        ? `
        <div class="status-section queue-section ${queueClass}">
          <span class="status-label">Queue</span>
          <span class="status-value queue-count">${this._queue}</span>
        </div>`
        : "";

    this.innerHTML = `
      <div class="status-bar ${streamingClass}">
        <div class="status-section streaming-section ${this._streaming ? "active" : "hidden"}">
          <span class="throbber">${throbberChar}</span>
          <span class="streaming-text">Thinking...</span>
        </div>
        <div class="status-section model-section">
          <span class="status-label">Model</span>
          <span class="status-value model-name">${this._escapeHtml(this._model) || "-"}</span>
        </div>
        <div class="status-section tokens-section">
          <span class="status-label">Tokens</span>
          <span class="status-value tokens-display">${tokensDisplay}</span>
        </div>
        <div class="status-section context-section mobile-context-section">
          <span class="status-label mobile-context-label">Ctx</span>
          <span class="status-value context-display">${this._formatContextCompact()}</span>
        </div>
        ${queueMarkup}
      </div>
    `;
  }

  _formatTokens() {
    const parts = [];
    if (this._inputTokens > 0) {
      parts.push(`In: ${this._formatNumber(this._inputTokens)}`);
    }
    if (this._outputTokens > 0) {
      parts.push(`Out: ${this._formatNumber(this._outputTokens)}`);
    }
    if (this._cachedTokens > 0) {
      parts.push(`Cache: ${this._formatNumber(this._cachedTokens)}`);
    }
    if (this._reasoningTokens > 0) {
      parts.push(`Reason: ${this._formatNumber(this._reasoningTokens)}`);
    }

    if (parts.length === 0) {
      return "-";
    }
    return parts.join(" | ");
  }

  _formatNumber(num) {
    if (num >= 1000000) {
      const value = num / 1000000;
      return value === Math.trunc(value) ? `${Math.trunc(value)}M` : `${value.toFixed(1)}M`;
    }
    if (num >= 1000) {
      const value = num / 1000;
      return value === Math.trunc(value) ? `${Math.trunc(value)}k` : `${value.toFixed(1)}k`;
    }
    return num.toString();
  }

  _formatContextCompact() {
    if (this._contextWindowTokens <= 0) {
      return this._contextTokens > 0 ? this._formatNumber(this._contextTokens) : "-";
    }

    const usedPercentage = (this._contextTokens / this._contextWindowTokens) * 100;
    return `${usedPercentage.toFixed(1)}%/${this._formatNumber(this._contextWindowTokens)}`;
  }

  _escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // Public API
  setModel(model) {
    this._model = model;
    this.setAttribute("model", model);
  }

  getModel() {
    return this._model;
  }

  setTokens(input, output, cached = 0, reasoning = 0, context = 0, contextWindow = 0) {
    this._inputTokens = input;
    this._outputTokens = output;
    this._cachedTokens = cached;
    this._reasoningTokens = reasoning;
    this._contextTokens = context;
    this._contextWindowTokens = contextWindow;
    this.setAttribute("inputtokens", input.toString());
    this.setAttribute("outputtokens", output.toString());
    this.setAttribute("cachedtokens", cached.toString());
    this.setAttribute("reasoningtokens", reasoning.toString());
    this.setAttribute("contexttokens", context.toString());
    this.setAttribute("contextwindowtokens", contextWindow.toString());
  }

  getTokens() {
    return {
      input: this._inputTokens,
      output: this._outputTokens,
      cached: this._cachedTokens,
      reasoning: this._reasoningTokens,
      context: this._contextTokens,
      contextWindow: this._contextWindowTokens,
    };
  }

  setQueue(count) {
    this._queue = count;
    this.setAttribute("queue", count.toString());
  }

  getQueue() {
    return this._queue;
  }

  setStreaming(isStreaming) {
    this._streaming = isStreaming;
    this.setAttribute("streaming", isStreaming.toString());
  }

  isStreaming() {
    return this._streaming;
  }

  updateStatus(status) {
    if (status.model !== undefined) {
      this._model = status.model;
      this.setAttribute("model", status.model);
    }
    if (status.inputTokens !== undefined) {
      this._inputTokens = status.inputTokens;
      this.setAttribute("inputtokens", status.inputTokens.toString());
    }
    if (status.outputTokens !== undefined) {
      this._outputTokens = status.outputTokens;
      this.setAttribute("outputtokens", status.outputTokens.toString());
    }
    if (status.cacheReadTokens !== undefined) {
      this._cachedTokens = status.cacheReadTokens;
      this.setAttribute("cachedtokens", status.cacheReadTokens.toString());
    }
    if (status.reasoningTokens !== undefined) {
      this._reasoningTokens = status.reasoningTokens;
      this.setAttribute("reasoningtokens", status.reasoningTokens.toString());
    }
    if (status.contextTokens !== undefined) {
      this._contextTokens = status.contextTokens;
      this.setAttribute("contexttokens", status.contextTokens.toString());
    }
    if (status.contextWindowTokens !== undefined) {
      this._contextWindowTokens = status.contextWindowTokens;
      this.setAttribute("contextwindowtokens", status.contextWindowTokens.toString());
    }
    if (status.queueLength !== undefined) {
      this._queue = status.queueLength;
      this.setAttribute("queue", status.queueLength.toString());
    }
    if (status.isStreaming !== undefined) {
      this._streaming = status.isStreaming;
      this.setAttribute("streaming", status.isStreaming.toString());
    }
  }
}

// Register the custom element
// customElements.define('status-bar'
customElements.define("status-bar", StatusBar);
