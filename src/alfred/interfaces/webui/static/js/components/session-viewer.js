/**
 * Session Viewer Web Component
 *
 * Usage: <session-viewer data-session='{"sessionId":"..."}'></session-viewer>
 *
 * Mirrors the context viewer surface so session details feel native to the same
 * sheet/card language as /context.
 */
class SessionViewer extends HTMLElement {
  constructor() {
    super();
    this._data = null;
    this._expandedSections = new Set(["overview", "summary"]);
  }

  static get observedAttributes() {
    return ["data-session"];
  }

  attributeChangedCallback(name, _oldValue, newValue) {
    if (name === "data-session" && newValue) {
      try {
        this._data = JSON.parse(newValue);
        this._render();
      } catch (error) {
        console.error("Failed to parse session data:", error);
      }
    }
  }

  connectedCallback() {
    this._render();
    this._setupEventListeners();
  }

  _setupEventListeners() {
    this.addEventListener("click", (event) => {
      const header = event.target.closest(".context-section-header");
      if (header) {
        const section = header.dataset.section;
        if (section) {
          this._toggleSection(section);
        }
      }

      if (event.target.closest(".session-refresh-btn")) {
        this.dispatchEvent(
          new CustomEvent("session-refresh", {
            bubbles: true,
            composed: true,
          }),
        );
      }
    });
  }

  _toggleSection(section) {
    if (this._expandedSections.has(section)) {
      this._expandedSections.delete(section);
    } else {
      this._expandedSections.add(section);
    }
    this._render();
  }

  _formatFullDate(isoString) {
    if (!isoString) return "Unknown";
    return new Date(isoString).toLocaleString();
  }

  _formatRelativeTime(isoString) {
    if (!isoString) return "Unknown";

    const date = new Date(isoString);
    const diffMs = Date.now() - date.getTime();
    const diffSecs = Math.max(0, Math.floor(diffMs / 1000));
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  _render() {
    if (!this._data) {
      this.innerHTML = '<div class="context-viewer loading">Loading session...</div>';
      return;
    }

    const { sessionId, status, messageCount, created, lastActive, summary } = this._data;
    const summaryCreatedAt = summary?.createdAt || null;
    const summaryDeltaMessages = summary?.deltaMessages ?? 0;
    const summaryMessageCount = summary?.messageCount ?? 0;
    const summaryVersion = summary?.version ?? null;
    const summaryText = summary?.text || "";
    const hasSummary = Boolean(summary && (summaryText || summaryCreatedAt));

    this.innerHTML = `
      <div class="context-viewer session-viewer">
        ${this._renderHeader(status)}
        <div class="context-sections">
          ${this._renderOverviewSection(sessionId, messageCount, created, lastActive)}
          ${this._renderSummarySection(
            hasSummary,
            summaryText,
            summaryCreatedAt,
            summaryDeltaMessages,
            summaryMessageCount,
            summaryVersion,
          )}
        </div>
      </div>
    `;
  }

  _renderHeader(status) {
    return `
      <div class="context-header">
        <h2 class="context-title">
          <span class="context-icon">◉</span>
          Current Session
        </h2>
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <span class="section-badge">${this._escapeHtml(status || "unknown")}</span>
          <button class="context-refresh-btn session-refresh-btn" title="Refresh session">
            ↻
          </button>
        </div>
      </div>
    `;
  }

  _renderOverviewSection(sessionId, messageCount, created, lastActive) {
    const isExpanded = this._expandedSections.has("overview");

    return `
      <div class="context-section">
        <div class="context-section-header" data-section="overview">
          <span class="section-toggle">${isExpanded ? "−" : "+"}</span>
          <span class="section-title">Session Overview</span>
          <span class="section-badge">${messageCount || 0} messages</span>
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
                    <span class="info-label">Session ID:</span>
                    <span class="info-value session-id">${this._escapeHtml(sessionId || "Unknown")}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">Messages:</span>
                    <span class="info-value">${messageCount || 0}</span>
                  </div>
                </div>
              </div>

              <div class="self-model-card">
                <div class="card-title">Timeline</div>
                <div class="card-content">
                  <div class="info-row">
                    <span class="info-label">Created:</span>
                    <span class="info-value" title="${this._escapeHtml(this._formatFullDate(created))}">${this._escapeHtml(this._formatRelativeTime(created))}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">Last Active:</span>
                    <span class="info-value" title="${this._escapeHtml(this._formatFullDate(lastActive))}">${this._escapeHtml(this._formatRelativeTime(lastActive))}</span>
                  </div>
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

  _renderSummarySection(
    hasSummary,
    summaryText,
    summaryCreatedAt,
    summaryDeltaMessages,
    summaryMessageCount,
    summaryVersion,
  ) {
    const isExpanded = this._expandedSections.has("summary");

    return `
      <div class="context-section">
        <div class="context-section-header" data-section="summary">
          <span class="section-toggle">${isExpanded ? "−" : "+"}</span>
          <span class="section-title">Latest Summary</span>
          <span class="section-badge">${hasSummary ? `${summaryDeltaMessages} new messages` : "None"}</span>
        </div>
        ${
          isExpanded
            ? `
          <div class="context-section-content">
            ${
              hasSummary
                ? `
              <div class="self-model-grid">
                <div class="self-model-card">
                  <div class="card-title">Summary Metadata</div>
                  <div class="card-content">
                    <div class="info-row">
                      <span class="info-label">Last Summary:</span>
                      <span class="info-value" title="${this._escapeHtml(this._formatFullDate(summaryCreatedAt))}">${this._escapeHtml(this._formatRelativeTime(summaryCreatedAt))}</span>
                    </div>
                    <div class="info-row">
                      <span class="info-label">Age:</span>
                      <span class="info-value">${this._escapeHtml(this._formatRelativeTime(summaryCreatedAt))}</span>
                    </div>
                    <div class="info-row">
                      <span class="info-label">Delta:</span>
                      <span class="info-value">${summaryDeltaMessages} message${summaryDeltaMessages === 1 ? "" : "s"}</span>
                    </div>
                    <div class="info-row">
                      <span class="info-label">Summary Messages:</span>
                      <span class="info-value">${summaryMessageCount}</span>
                    </div>
                    <div class="info-row">
                      <span class="info-label">Version:</span>
                      <span class="info-value">${summaryVersion ?? 1}</span>
                    </div>
                  </div>
                </div>

                <div class="self-model-card">
                  <div class="card-title">Summary Text</div>
                  <div class="card-content">
                    <div style="white-space: pre-wrap; word-break: break-word; color: var(--text-primary, #fff);">
                      ${this._escapeHtml(summaryText || "")}
                    </div>
                  </div>
                </div>
              </div>
            `
                : `
              <div class="self-model-card">
                <div class="card-title">Summary</div>
                <div class="card-content">
                  <div class="info-row">
                    <span class="info-label">Last Summary:</span>
                    <span class="info-value">Not available yet</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">Age:</span>
                    <span class="info-value">—</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">Delta:</span>
                    <span class="info-value">0 messages</span>
                  </div>
                </div>
              </div>
            `
            }
          </div>
        `
            : ""
        }
      </div>
    `;
  }

  _escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text ?? "";
    return div.innerHTML;
  }
}

customElements.define("session-viewer", SessionViewer);
