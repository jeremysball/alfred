// Alfred Web UI - Main JavaScript

/**
 * Initialize the Alfred Web UI
 */
function initAlfredUI() {
  console.log('Initializing Alfred Web UI...');

  // DOM Elements
  const messageList = document.getElementById('message-list');
  const messageInput = document.getElementById('message-input');
  const sendButton = document.getElementById('send-button');
  const connectionPill = document.getElementById('connection-pill');
  const chatContainer = document.getElementById('chat-container');
  const queueBadge = document.getElementById('queue-badge');
  const streamingDot = document.getElementById('streaming-dot');
  const completionMenu = document.getElementById('completion-menu');

  // WebSocket Client
  const wsClient = new AlfredWebSocketClient();
  let currentAssistantMessage = null;
  const activeToolCalls = new Map();
  let allToolsExpanded = false;

  // Message Queue
  const messageQueue = [];

  // Message History
  const messageHistory = [];
  let historyIndex = -1;

  // Available Commands
  const commands = [
    { value: '/new', description: 'Start new session' },
    { value: '/resume', description: 'Resume a session' },
    { value: '/sessions', description: 'List recent sessions' },
    { value: '/session', description: 'Show current session info' },
    { value: '/context', description: 'Show system context' },
    { value: '/help', description: 'Show available commands' }
  ];

  // Connection Status Handler
  function updateConnectionStatus(status) {
    connectionPill.className = `connection-pill ${status}`;
  }

  wsClient.addEventListener('connected', () => {
    updateConnectionStatus('connected');
  });

  wsClient.addEventListener('disconnected', () => {
    updateConnectionStatus('disconnected');
  });

  wsClient.addEventListener('error', () => {
    updateConnectionStatus('disconnected');
  });

  // Streaming Indicator
  function showStreaming() {
    streamingDot?.classList.remove('hidden');
  }

  function hideStreaming() {
    streamingDot?.classList.add('hidden');
  }

  // Message Handler
  wsClient.addEventListener('message', (event) => {
    const msg = event.detail;

    switch (msg.type) {
      case 'chat.started':
        showStreaming();
        currentAssistantMessage = document.createElement('chat-message');
        currentAssistantMessage.setAttribute('role', 'assistant');
        currentAssistantMessage.setAttribute('content', '');
        currentAssistantMessage.setAttribute('timestamp', new Date().toISOString());
        messageList.appendChild(currentAssistantMessage);
        scrollToBottom();
        break;

      case 'reasoning.chunk':
        if (currentAssistantMessage && msg.payload && msg.payload.content) {
          currentAssistantMessage.appendReasoning(msg.payload.content);
          scrollToBottom();
        }
        break;

      case 'chat.chunk':
        if (currentAssistantMessage && msg.payload && msg.payload.content) {
          currentAssistantMessage.appendContent(msg.payload.content);
          scrollToBottom();
        }
        break;

      case 'chat.complete':
        hideStreaming();
        currentAssistantMessage = null;
        enableInput();
        // Add copy buttons to any new code blocks
        addCopyButtons();
        // Send next queued message if any
        processQueue();
        break;

      case 'chat.error':
        hideStreaming();
        hideThinking();
        showError(msg.payload?.error || 'An error occurred');
        currentAssistantMessage = null;
        enableInput();
        break;

      case 'session.new':
        handleSessionNew(msg.payload);
        break;

      case 'session.loaded':
        handleSessionLoaded(msg.payload);
        break;

      case 'session.list':
        handleSessionList(msg.payload);
        break;

      case 'session.info':
        handleSessionInfo(msg.payload);
        break;

      case 'context.info':
        handleContextInfo(msg.payload);
        break;

      case 'tool.start':
        handleToolStart(msg.payload);
        break;

      case 'tool.output':
        handleToolOutput(msg.payload);
        break;

      case 'tool.end':
        handleToolEnd(msg.payload);
        break;

      case 'completion.suggestions':
        showCompletionMenu(msg.payload?.suggestions || []);
        break;

      case 'status.update':
        updateStatusBar(msg.payload);
        break;

      case 'toast':
        showToast(msg.payload?.message, msg.payload?.level);
        break;

      default:
        console.log('Unhandled message type:', msg.type);
    }
  });

  // Session Handlers
  function handleSessionNew(payload) {
    // Clear message list for new session
    messageList.innerHTML = '';
    showSystemMessage(`New session created: ${payload.sessionId}`);
    enableInput();
  }

  function handleSessionLoaded(payload) {
    // Clear current messages
    messageList.innerHTML = '';

    // Load session messages
    if (payload.messages && payload.messages.length > 0) {
      payload.messages.forEach(msg => {
        const messageEl = document.createElement('chat-message');
        messageEl.setAttribute('role', msg.role);
        messageEl.setAttribute('content', msg.content);
        messageEl.setAttribute('timestamp', new Date().toISOString());
        // Set reasoning content if present (for assistant messages)
        if (msg.reasoningContent && msg.reasoningContent.trim()) {
          messageEl.setReasoning(msg.reasoningContent);
        }
        messageList.appendChild(messageEl);
      });
      scrollToBottom();
      // Add copy buttons to code blocks in loaded messages
      addCopyButtons();
    }

    showSystemMessage(`Session resumed: ${payload.sessionId}`);
    enableInput();
  }

  function handleSessionList(payload) {
    const sessions = payload.sessions || [];

    if (sessions.length === 0) {
      showSystemMessage('No recent sessions found.');
      return;
    }

    let content = 'Recent sessions:\n\n';
    sessions.forEach(session => {
      const created = session.created ? new Date(session.created).toLocaleString() : 'Unknown';
      content += `ID: ${session.id}\n`;
      content += `  Created: ${created}\n`;
      content += `  Messages: ${session.messageCount}\n`;
      if (session.summary) {
        content += `  Summary: ${session.summary}\n`;
      }
      content += '\n';
    });

    showSystemMessage(content);
    enableInput();
  }

  function handleSessionInfo(payload) {
    let content = 'Current Session:\n\n';
    content += `ID: ${payload.sessionId}\n`;
    content += `Messages: ${payload.messageCount}\n`;
    if (payload.created) {
      content += `Created: ${new Date(payload.created).toLocaleString()}\n`;
    }

    showSystemMessage(content);
    enableInput();
  }

  function handleContextInfo(payload) {
    let content = 'System Context:\n\n';
    content += `Working Directory: ${payload.cwd || 'Unknown'}\n\n`;

    if (payload.files && payload.files.length > 0) {
      content += 'Files in context:\n';
      payload.files.forEach(file => {
        content += `  - ${file}\n`;
      });
      content += '\n';
    }

    if (payload.systemInfo) {
      content += 'System Info:\n';
      Object.entries(payload.systemInfo).forEach(([key, value]) => {
        content += `  ${key}: ${value}\n`;
      });
    }

    showSystemMessage(content);
    enableInput();
  }

  function showSystemMessage(content) {
    const systemMsg = document.createElement('chat-message');
    systemMsg.setAttribute('role', 'system');
    systemMsg.setAttribute('content', content);
    messageList.appendChild(systemMsg);
    scrollToBottom();
  }

  // Tool Call Handlers
  function handleToolStart(payload) {
    if (!currentAssistantMessage) return;

    const toolCall = document.createElement('tool-call');
    toolCall.setAttribute('tool-call-id', payload.toolCallId);
    toolCall.setAttribute('tool-name', payload.toolName);
    toolCall.setAttribute('arguments', JSON.stringify(payload.arguments || {}));
    toolCall.setAttribute('status', 'running');
    toolCall.setAttribute('expanded', 'false');

    activeToolCalls.set(payload.toolCallId, toolCall);
    currentAssistantMessage.appendChild(toolCall);
    scrollToBottom();
  }

  function handleToolOutput(payload) {
    const toolCall = activeToolCalls.get(payload.toolCallId);
    if (toolCall) {
      toolCall.appendOutput(payload.chunk);
      scrollToBottom();
    }
  }

  function handleToolEnd(payload) {
    const toolCall = activeToolCalls.get(payload.toolCallId);
    if (toolCall) {
      toolCall.setStatus(payload.success ? 'success' : 'error');
      if (payload.output) {
        toolCall.setAttribute('output', payload.output);
      }
    }
  }

  // Queue Management
  function addToQueue(content) {
    messageQueue.push(content);
    updateQueueBadge();
    showToast(`Message queued (${messageQueue.length})`, 'info');
  }

  function processQueue() {
    if (messageQueue.length > 0 && !currentAssistantMessage) {
      const content = messageQueue.shift();
      updateQueueBadge();
      sendMessageContent(content);
    }
  }

  function updateQueueBadge() {
    queueBadge.textContent = messageQueue.length;
    if (messageQueue.length === 0) {
      queueBadge.classList.add('hidden');
    } else {
      queueBadge.classList.remove('hidden');
    }
  }

  function clearQueue() {
    messageQueue.length = 0;
    updateQueueBadge();
    showToast('Queue cleared', 'info');
  }

  // Message History
  function addToHistory(content) {
    messageHistory.push(content);
    historyIndex = messageHistory.length;
  }

  function navigateHistory(direction) {
    if (messageHistory.length === 0) return;

    if (direction === 'up') {
      historyIndex = Math.max(0, historyIndex - 1);
    } else {
      historyIndex = Math.min(messageHistory.length, historyIndex + 1);
    }

    if (historyIndex < messageHistory.length) {
      messageInput.value = messageHistory[historyIndex];
    } else {
      messageInput.value = '';
    }

    autoResizeTextarea();
  }

  // Send Message
  function sendMessage() {
    const content = messageInput.value.trim();
    if (!content) return;

    sendMessageContent(content);
    messageInput.value = '';
    autoResizeTextarea();
  }

  function sendMessageContent(content) {
    // Add to history
    addToHistory(content);

    // Send via WebSocket - commands use command.execute, chat uses chat.send
    if (content.startsWith('/')) {
      // Commands: show as system message, don't disable input
      const cmdMsg = document.createElement('chat-message');
      cmdMsg.setAttribute('role', 'system');
      cmdMsg.setAttribute('content', `Command: ${content}`);
      cmdMsg.setAttribute('timestamp', new Date().toISOString());
      messageList.appendChild(cmdMsg);
      scrollToBottom();

      wsClient.sendCommand(content);
      // Don't disable input - commands are instant
    } else {
      // Chat messages: show as user message, disable input during streaming
      const userMessage = document.createElement('chat-message');
      userMessage.setAttribute('role', 'user');
      userMessage.setAttribute('content', content);
      userMessage.setAttribute('timestamp', new Date().toISOString());
      messageList.appendChild(userMessage);

      disableInput();
      scrollToBottom();

      wsClient.sendChat(content);
    }
  }

  // Textarea Auto-Resize
  function autoResizeTextarea() {
    messageInput.style.height = 'auto';
    const newHeight = Math.min(messageInput.scrollHeight, 200);
    messageInput.style.height = `${newHeight}px`;
  }

  // Command Completion
  function showCompletionMenu(items) {
    if (items.length === 0) {
      completionMenu.hide();
      return;
    }
    completionMenu.setItems(items);
    completionMenu.show();
  }

  function checkForCompletionTrigger() {
    const value = messageInput.value;
    const cursorPosition = messageInput.selectionStart;

    // Get text before cursor
    const textBeforeCursor = value.substring(0, cursorPosition);
    const lines = textBeforeCursor.split('\n');
    const currentLine = lines[lines.length - 1];

    // Check if we're at the start of a command
    if (currentLine.startsWith('/')) {
      const filter = currentLine.substring(1);
      const filtered = commands.filter(cmd =>
        cmd.value.toLowerCase().includes(filter.toLowerCase()) ||
        (cmd.description && cmd.description.toLowerCase().includes(filter.toLowerCase()))
      );
      showCompletionMenu(filtered);
    } else {
      completionMenu.hide();
    }
  }

  // Global Tool Toggle (Ctrl+T)
  function toggleAllTools() {
    allToolsExpanded = !allToolsExpanded;
    const toolCalls = document.querySelectorAll('tool-call');
    toolCalls.forEach(tool => {
      if (allToolsExpanded) {
        tool.expand();
      } else {
        tool.collapse();
      }
    });
  }

  // UI Helpers
  function disableInput() {
    messageInput.disabled = true;
    sendButton.disabled = true;
  }

  function enableInput() {
    messageInput.disabled = false;
    sendButton.disabled = false;
    messageInput.focus();
  }

  function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  function showError(message) {
    const errorMsg = document.createElement('chat-message');
    errorMsg.setAttribute('role', 'system');
    errorMsg.setAttribute('content', `Error: ${message}`);
    messageList.appendChild(errorMsg);
    scrollToBottom();
  }

  // Toast notification
  function showToast(message, level = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (toastContainer && toastContainer.show) {
      toastContainer.show(message, level, 5000);
    } else {
      console.log(`[${level?.toUpperCase() || 'INFO'}] ${message}`);
    }
  }

  // Status Bar Update
  function updateStatusBar(payload) {
    const statusBar = document.getElementById('status-bar');
    if (!statusBar) return;

    // Update model
    if (payload.model !== undefined) {
      statusBar.setAttribute('model', payload.model);
    }

    // Update tokens
    if (payload.inputTokens !== undefined || payload.outputTokens !== undefined) {
      statusBar.setAttribute('inputtokens', payload.inputTokens || 0);
      statusBar.setAttribute('outputtokens', payload.outputTokens || 0);
      if (payload.cacheReadTokens !== undefined) {
        statusBar.setAttribute('cachedtokens', payload.cacheReadTokens);
      }
      if (payload.reasoningTokens !== undefined) {
        statusBar.setAttribute('reasoningtokens', payload.reasoningTokens);
      }
      if (payload.contextTokens !== undefined) {
        statusBar.setAttribute('contexttokens', payload.contextTokens);
      }
    }

    // Update queue
    if (payload.queueLength !== undefined) {
      statusBar.setAttribute('queue', payload.queueLength);
    }

    // Update streaming status
    if (payload.isStreaming !== undefined) {
      statusBar.setAttribute('streaming', payload.isStreaming);
    }
  }

  // Event Listeners
  sendButton.addEventListener('click', sendMessage);

  // History navigation buttons (mobile)
  const historyUpBtn = document.getElementById('history-up');
  const historyDownBtn = document.getElementById('history-down');
  historyUpBtn?.addEventListener('click', () => navigateHistory('up'));
  historyDownBtn?.addEventListener('click', () => navigateHistory('down'));

  // Textarea input handling
  messageInput.addEventListener('input', () => {
    autoResizeTextarea();
    checkForCompletionTrigger();
  });

  // Keyboard handling
  messageInput.addEventListener('keydown', (e) => {
    // Shift+Enter: Queue message
    if (e.key === 'Enter' && e.shiftKey) {
      e.preventDefault();
      const content = messageInput.value.trim();
      if (content) {
        addToQueue(content);
        messageInput.value = '';
        autoResizeTextarea();
      }
      return;
    }

    // Enter (without Shift): Send message
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
      return;
    }

    // Handle completion menu navigation
    if (completionMenu.isVisible()) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        completionMenu.selectNext();
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        completionMenu.selectPrevious();
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        completionMenu.selectCurrent();
        return;
      }
      if (e.key === 'Escape') {
        completionMenu.hide();
        return;
      }
    }

    // History navigation (only if completion not visible)
    if (!completionMenu.isVisible()) {
      if (e.key === 'ArrowUp' && messageInput.selectionStart === 0) {
        e.preventDefault();
        navigateHistory('up');
        return;
      }
      if (e.key === 'ArrowDown' && messageInput.selectionStart === messageInput.value.length) {
        e.preventDefault();
        navigateHistory('down');
        return;
      }
    }

    // Ctrl+U: Clear input
    if (e.ctrlKey && e.key === 'u') {
      e.preventDefault();
      messageInput.value = '';
      autoResizeTextarea();
      return;
    }
  });

  // Global keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Ctrl+T: Toggle all tool calls
    if (e.ctrlKey && e.key === 't') {
      e.preventDefault();
      toggleAllTools();
      return;
    }

    // Escape: Clear queue
    if (e.key === 'Escape' && messageQueue.length > 0) {
      clearQueue();
    }
  });

  // Completion menu selection
  completionMenu.addEventListener('select', (e) => {
    const selected = e.detail;
    const value = messageInput.value;
    const cursorPosition = messageInput.selectionStart;

    // Replace current command with selected one
    const textBeforeCursor = value.substring(0, cursorPosition);
    const lines = textBeforeCursor.split('\n');
    const currentLineIndex = lines.length - 1;
    const currentLine = lines[currentLineIndex];

    if (currentLine.startsWith('/')) {
      lines[currentLineIndex] = selected.value + ' ';
      const newTextBefore = lines.join('\n');
      const newValue = newTextBefore + value.substring(cursorPosition);

      messageInput.value = newValue;
      const newCursorPos = newTextBefore.length;
      messageInput.setSelectionRange(newCursorPos, newCursorPos);
      messageInput.focus();
    }

    completionMenu.hide();
  });

  // Auto-scroll on window resize
  window.addEventListener('resize', scrollToBottom);

  // Connect WebSocket
  wsClient.connect();

  // Focus input on load
  messageInput.focus();

  console.log('Alfred Web UI initialized');
}

// Add copy buttons to code blocks
function addCopyButtons() {
  const codeBlocks = document.querySelectorAll('pre code');
  codeBlocks.forEach((codeBlock) => {
    // Skip if already wrapped
    if (codeBlock.closest('.code-block-wrapper')) return;

    const pre = codeBlock.parentElement;
    const wrapper = document.createElement('div');
    wrapper.className = 'code-block-wrapper';

    // Create copy button
    const copyBtn = document.createElement('button');
    copyBtn.className = 'code-copy-btn';
    copyBtn.innerHTML = 'Copy';
    copyBtn.title = 'Copy to clipboard';

    copyBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(codeBlock.textContent);
        copyBtn.innerHTML = 'Copied!';
        copyBtn.classList.add('copied');
        setTimeout(() => {
          copyBtn.innerHTML = 'Copy';
          copyBtn.classList.remove('copied');
        }, 2000);
      } catch (err) {
        console.error('Failed to copy:', err);
        copyBtn.innerHTML = 'Failed';
        setTimeout(() => {
          copyBtn.innerHTML = 'Copy';
        }, 2000);
      }
    });

    // Wrap the pre element
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(copyBtn);
    wrapper.appendChild(pre);
  });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAlfredUI);
} else {
  initAlfredUI();
}
