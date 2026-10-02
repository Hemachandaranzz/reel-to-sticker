import React from 'react';

export const PRESETS = {
  smallest: {
    id: 'smallest',
    name: 'Smallest File',
    desc: 'Faster send • ~8 FPS',
    icon: '⚡',
  },
  balanced: {
    id: 'balanced',
    name: 'Balanced',
    desc: 'Recommended • ~12 FPS',
    icon: '⚖️',
  },
  best: {
    id: 'best',
    name: 'Best Quality',
    desc: 'Crispest video • ~15 FPS',
    icon: '💎',
  },
};

export default function Presets({ selectedPreset, onSelectPreset, disabled }) {
  return (
    <div className="presets-container">
      <label className="control-label">Quality Preset</label>
      <div className="presets-grid">
        {Object.values(PRESETS).map((p) => (
          <button
            key={p.id}
            type="button"
            className={`preset-card ${selectedPreset === p.id ? 'active' : ''}`}
            onClick={() => onSelectPreset(p.id)}
            disabled={disabled}
          >
            <span className="preset-icon">{p.icon}</span>
            <div className="preset-info">
              <span className="preset-name">{p.name}</span>
              <span className="preset-desc">{p.desc}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
