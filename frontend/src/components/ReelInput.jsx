import React, { useState } from 'react';
import { checkReelUrl } from '../lib/api';

export default function ReelInput({ onPermissionConfirmed, disabled }) {
  const [url, setUrl] = useState('');
  const [isChecking, setIsChecking] = useState(false);
  const [error, setError] = useState(null);
  const [reelData, setReelData] = useState(null);
  const [hasPermission, setHasPermission] = useState(false);

  const handleCheck = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;

    setError(null);
    setReelData(null);
    setIsChecking(true);

    try {
      const data = await checkReelUrl(url.trim());
      setReelData(data);
      if (hasPermission && onPermissionConfirmed) {
        onPermissionConfirmed(true);
      }
    } catch (err) {
      setError(err.message || 'Invalid Instagram Reel URL.');
    } finally {
      setIsChecking(false);
    }
  };

  const handlePermissionToggle = (checked) => {
    setHasPermission(checked);
    if (onPermissionConfirmed) {
      onPermissionConfirmed(checked);
    }
  };

  return (
    <div className="reel-input-card">
      <div className="reel-header">
        <span className="reel-icon">📸</span>
        <div>
          <h3>Convert from Instagram Reel</h3>
          <p className="reel-sub">
            Paste a link to verify the Reel, then follow the 3-step guide to convert.
          </p>
        </div>
      </div>

      <form onSubmit={handleCheck} className="reel-form">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.instagram.com/reel/C_8xYzaB123/..."
          className="reel-text-input"
          disabled={disabled || isChecking}
        />
        <button
          type="submit"
          className="reel-check-btn"
          disabled={disabled || isChecking || !url.trim()}
        >
          {isChecking ? 'Checking...' : 'Check Link'}
        </button>
      </form>

      {error && <div className="status-banner error">{error}</div>}

      {reelData && (
        <div className="reel-guidance-box">
          <div className="reel-badge-row">
            <span className="valid-pill">✅ Verified Reel: {reelData.shortcode}</span>
            <a
              href={reelData.clean_url}
              target="_blank"
              rel="noopener noreferrer"
              className="open-reel-link"
            >
              Open on Instagram ↗
            </a>
          </div>

          <ol className="guidance-steps">
            {reelData.guidance.map((step, idx) => (
              <li key={idx}>{step}</li>
            ))}
          </ol>

          <label className="permission-checkbox-label">
            <input
              type="checkbox"
              checked={hasPermission}
              onChange={(e) => handlePermissionToggle(e.target.checked)}
            />
            <span>
              I own this video or have permission from the creator to create stickers from it.
            </span>
          </label>
        </div>
      )}
    </div>
  );
}
