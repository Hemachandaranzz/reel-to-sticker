import React, { useState, useEffect, useMemo } from 'react';
import {
  getPackStickers,
  removeStickerFromPack,
  updateStickerEmojis,
  clearStickerPack,
} from '../lib/packDb';
import ImportGuideModal from './ImportGuideModal';

const QUICK_EMOJIS = ['🔥', '😂', '❤️', '🚀', '😎', '✨', '💯', '👏', '🥳', '💀', '🎉', '🤩'];

export default function PackBuilder({ onRefreshRequired }) {
  const [stickers, setStickers] = useState([]);
  const [packName, setPackName] = useState('My Sticker Pack');
  const [publisher, setPublisher] = useState('WhatsApp Sticker Maker');
  const [trayIndex, setTrayIndex] = useState(0);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState(null);
  const [showGuide, setShowGuide] = useState(false);

  // Load stickers from IndexedDB
  const reloadStickers = async () => {
    try {
      const items = await getPackStickers();
      setStickers(items);
    } catch (e) {
      console.error('Failed to load pack stickers', e);
    }
  };

  useEffect(() => {
    reloadStickers();
  }, [onRefreshRequired]);

  // Validation rules
  const count = stickers.length;
  const countValid = count >= 3 && count <= 30;

  // Uniformity check
  const packMode = stickers.length > 0 ? stickers[0].mode : null;
  const isUniform = useMemo(() => {
    if (stickers.length === 0) return true;
    return stickers.every((s) => s.mode === packMode);
  }, [stickers, packMode]);

  const canExport = countValid && isUniform && !isExporting;

  const handleRemove = async (id) => {
    await removeStickerFromPack(id);
    await reloadStickers();
  };

  const handleClear = async () => {
    if (window.confirm('Are you sure you want to clear all stickers from this pack?')) {
      await clearStickerPack();
      await reloadStickers();
    }
  };

  const handleEmojiToggle = async (stickerId, currentEmojis, emoji) => {
    let nextEmojis;
    if (currentEmojis.includes(emoji)) {
      nextEmojis = currentEmojis.filter((e) => e !== emoji);
      if (nextEmojis.length === 0) nextEmojis = ['✨'];
    } else {
      if (currentEmojis.length >= 3) {
        nextEmojis = [...currentEmojis.slice(1), emoji];
      } else {
        nextEmojis = [...currentEmojis, emoji];
      }
    }
    await updateStickerEmojis(stickerId, nextEmojis);
    await reloadStickers();
  };

  const handleExport = async () => {
    if (!canExport) return;
    setError(null);
    setIsExporting(true);

    try {
      const formData = new FormData();
      formData.append('name', packName.trim() || 'My Sticker Pack');
      formData.append('publisher', publisher.trim() || 'WhatsApp Sticker Maker');

      const meta = stickers.map((s) => ({
        emojis: s.emojis || ['✨'],
      }));
      formData.append('stickers_meta', JSON.stringify(meta));

      // Append sticker files
      stickers.forEach((s, idx) => {
        const ext = 'webp';
        formData.append('stickers', s.blob, `sticker_${idx + 1}.${ext}`);
      });

      // Optional tray file if user selected one
      if (stickers[trayIndex]) {
        formData.append('tray_file', stickers[trayIndex].blob, 'tray.webp');
      }

      const res = await fetch('/api/packs/export', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Export failed: HTTP ${res.status}`);
      }

      const zipBlob = await res.blob();
      const downloadUrl = URL.createObjectURL(zipBlob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      const cleanName = (packName || 'pack').toLowerCase().replace(/\s+/g, '_');
      a.download = `${cleanName}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(downloadUrl), 5000);

      setShowGuide(true);
    } catch (err) {
      setError(err.message || 'Failed to export sticker pack.');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="pack-builder-section">
      <div className="pack-header-card">
        <div className="pack-title-row">
          <div>
            <h3>📦 WhatsApp Sticker Pack Builder</h3>
            <p className="pack-subtitle">
              Collect 3–30 stickers, configure WhatsApp emojis, and export as a ZIP package.
            </p>
          </div>
          {stickers.length > 0 && (
            <button type="button" className="clear-pack-btn" onClick={handleClear}>
              Clear Pack
            </button>
          )}
        </div>

        <div className="pack-inputs-grid">
          <div className="form-row">
            <label className="control-label">Pack Title:</label>
            <input
              type="text"
              value={packName}
              onChange={(e) => setPackName(e.target.value)}
              placeholder="e.g. Daily Reactions"
              maxLength={40}
              className="text-input"
            />
          </div>
          <div className="form-row">
            <label className="control-label">Author / Publisher:</label>
            <input
              type="text"
              value={publisher}
              onChange={(e) => setPublisher(e.target.value)}
              placeholder="e.g. My Name"
              maxLength={40}
              className="text-input"
            />
          </div>
        </div>

        {/* WhatsApp Requirements Checklist */}
        <div className="checklist-box">
          <div className={`check-item ${countValid ? 'valid' : 'invalid'}`}>
            <span className="check-icon">{countValid ? '✅' : '⚪'}</span>
            <span>
              3 to 30 Stickers: <strong>{count}/30</strong>{' '}
              {count < 3 ? `(Add ${3 - count} more)` : ''}
            </span>
          </div>

          <div className={`check-item ${isUniform ? 'valid' : 'invalid'}`}>
            <span className="check-icon">{isUniform ? '✅' : '❌'}</span>
            <span>
              Uniform Pack Type:{' '}
              <strong>
                {stickers.length === 0
                  ? 'None added yet'
                  : isUniform
                  ? `All ${packMode}`
                  : 'Mixed (Must be all static or all animated)'}
              </strong>
            </span>
          </div>

          <div className="check-item valid">
            <span className="check-icon">✅</span>
            <span>
              Tray Icon: <strong>Sticker #{trayIndex + 1} (96×96 PNG auto-scaled)</strong>
            </span>
          </div>
        </div>
      </div>

      {error && <div className="status-banner error">{error}</div>}

      {/* Sticker Grid */}
      {stickers.length === 0 ? (
        <div className="empty-pack-placeholder">
          <span className="empty-icon">🗂️</span>
          <p>No stickers in pack yet.</p>
          <small>
            Convert any video clip above and tap <strong>"Add to Pack"</strong> to begin building!
          </small>
        </div>
      ) : (
        <div className="pack-grid">
          {stickers.map((s, idx) => {
            const url = URL.createObjectURL(s.blob);
            return (
              <div key={s.id} className="pack-item-card">
                <div className="pack-thumb-wrapper">
                  <img
                    src={url}
                    alt={`Sticker ${idx + 1}`}
                    className="pack-thumb-img"
                    onLoad={() => URL.revokeObjectURL(url)}
                  />
                  <span className="pack-mode-pill">{s.mode}</span>
                  {trayIndex === idx && <span className="tray-badge">Tray Icon</span>}
                </div>

                <div className="pack-item-controls">
                  <div className="emoji-display">
                    <span className="control-label">Emojis (1–3):</span>
                    <div className="active-emojis">
                      {(s.emojis || ['✨']).map((em, i) => (
                        <span key={i} className="active-emoji-tag">
                          {em}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="quick-emoji-row">
                    {QUICK_EMOJIS.map((em) => (
                      <button
                        key={em}
                        type="button"
                        className={`mini-emoji-btn ${(s.emojis || []).includes(em) ? 'selected' : ''}`}
                        onClick={() => handleEmojiToggle(s.id, s.emojis || [], em)}
                      >
                        {em}
                      </button>
                    ))}
                  </div>

                  <div className="pack-item-actions">
                    <button
                      type="button"
                      className={`tray-select-btn ${trayIndex === idx ? 'active' : ''}`}
                      onClick={() => setTrayIndex(idx)}
                    >
                      {trayIndex === idx ? '★ Tray Icon' : 'Set as Tray'}
                    </button>
                    <button
                      type="button"
                      className="delete-item-btn"
                      onClick={() => handleRemove(s.id)}
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Export Action */}
      <div className="export-action-card">
        <button
          type="button"
          className="export-pack-btn"
          disabled={!canExport}
          onClick={handleExport}
        >
          {isExporting ? 'Packaging Sticker Pack...' : '📦 Export WhatsApp Sticker Pack (ZIP)'}
        </button>
        {!countValid && (
          <small className="export-hint">
            You need at least 3 stickers to export a valid WhatsApp pack.
          </small>
        )}
      </div>

      <ImportGuideModal
        isOpen={showGuide}
        onClose={() => setShowGuide(false)}
        packName={packName}
      />
    </div>
  );
}
