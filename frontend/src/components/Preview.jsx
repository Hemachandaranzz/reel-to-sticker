import React from 'react';
import { formatBytes } from '../lib/format';

export default function Preview({ result, mode, onReset, onTrySmaller, onAddToPack }) {
  if (!result || !result.url) return null;

  const maxBytes = mode === 'static' ? 100_000 : 500_000;
  const sizeRatio = Math.min(100, Math.round((result.size / maxBytes) * 100));
  const isCloseToLimit = sizeRatio > 90;

  const downloadFilename =
    mode === 'static' ? 'sticker.webp' : 'animated_sticker.webp';

  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = result.url;
    a.download = downloadFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="preview-container">
      <div className="preview-header">
        <h3>Generated WhatsApp Sticker</h3>
        <span className="dimension-badge">512 × 512 px</span>
      </div>

      <div className="checkerboard-wrapper">
        <img
          src={result.url}
          alt="WhatsApp Sticker Preview"
          className="sticker-image"
        />
      </div>

      <div className="size-progress-section">
        <div className="size-labels">
          <span className="current-size">
            <strong>{formatBytes(result.size)}</strong> ({sizeRatio}% of limit)
          </span>
          <span className="max-size">
            WhatsApp Limit: {formatBytes(maxBytes)}
          </span>
        </div>
        <div className="progress-bar-bg">
          <div
            className={`progress-bar-fill ${isCloseToLimit ? 'near-limit' : ''}`}
            style={{ width: `${sizeRatio}%` }}
          />
        </div>
      </div>

      {/* Optimizer explanation */}
      <div className="optimizer-summary">
        {mode === 'animated' ? (
          <p className="optimizer-note">
            ⚡ Optimizer tuned clip to <strong>{result.fps || 12} FPS</strong> at{' '}
            <strong>{result.quality || 60}% quality</strong> to satisfy WhatsApp size limits.
          </p>
        ) : (
          <p className="optimizer-note">
            🖼️ Encoded static WebP at <strong>{result.quality || 80}% quality</strong>.
          </p>
        )}
      </div>

      <div className="meta-badges">
        {result.quality && (
          <span className="meta-pill">Quality: {result.quality}%</span>
        )}
        {result.fps && (
          <span className="meta-pill">FPS: {result.fps}</span>
        )}
        {result.duration && (
          <span className="meta-pill">Duration: {result.duration}s</span>
        )}
        {result.frames && (
          <span className="meta-pill">Frames: {result.frames}</span>
        )}
      </div>

      <div className="preview-actions">
        <button
          type="button"
          className="download-btn"
          onClick={handleDownload}
        >
          ⬇️ Download Sticker (.webp)
        </button>

        {onAddToPack && (
          <button
            type="button"
            className="add-to-pack-btn"
            onClick={async () => {
              if (onAddToPack) {
                await onAddToPack(result.blob, mode);
              }
            }}
          >
            📦 Add to Sticker Pack
          </button>
        )}

        <div className="secondary-actions-row">
          {onTrySmaller && (
            <button
              type="button"
              className="action-pill-btn"
              onClick={onTrySmaller}
            >
              🔄 Try Again Smaller
            </button>
          )}

          {onReset && (
            <button
              type="button"
              className="action-pill-btn"
              onClick={onReset}
            >
              ➕ Convert Another
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
