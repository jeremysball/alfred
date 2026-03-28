/**
 * Context Viewer Web Component - Interactive context inspection and control
 *
 * Usage: <context-viewer></context-viewer>
 *
 * Provides detailed, interactive view of Alfred's context including:
 * - Self-model (identity, capabilities, runtime state)
 * - System prompt sections with toggle controls
 * - Memories with filtering
 * - Session history
 * - Tool call history
 * - Token usage breakdown
 */

class ContextViewer extends HTMLElement {
  constructor() {
    super();
    this._data = null;
    this._expandedSections = new Set(["self-model", "token-breakdown"]);
  }

  static get observedAttributes() {
    return ["data-context"];
  }

  attributeChangedCallback(name, _oldValue, newValue) {
    if (name === "data-context" && newValue) {
      try {
        this._data = JSON.parse(newValue);
        this._render();
      } catch (e) {
        console.error("Failed to parse context data:", e);
      }
    }
  }

  connectedCallback() {
    this._render();
    this._setupEventListeners();
  }

  _setupEventListeners() {
    this.addEventListener("click", (e) => {
      // Section toggle
      const header = e.target.closest(".context-section-header");
      if (header) {
        const section = header.dataset.section;
        this._toggleSection(section);
      }

      // Toggle switch for context sections
      const toggle = e.target.closest(".context-toggle");
      if (toggle) {
        const section = toggle.dataset.section;
        const enabled = toggle.checked;
        this._toggleContextSection(section, enabled);
      }

      // Refresh button
      if (e.target.closest(".context-refresh-btn")) {
        this._refreshContext();
      }

      // Memory filter
      if (e.target.closest(".memory-filter-input")) {
        e.stopPropagation();
      }
    });

    // Memory filter input
    const filterInput = this.querySelector(".memory-filter-input");
    if (filterInput) {
      filterInput.addEventListener("input", (e) => {
        this._filterMemories(e.target.value);
      });
    }
  }

  _toggleSection(section) {
    if (this._expandedSections.has(section)) {
      this._expandedSections.delete(section);
    } else {
      this._expandedSections.add(section);
    }
    this._render();
  }

  _toggleContextSection(section, enabled) {
    // Dispatch event to parent to handle context modification
    this.dispatchEvent(
      new CustomEvent("context-toggle", {
        bubbles: true,
        composed: true,
        detail: { section, enabled },
      }),
    );

    // Also dispatch command event for direct server communication
    this.dispatchEvent(
      new CustomEvent("send-command", {
        bubbles: true,
        composed: true,
        detail: { command: `/context toggle ${section} ${enabled ? "on" : "off"}` },
      }),
    );
  }

  _refreshContext() {
    this.dispatchEvent(
      new CustomEvent("context-refresh", {
        bubbles: true,
        composed: true,
      }),
    );
  }

  _filterMemories(query) {
    const items = this.querySelectorAll(".memory-item");
    const lowerQuery = query.toLowerCase();
    items.forEach((item) => {
      const text = item.textContent.toLowerCase();
      item.style.display = text.includes(lowerQuery) ? "" : "none";
    });
  }

  _formatNumber(num) {
    return num?.toLocaleString() || "0";
  }

  _render() {
    if (!this._data) {
      this.innerHTML = '<div class="context-viewer loading">Loading context...</div>';
      return;
    }

    const {
      system_prompt,
      memories,
      session_history,
      tool_calls,
      self_model,
      total_tokens,
      warnings,
      blocked_context_files,
    } = this._data;

    this.innerHTML = `
      <div class="context-viewer">
        ${this._renderHeader()}
        ${warnings?.length ? this._renderWarnings(warnings) : ""}
        ${blocked_context_files?.length ? this._renderBlockedFiles(blocked_context_files) : ""}
        
        <div class="context-sections">
          ${this._renderSelfModel(self_model)}
          ${this._renderTokenBreakdown(total_tokens, system_prompt, memories, session_history, tool_calls)}
          ${this._renderSystemPrompt(system_prompt)}
          ${this._renderMemories(memories)}
          ${this._renderSessionHistory(session_history)}
          ${this._renderToolCalls(tool_calls)}
        </div>
      </div>
    `;
  }

