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
  const connectionStatus = document.getElementById('connection-status');
  const chatContainer = document.getElementById('chat-container');

  // WebSocket Client
  const wsClient = new AlfredWebSocketClient();
  let currentAssistantMessage = null;
  const activeToolCalls = new Map(); // toolCallId -> tool-call element
  let allToolsExpanded = false;

  // Connection Status Handler
  function updateConnectionStatus(status, text) {
    connectionStatus.className = `status ${status}`;
    connectionStatus.textContent = text;
  }

  wsClient.addEventListener('connected', () => {
    updateConnectionStatus('connected', 'Connected');
  });

  wsClient.addEventListener('disconnected', () => {
    updateConnectionStatus('disconnected', 'Disconnected');
  });

  wsClient.addEventListener('error', () => {
    updateConnectionStatus('disconnected', 'Error');
  });

  // Message Handler
  wsClient.addEventListener('message', (event) => {
    const msg = event.detail;

    switch (msg.type) {
      case 'chat.started':
        // Create new assistant message element for streaming
        currentAssistantMessage = document.createElement('chat-message');
        currentAssistantMessage.setAttribute('role', 'assistant');
        currentAssistantMessage.setAttribute('content', '');
        currentAssistantMessage.setAttribute('timestamp', new Date().toISOString());
        messageList.appendChild(currentAssistantMessage);
        scrollToBottom();
        break;

      case 'chat.chunk':
        // Append chunk to current assistant message
        if (currentAssistantMessage && msg.payload && msg.payload.content) {
          currentAssistantMessage.appendContent(msg.payload.content);
          scrollToBottom();
        }
        break;

      case 'chat.complete':
        // Finalize assistant message
        currentAssistantMessage = null;
        enableInput();
        break;

      case 'chat.error':
        showError(msg.payload?.error || 'An error occurred');
        currentAssistantMessage = null;
        enableInput();
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

      case 'status.update':
        console.log('Status update:', msg.payload);
        break;

      case 'toast':
        showToast(msg.payload?.message, msg.payload?.level);
        break;

      default:
        console.log('Unhandled message type:', msg.type);
    }
  });

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

    // Append to current assistant message
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
      // Keep in map for potential Ctrl+T toggle
    }
  }

  // Send Message Handler
  function sendMessage() {
    const content = messageInput.value.trim();
    if (!content) return;

    // Add user message to UI
    const userMessage = document.createElement('chat-message');
    userMessage.setAttribute('role', 'user');
    userMessage.setAttribute('content', content);
    userMessage.setAttribute('timestamp', new Date().toISOString());
    messageList.appendChild(userMessage);

    // Clear input and disable until response
    messageInput.value = '';
    disableInput();
    scrollToBottom();

    // Send via WebSocket
    wsClient.sendChat(content);
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
    console.log(`All tools ${allToolsExpanded ? 'expanded' : 'collapsed'}`);
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

  function showToast(message, level = 'info') {
    console.log(`[${level?.toUpperCase() || 'INFO'}] ${message}`);
  }

  // Event Listeners
  sendButton.addEventListener('click', sendMessage);

  messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Ctrl+T - Toggle all tool calls
    if (e.ctrlKey && e.key === 't') {
      e.preventDefault();
      toggleAllTools();
    }
  });

  // Auto-scroll on window resize
  window.addEventListener('resize', scrollToBottom);

  // Connect WebSocket
  wsClient.connect();

  // Focus input on load
  messageInput.focus();

  console.log('Alfred Web UI initialized');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAlfredUI);
} else {
  initAlfredUI();
}
