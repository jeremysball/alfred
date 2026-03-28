/**
 * File Validation
 *
 * Validates file types and sizes before upload.
 *
 * Constraints:
 *   - Max file size: 10MB
 *   - Allowed types: images, text files
 */

const FileValidation = {
  // Maximum file size in bytes (10MB)
  MAX_FILE_SIZE: 10 * 1024 * 1024,

  // Allowed MIME types
  ALLOWED_MIME_TYPES: [
    // Images
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/gif",
    "image/webp",
    // Text files
    "text/plain",
    "text/markdown",
    "text/x-python",
    "application/javascript",
    "application/json",
    "text/javascript",
    "text/json",
    "text/x-python-script",
  ],

  // Allowed extensions (as fallback)
  ALLOWED_EXTENSIONS: [
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".txt",
    ".md",
    ".py",
    ".js",
    ".json",
  ],

  /**
   * Check if file type is allowed
   * @param {File} file
   * @returns {boolean}
   */
  isFileTypeAllowed(file) {
    if (!file) return false;

    // Check MIME type
    if (this.ALLOWED_MIME_TYPES.includes(file.type)) {
      return true;
    }

    // Fallback: check extension
    const name = file.name.toLowerCase();
    return this.ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));
  },

  /**
   * Check if file size is within limit
   * @param {File} file
   * @returns {boolean}
   */
  isFileSizeAllowed(file) {
    if (!file) return false;
    return file.size <= this.MAX_FILE_SIZE;
  },

  /**
   * Validate a file (type + size)
   * @param {File} file
   * @returns {{valid: boolean, error?: string}}
   */
  validateFile(file) {
    if (!file) {
      return { valid: false, error: "No file provided" };
    }

    // Check type
    if (!this.isFileTypeAllowed(file)) {
      return {
        valid: false,
        error: `File type not allowed: ${file.name}. Allowed: images (png, jpg, gif, webp), text files (txt, md, py, js, json)`,
      };
    }

    // Check size
    if (!this.isFileSizeAllowed(file)) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      return {
        valid: false,
        error: `File too large: ${file.name} (${sizeMB}MB). Maximum: 10MB`,
      };
    }

    return { valid: true };
  },

  /**
   * Validate multiple files
   * @param {File[]} files
   * @returns {{valid: File[], invalid: {file: File, error: string}[]}}
   */
  validateFiles(files) {
    const valid = [];
    const invalid = [];

    for (const file of files) {
      const result = this.validateFile(file);
      if (result.valid) {
        valid.push(file);
      } else {
        invalid.push({ file, error: result.error });
      }
    }

    return { valid, invalid };
  },

  /**
   * Check if file is an image
   * @param {File} file
   * @returns {boolean}
   */
  isImage(file) {
    if (!file) return false;
    return file.type.startsWith("image/");
  },

  /**
   * Format file size for display
   * @param {number} bytes
   * @returns {string}
   */
  formatFileSize(bytes) {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / k ** i).toFixed(2))} ${sizes[i]}`;
  },
};

// Export for ESM and browser usage
export { FileValidation };

if (typeof window !== "undefined") {
  window.FileValidation = FileValidation;
}
