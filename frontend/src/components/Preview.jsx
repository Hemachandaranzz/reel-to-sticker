import React, { useState } from 'react';
import { formatBytes } from '../lib/format';
import { convertWebpToGif, convertWebpToMp4 } from '../lib/api';

export default function Preview({ result, mode, onReset, onTrySmaller, onAddToPack }) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(null);
  const [isConvertingGif, setIsConvertingGif] = useState(false);
  const [gifError, setGifError] = useState(null);
  const [isConvertingMp4, setIsConvertingMp4] = useState(false);
  const [mp4Error, setMp4Error] = useState(null);

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

  const handleDownloadGif = async () => {
    if (!result?.blob) return;
    setIsConvertingGif(true);
    setGifError(null);
    try {
      const { blob: gifBlob } = await convertWebpToGif(result.blob);
      const url = URL.createObjectURL(gifBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'sticker.gif';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (err) {
      console.error('GIF export error:', err);
      setGifError(err.message || 'Failed to convert sticker to GIF.');
      setTimeout(() => setGifError(null), 4000);
    } finally {
      setIsConvertingGif(false);
    }
  };

  const handleDownloadMp4 = async () => {
    if (!result?.blob) return;
    setIsConvertingMp4(true);
    setMp4Error(null);
    try {
      const { blob: mp4Blob } = await convertWebpToMp4(result.blob);
      const url = URL.createObjectURL(mp4Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'sticker.mp4';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (err) {
      console.error('MP4 export error:', err);
      setMp4Error(err.message || 'Failed to convert sticker to MP4.');
      setTimeout(() => setMp4Error(null), 4000);
    } finally {
      setIsConvertingMp4(false);
    }
  };


  const handleCopyToClipboard = async () => {
    setCopyError(null);
    try {
      if (!navigator.clipboard || !window.ClipboardItem) {
        throw new Error('Clipboard image copying is not supported in this browser.');
      }

      // Convert the WebP image to standard PNG for universal clipboard support
      const img = new Image();
      img.crossOrigin = 'anonymous';

      await new Promise((resolve, reject) => {
        img.onload = () => resolve();
        img.onerror = () => reject(new Error('Failed to load sticker image for copying.'));
        img.src = result.url;
      });

      const canvas = document.createElement('canvas');
      canvas.width = img.naturalWidth || 512;
      canvas.height = img.naturalHeight || 512;
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);

      const pngBlob = await new Promise((resolve) => {
        canvas.toBlob(resolve, 'image/png');
      });

      if (!pngBlob) {
        throw new Error('Failed to create clipboard image data.');
      }

      const item = new ClipboardItem({ 'image/png': pngBlob });
      await navigator.clipboard.write([item]);

      setCopied(true);
      setTimeout(() => setCopied(false), 4000);
    } catch (err) {
      console.error('Clipboard copy error:', err);
      setCopyError(err.message || 'Failed to copy to clipboard.');
      setTimeout(() => setCopyError(null), 4000);
    }
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

      {copyError && (
        <div className="status-banner error" style={{ fontSize: '0.8rem', padding: '0.5rem' }}>
          ⚠️ {copyError}
        </div>
      )}

      <div className="preview-actions">
        <div className="primary-actions-row">
          <button
            type="button"
            className="download-btn"
            onClick={handleDownload}
            title="Download WhatsApp WebP Sticker (512x512) for mobile Sticker Pack apps"
          >
            ⬇️ Download Sticker (.webp)
          </button>

          {mode === 'animated' && (
            <>
              <button
                type="button"
                className="download-mp4-btn"
                onClick={handleDownloadMp4}
                disabled={isConvertingMp4}
                title="Download MP4 clip — WhatsApp Web natively provides a GIF toggle for this"
              >
                {isConvertingMp4 ? (
                  <>
                    <span className="spinner" style={{ width: '0.8rem', height: '0.8rem' }} /> Converting MP4...
                  </>
                ) : (
                  '🎬 Download MP4 (WA GIF)'
                )}
              </button>

              <button
                type="button"
                className="download-gif-btn"
                onClick={handleDownloadGif}
                disabled={isConvertingGif}
                title="Convert and download as animated GIF file"
              >
                {isConvertingGif ? (
                  <>
                    <span className="spinner" style={{ width: '0.8rem', height: '0.8rem' }} /> Converting GIF...
                  </>
                ) : (
                  '🎞️ Download as GIF'
                )}
              </button>
            </>
          )}

          <button
            type="button"
            className={`copy-clipboard-btn ${copied ? 'copied' : ''}`}
            onClick={handleCopyToClipboard}
            title="Copies static PNG image to clipboard"
          >
            {copied ? '✅ Photo Copied!' : '📋 Copy Image'}
          </button>
        </div>

        {mp4Error && (
          <div className="status-banner error" style={{ fontSize: '0.8rem', padding: '0.5rem' }}>
            ⚠️ {mp4Error}
          </div>
        )}

        {gifError && (
          <div className="status-banner error" style={{ fontSize: '0.8rem', padding: '0.5rem' }}>
            ⚠️ {gifError}
          </div>
        )}

        {copied && (
          <small className="copied-hint">
            Copied image frame! (Note: WhatsApp Web Ctrl+V pastes images as photos. To send as a sticker or GIF, use the buttons above).
          </small>
        )}

        {/* WhatsApp Send Guide Card */}
        <div className="wa-guide-box">
          <div className="wa-guide-header">
            <span>💡 Why Did .webp Become a Static Sticker in WhatsApp Web?</span>
          </div>
          <p className="wa-guide-desc">
            WhatsApp Web's <strong>+ &gt; Sticker</strong> tool is hardcoded by Meta as a <em>static-only image creator</em> — it automatically flattens any animated WebP into frame 1. Here is how to send your animation properly:
          </p>
          <div className="wa-guide-grid">
            <div className="wa-guide-card highlight-card">
              <span className="wa-guide-badge">⚡ Method 1: Instant WhatsApp Web Animation (Recommended)</span>
              <p>Send an auto-looping animated sticker without needing phone apps:</p>
              <ol className="wa-steps-list">
                <li>Click <strong>🎬 Download MP4</strong> (or <strong>🎞️ Download GIF</strong>)</li>
                <li>In WhatsApp Web, click <strong>+ (Attach)</strong> → <strong>Photos &amp; videos</strong> (do NOT use "+ &gt; Sticker")</li>
                <li>In the WhatsApp preview, click the <strong>GIF</strong> toggle button at the top right</li>
                <li>Click <strong>Send</strong> — it loops infinitely in the chat as an animated GIF sticker!</li>
              </ol>
            </div>
            <div className="wa-guide-card">
              <span className="wa-guide-badge">📱 Method 2: Official Animated Sticker Tray</span>
              <p>To put animated .webp stickers into WhatsApp's official sticker keyboard:</p>
              <ol className="wa-steps-list">
                <li>Click <strong>⬇️ Download Sticker (.webp)</strong> or <strong>📦 Add to Sticker Pack</strong></li>
                <li>Send the file to your phone and open in <strong>Sticker.ly</strong> or <strong>Sticker Maker</strong></li>
                <li>Tap <strong>Add to WhatsApp</strong> to install the pack</li>
                <li>Now it stays in your official sticker drawer and syncs to WhatsApp Web with full animation!</li>
              </ol>
            </div>
          </div>
        </div>

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
