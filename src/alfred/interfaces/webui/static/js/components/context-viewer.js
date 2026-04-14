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
    this._expandedSections = new Set(["support-state", "self-model", "token-breakdown"]);
    this._renderSerial = 0;
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
    // Dispatch event to parent to handle context modification.
    this.dispatchEvent(
      new CustomEvent("context-toggle", {
        bubbles: true,
        composed: true,
        detail: { section, enabled },
      }),
    );
  }

  _normalizeSectionId(section) {
    const normalized = String(section ?? "").trim();
    if (!normalized) {
      return "";
    }
    return normalized.replace(/\.md$/i, "").toLowerCase();
  }

  _formatSectionLabel(section) {
    const sectionId = this._normalizeSectionId(section);
    if (!sectionId) {
      return "";
    }
    return `${sectionId.toUpperCase()}.md`;
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

  _asInt(value, fallback = 0) {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  _getScrollContainer() {
    return this.querySelector(".context-viewer");
  }

  _captureScrollPosition() {
    const scrollContainer = this._getScrollContainer();
    if (!scrollContainer) {
      return null;
    }

    return {
      scrollLeft: scrollContainer.scrollLeft,
      scrollTop: scrollContainer.scrollTop,
    };
  }

  _restoreScrollPosition(scrollPosition, renderSerial) {
    if (!scrollPosition) {
      return;
    }

    window.requestAnimationFrame(() => {
      if (this._renderSerial !== renderSerial) {
        return;
      }

      const scrollContainer = this._getScrollContainer();
      if (!scrollContainer) {
        return;
      }

      scrollContainer.scrollLeft = scrollPosition.scrollLeft;
      scrollContainer.scrollTop = scrollPosition.scrollTop;
    });
  }

  _formatSystemPromptBadge(system, disabledSections) {
    const activeCount = system?.sections?.length || 0;
    const disabledCount = disabledSections?.length || 0;
    return `${activeCount} active / ${disabledCount} disabled`;
  }

  _formatSessionHistoryBadge(session) {
    const displayed = this._asInt(
      session?.displayed,
      this._asInt(session?.count, session?.messages?.length || 0),
    );
    const included = this._asInt(session?.included, displayed);
    const total = this._asInt(session?.total, included);

    if (displayed === included && included === total) {
      return `${displayed} messages`;
    }

    return `${displayed} displayed / ${included} included / ${total} total messages`;
  }

  _formatMemoryBadge(memories) {
    const displayed = this._asInt(memories?.displayed, memories?.items?.length || 0);
    const total = this._asInt(memories?.total, displayed);

    if (displayed === total) {
      return `${this._formatNumber(displayed)} ${displayed === 1 ? "memory" : "memories"}`;
    }

    return `${this._formatNumber(displayed)} displayed / ${this._formatNumber(total)} total memories`;
  }

  _formatToolCallsBadge(toolCalls) {
    const displayed = this._asInt(
      toolCalls?.displayed,
      this._asInt(toolCalls?.count, toolCalls?.items?.length || 0),
    );
    const total = this._asInt(toolCalls?.total, displayed);

    if (displayed === total) {
      return `${this._formatNumber(displayed)} ${displayed === 1 ? "outcome" : "outcomes"}`;
    }

    return `${this._formatNumber(displayed)} displayed / ${this._formatNumber(total)} total outcomes`;
  }

  _previewText(text, maxLength = 120) {
    const normalized = String(text ?? "")
      .replace(/\s+/g, " ")
      .trim();
    if (!normalized) {
      return "";
    }

    if (normalized.length <= maxLength) {
      return normalized;
    }

    return `${normalized.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
  }

  _renderMemoryItem(memory) {
    const preview = this._escapeHtml(
      this._previewText(memory?.preview || memory?.content || "", 140),
    );
    const content = this._escapeHtml(memory?.content || "");
    const role = this._escapeHtml(memory?.role || "unknown");
    const timestamp = this._escapeHtml(memory?.timestamp || "");

    return `
      <details class="memory-item" open>
        <summary class="memory-summary">
          <div class="memory-summary-main">
            <span class="memory-role">${role}</span>
            <span class="memory-date">${timestamp}</span>
          </div>
          <div class="memory-preview">${preview}</div>
        </summary>
        <div class="memory-body">
          <div class="memory-content">${content}</div>
        </div>
      </details>
    `;
  }

  _renderSessionMessage(message) {
    const preview = this._escapeHtml(this._previewText(message?.content || "", 140));
    const role = this._escapeHtml(message?.role || "unknown");
    const content = this._escapeHtml(message?.content || "");

    return `
      <details class="session-message ${this._escapeHtml(message?.role || "unknown")}" open>
        <summary class="session-message-summary">
          <div class="session-message-summary-main">
            <span class="message-role-badge">${role}</span>
          </div>
          <div class="message-preview">${preview}</div>
        </summary>
        <div class="session-message-body">
          <div class="message-content">${content}</div>
        </div>
      </details>
    `;
  }

  _renderToolCallItem(toolCall) {
    const status = String(toolCall?.status || "success").toLowerCase();
    const summary = this._escapeHtml(
      toolCall?.summary || `${toolCall?.tool_name || "tool"} activity`,
    );
    const toolName = this._escapeHtml(toolCall?.tool_name || "tool");
    const argumentsValue = toolCall?.arguments || {};
    const hasArguments = Boolean(argumentsValue && Object.keys(argumentsValue).length > 0);
    const argumentJson = hasArguments
      ? this._escapeHtml(JSON.stringify(argumentsValue, null, 2))
      : "";
    const output = this._escapeHtml(toolCall?.output || "");

    return `
      <details class="tool-call-item ${status}" open>
        <summary class="tool-call-summary">
          <div class="tool-call-summary-main">
            <span class="tool-name">${toolName}</span>
            <span class="tool-status">${this._escapeHtml(status)}</span>
          </div>
          <div class="tool-summary">${summary}</div>
        </summary>
        <div class="tool-call-body">
          ${
            hasArguments
              ? `
          <div class="tool-call-detail">
            <div class="tool-call-detail-title">Arguments</div>
            <div class="tool-arguments">${argumentJson}</div>
          </div>
        `
              : ""
          }
          ${
            output
              ? `
          <div class="tool-call-detail">
            <div class="tool-call-detail-title">Output</div>
            <div class="tool-output">${output}</div>
          </div>
        `
              : ""
          }
        </div>
      </details>
    `;
  }

  _render() {
    if (!this._data) {
      this.innerHTML = '<div class="context-viewer loading">Loading context...</div>';
      return;
    }

    const {
      system_prompt,
      support_state,
      memories,
      session_history,
      tool_calls,
      self_model,
      total_tokens,
      warnings,
      blocked_context_files,
      conflicted_context_files,
    } = this._data;
    const scrollPosition = this._captureScrollPosition();
    const renderSerial = ++this._renderSerial;

    this.innerHTML = `
      <div class="context-viewer">
        ${this._renderHeader()}
        ${conflicted_context_files?.length ? this._renderConflictedFiles(conflicted_context_files) : ""}
        ${warnings?.length ? this._renderWarnings(warnings) : ""}
        ${!conflicted_context_files?.length && blocked_context_files?.length ? this._renderBlockedFiles(blocked_context_files) : ""}
        
        <div class="context-sections">
          ${this._renderSupportState(support_state)}
          ${this._renderSelfModel(self_model)}
          ${this._renderTokenBreakdown(total_tokens, system_prompt, memories, session_history, tool_calls)}
          ${this._renderSystemPrompt(system_prompt)}
          ${this._renderMemories(memories)}
          ${this._renderSessionHistory(session_history)}
          ${this._renderToolCalls(tool_calls)}
        </div>
      </div>
    `;

    this._restoreScrollPosition(scrollPosition, renderSerial);
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

  _renderConflictedFiles(files) {
    const count = files?.length || 0;
    const noun = count === 1 ? "file" : "files";
    return `
      <div class="context-conflicted-files">
        <div class="conflicted-header">
          <span class="conflicted-title">Conflicted Managed Templates</span>
          <span class="section-badge">${count} ${noun}</span>
        </div>
        ${files
          .map(
            (file) => `
          <div class="conflicted-file">
            <div class="conflicted-file-name">${this._escapeHtml(file.label || file.name || file.id || "Unknown")}</div>
            <div class="conflicted-file-reason">${this._escapeHtml(file.reason || "Blocked context file")}</div>
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

  _formatSupportStateBadge(supportState) {
    if (!supportState) {
      return "unavailable";
    }

    if (!supportState.enabled) {
      return "unavailable";
    }

    const activeArcId = supportState.summary?.active_arc_id;
    if (activeArcId) {
      return activeArcId;
    }

    return `${supportState.summary?.response_mode || "unknown"} mode`;
  }

  _renderSupportPatternItem(pattern) {
    const claim = this._escapeHtml(pattern?.claim || "Unnamed pattern");
    const kind = this._escapeHtml(pattern?.kind || "unknown");
    const status = this._escapeHtml(pattern?.status || "unknown");
    const scopeLabel = this._escapeHtml(pattern?.scope?.label || "unknown");
    const confidence = Number.parseFloat(pattern?.confidence || 0).toFixed(2);

    return `
      <div class="info-row">
        <span class="info-value">${claim}</span>
        <span class="info-label">${kind} · ${status} · ${scopeLabel} · ${confidence}</span>
      </div>
    `;
  }

  _renderSupportEventItem(event) {
    const label = `${event?.registry || "unknown"}:${event?.dimension || "unknown"} → ${event?.new_value || ""}`;
    const meta = `${event?.scope?.label || "unknown"} · ${event?.status || "unknown"}`;
    return `
      <div class="info-row">
        <span class="info-value">${this._escapeHtml(label)}</span>
        <span class="info-label">${this._escapeHtml(meta)}</span>
      </div>
    `;
  }

  _formatValueLedgerSummary(summary) {
    const total = this._asInt(summary?.total, 0);
    const counts = summary?.counts_by_status || {};
    const parts = Object.entries(counts)
      .filter(([, count]) => this._asInt(count, 0) > 0)
      .map(([status, count]) => `${status}: ${this._formatNumber(this._asInt(count, 0))}`);

    if (!parts.length) {
      return `${this._formatNumber(total)} total`;
    }

    return `${this._formatNumber(total)} total · ${parts.join(" · ")}`;
  }

  _renderSupportValueLedgerEntryItem(entry) {
    const registry = this._escapeHtml(entry?.registry || "unknown");
    const dimension = this._escapeHtml(entry?.dimension || "unknown");
    const scopeLabel = this._escapeHtml(entry?.scope?.label || "unknown");
    const value = this._escapeHtml(entry?.value || "");
    const status = this._escapeHtml(entry?.status || "unknown");
    const confidence = Number.parseFloat(entry?.confidence || 0).toFixed(2);
    const evidenceCount = this._formatNumber(this._asInt(entry?.evidence_count, 0));
    const contradictionCount = this._formatNumber(this._asInt(entry?.contradiction_count, 0));
    const why = this._escapeHtml(entry?.why || "");

    const label = `${registry}:${dimension} = ${value}`;
    const meta = `${scopeLabel} · ${status} · conf ${confidence} · ev ${evidenceCount} · contra ${contradictionCount}`;

    return `
      <div class="support-ledger-entry info-row">
        <span class="info-value">${this._escapeHtml(label)}</span>
        <span class="info-label">${this._escapeHtml(meta)}${why ? ` · ${why}` : ""}</span>
      </div>
    `;
  }

  _renderSupportLedgerUpdateEventItem(event) {
    const entityType = this._escapeHtml(event?.entity_type || "unknown");
    const registry = this._escapeHtml(event?.registry || "unknown");
    const dimension = this._escapeHtml(event?.dimension_or_kind || "unknown");
    const scopeLabel = this._escapeHtml(event?.scope?.label || "unknown");
    const newStatus = this._escapeHtml(event?.new_status || "unknown");
    const newValue = this._escapeHtml(event?.new_value || "");
    const confidence = Number.parseFloat(event?.confidence || 0).toFixed(2);

    const label = `${entityType} ${registry}:${dimension} → ${newValue || newStatus}`;
    const meta = `${scopeLabel} · ${newStatus} · conf ${confidence}`;

    return `
      <div class="support-ledger-event info-row">
        <span class="info-value">${this._escapeHtml(label)}</span>
        <span class="info-label">${this._escapeHtml(meta)}</span>
      </div>
    `;
  }

  _renderSupportArcItem(arc) {
    const title = this._escapeHtml(arc?.title || arc?.arc_id || "Unknown arc");
    const meta = `${arc?.kind || "unknown"} · ${arc?.status || "unknown"}`;
    return `
      <div class="info-row">
        <span class="info-value">${title}</span>
        <span class="info-label">${this._escapeHtml(meta)}</span>
      </div>
    `;
  }

  _renderSupportDomainItem(domain) {
    const name = this._escapeHtml(domain?.name || domain?.domain_id || "Unknown domain");
    const status = this._escapeHtml(domain?.status || "unknown");
    return `
      <div class="info-row">
        <span class="info-value">${name}</span>
        <span class="info-label">${status}</span>
      </div>
    `;
  }

  _renderSupportState(supportState) {
    if (!supportState) return "";
    const isExpanded = this._expandedSections.has("support-state");
    const summary = supportState.summary || {};
    const runtimeState = supportState.active_runtime_state || {};
    const learnedState = supportState.learned_state || {};
    const activePatterns = runtimeState.active_patterns || [];
    const candidatePatterns = learnedState.candidate_patterns || [];
    const confirmedPatterns = learnedState.confirmed_patterns || [];
    const recentEvents = learnedState.recent_update_events || [];
    const valueLedgerEntries = learnedState.value_ledger_entries || [];
    const valueLedgerSummary = learnedState.value_ledger_summary || {};
    const recentLedgerEvents = learnedState.recent_ledger_update_events || [];
    const activeArcs = supportState.active_arcs || [];
    const activeDomains = supportState.active_domains || [];
    const effectiveSupportValues = Object.entries(runtimeState.effective_support_values || {});
    const effectiveRelationalValues = Object.entries(
      runtimeState.effective_relational_values || {},
    );

    return `
      <div class="context-section">
        <div class="context-section-header" data-section="support-state">
          <span class="section-toggle">${isExpanded ? "−" : "+"}</span>
          <span class="section-title">Support State</span>
          <span class="section-badge">${this._escapeHtml(this._formatSupportStateBadge(supportState))}</span>
        </div>
        ${
          isExpanded
            ? `
          <div class="context-section-content">
            ${
              supportState.enabled
                ? `
              <div class="self-model-grid">
                <div class="self-model-card">
                  <div class="card-title">Runtime</div>
                  <div class="card-content">
                    <div class="info-row">
                      <span class="info-label">Mode:</span>
                      <span class="info-value">${this._escapeHtml(summary.response_mode || "unknown")}</span>
                    </div>
                    <div class="info-row">
                      <span class="info-label">Active Arc:</span>
                      <span class="info-value">${this._escapeHtml(summary.active_arc_id || "None")}</span>
                    </div>
                    <div class="info-row">
                      <span class="info-label">Patterns:</span>
                      <span class="info-value">${this._formatNumber(summary.active_pattern_count || 0)} active</span>
                    </div>
                  </div>
                </div>

                <div class="self-model-card">
                  <div class="card-title">Learned State</div>
                  <div class="card-content">
                    <div class="info-row">
                      <span class="info-label">Candidate:</span>
                      <span class="info-value">${this._formatNumber(summary.candidate_pattern_count || 0)}</span>
                    </div>
                    <div class="info-row">
                      <span class="info-label">Confirmed:</span>
                      <span class="info-value">${this._formatNumber(summary.confirmed_pattern_count || 0)}</span>
                    </div>
                    <div class="info-row">
                      <span class="info-label">Recent Changes:</span>
                      <span class="info-value">${this._formatNumber(summary.recent_update_event_count || 0)}</span>
                    </div>
                  </div>
                </div>

                <div class="self-model-card">
                  <div class="card-title">Coverage</div>
                  <div class="card-content">
                    <div class="info-row">
                      <span class="info-label">Recent Interventions:</span>
                      <span class="info-value">${this._formatNumber(summary.recent_intervention_count || 0)}</span>
                    </div>
                    <div class="info-row">
                      <span class="info-label">Active Domains:</span>
                      <span class="info-value">${this._formatNumber(summary.active_domain_count || 0)}</span>
                    </div>
                    <div class="info-row">
                      <span class="info-label">Active Arcs:</span>
                      <span class="info-value">${this._formatNumber(summary.active_arc_count || 0)}</span>
                    </div>
                  </div>
                </div>
              </div>

              ${
                effectiveSupportValues.length
                  ? `
                <div class="self-model-card">
                  <div class="card-title">Effective Support Values</div>
                  <div class="card-content">
                    ${effectiveSupportValues
                      .map(
                        ([dimension, value]) => `
                      <div class="info-row">
                        <span class="info-label">${this._escapeHtml(dimension)}:</span>
                        <span class="info-value">${this._escapeHtml(value)}</span>
                      </div>
                    `,
                      )
                      .join("")}
                  </div>
                </div>
              `
                  : ""
              }

              ${
                effectiveRelationalValues.length
                  ? `
                <div class="self-model-card">
                  <div class="card-title">Effective Relational Values</div>
                  <div class="card-content">
                    ${effectiveRelationalValues
                      .map(
                        ([dimension, value]) => `
                      <div class="info-row">
                        <span class="info-label">${this._escapeHtml(dimension)}:</span>
                        <span class="info-value">${this._escapeHtml(value)}</span>
                      </div>
                    `,
                      )
                      .join("")}
                  </div>
                </div>
              `
                  : ""
              }

              ${
                activePatterns.length
                  ? `
                <div class="self-model-card">
                  <div class="card-title">Active Runtime Patterns</div>
                  <div class="card-content">
                    ${activePatterns.map((pattern) => this._renderSupportPatternItem(pattern)).join("")}
                  </div>
                </div>
              `
                  : ""
              }

              ${
                candidatePatterns.length
                  ? `
                <div class="self-model-card">
                  <div class="card-title">Candidate Patterns</div>
                  <div class="card-content">
                    ${candidatePatterns.map((pattern) => this._renderSupportPatternItem(pattern)).join("")}
                  </div>
                </div>
              `
                  : ""
              }

              ${
                confirmedPatterns.length
                  ? `
                <div class="self-model-card">
                  <div class="card-title">Confirmed Patterns</div>
                  <div class="card-content">
                    ${confirmedPatterns.map((pattern) => this._renderSupportPatternItem(pattern)).join("")}
                  </div>
                </div>
              `
                  : ""
              }

              ${
                recentEvents.length
                  ? `
                <div class="self-model-card">
                  <div class="card-title">Recent Changes</div>
                  <div class="card-content">
                    ${recentEvents.map((event) => this._renderSupportEventItem(event)).join("")}
                  </div>
                </div>
              `
                  : ""
              }

              ${
                valueLedgerEntries.length
                  ? `
                <div class="self-model-card">
                  <div class="card-title">Value Ledger</div>
                  <div class="card-content">
                    <div class="info-row">
                      <span class="info-label">Summary:</span>
                      <span class="info-value">${this._escapeHtml(this._formatValueLedgerSummary(valueLedgerSummary))}</span>
                    </div>
                    ${valueLedgerEntries
                      .map((entry) => this._renderSupportValueLedgerEntryItem(entry))
                      .join("")}
                  </div>
                </div>
              `
                  : ""
              }

              ${
                recentLedgerEvents.length
                  ? `
                <div class="self-model-card">
                  <div class="card-title">Ledger Updates</div>
                  <div class="card-content">
                    ${recentLedgerEvents
                      .map((event) => this._renderSupportLedgerUpdateEventItem(event))
                      .join("")}
                  </div>
                </div>
              `
                  : ""
              }

              ${
                activeArcs.length
                  ? `
                <div class="self-model-card">
                  <div class="card-title">Active Arcs</div>
                  <div class="card-content">
                    ${activeArcs.map((arc) => this._renderSupportArcItem(arc)).join("")}
                  </div>
                </div>
              `
                  : ""
              }

              ${
                activeDomains.length
                  ? `
                <div class="self-model-card">
                  <div class="card-title">Active Domains</div>
                  <div class="card-content">
                    ${activeDomains.map((domain) => this._renderSupportDomainItem(domain)).join("")}
                  </div>
                </div>
              `
                  : ""
              }
            `
                : `
              <div class="empty-state">${this._escapeHtml(supportState.error || "Support inspection is not available in this runtime.")}</div>
            `
            }
          </div>
        `
            : ""
        }
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
    const memoryTokens = memories?.tokens || memories?.displayed_tokens || 0;
    const sessionTokens = session?.included_tokens ?? session?.tokens ?? 0;
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
    if (!system?.sections?.length && !this._data?.disabled_sections?.length) return "";
    const isExpanded = this._expandedSections.has("system-prompt");
    const disabledSections = this._data?.disabled_sections || [];

    return `
      <div class="context-section">
        <div class="context-section-header" data-section="system-prompt">
          <span class="section-toggle">${isExpanded ? "−" : "+"}</span>
          <span class="section-title">System Prompt Sections</span>
          <span class="section-badge">${this._formatSystemPromptBadge(system, disabledSections)}</span>
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
                    <input type="checkbox" class="context-toggle" data-section="${this._normalizeSectionId(s.id || s.name || s.label || "")}" checked>
                    <span class="toggle-slider"></span>
                  </label>
                  <span class="section-name">${this._escapeHtml(s.label || this._formatSectionLabel(s.id || s.name || s.label || ""))}</span>
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
                    <input type="checkbox" class="context-toggle" data-section="${this._normalizeSectionId(name)}">
                    <span class="toggle-slider"></span>
                  </label>
                  <span class="section-name">${this._escapeHtml(this._formatSectionLabel(name))}</span>
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
          <span class="section-badge">${this._formatMemoryBadge(memories)}</span>
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
                  ? memories.items.map((m) => this._renderMemoryItem(m)).join("")
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
          <span class="section-badge">${this._formatSessionHistoryBadge(session)}</span>
        </div>
        ${
          isExpanded
            ? `
          <div class="context-section-content">
            <div class="session-messages">
              ${session.messages.map((m) => this._renderSessionMessage(m)).join("")}
            </div>
          </div>
        `
            : ""
        }
      </div>
    `;
  }

  _renderToolCalls(tool_calls) {
    if (!tool_calls?.count && !tool_calls?.items?.length) return "";
    const isExpanded = this._expandedSections.has("tool-calls");
    const badgeText = this._formatToolCallsBadge(tool_calls);

    return `
      <div class="context-section">
        <div class="context-section-header" data-section="tool-calls">
          <span class="section-toggle">${isExpanded ? "−" : "+"}</span>
          <span class="section-title">Tool Activity</span>
          <span class="section-badge">${badgeText}</span>
        </div>
        ${
          isExpanded
            ? `
          <div class="context-section-content">
            <div class="tool-calls-list">
              ${tool_calls.items?.map((tc) => this._renderToolCallItem(tc)).join("") || '<div class="empty-state">No tool activity recorded</div>'}
            </div>
          </div>
        `
            : ""
        }
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
