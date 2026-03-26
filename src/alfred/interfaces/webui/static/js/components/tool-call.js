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
    // Toggle when clicking anywhere on the tool call (but not the content area)
    if (!e.target.closest('.tool-content')) {
      this.toggle();
    }
  };

  _getStatusIcon() {
    switch (this._status) {
      case 'running':
        return '>';
      case 'success':
        return 'ok';
      case 'error':
        return 'err';
      default:
        return '>';
    }
  }

  _render() {
    const statusClass = this._status.toLowerCase();
    const expandedClass = this._expanded ? 'expanded' : 'collapsed';
    const statusIcon = this._getStatusIcon();

    // Build arguments summary for the button
    const argsSummary = this._buildArgsSummary();

    this.innerHTML = `
      <div class="tool-call ${statusClass} ${expandedClass}">
        <button class="tool-button" type="button" aria-expanded="${this._expanded}">
          <span class="tool-status-icon">${statusIcon}</span>
          <span class="tool-name">${this._escapeHtml(this._toolName)}</span>
          ${argsSummary ? `<span class="tool-args">${this._escapeHtml(argsSummary)}</span>` : ''}
          <span class="tool-toggle">${this._expanded ? '-' : '+'}</span>
        </button>
        <div class="tool-content" style="display: ${this._expanded ? 'block' : 'none'}">
          <div class="tool-arguments">
            ${this._renderArguments()}
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

  _buildArgsSummary() {
    const argKeys = Object.keys(this._arguments);
    if (argKeys.length === 0) return '';

    // Special handling for common tools
    switch (this._toolName) {
      case 'read':
        return this._arguments.path || '';
      case 'write':
        return this._arguments.path || '';
      case 'edit':
        return this._arguments.path || '';
      case 'bash':
        const cmd = this._arguments.command || '';
        return cmd.length > 30 ? cmd.substring(0, 30) + '...' : cmd;
      case 'remember':
        const content = this._arguments.content || '';
        return content.length > 30 ? content.substring(0, 30) + '...' : content;
      case 'search_memories':
        return this._arguments.query || '';
      default:
        // Generic: first key=value
        const firstKey = argKeys[0];
        const firstValue = this._arguments[firstKey];
        const valueStr = typeof firstValue === 'string'
          ? (firstValue.length > 20 ? firstValue.substring(0, 20) + '...' : firstValue)
          : JSON.stringify(firstValue).substring(0, 20);
        return `${firstKey}=${valueStr}${argKeys.length > 1 ? ` +${argKeys.length - 1}` : ''}`;
    }
  }

  _renderArguments() {
    switch (this._toolName) {
      case 'read':
        return this._renderReadArgs();
      case 'write':
        return this._renderWriteArgs();
      case 'edit':
        return this._renderEditArgs();
      case 'bash':
        return this._renderBashArgs();
      case 'remember':
        return this._renderRememberArgs();
      case 'search_memories':
        return this._renderSearchMemoriesArgs();
      case 'forget':
        return this._renderForgetArgs();
      case 'update_memory':
        return this._renderUpdateMemoryArgs();
      default:
        // Fallback to JSON for unknown tools
        return `<strong>Arguments:</strong><pre><code>${this._escapeHtml(JSON.stringify(this._arguments, null, 2))}</code></pre>`;
    }
  }

  _renderReadArgs() {
    const path = this._arguments.path || '';
    const limit = this._arguments.limit;
    const offset = this._arguments.offset;

    let html = '<div class="tool-args-ui">';
    html += `<div class="tool-arg-row"><span class="tool-arg-label">Path:</span><span class="tool-arg-value tool-path">${this._escapeHtml(path)}</span></div>`;
    if (limit !== undefined) {
      html += `<div class="tool-arg-row"><span class="tool-arg-label">Limit:</span><span class="tool-arg-value">${limit}</span></div>`;
    }
    if (offset !== undefined) {
      html += `<div class="tool-arg-row"><span class="tool-arg-label">Offset:</span><span class="tool-arg-value">${offset}</span></div>`;
    }
    html += '</div>';
    return html;
  }

  _renderWriteArgs() {
    const path = this._arguments.path || '';
    const content = this._arguments.content || '';

    let html = '<div class="tool-args-ui">';
    html += `<div class="tool-arg-row"><span class="tool-arg-label">Path:</span><span class="tool-arg-value tool-path">${this._escapeHtml(path)}</span></div>`;
    html += `<div class="tool-arg-row"><span class="tool-arg-label">Content:</span></div>`;
    html += `<pre class="tool-content-preview"><code>${this._escapeHtml(content.length > 500 ? content.substring(0, 500) + '\n...' : content)}</code></pre>`;
    html += '</div>';
    return html;
  }

  _renderEditArgs() {
    const path = this._arguments.path || '';
    const oldText = this._arguments.old_text || '';
    const newText = this._arguments.new_text || '';

    let html = '<div class="tool-args-ui">';
    html += `<div class="tool-arg-row"><span class="tool-arg-label">Path:</span><span class="tool-arg-value tool-path">${this._escapeHtml(path)}</span></div>`;
    html += `<div class="tool-arg-row"><span class="tool-arg-label">Replace:</span></div>`;
    html += `<div class="tool-edit-diff">`;
    html += `<div class="tool-edit-old"><span class="tool-edit-label">Old:</span><pre><code>${this._escapeHtml(oldText.length > 200 ? oldText.substring(0, 200) + '...' : oldText)}</code></pre></div>`;
    html += `<div class="tool-edit-arrow">→</div>`;
    html += `<div class="tool-edit-new"><span class="tool-edit-label">New:</span><pre><code>${this._escapeHtml(newText.length > 200 ? newText.substring(0, 200) + '...' : newText)}</code></pre></div>`;
    html += `</div>`;
    html += '</div>';
    return html;
  }

  _renderBashArgs() {
    const command = this._arguments.command || '';
    const timeout = this._arguments.timeout;
    const workingDir = this._arguments.workingDir;

    let html = '<div class="tool-args-ui">';
    html += `<div class="tool-arg-row"><span class="tool-arg-label">Command:</span></div>`;
    html += `<pre class="tool-bash-command"><code>${this._escapeHtml(command)}</code></pre>`;
    if (workingDir) {
      html += `<div class="tool-arg-row"><span class="tool-arg-label">Working Dir:</span><span class="tool-arg-value tool-path">${this._escapeHtml(workingDir)}</span></div>`;
    }
    if (timeout !== undefined) {
      html += `<div class="tool-arg-row"><span class="tool-arg-label">Timeout:</span><span class="tool-arg-value">${timeout}s</span></div>`;
    }
    html += '</div>';
    return html;
  }

  _renderRememberArgs() {
    const content = this._arguments.content || '';
    const permanent = this._arguments.permanent;

    let html = '<div class="tool-args-ui">';
    html += `<div class="tool-arg-row"><span class="tool-arg-label">Content:</span></div>`;
    html += `<div class="tool-fact-box">${this._escapeHtml(content)}</div>`;
    if (permanent) {
      html += `<div class="tool-arg-row"><span class="tool-arg-value tool-badge tool-badge-permanent">Permanent</span></div>`;
    }
    html += '</div>';
    return html;
  }

  _renderSearchMemoriesArgs() {
    const query = this._arguments.query || '';
    const limit = this._arguments.limit;

    let html = '<div class="tool-args-ui">';
    html += `<div class="tool-arg-row"><span class="tool-arg-label">Query:</span><span class="tool-arg-value tool-query">"${this._escapeHtml(query)}"</span></div>`;
    if (limit !== undefined) {
      html += `<div class="tool-arg-row"><span class="tool-arg-label">Limit:</span><span class="tool-arg-value">${limit}</span></div>`;
    }
    html += '</div>';
    return html;
  }

  _renderForgetArgs() {
    const memoryId = this._arguments.memoryId || '';

    let html = '<div class="tool-args-ui">';
    html += `<div class="tool-arg-row"><span class="tool-arg-label">Memory ID:</span><span class="tool-arg-value tool-id">${this._escapeHtml(memoryId)}</span></div>`;
    html += '</div>';
    return html;
  }

  _renderUpdateMemoryArgs() {
    const memoryId = this._arguments.memoryId || '';
    const newContent = this._arguments.newContent || '';

    let html = '<div class="tool-args-ui">';
    html += `<div class="tool-arg-row"><span class="tool-arg-label">Memory ID:</span><span class="tool-arg-value tool-id">${this._escapeHtml(memoryId)}</span></div>`;
    html += `<div class="tool-arg-row"><span class="tool-arg-label">New Content:</span></div>`;
    html += `<div class="tool-fact-box">${this._escapeHtml(newContent)}</div>`;
    html += '</div>';
    return html;
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
