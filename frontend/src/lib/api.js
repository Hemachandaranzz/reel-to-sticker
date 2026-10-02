/**
 * API client for Reel -> WhatsApp Sticker backend
 */

export async function probeVideo(file, signal) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch('/api/probe', {
    method: 'POST',
    body: formData,
    signal,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Probe failed: HTTP ${res.status}`);
  }

  return res.json();
}

export async function getStickerCapabilities(signal) {
  try {
    const res = await fetch('/api/sticker/capabilities', { signal });
    if (!res.ok) return { cutout_available: false, outline_available: true };
    return res.json();
  } catch {
    return { cutout_available: false, outline_available: true };
  }
}

export async function createStaticSticker(params, signal) {
  const {
    file,
    second = 0.0,
    fit = 'contain',
    crop_x,
    crop_y,
    crop_size,
    preset = 'balanced',
    remove_bg = false,
    outline_px = 0,
    feather = 0,
    flip_h = false,
    text,
    font_family = 'impact',
    font_size = 38,
    text_color = '#ffffff',
    stroke_color = '#000000',
    stroke_width = 3,
    text_y,
    emoji,
    emoji_y,
  } = params;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('second', String(second));
  formData.append('fit', fit);
  formData.append('preset', preset);
  formData.append('remove_bg', String(Boolean(remove_bg)));
  formData.append('outline_px', String(outline_px || 0));
  formData.append('feather', String(feather || 0));
  formData.append('flip_h', String(Boolean(flip_h)));

  if (crop_size != null && crop_x != null && crop_y != null) {
    formData.append('crop_x', String(crop_x));
    formData.append('crop_y', String(crop_y));
    formData.append('crop_size', String(crop_size));
  }

  if (text) formData.append('text', text);
  if (font_family) formData.append('font_family', font_family);
  if (font_size) formData.append('font_size', String(font_size));
  if (text_color) formData.append('text_color', text_color);
  if (stroke_color) formData.append('stroke_color', stroke_color);
  if (stroke_width != null) formData.append('stroke_width', String(stroke_width));
  if (text_y != null) formData.append('text_y', String(text_y));
  if (emoji) formData.append('emoji', emoji);
  if (emoji_y != null) formData.append('emoji_y', String(emoji_y));

  const res = await fetch('/api/sticker/static', {
    method: 'POST',
    body: formData,
    signal,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Conversion failed: HTTP ${res.status}`);
  }

  const blob = await res.blob();
  return {
    blob,
    size: Number(res.headers.get('X-Sticker-Size')) || blob.size,
    quality: Number(res.headers.get('X-Sticker-Quality')) || null,
  };
}

export async function createAnimatedSticker(params, signal) {
  const {
    file,
    start = 0.0,
    duration = 3.0,
    fit = 'contain',
    speed = 1.0,
    crop_x,
    crop_y,
    crop_size,
    preset = 'balanced',
    flip_h = false,
    reverse = false,
    boomerang = false,
    text,
    font_family = 'impact',
    font_size = 38,
    text_color = '#ffffff',
    stroke_color = '#000000',
    stroke_width = 3,
    text_y,
    emoji,
    emoji_y,
  } = params;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('start', String(start));
  formData.append('duration', String(duration));
  formData.append('fit', fit);
  formData.append('speed', String(speed));
  formData.append('preset', preset);
  formData.append('flip_h', String(Boolean(flip_h)));
  formData.append('reverse', String(Boolean(reverse)));
  formData.append('boomerang', String(Boolean(boomerang)));

  if (crop_size != null && crop_x != null && crop_y != null) {
    formData.append('crop_x', String(crop_x));
    formData.append('crop_y', String(crop_y));
    formData.append('crop_size', String(crop_size));
  }

  if (text) formData.append('text', text);
  if (font_family) formData.append('font_family', font_family);
  if (font_size) formData.append('font_size', String(font_size));
  if (text_color) formData.append('text_color', text_color);
  if (stroke_color) formData.append('stroke_color', stroke_color);
  if (stroke_width != null) formData.append('stroke_width', String(stroke_width));
  if (text_y != null) formData.append('text_y', String(text_y));
  if (emoji) formData.append('emoji', emoji);
  if (emoji_y != null) formData.append('emoji_y', String(emoji_y));

  const res = await fetch('/api/sticker/animated', {
    method: 'POST',
    body: formData,
    signal,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Conversion failed: HTTP ${res.status}`);
  }

  const blob = await res.blob();
  return {
    blob,
    size: Number(res.headers.get('X-Sticker-Size')) || blob.size,
    quality: Number(res.headers.get('X-Sticker-Quality')) || null,
    fps: Number(res.headers.get('X-Sticker-Fps')) || null,
    duration: Number(res.headers.get('X-Sticker-Duration')) || null,
    frames: Number(res.headers.get('X-Sticker-Frames')) || null,
  };
}

export async function checkReelUrl(url, signal) {
  const res = await fetch('/api/reel/check', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
    signal,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `URL check failed: HTTP ${res.status}`);
  }

  return res.json();
}

export async function downloadReelVideo(url, signal) {
  const res = await fetch('/api/reel/download', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
    signal,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Download failed: HTTP ${res.status}`);
  }

  const blob = await res.blob();
  const duration = parseFloat(res.headers.get('X-Video-Duration')) || null;
  const width = parseInt(res.headers.get('X-Video-Width'), 10) || null;
  const height = parseInt(res.headers.get('X-Video-Height'), 10) || null;
  const fps = parseFloat(res.headers.get('X-Video-Fps')) || null;

  return {
    blob,
    metadata: duration && width ? { duration, width, height, fps } : null,
  };
}

export async function convertWebpToGif(webpBlob, signal) {
  const formData = new FormData();
  formData.append('file', webpBlob, 'sticker.webp');

  const res = await fetch('/api/sticker/convert-to-gif', {
    method: 'POST',
    body: formData,
    signal,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `GIF conversion failed: HTTP ${res.status}`);
  }

  const blob = await res.blob();
  return {
    blob,
    size: Number(res.headers.get('X-Sticker-Size')) || blob.size,
  };
}

export async function convertWebpToMp4(webpBlob, signal) {
  const formData = new FormData();
  formData.append('file', webpBlob, 'sticker.webp');

  const res = await fetch('/api/sticker/convert-to-mp4', {
    method: 'POST',
    body: formData,
    signal,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `MP4 conversion failed: HTTP ${res.status}`);
  }

  const blob = await res.blob();
  return {
    blob,
    size: Number(res.headers.get('X-Sticker-Size')) || blob.size,
  };
}