  _renderHeader() {
    return `
      <div class="context-header">
        <h2 class="context-title">
          <span class="context-icon">◉</span>
          System Context
        </h2>
        <button class="context-refresh-btn" title="Refresh context">
          ↻
        </button>
      </div>
    `;
  }

  _renderWarnings(warnings) {
    return `
      <div class="context-warnings">
        ${warnings
          .map(
            (w) => `
          <div class="context-warning">
            <span class="warning-icon">⚠</span>
            ${this._escapeHtml(w)}
          </div>
        `,
          )
          .join("")}
      </div>
    `;
  }

  _renderBlockedFiles(files) {
    return `
      <div class="context-blocked-files">
        <div class="blocked-header">Blocked Context Files:</div>
        ${files
          .map(
            (f) => `
          <span class="blocked-file">${this._escapeHtml(f)}</span>
        `,
          )
          .join("")}
      </div>
    `;
  }

  _renderSelfModel(model) {
    if (!model) return "";
    const isExpanded = this._expandedSections.has("self-model");

    return `
      <div class="context-section">
        <div class="context-section-header" data-section="self-model">
          <span class="section-toggle">${isExpanded ? "−" : "+"}</span>
          <span class="section-title">${model.identity?.name || "Alfred"} - Self Model</span>
          <span class="section-badge">${model.runtime?.interface || "unknown"}</span>
        </div>
        ${
          isExpanded
            ? `
          <div class="context-section-content">
            <div class="self-model-grid">
              <div class="self-model-card">
                <div class="card-title">Identity</div>
                <div class="card-content">
                  <div class="info-row">
                    <span class="info-label">Name:</span>
                    <span class="info-value">${this._escapeHtml(model.identity?.name || "Unknown")}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">Role:</span>
                    <span class="info-value">${this._escapeHtml(model.identity?.role || "Unknown")}</span>
                  </div>
                </div>
              </div>
              
              <div class="self-model-card">
                <div class="card-title">Runtime</div>
                <div class="card-content">
                  <div class="info-row">
                    <span class="info-label">Interface:</span>
                    <span class="info-value">${model.runtime?.interface || "unknown"}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">Session:</span>
                    <span class="info-value session-id">${this._escapeHtml(model.runtime?.session_id?.slice(0, 8) || "N/A")}...</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">Daemon Mode:</span>
                    <span class="info-value">${model.runtime?.daemon_mode ? "Yes" : "No"}</span>
                  </div>
                </div>
              </div>
              
              <div class="self-model-card">
                <div class="card-title">Capabilities</div>
                <div class="card-content">
                  <div class="info-row">
                    <span class="info-label">Memory:</span>
                    <span class="info-value">${model.capabilities?.memory_enabled ? "✓ Enabled" : "✗ Disabled"}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">Search:</span>
                    <span class="info-value">${model.capabilities?.search_enabled ? "✓ Enabled" : "✗ Disabled"}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">Tools:</span>
                    <span class="info-value">${model.capabilities?.tools_count || 0} available</span>
                  </div>
                </div>
              </div>
              
              <div class="self-model-card ${this._getPressureClass(model.context_pressure?.approximate_tokens)}">
                <div class="card-title">Context Pressure</div>
                <div class="card-content">
                  <div class="info-row">
                    <span class="info-label">Messages:</span>
                    <span class="info-value">${model.context_pressure?.message_count || 0}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">Memories:</span>
                    <span class="info-value">${model.context_pressure?.memory_count || 0}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">Est. Tokens:</span>
                    <span class="info-value">${this._formatNumber(model.context_pressure?.approximate_tokens)}</span>
                  </div>
                </div>
              </div>
            </div>
            
            ${
              model.capabilities?.tools?.length
                ? `
              <div class="tools-list">
                <div class="tools-title">Available Tools:</div>
                <div class="tools-grid">
                  ${model.capabilities.tools
                    .map(
                      (t) => `
                    <span class="tool-badge">${this._escapeHtml(t)}</span>
                  `,
                    )
                    .join("")}
                </div>
              </div>
            `
                : ""
            }
          </div>
        `
            : ""
        }
      </div>
    `;
  }

