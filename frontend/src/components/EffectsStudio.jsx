import React, { useState } from 'react';

const QUICK_EMOJIS = ['🔥', '😂', '❤️', '🚀', '😎', '✨', '💯', '👏', '🥳', '💀'];

export default function EffectsStudio({
  mode,
  capabilities,
  // Cutout & outline
  removeBg,
  onRemoveBgChange,
  outlinePx,
  onOutlinePxChange,
  feather,
  onFeatherChange,
  // Video effects
  flipH,
  onFlipHChange,
  reverse,
  onReverseChange,
  boomerang,
  onBoomerangChange,
  // Caption & emoji
  captionText,
  onCaptionTextChange,
  fontFamily,
  onFontFamilyChange,
  fontSize,
  onFontSizeChange,
  textColor,
  onTextColorChange,
  strokeColor,
  onStrokeColorChange,
  textPos,
  onTextPosChange,
  selectedEmoji,
  onSelectedEmojiChange,
  disabled,
}) {
  const [activeTab, setActiveTab] = useState('effects'); // 'effects' | 'caption' | 'cutout'

  const cutoutAvail = capabilities?.cutout_available ?? false;

  return (
    <div className="effects-studio-container">
      <div className="studio-subtabs">
        <button
          type="button"
          className={`subtab-btn ${activeTab === 'effects' ? 'active' : ''}`}
          onClick={() => setActiveTab('effects')}
        >
          ✨ Motion &amp; Flip
        </button>
        <button
          type="button"
          className={`subtab-btn ${activeTab === 'caption' ? 'active' : ''}`}
          onClick={() => setActiveTab('caption')}
        >
          💬 Text &amp; Emoji
        </button>
        <button
          type="button"
          className={`subtab-btn ${activeTab === 'cutout' ? 'active' : ''}`}
          onClick={() => setActiveTab('cutout')}
        >
          ✂️ Cutout &amp; Outline
        </button>
      </div>

      <div className="subtab-panel">
        {/* Tab 1: Video / Motion Effects */}
        {activeTab === 'effects' && (
          <div className="effects-grid">
            <label className="toggle-card">
              <input
                type="checkbox"
                checked={flipH}
                onChange={(e) => onFlipHChange(e.target.checked)}
                disabled={disabled}
              />
              <span className="toggle-label">
                <strong>↔️ Flip Horizontally</strong>
                <small>Mirror the video orientation</small>
              </span>
            </label>

            {mode === 'animated' && (
              <>
                <label className="toggle-card">
                  <input
                    type="checkbox"
                    checked={boomerang}
                    onChange={(e) => {
                      onBoomerangChange(e.target.checked);
                      if (e.target.checked) onReverseChange(false);
                    }}
                    disabled={disabled}
                  />
                  <span className="toggle-label">
                    <strong>🪃 Boomerang Loop</strong>
                    <small>Plays forward then reverses back</small>
                  </span>
                </label>

                <label className="toggle-card">
                  <input
                    type="checkbox"
                    checked={reverse}
                    onChange={(e) => {
                      onReverseChange(e.target.checked);
                      if (e.target.checked) onBoomerangChange(false);
                    }}
                    disabled={disabled || boomerang}
                  />
                  <span className="toggle-label">
                    <strong>⏪ Reverse Playback</strong>
                    <small>Plays the entire clip in reverse</small>
                  </span>
                </label>
              </>
            )}
          </div>
        )}

        {/* Tab 2: Caption & Emoji */}
        {activeTab === 'caption' && (
          <div className="caption-panel">
            <div className="form-row">
              <label className="control-label">Caption Text:</label>
              <input
                type="text"
                value={captionText}
                onChange={(e) => onCaptionTextChange(e.target.value)}
                placeholder="e.g. WHEN THE CODE WORKS"
                maxLength={60}
                disabled={disabled}
                className="text-input"
              />
            </div>

            {captionText.trim() && (
              <div className="caption-controls-grid">
                <div>
                  <label className="control-label">Font Style:</label>
                  <select
                    value={fontFamily}
                    onChange={(e) => onFontFamilyChange(e.target.value)}
                    disabled={disabled}
                    className="select-input"
                  >
                    <option value="impact">Impact (Classic Meme)</option>
                    <option value="arial">Bold Sans</option>
                    <option value="comic">Comic Style</option>
                  </select>
                </div>

                <div>
                  <label className="control-label">Position:</label>
                  <select
                    value={textPos}
                    onChange={(e) => onTextPosChange(e.target.value)}
                    disabled={disabled}
                    className="select-input"
                  >
                    <option value="bottom">Bottom</option>
                    <option value="top">Top</option>
                    <option value="center">Center</option>
                  </select>
                </div>

                <div>
                  <label className="control-label">Size: {fontSize}px</label>
                  <input
                    type="range"
                    min={24}
                    max={56}
                    step={2}
                    value={fontSize}
                    onChange={(e) => onFontSizeChange(parseInt(e.target.value, 10))}
                    disabled={disabled}
                    className="range-input"
                  />
                </div>

                <div className="color-pickers">
                  <div>
                    <label className="control-label">Text Color:</label>
                    <input
                      type="color"
                      value={textColor}
                      onChange={(e) => onTextColorChange(e.target.value)}
                      disabled={disabled}
                      className="color-input"
                    />
                  </div>
                  <div>
                    <label className="control-label">Outline Color:</label>
                    <input
                      type="color"
                      value={strokeColor}
                      onChange={(e) => onStrokeColorChange(e.target.value)}
                      disabled={disabled}
                      className="color-input"
                    />
                  </div>
                </div>
              </div>
            )}

            <div className="form-row emoji-section">
              <label className="control-label">Add Emoji Overlay:</label>
              <div className="emoji-quick-pills">
                {QUICK_EMOJIS.map((em) => (
                  <button
                    key={em}
                    type="button"
                    className={`emoji-pill ${selectedEmoji === em ? 'active' : ''}`}
                    onClick={() => onSelectedEmojiChange(selectedEmoji === em ? '' : em)}
                    disabled={disabled}
                  >
                    {em}
                  </button>
                ))}
                {selectedEmoji && (
                  <button
                    type="button"
                    className="clear-emoji-btn"
                    onClick={() => onSelectedEmojiChange('')}
                    disabled={disabled}
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Cutout & Outline */}
        {activeTab === 'cutout' && (
          <div className="cutout-panel">
            <label className="toggle-card">
              <input
                type="checkbox"
                checked={removeBg}
                onChange={(e) => onRemoveBgChange(e.target.checked)}
                disabled={disabled || !cutoutAvail}
              />
              <span className="toggle-label">
                <strong>✂️ Remove Background (Cutout)</strong>
                <small>
                  {cutoutAvail
                    ? 'AI cutout removes background for transparent sticker'
                    : 'AI cutout module unavailable in current environment'}
                </small>
              </span>
            </label>

            <div className="outline-controls">
              <label className="control-label">
                Sticker White Outline: {outlinePx}px
              </label>
              <input
                type="range"
                min={0}
                max={12}
                step={1}
                value={outlinePx}
                onChange={(e) => onOutlinePxChange(parseInt(e.target.value, 10))}
                disabled={disabled}
                className="range-input"
              />
              <span className="control-hint">
                Adds a classic die-cut white border around transparent elements.
              </span>
            </div>

            {outlinePx > 0 && (
              <div className="outline-controls">
                <label className="control-label">Edge Feathering: {feather}px</label>
                <input
                  type="range"
                  min={0}
                  max={4}
                  step={1}
                  value={feather}
                  onChange={(e) => onFeatherChange(parseInt(e.target.value, 10))}
                  disabled={disabled}
                  className="range-input"
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
