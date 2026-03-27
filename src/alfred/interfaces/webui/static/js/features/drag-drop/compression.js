/**
 * Image Compression
 *
 * Compresses images before upload to reduce size.
 * Only compresses if image > 2MB.
 *
 * Constraints:
 *   - Compress images > 2MB
 *   - Max dimension: 1920px
 *   - JPEG quality: 0.8
 *   - PNG: no re-encoding (just resize)
 */

const ImageCompression = {
  // Size threshold for compression (2MB)
  COMPRESSION_THRESHOLD: 2 * 1024 * 1024,

  // Maximum dimension (width or height)
  MAX_DIMENSION: 1920,

  // JPEG quality (0.0 - 1.0)
  JPEG_QUALITY: 0.8,

  /**
   * Check if image needs compression
   * @param {File} file
   * @returns {boolean}
   */
  needsCompression(file) {
    if (!file || !file.type.startsWith('image/')) return false;
    return file.size > this.COMPRESSION_THRESHOLD;
  },

  /**
   * Compress an image file
   * @param {File} file - The image file
   * @returns {Promise<Blob>} - The compressed image as Blob
   */
  async compress(file) {
    if (!this.needsCompression(file)) {
      return file; // No compression needed
    }

    console.log(`Compressing image: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)}MB)`);

    return new Promise((resolve, reject) => {
      const img = new Image();
      const url = URL.createObjectURL(file);

      img.onload = () => {
        URL.revokeObjectURL(url);

        // Calculate new dimensions
        const { width, height } = this._calculateDimensions(img.width, img.height);

        // Create canvas
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        // Draw image
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);

        // Determine output format
        const outputType = this._getOutputType(file.type);

        // Convert to blob
        canvas.toBlob(
          (blob) => {
            if (blob) {
              console.log(`Compressed: ${file.name} from ${(file.size / 1024 / 1024).toFixed(2)}MB to ${(blob.size / 1024 / 1024).toFixed(2)}MB`);
              resolve(blob);
            } else {
              reject(new Error('Canvas toBlob failed'));
            }
          },
          outputType,
          this.JPEG_QUALITY
        );
      };

      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error('Failed to load image'));
      };

      img.src = url;
    });
  },

  /**
   * Calculate new dimensions while preserving aspect ratio
   * @param {number} width - Original width
   * @param {number} height - Original height
   * @returns {{width: number, height: number}}
   */
  _calculateDimensions(width, height) {
    if (width <= this.MAX_DIMENSION && height <= this.MAX_DIMENSION) {
      return { width, height };
    }

    const ratio = Math.min(
      this.MAX_DIMENSION / width,
      this.MAX_DIMENSION / height
    );

    return {
      width: Math.round(width * ratio),
      height: Math.round(height * ratio),
    };
  },

  /**
   * Get output MIME type
   * @param {string} originalType
   * @returns {string}
   */
  _getOutputType(originalType) {
    // Keep PNG as PNG (lossless), convert others to JPEG
    if (originalType === 'image/png') {
      return 'image/png';
    }
    return 'image/jpeg';
  },

  /**
   * Create a File from a Blob with original metadata
   * @param {Blob} blob
   * @param {File} originalFile
   * @returns {File}
   */
  createFileFromBlob(blob, originalFile) {
    const extension = blob.type === 'image/png' ? '.png' : '.jpg';
    const name = originalFile.name.replace(/\.[^/.]+$/, '') + extension;

    return new File([blob], name, {
      type: blob.type,
      lastModified: originalFile.lastModified,
    });
  },

  /**
   * Compress image and return as File
   * @param {File} file
   * @returns {Promise<File>}
   */
  async compressToFile(file) {
    const blob = await this.compress(file);

    if (blob === file) {
      return file; // No compression applied
    }

    return this.createFileFromBlob(blob, file);
  },
};

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ImageCompression };
}

if (typeof window !== 'undefined') {
  window.ImageCompression = ImageCompression;
}
