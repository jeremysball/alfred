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
        ${this._expanded ? `
          <div class="tool-details">
            ${this._renderArguments()}
            ${this._output ? this._renderOutput() : ''}
          </div>
        ` : ''}
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
        const tags = this._arguments.tags || '';
        const contentStr = content.length > 30 ? content.substring(0, 30) + '...' : content;
        if (tags) {
          return `${contentStr} (${tags})`;
        }
        return contentStr;
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

  _renderOutput() {
    const output = this._output || '';
    
    switch (this._toolName) {
      case 'remember':
        // Output is just a status indicator - content+tags shown in args
        return '<div class="tool-status tool-status-success">Saved</div>';
      case 'search_memories':
        return this._renderCodeOutput(output, 'search', 'Found');
      case 'forget':
        return this._renderCardOutput(output, 'forget', 'Removed', 'error');
      case 'update_memory':
        return this._renderCardOutput(output, 'update', 'Updated', 'warning');
      case 'read':
        return this._renderCodeOutput(output, 'read', 'Content');
      case 'write':
        return this._renderCardOutput(output, 'write', 'Saved', 'success');
      case 'edit':
        return this._renderCardOutput(output, 'edit', 'Modified', 'warning');
      case 'bash':
        return this._renderCodeOutput(output, 'bash', 'Result');
      default:
        return this._renderCodeOutput(output, 'default', 'Output');
    }
  }

  _renderCardOutput(output, toolType, title, variant) {
    return `
      <div class="tool-output tool-output-${toolType} tool-output-${variant}">
        <div class="tool-output-body">${this._escapeHtml(output)}</div>
      </div>
    `;
  }

  _renderCodeOutput(output, toolType, title) {
    return `
      <div class="tool-output tool-output-${toolType}">
        <pre class="tool-output-code"><code>${this._escapeHtml(output)}</code></pre>
      </div>
    `;
  }

  _renderReadArgs() {
    const path = this._arguments.path || '';
    return `<div class="tool-read-path">${this._escapeHtml(path)}</div>`;
  }

  _renderWriteArgs() {
    const content = this._arguments.content || '';
    return `<pre class="tool-write-content"><code>${this._escapeHtml(content.length > 500 ? content.substring(0, 500) + '\n...' : content)}</code></pre>`;
  }

  _renderEditArgs() {
    const oldText = this._arguments.old_text || '';
    const newText = this._arguments.new_text || '';

    return `
      <div class="tool-edit-simple">
        <div class="tool-edit-removed">${this._escapeHtml(oldText.length > 200 ? oldText.substring(0, 200) + '...' : oldText)}</div>
        <div class="tool-edit-added">${this._escapeHtml(newText.length > 200 ? newText.substring(0, 200) + '...' : newText)}</div>
      </div>
    `;
  }

  _renderBashArgs() {
    const command = this._arguments.command || '';
    return `<pre class="tool-bash-command"><code>${this._escapeHtml(command)}</code></pre>`;
  }

  _renderRememberArgs() {
    const content = this._arguments.content || '';

    // Just show the content directly - no labels, no boxes
    return `<div class="tool-remember-content">${this._escapeHtml(content)}</div>`;
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
