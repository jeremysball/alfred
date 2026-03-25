/**
 * Tool Call Web Component - Button-only style
 *
 * Usage:
 * <tool-call
 *   tool-call-id="call_abc123"
 *   tool-name="read_file"
 *   arguments='{"path": "/tmp/file.txt"}'
 *   output="File contents..."
 *   status="running|success|error"
 *   expanded="false">
 * </tool-call>
 *
 * Attributes:
 *   - tool-call-id: Unique tool call ID
 *   - tool-name: Name of the tool being executed
 *   - arguments: JSON string of tool arguments
 *   - output: Tool output (accumulated for streaming)
 *   - status: 'running' | 'success' | 'error'
 *   - expanded: 'true' | 'false' (whether content is visible)
 */
class ToolCall extends HTMLElement {
  constructor() {
    super();
    this._toolCallId = '';
    this._toolName = '';
    this._arguments = {};
    this._output = '';
    this._status = 'running';
    this._expanded = false;
  }

  static get observedAttributes() {
    return ['tool-call-id', 'tool-name', 'arguments', 'output', 'status', 'expanded'];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue === newValue) return;

    switch (name) {
      case 'tool-call-id':
        this._toolCallId = newValue || '';
        break;
      case 'tool-name':
        this._toolName = newValue || '';
        break;
      case 'arguments':
        try {
          this._arguments = JSON.parse(newValue || '{}');
        } catch {
          this._arguments = {};
        }
        break;
      case 'output':
        this._output = newValue || '';
        break;
      case 'status':
        this._status = newValue || 'running';
        break;
      case 'expanded':
        this._expanded = newValue === 'true';
        break;
    }
    this._render();
  }

  connectedCallback() {
    this._render();
    this.addEventListener('click', this._handleClick);
  }

  disconnectedCallback() {
    this.removeEventListener('click', this._handleClick);
  }

  _handleClick = (e) => {
    // Only toggle if clicking the button header
    if (e.target.closest('.tool-button')) {
      this.toggle();
    }
  };

  _getStatusIcon() {
    switch (this._status) {
      case 'running':
        return '▶';
      case 'success':
        return '✓';
      case 'error':
        return '✗';
      default:
        return '▶';
    }
  }

  _render() {
    const statusClass = this._status.toLowerCase();
    const expandedClass = this._expanded ? 'expanded' : 'collapsed';
    const statusIcon = this._getStatusIcon();

    // Build arguments summary (first key=value pair, or count)
    let argsSummary = '';
    const argKeys = Object.keys(this._arguments);
    if (argKeys.length > 0) {
      const firstKey = argKeys[0];
      const firstValue = this._arguments[firstKey];
      const valueStr = typeof firstValue === 'string' 
        ? (firstValue.length > 20 ? firstValue.substring(0, 20) + '...' : firstValue)
        : JSON.stringify(firstValue).substring(0, 20);
      argsSummary = `${firstKey}=${valueStr}`;
      if (argKeys.length > 1) {
        argsSummary += ` +${argKeys.length - 1}`;
      }
    }

    this.innerHTML = `
      <div class="tool-call ${statusClass} ${expandedClass}">
        <button class="tool-button" type="button" aria-expanded="${this._expanded}">
          <span class="tool-status-icon">${statusIcon}</span>
          <span class="tool-name">${this._escapeHtml(this._toolName)}</span>
          ${argsSummary ? `<span class="tool-args">${this._escapeHtml(argsSummary)}</span>` : ''}
          <span class="tool-toggle">${this._expanded ? '▼' : '▶'}</span>
        </button>
        <div class="tool-content" style="display: ${this._expanded ? 'block' : 'none'}">
          <div class="tool-arguments">
            <strong>Arguments:</strong>
            <pre><code>${this._escapeHtml(JSON.stringify(this._arguments, null, 2))}</code></pre>
          </div>
          ${this._output ? `
            <div class="tool-output">
              <strong>Output:</strong>
              <pre><code>${this._escapeHtml(this._output)}</code></pre>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Public API
  toggle() {
    this._expanded = !this._expanded;
    this.setAttribute('expanded', this._expanded.toString());
  }

  expand() {
    this._expanded = true;
    this.setAttribute('expanded', 'true');
  }

  collapse() {
    this._expanded = false;
    this.setAttribute('expanded', 'false');
  }

  appendOutput(chunk) {
    this._output += chunk;
    this.setAttribute('output', this._output);
  }

  setStatus(status) {
    this._status = status;
    this.setAttribute('status', status);
  }

  // Getters
  getToolCallId() {
    return this._toolCallId;
  }

  getToolName() {
    return this._toolName;
  }

  getStatus() {
    return this._status;
  }

  isExpanded() {
    return this._expanded;
  }
}

// Register the custom element
customElements.define('tool-call', ToolCall);
