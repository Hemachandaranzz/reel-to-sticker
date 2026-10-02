import React, { useRef, useState } from 'react';
import { formatBytes } from '../lib/format';

export default function Dropzone({ onFileSelected, selectedFile, disabled }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    if (disabled) return;
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      onFileSelected(e.target.files[0]);
    }
  };

  return (
    <div
      className={`dropzone ${isDragOver ? 'drag-over' : ''} ${selectedFile ? 'has-file' : ''} ${disabled ? 'disabled' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      aria-label="Upload video file for WhatsApp sticker"
    >
      <input
        ref={inputRef}
        type="file"
        accept=".mp4,.mov,.webm,.m4v,.gif,video/*"
        style={{ display: 'none' }}
        onChange={handleChange}
        disabled={disabled}
      />

      {selectedFile ? (
        <div className="file-info">
          <div className="file-icon">🎬</div>
          <div className="file-details">
            <span className="file-name">{selectedFile.name}</span>
            <span className="file-size">{formatBytes(selectedFile.size)}</span>
          </div>
          <button
            type="button"
            className="change-file-btn"
            onClick={(e) => {
              e.stopPropagation();
              inputRef.current?.click();
            }}
            disabled={disabled}
          >
            Change
          </button>
        </div>
      ) : (
        <div className="dropzone-prompt">
          <div className="upload-icon">📤</div>
          <p className="prompt-primary">
            <strong>Click to upload</strong> or drag & drop video
          </p>
          <p className="prompt-secondary">MP4, MOV, WebM, M4V, GIF (max 50 MB)</p>
        </div>
      )}
    </div>
  );
}
