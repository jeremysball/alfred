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
        if (currentAssistantMessage && msg.content) {
          currentAssistantMessage.appendContent(msg.content);
          scrollToBottom();
        }
        break;
        
      case 'chat.complete':
        // Finalize assistant message
        currentAssistantMessage = null;
        enableInput();
        break;
        
      case 'chat.error':
        showError(msg.message || 'An error occurred');
        currentAssistantMessage = null;
        enableInput();
        break;
        
      case 'status.update':
        console.log('Status update:', msg.status);
        break;
        
      case 'toast':
        showToast(msg.message, msg.level);
        break;
        
      default:
        console.log('Unhandled message type:', msg.type);
    }
  });

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
    // Simple console log for now, could be expanded to UI toast
    console.log(`[${level.toUpperCase()}] ${message}`);
  }

  // Event Listeners
  sendButton.addEventListener('click', sendMessage);
  
  messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
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
