/**
 * File Upload
 *
 * Handles file upload via WebSocket using base64 encoding.
 * Integrates with validation and compression.
 *
 * Usage:
 *   uploadFile(file, websocketClient)
 *     .then(result => console.log('Upload complete:', result))
 *     .catch(error => console.error('Upload failed:', error));
 */

const FileUpload = {
  // Track active uploads
  activeUploads: new Map(),

  /**
   * Generate a unique file ID
   * @returns {string}
   */
  generateFileId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  },

  /**
   * Read file as base64
   * @param {File} file
   * @param {Function} onProgress - Callback(percent)
   * @returns {Promise<string>}
   */
  readFileAsBase64(file, onProgress = null) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };

      reader.onload = () => {
        // Remove data URL prefix (e.g., "data:image/jpeg;base64,")
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      };

      reader.onerror = () => {
        reject(new Error(`Failed to read file: ${file.name}`));
      };

      reader.readAsDataURL(file);
    });
  },

  /**
   * Upload a single file via WebSocket
   * @param {File} file
   * @param {Object} wsClient - WebSocket client (AlfredWebSocketClient)
   * @param {Object} options
   * @returns {Promise<Object>}
   */
  async uploadFile(file, wsClient, options = {}) {
    const {
      onProgress = null,
      onComplete = null,
      onError = null,
    } = options;

    const fileId = this.generateFileId();

    console.log(`Starting upload: ${file.name} (ID: ${fileId})`);

    // Store upload state
    this.activeUploads.set(fileId, {
      file,
      startTime: Date.now(),
      status: 'reading',
    });

    try {
      // Read file as base64
      if (onProgress) onProgress(0);
      const base64Data = await this.readFileAsBase64(file, onProgress);

      this.activeUploads.get(fileId).status = 'uploading';

      // Create upload message
      const uploadMessage = {
        type: 'file.upload',
        payload: {
          fileId,
          name: file.name,
          mimeType: file.type || 'application/octet-stream',
          size: file.size,
          data: base64Data,
        },
      };

      // Send via WebSocket
      if (!wsClient || typeof wsClient.send !== 'function') {
        throw new Error('Invalid WebSocket client');
      }

      wsClient.send(uploadMessage);

      // Wait for response (handled by caller)
      this.activeUploads.get(fileId).status = 'sent';

      return {
        fileId,
        file,
        status: 'sent',
      };

    } catch (error) {
      this.activeUploads.get(fileId).status = 'error';
      this.activeUploads.get(fileId).error = error.message;

      if (onError) onError(error);
      throw error;
    }
  },

  /**
   * Handle server response for file upload
   * @param {Object} message - WebSocket message
   * @returns {Object|null}
   */
  handleResponse(message) {
    if (message.type !== 'file.received') {
      return null;
    }

    const { fileId, status, reason, url } = message.payload || {};

    if (!fileId || !this.activeUploads.has(fileId)) {
      console.warn('Unknown file ID in response:', fileId);
      return null;
    }

    const upload = this.activeUploads.get(fileId);
    upload.status = status;
    upload.endTime = Date.now();
    upload.duration = upload.endTime - upload.startTime;

    if (status === 'accepted') {
      upload.url = url;
      console.log(`Upload accepted: ${upload.file.name} (${upload.duration}ms)`);
    } else {
      upload.error = reason;
      console.error(`Upload rejected: ${upload.file.name} - ${reason}`);
    }

    return {
      fileId,
      file: upload.file,
      status,
      reason,
      url,
      duration: upload.duration,
    };
  },

  /**
   * Get upload status
   * @param {string} fileId
   * @returns {Object|null}
   */
  getUploadStatus(fileId) {
    return this.activeUploads.get(fileId) || null;
  },

  /**
   * Clear completed uploads
   * @param {number} olderThan - Clear uploads older than X ms (default: 5 minutes)
   */
  clearCompleted(olderThan = 5 * 60 * 1000) {
    const cutoff = Date.now() - olderThan;
    for (const [fileId, upload] of this.activeUploads.entries()) {
      if (upload.status === 'accepted' || upload.status === 'rejected') {
        if (upload.endTime && upload.endTime < cutoff) {
          this.activeUploads.delete(fileId);
        }
      }
    }
  },

  /**
   * Upload multiple files
   * @param {File[]} files
   * @param {Object} wsClient
   * @param {Object} callbacks
   * @returns {Promise<Object[]>}
   */
  async uploadFiles(files, wsClient, callbacks = {}) {
    const { onFileComplete, onFileError, onProgress } = callbacks;
    const results = [];

    for (const file of files) {
      try {
        const result = await this.uploadFile(file, wsClient, {
          onProgress: (percent) => onProgress?.(file, percent),
        });

        results.push({ file, success: true, fileId: result.fileId });
        onFileComplete?.(file, result);

      } catch (error) {
        results.push({ file, success: false, error: error.message });
        onFileError?.(file, error);
      }
    }

    return results;
  },
};

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { FileUpload };
}

if (typeof window !== 'undefined') {
  window.FileUpload = FileUpload;
}
