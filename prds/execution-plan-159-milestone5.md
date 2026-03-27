# Execution Plan: PRD #159 Milestone 5 - Drag & Drop

## Overview
Implement drag & drop file upload and message interaction for Alfred Web UI.

## Phase 1: Drag-Drop Manager Core
**Goal**: Handle drag events and show drop zone indicator

### Task 1.1: Create manager.js with event handling
- [ ] Test: Drag files over chat triggers dragenter event
- [ ] Implement: DragDropManager.attachToElement() attaches listeners
- [ ] Test: Dragleave clears drop state
- [ ] Implement: Dragleave handler clears visual state
- [ ] Test: Drop event captures files
- [ ] Implement: Drop handler extracts File objects
- [ ] Run: Verify in browser (drag files, see console logs)

### Task 1.2: Visual drop zone indicator
- [ ] Test: Dragenter adds CSS class to container
- [ ] Implement: showDropZone() adds highlight class
- [ ] Test: Dragleave removes CSS class
- [ ] Implement: hideDropZone() removes highlight class
- [ ] Test: Drop zone shows "Drop files here" text
- [ ] Implement: Overlay with drop message
- [ ] Run: Visual test in browser

## Phase 2: File Validation
**Goal**: Validate file types and sizes before upload

### Task 2.1: File type validation
- [ ] Test: acceptMimeTypes filters allowed types
- [ ] Implement: isFileTypeAllowed() checks extension/mime
- [ ] Test: Reject unknown file types
- [ ] Implement: Show error toast for invalid type
- [ ] Run: Test with .exe file (should reject)

### Task 2.2: File size validation  
- [ ] Test: 10MB limit enforced
- [ ] Implement: isFileSizeAllowed() checks size
- [ ] Test: Show error for oversized file
- [ ] Implement: Toast notification for size error
- [ ] Run: Test with 15MB file (should reject)

## Phase 3: Image Compression
**Goal**: Compress images >2MB before upload

### Task 3.1: Image detection and compression
- [ ] Test: isImage() detects image mime types
- [ ] Implement: Check mime type for image/*
- [ ] Test: Images >2MB trigger compression
- [ ] Implement: compressImage() using canvas
- [ ] Test: Compression reduces file size
- [ ] Implement: Resize if dimensions > 1920px
- [ ] Run: Test with large image, verify size reduction

### Task 3.2: Compression quality settings
- [ ] Test: JPEG quality 0.8, PNG no re-encoding
- [ ] Implement: Quality per format
- [ ] Test: Compressed image maintains aspect ratio
- [ ] Implement: Preserve aspect ratio in resize
- [ ] Run: Visual quality check

## Phase 4: File Upload via WebSocket
**Goal**: Send files to server as base64

### Task 4.1: File to base64 conversion
- [ ] Test: readFileAsBase64 returns base64 string
- [ ] Implement: FileReader API wrapper
- [ ] Test: Progress callback fires during read
- [ ] Implement: onprogress event handler
- [ ] Run: Test with small file

### Task 4.2: WebSocket upload message
- [ ] Test: generateFileId creates unique IDs
- [ ] Implement: UUID v4 generator
- [ ] Test: uploadFile sends correct message format
- [ ] Implement: WebSocket message with metadata
- [ ] Test: Upload progress notification shown
- [ ] Implement: Show progress via Toast
- [ ] Run: End-to-end upload test

### Task 4.3: Server response handling
- [ ] Test: file.received message parsed correctly
- [ ] Implement: Response handler
- [ ] Test: Success shows confirmation toast
- [ ] Implement: Success notification
- [ ] Test: Error shows error toast with reason
- [ ] Implement: Error handling
- [ ] Run: Test error case

## Phase 5: Clipboard Paste
**Goal**: Paste images from clipboard

### Task 5.1: Paste event handling
- [ ] Test: Ctrl+V triggers paste handler
- [ ] Implement: paste event listener
- [ ] Test: Clipboard items extracted
- [ ] Implement: getClipboardFiles() extracts images
- [ ] Test: Pasted image triggers upload
- [ ] Implement: Auto-upload on paste
- [ ] Run: Screenshot paste test

## Phase 6: Integration
**Goal**: Wire everything together in main.js

### Task 6.1: Module integration
- [ ] Test: DragDropManager initializes on page load
- [ ] Implement: initDragDrop() in main.js
- [ ] Test: All file types work end-to-end
- [ ] Implement: Hook into upload.js
- [ ] Test: Error handling works globally
- [ ] Implement: Global error handler
- [ ] Run: Full integration test

### Task 6.2: HTML/Script tags
- [ ] Add drag-drop scripts to index.html
- [ ] Add drag-drop styles to index.html
- [ ] Verify load order (after WebSocket client)
- [ ] Run: Page loads without errors

## Phase 7: Command Palette Integration
**Goal**: Add "Upload File" command

### Task 7.1: Upload command
- [ ] Test: "Upload File" command appears in palette
- [ ] Implement: Register upload command
- [ ] Test: Command opens file picker
- [ ] Implement: Trigger hidden file input
- [ ] Run: Command palette upload test

## Phase 8: Visual Polish
**Goal**: Final styling and animations

### Task 8.1: Drop zone styling
- [ ] Glassmorphism background
- [ ] Border highlight on drag
- [ ] Smooth transitions (200ms)
- [ ] Reduced motion support
- [ ] Run: Visual polish check

## Validation Checklist
- [ ] Drag file over chat → drop zone appears
- [ ] Drop valid file → upload starts, progress shown
- [ ] Drop 15MB file → error toast, no upload
- [ ] Drop .exe file → error toast, no upload
- [ ] Paste screenshot → upload starts
- [ ] Upload completes → success toast
- [ ] Server error → error toast with message
- [ ] All animations use transform/opacity only