  _getPressureClass(tokens) {
    if (!tokens) return "";
    if (tokens > 100000) return "pressure-high";
    if (tokens > 50000) return "pressure-medium";
    return "pressure-low";
  }

  _renderTokenBreakdown(total, system, memories, session, tool_calls) {
    const isExpanded = this._expandedSections.has("token-breakdown");
    const systemTokens = system?.total_tokens || 0;
    const memoryTokens = memories?.tokens || 0;
    const sessionTokens = session?.tokens || 0;
    const toolTokens = tool_calls?.tokens || 0;

    return `
      <div class="context-section">
        <div class="context-section-header" data-section="token-breakdown">
          <span class="section-toggle">${isExpanded ? "−" : "+"}</span>
          <span class="section-title">Token Usage Breakdown</span>
          <span class="section-badge">${this._formatNumber(total)} total</span>
        </div>
        ${
          isExpanded
            ? `
          <div class="context-section-content">
            <div class="token-breakdown">
              <div class="token-bar">
                <div class="token-segment system" style="width: ${(systemTokens / total) * 100 || 0}%"></div>
                <div class="token-segment memories" style="width: ${(memoryTokens / total) * 100 || 0}%"></div>
                <div class="token-segment session" style="width: ${(sessionTokens / total) * 100 || 0}%"></div>
                <div class="token-segment tools" style="width: ${(toolTokens / total) * 100 || 0}%"></div>
              </div>
              <div class="token-legend">
                <div class="legend-item">
                  <span class="legend-color system"></span>
                  <span class="legend-label">System Prompt</span>
                  <span class="legend-value">${this._formatNumber(systemTokens)}</span>
                </div>
                <div class="legend-item">
                  <span class="legend-color memories"></span>
                  <span class="legend-label">Memories</span>
                  <span class="legend-value">${this._formatNumber(memoryTokens)}</span>
                </div>
                <div class="legend-item">
                  <span class="legend-color session"></span>
                  <span class="legend-label">Session History</span>
                  <span class="legend-value">${this._formatNumber(sessionTokens)}</span>
                </div>
                <div class="legend-item">
                  <span class="legend-color tools"></span>
                  <span class="legend-label">Tool Calls</span>
                  <span class="legend-value">${this._formatNumber(toolTokens)}</span>
                </div>
              </div>
            </div>
          </div>
        `
            : ""
        }
      </div>
    `;
  }

  _renderSystemPrompt(system) {
    if (!system?.sections?.length && !this._data?.disabledSections?.length) return "";
    const isExpanded = this._expandedSections.has("system-prompt");
    const disabledSections = this._data?.disabledSections || [];

    return `
      <div class="context-section">
        <div class="context-section-header" data-section="system-prompt">
          <span class="section-toggle">${isExpanded ? "−" : "+"}</span>
          <span class="section-title">System Prompt Sections</span>
          <span class="section-badge">${system?.sections?.length || 0} active</span>
        </div>
        ${
          isExpanded
            ? `
          <div class="context-section-content">
            <div class="system-sections-list">
              ${
                system?.sections
                  ?.map(
                    (s) => `
                <div class="system-section-item enabled">
                  <label class="section-toggle-label">
                    <input type="checkbox" class="context-toggle" data-section="${s.name}" checked>
                    <span class="toggle-slider"></span>
                  </label>
                  <span class="section-name">${this._escapeHtml(s.name)}</span>
                  <span class="section-tokens">${this._formatNumber(s.tokens)} tokens</span>
                </div>
              `,
                  )
                  .join("") || '<div class="empty-state">No active context sections</div>'
              }
              ${disabledSections
                .map(
                  (name) => `
                <div class="system-section-item disabled">
                  <label class="section-toggle-label">
                    <input type="checkbox" class="context-toggle" data-section="${name}">
                    <span class="toggle-slider"></span>
                  </label>
                  <span class="section-name">${this._escapeHtml(name)}</span>
                  <span class="section-status">(disabled)</span>
                </div>
              `,
                )
                .join("")}
            </div>
          </div>
        `
            : ""
        }
      </div>
    `;
  }

