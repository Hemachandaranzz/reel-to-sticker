import { describe, it, expect } from 'vitest';
import { formatBytes, formatDuration } from '../lib/format';

describe('format helpers', () => {
  it('formats bytes properly', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(500)).toBe('500.0 B');
    expect(formatBytes(1024)).toBe('1.0 KB');
    expect(formatBytes(500 * 1024)).toBe('500.0 KB');
    expect(formatBytes(10 * 1024 * 1024)).toBe('10.0 MB');
  });

  it('formats duration properly', () => {
    expect(formatDuration(0)).toBe('0.0s');
    expect(formatDuration(4.5)).toBe('4.5s');
    expect(formatDuration(65)).toBe('1m 5.0s');
    expect(formatDuration(125.8)).toBe('2m 5.8s');
  });
});

describe('pack validation rules', () => {
  it('checks 3-30 sticker count', () => {
    const isCountValid = (count) => count >= 3 && count <= 30;
    expect(isCountValid(0)).toBe(false);
    expect(isCountValid(2)).toBe(false);
    expect(isCountValid(3)).toBe(true);
    expect(isCountValid(15)).toBe(true);
    expect(isCountValid(30)).toBe(true);
    expect(isCountValid(31)).toBe(false);
  });

  it('checks pack uniformity', () => {
    const isUniform = (stickers) => {
      if (stickers.length === 0) return true;
      const first = stickers[0].mode;
      return stickers.every((s) => s.mode === first);
    };

    expect(isUniform([{ mode: 'static' }, { mode: 'static' }, { mode: 'static' }])).toBe(true);
    expect(isUniform([{ mode: 'animated' }, { mode: 'animated' }])).toBe(true);
    expect(isUniform([{ mode: 'static' }, { mode: 'animated' }])).toBe(false);
  });
});
