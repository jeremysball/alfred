/**
 * Drag-Drop Module
 *
 * File upload via drag-drop and clipboard paste.
 *
 * Usage:
 *   import { DragDropManager, FileUpload, FileValidation, ImageCompression, ClipboardHandler } from './drag-drop/index.js';
 *
 *   // Initialize
 *   const manager = new DragDropManager();
 *   manager.attachToElement(document.getElementById('chat'));
 *
 *   // Handle files
 *   manager.onFilesDropped = async (files) => {
 *     // Validate
 *     const { valid, invalid } = FileValidation.validateFiles(files);
 *
 *     // Show errors for invalid
 *     invalid.forEach(({ error }) => Toast.error(error));
 *
 *     // Upload valid files
 *     for (const file of valid) {
 *       // Compress images if needed
 *       const processedFile = await ImageCompression.compressToFile(file);
 *       await FileUpload.uploadFile(processedFile, wsClient);
 *     }
 *   };
 */

// These will be loaded via script tags before this module
const DragDropManager = window.DragDropManager;
const FileValidation = window.FileValidation;
const ImageCompression = window.ImageCompression;
const FileUpload = window.FileUpload;
const ClipboardHandler = window.ClipboardHandler;
const DropZoneVisual = window.DropZoneVisual;

// Export for CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    DragDropManager,
    FileValidation,
    ImageCompression,
    FileUpload,
    ClipboardHandler,
    DropZoneVisual,
  };
}

// Export for ES modules
export {
  DragDropManager,
  FileValidation,
  ImageCompression,
  FileUpload,
  ClipboardHandler,
  DropZoneVisual,
};

// Expose as namespace
if (typeof window !== 'undefined') {
  window.DragDropLib = {
    DragDropManager,
    FileValidation,
    ImageCompression,
    FileUpload,
    ClipboardHandler,
    DropZoneVisual,
  };
}
