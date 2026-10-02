import React from 'react';

export default function ModeTabs({ mode, onChange, disabled }) {
  return (
    <div className="mode-tabs" role="tablist">
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'static'}
        className={`tab-btn ${mode === 'static' ? 'active' : ''}`}
        onClick={() => onChange('static')}
        disabled={disabled}
      >
        <span className="tab-title">🖼️ Static Sticker</span>
        <span className="tab-hint">≤ 100 KB • Single Frame</span>
      </button>

      <button
        type="button"
        role="tab"
        aria-selected={mode === 'animated'}
        className={`tab-btn ${mode === 'animated' ? 'active' : ''}`}
        onClick={() => onChange('animated')}
        disabled={disabled}
      >
        <span className="tab-title">✨ Animated Sticker</span>
        <span className="tab-hint">≤ 500 KB • ≤ 10s Loop</span>
      </button>
    </div>
  );
}
