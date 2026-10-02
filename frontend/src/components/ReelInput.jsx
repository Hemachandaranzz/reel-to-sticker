import React, { useState } from 'react';
import { downloadReelVideo, checkReelUrl } from '../lib/api';

export default function ReelInput({
  onVideoLoaded,
  onClearVideo,
  hasLoadedVideo = false,
  currentFileName = '',
  disabled = false,
}) {
  const [url, setUrl] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(null);
  const [error, setError] = useState(null);
  const [fallbackGuide, setFallbackGuide] = useState(null);

  const handleFetchAndLoad = async (e) => {
    e.preventDefault();
    const cleanUrl = url.trim();
    if (!cleanUrl) return;

    setError(null);
    setFallbackGuide(null);
    setIsDownloading(true);
    setDownloadProgress('Connecting to Instagram and extracting video...');

    try {
      const { blob, metadata } = await downloadReelVideo(cleanUrl);
      setDownloadProgress('Video received! Initializing sticker studio...');

      // Convert downloaded blob into a standard File object
      const videoFile = new File([blob], 'instagram_reel.mp4', { type: 'video/mp4' });

      if (onVideoLoaded) {
        onVideoLoaded(videoFile, metadata);
      }

      // Clear URL input so user can enter another URL immediately
      setUrl('');
    } catch (err) {
      setError(err.message || 'Failed to download video directly.');
      // Attempt checkReelUrl to show fallback instructions if available
      try {
        const checkData = await checkReelUrl(cleanUrl);
        setFallbackGuide(checkData);
      } catch {
        // ignore check errors
      }
    } finally {
      setIsDownloading(false);
      setDownloadProgress(null);
    }
  };

  const handleClearInput = () => {
    setUrl('');
    setError(null);
    setFallbackGuide(null);
  };

  return (
    <div className="reel-input-card">
      <div className="reel-header">
        <span className="reel-icon">⚡</span>
        <div>
          <h3>Download &amp; Convert Instagram Reel</h3>
          <p className="reel-sub">
            Paste an Instagram Reel link — our server will download the video automatically and load it into the editor!
          </p>
        </div>
      </div>

      {hasLoadedVideo && (
        <div className="current-video-bar">
          <div className="current-video-info">
            <span className="current-video-dot">●</span>
            <span>
              Active Video: <strong>{currentFileName || 'instagram_reel.mp4'}</strong>
            </span>
          </div>
          {onClearVideo && (
            <button
              type="button"
              className="clear-video-pill-btn"
              onClick={onClearVideo}
              disabled={disabled || isDownloading}
            >
              ✕ Clear / Start Fresh
            </button>
          )}
        </div>
      )}

      <form onSubmit={handleFetchAndLoad} className="reel-form">
        <div className="reel-input-wrapper">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder={
              hasLoadedVideo
                ? 'Paste another Reel URL to switch video...'
                : 'Paste Instagram Reel link (https://www.instagram.com/reel/...)'
            }
            className="reel-text-input"
            disabled={disabled || isDownloading}
            required
          />
          {url && !isDownloading && (
            <button
              type="button"
              className="clear-url-btn"
              onClick={handleClearInput}
              title="Clear URL"
            >
              ✕
            </button>
          )}
        </div>

        <button
          type="submit"
          className="reel-check-btn"
          disabled={disabled || isDownloading || !url.trim()}
        >
          {isDownloading ? (
            <>
              <span className="spinner" style={{ width: '0.8rem', height: '0.8rem' }} /> Fetching Video...
            </>
          ) : hasLoadedVideo ? (
            '🔄 Switch Video'
          ) : (
            '🚀 Fetch & Edit'
          )}
        </button>
      </form>

      {downloadProgress && (
        <div className="status-banner info">
          <span className="spinner" /> {downloadProgress}
        </div>
      )}

      {error && (
        <div className="status-banner error" role="alert">
          <span className="error-icon">⚠️</span>
          <div className="error-message">
            <strong>Download Error:</strong> {error}
          </div>
        </div>
      )}

      {fallbackGuide && (
        <div className="reel-guidance-box">
          <div className="reel-badge-row">
            <span className="valid-pill">ℹ️ Manual Option: {fallbackGuide.shortcode}</span>
            <a
              href={fallbackGuide.clean_url}
              target="_blank"
              rel="noopener noreferrer"
              className="open-reel-link"
            >
              Open on Instagram ↗
            </a>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            If Instagram restricts automated access to this clip, you can save it on Instagram and drop it below:
          </p>
          <ol className="guidance-steps">
            {fallbackGuide.guidance.map((step, idx) => (
              <li key={idx}>{step}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
