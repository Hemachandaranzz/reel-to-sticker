import React, { useState } from 'react';

export default function ImportGuideModal({ isOpen, onClose, packName }) {
  const [platform, setPlatform] = useState('android'); // 'android' | 'ios'

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>📲 How to Add "{packName}" to WhatsApp</h3>
            <p className="modal-subtitle">
              Meta does not allow direct web-to-WhatsApp sticker injection. Follow these simple steps:
            </p>
          </div>
          <button type="button" className="close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="platform-toggle">
          <button
            type="button"
            className={`platform-btn ${platform === 'android' ? 'active' : ''}`}
            onClick={() => setPlatform('android')}
          >
            🤖 Android
          </button>
          <button
            type="button"
            className={`platform-btn ${platform === 'ios' ? 'active' : ''}`}
            onClick={() => setPlatform('ios')}
          >
            🍎 iPhone (iOS)
          </button>
        </div>

        <div className="guide-content">
          {platform === 'android' ? (
            <div className="steps-list">
              <div className="guide-step">
                <span className="step-num">1</span>
                <div>
                  <strong>Install a Sticker Importer App</strong>
                  <p>
                    Download <em>"Sticker Maker"</em> (by Viko &amp; Co) or{' '}
                    <em>"Personal Stickers for WhatsApp"</em> from the Google Play Store.
                  </p>
                </div>
              </div>
              <div className="guide-step">
                <span className="step-num">2</span>
                <div>
                  <strong>Extract or Open the ZIP</strong>
                  <p>
                    Unzip your downloaded <code>{packName || 'pack'}.zip</code> file using your phone's File Manager.
                  </p>
                </div>
              </div>
              <div className="guide-step">
                <span className="step-num">3</span>
                <div>
                  <strong>Tap "Add to WhatsApp"</strong>
                  <p>
                    Select the stickers in Sticker Maker and tap <strong>Add to WhatsApp</strong>.
                    They will immediately appear in your WhatsApp emoji &gt; stickers tray!
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="steps-list">
              <div className="guide-step">
                <span className="step-num">1</span>
                <div>
                  <strong>Install "Top Stickers" or "Sticker.ly"</strong>
                  <p>
                    Download <em>"Top Stickers"</em> or <em>"Sticker.ly"</em> from the iOS App Store.
                  </p>
                </div>
              </div>
              <div className="guide-step">
                <span className="step-num">2</span>
                <div>
                  <strong>Unzip in Files App</strong>
                  <p>
                    Tap the downloaded <code>.zip</code> in Safari / Files app to extract the folder.
                  </p>
                </div>
              </div>
              <div className="guide-step">
                <span className="step-num">3</span>
                <div>
                  <strong>Export to WhatsApp</strong>
                  <p>
                    In Top Stickers, choose <em>Import Pack</em>, select your sticker files, and tap{' '}
                    <strong>Add to WhatsApp</strong>.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="got-it-btn" onClick={onClose}>
            Got it, thanks!
          </button>
        </div>
      </div>
    </div>
  );
}