  _renderMemories(memories) {
    if (!memories) return "";
    const isExpanded = this._expandedSections.has("memories");

    return `
      <div class="context-section">
        <div class="context-section-header" data-section="memories">
          <span class="section-toggle">${isExpanded ? "−" : "+"}</span>
          <span class="section-title">Memories</span>
          <span class="section-badge">${memories.displayed || 0} / ${memories.total || 0}</span>
        </div>
        ${
          isExpanded
            ? `
          <div class="context-section-content">
            <div class="memories-filter">
              <input type="text" class="memory-filter-input" placeholder="Filter memories...">
            </div>
            <div class="memories-list">
              ${
                memories.items?.length
                  ? memories.items
                      .map(
                        (m) => `
                <div class="memory-item">
                  <div class="memory-content">${this._escapeHtml(m.content)}</div>
                  <div class="memory-meta">
                    <span class="memory-role">${m.role}</span>
                    <span class="memory-date">${m.timestamp}</span>
                  </div>
                </div>
              `,
                      )
                      .join("")
                  : '<div class="empty-state">No memories loaded</div>'
              }
            </div>
          </div>
        `
            : ""
        }
      </div>
    `;
  }

  _renderSessionHistory(session) {
    if (!session?.messages?.length) return "";
    const isExpanded = this._expandedSections.has("session-history");

    return `
      <div class="context-section">
        <div class="context-section-header" data-section="session-history">
          <span class="section-toggle">${isExpanded ? "−" : "+"}</span>
          <span class="section-title">Session History</span>
          <span class="section-badge">${session.count || 0} messages</span>
        </div>
        ${
          isExpanded
            ? `
          <div class="context-section-content">
            <div class="session-messages">
              ${session.messages
                .map(
                  (m) => `
                <div class="session-message ${m.role}">
                  <span class="message-role-badge">${m.role}</span>
                  <span class="message-content">${this._escapeHtml(m.content)}</span>
                </div>
              `,
                )
                .join("")}
            </div>
          </div>
        `
            : ""
        }
      </div>
    `;
  }

  _renderToolCalls(tool_calls) {
    if (!tool_calls?.count) return "";
    const isExpanded = this._expandedSections.has("tool-calls");

    return `
      <div class="context-section">
        <div class="context-section-header" data-section="tool-calls">
          <span class="section-toggle">${isExpanded ? "−" : "+"}</span>
          <span class="section-title">Recent Tool Calls</span>
          <span class="section-badge">${tool_calls.count} calls</span>
        </div>
        ${
          isExpanded
            ? `
          <div class="context-section-content">
            <div class="tool-calls-list">
              ${tool_calls.items
                ?.map(
                  (tc) => `
                <div class="tool-call-item ${tc.status}">
                  <div class="tool-call-header">
                    <span class="tool-name">${this._escapeHtml(tc.tool_name)}</span>
                    <span class="tool-status">${tc.status}</span>
                  </div>
                  <div class="tool-arguments">
                    ${this._renderArguments(tc.arguments)}
                  </div>
                  <div class="tool-output">${this._escapeHtml(tc.output)}</div>
                </div>
              `,
                )
                .join("")}
            </div>
          </div>
        `
            : ""
        }
      </div>
    `;
  }

  _renderArguments(args) {
    if (!args || typeof args !== "object") return "";
    const entries = Object.entries(args);
    if (!entries.length) return "";

    return `
      <div class="args-list">
        ${entries
          .map(
            ([k, v]) => `
          <span class="arg-item">
            <span class="arg-key">${k}:</span>
            <span class="arg-value">${this._escapeHtml(String(v).slice(0, 50))}</span>
          </span>
        `,
          )
          .join("")}
      </div>
    `;
  }

  _escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}

// Register the custom element
customElements.define("context-viewer", ContextViewer);
