import React, { useState, useRef, useEffect, useMemo } from 'react';
import Dropzone from './components/Dropzone';
import ModeTabs from './components/ModeTabs';
import Trimmer from './components/Trimmer';
import CropBox from './components/CropBox';
import Presets from './components/Presets';
import Preview from './components/Preview';
import EffectsStudio from './components/EffectsStudio';
import ReelInput from './components/ReelInput';
import PackBuilder from './components/PackBuilder';
import LegalModal from './components/LegalModal';
import { addStickerToPack } from './lib/packDb';
import {
  probeVideo,
  createStaticSticker,
  createAnimatedSticker,
  getStickerCapabilities,
} from './lib/api';
import { formatDuration } from './lib/format';
import './App.css';

export default function App() {
  const [file, setFile] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [mode, setMode] = useState('static'); // 'static' | 'animated'
  const [cropMode, setCropMode] = useState('contain'); // 'contain' | 'cover' | 'custom'
  const [cropParams, setCropParams] = useState({ x: 0.1, y: 0.1, size: 0.8 });
  const [preset, setPreset] = useState('balanced'); // 'smallest' | 'balanced' | 'best'

  // Static controls
  const [second, setSecond] = useState(0.0);

  // Animated controls
  const [start, setStart] = useState(0.0);
  const [duration, setDuration] = useState(3.0);
  const [speed, setSpeed] = useState(1.0);

  // Effects & Cutout states
  const [capabilities, setCapabilities] = useState({ cutout_available: false, outline_available: true });
  const [removeBg, setRemoveBg] = useState(false);
  const [outlinePx, setOutlinePx] = useState(0);
  const [feather, setFeather] = useState(0);
  const [flipH, setFlipH] = useState(false);
  const [reverse, setReverse] = useState(false);
  const [boomerang, setBoomerang] = useState(false);
  const [captionText, setCaptionText] = useState('');
  const [fontFamily, setFontFamily] = useState('impact');
  const [fontSize, setFontSize] = useState(38);
  const [textColor, setTextColor] = useState('#ffffff');
  const [strokeColor, setStrokeColor] = useState('#000000');
  const [textPos, setTextPos] = useState('bottom');
  const [selectedEmoji, setSelectedEmoji] = useState('');

  // Status & output
  const [isProbing, setIsProbing] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [legalModalOpen, setLegalModalOpen] = useState(false);
  const [legalTab, setLegalTab] = useState('privacy');

  // Load capabilities once on mount
  useEffect(() => {
    getStickerCapabilities().then(setCapabilities).catch(() => {});
  }, []);

  // Refs
  const videoRef = useRef(null);
  const videoContainerRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Container dimensions for crop box overlay
  const [containerDims, setContainerDims] = useState({ width: 320, height: 240 });

  // Generate object URL for video preview
  const videoUrl = useMemo(() => {
    return file ? URL.createObjectURL(file) : null;
  }, [file]);

  useEffect(() => {
    return () => {
      if (videoUrl) URL.revokeObjectURL(videoUrl);
    };
  }, [videoUrl]);

  // Clean up sticker object URL
  useEffect(() => {
    return () => {
      if (result?.url) URL.revokeObjectURL(result.url);
    };
  }, [result]);

  // Measure container for crop overlay
  useEffect(() => {
    if (videoContainerRef.current) {
      const { clientWidth, clientHeight } = videoContainerRef.current;
      if (clientWidth && clientHeight) {
        setContainerDims({ width: clientWidth, height: clientHeight });
      }
    }
  }, [metadata]);

  const handleFileSelected = async (selectedFile) => {
    if (!selectedFile) return;

    setError(null);
    setResult(null);
    setFile(selectedFile);
    setMetadata(null);
    setIsProbing(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const probed = await probeVideo(selectedFile, controller.signal);
      setMetadata(probed);
      setSecond(0.0);
      setStart(0.0);
      setDuration(Math.min(3.0, probed.duration));
      setCropMode('contain');
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Failed to analyze video.');
        setFile(null);
      }
    } finally {
      setIsProbing(false);
      abortControllerRef.current = null;
    }
  };

  const handleConvert = async (overridePreset = null) => {
    if (!file || !metadata) return;

    const activePreset = overridePreset || preset;
    setError(null);
    setIsConverting(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Prepare crop args if custom mode
    const isCustomCrop = cropMode === 'custom';
    const cropPayload = isCustomCrop
      ? { crop_x: cropParams.x, crop_y: cropParams.y, crop_size: cropParams.size }
      : {};

    const fitParam = isCustomCrop ? 'contain' : cropMode;

    try {
      let conversionResult;
      const textYNorm = textPos === 'top' ? 0.12 : textPos === 'center' ? 0.5 : 0.88;
      const emojiYNorm = textPos === 'top' ? 0.82 : 0.15;
      const hasText = Boolean(captionText.trim());

      if (mode === 'static') {
        conversionResult = await createStaticSticker(
          {
            file,
            second: parseFloat(second) || 0.0,
            fit: fitParam,
            preset: activePreset,
            remove_bg: removeBg,
            outline_px: outlinePx,
            feather,
            flip_h: flipH,
            text: hasText ? captionText.trim() : undefined,
            font_family: fontFamily,
            font_size: fontSize,
            text_color: textColor,
            stroke_color: strokeColor,
            stroke_width: 3,
            text_y: textYNorm,
            emoji: selectedEmoji || undefined,
            emoji_y: emojiYNorm,
            ...cropPayload,
          },
          controller.signal
        );
      } else {
        conversionResult = await createAnimatedSticker(
          {
            file,
            start: parseFloat(start) || 0.0,
            duration: parseFloat(duration) || 3.0,
            fit: fitParam,
            speed: parseFloat(speed) || 1.0,
            preset: activePreset,
            flip_h: flipH,
            reverse,
            boomerang,
            text: hasText ? captionText.trim() : undefined,
            font_family: fontFamily,
            font_size: fontSize,
            text_color: textColor,
            stroke_color: strokeColor,
            stroke_width: 3,
            text_y: textYNorm,
            emoji: selectedEmoji || undefined,
            emoji_y: emojiYNorm,
            ...cropPayload,
          },
          controller.signal
        );
      }

      const url = URL.createObjectURL(conversionResult.blob);
      setResult({
        ...conversionResult,
        url,
      });
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Failed to generate sticker.');
      }
    } finally {
      setIsConverting(false);
      abortControllerRef.current = null;
    }
  };

  const handleTrySmaller = () => {
    setPreset('smallest');
    handleConvert('smallest');
  };

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsConverting(false);
      setIsProbing(false);
      setError('Operation canceled by user.');
    }
  };

  const [packRefreshKey, setPackRefreshKey] = useState(0);
  const [packMessage, setPackMessage] = useState(null);

  const handleAddToPack = async (blob, stickerMode) => {
    try {
      await addStickerToPack({
        blob,
        mode: stickerMode,
        emojis: selectedEmoji ? [selectedEmoji] : ['✨'],
      });
      setPackRefreshKey((k) => k + 1);
      setPackMessage('Sticker successfully added to your pack! 📦');
      setTimeout(() => setPackMessage(null), 4000);
    } catch (e) {
      console.error(e);
      setError('Failed to save sticker to pack.');
    }
  };

  const handleReset = () => {
    if (result?.url) URL.revokeObjectURL(result.url);
    setFile(null);
    setMetadata(null);
    setResult(null);
    setError(null);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-badge">WhatsApp Sticker Maker</div>
        <h1>Reel &amp; Video → WhatsApp Sticker</h1>
        <p className="subtitle">
          Create WhatsApp-ready 512×512 WebP stickers with visual trimming &amp; custom framing.
        </p>
      </header>

      <main className="main-content">
        {/* Instagram Reel Link Checker */}
        {!file && (
          <section className="section-card">
            <ReelInput disabled={isProbing || isConverting} />
          </section>
        )}

        {/* Upload Dropzone */}
        <section className="section-card">
          <Dropzone
            onFileSelected={handleFileSelected}
            selectedFile={file}
            disabled={isProbing || isConverting}
          />

          {isProbing && (
            <div className="status-banner info">
              <span className="spinner" /> Analyzing video format and timeline...
            </div>
          )}

          {metadata && (
            <div className="metadata-bar">
              <span className="meta-tag">
                ⏱️ Duration: <strong>{formatDuration(metadata.duration)}</strong>
              </span>
              <span className="meta-tag">
                📐 Native: <strong>{metadata.width} × {metadata.height}</strong>
              </span>
              <span className="meta-tag">
                ⚡ FPS: <strong>{metadata.fps}</strong>
              </span>
            </div>
          )}
        </section>

        {error && (
          <div className="status-banner error" role="alert">
            <span className="error-icon">⚠️</span>
            <div className="error-message">
              <strong>Error:</strong> {error}
            </div>
          </div>
        )}

        {/* Video Player & Editor Studio */}
        {metadata && videoUrl && (
          <section className="section-card editor-card">
            <ModeTabs
              mode={mode}
              onChange={(m) => {
                setMode(m);
                setResult(null);
              }}
              disabled={isConverting}
            />

            {/* Live Video Preview with Crop Overlay */}
            <div className="video-player-wrapper" ref={videoContainerRef}>
              <video
                ref={videoRef}
                src={videoUrl}
                playsInline
                muted
                className={`main-video-player ${flipH ? 'flipped-h' : ''}`}
              />

              {selectedEmoji && (
                <div className="live-emoji-overlay">{selectedEmoji}</div>
              )}

              {captionText.trim() && (
                <div
                  className={`live-caption-overlay ${textPos}`}
                  style={{
                    fontFamily:
                      fontFamily === 'impact'
                        ? 'Impact, sans-serif'
                        : fontFamily === 'comic'
                        ? '"Comic Sans MS", cursive'
                        : 'sans-serif',
                    fontSize: `${Math.round(fontSize * 0.7)}px`,
                    color: textColor,
                    WebkitTextStroke: `2px ${strokeColor}`,
                    textShadow: `0 0 4px ${strokeColor}`,
                  }}
                >
                  {captionText}
                </div>
              )}

              <CropBox
                videoWidth={metadata.width}
                videoHeight={metadata.height}
                containerWidth={containerDims.width}
                containerHeight={containerDims.height}
                cropMode={cropMode}
                onCropModeChange={setCropMode}
                cropParams={cropParams}
                onCropParamsChange={setCropParams}
              />
            </div>

            {/* Visual Timeline & Trimmer */}
            <Trimmer
              file={file}
              duration={metadata.duration}
              mode={mode}
              second={second}
              onSecondChange={setSecond}
              start={start}
              onStartChange={setStart}
              clipDuration={duration}
              onClipDurationChange={setDuration}
              videoRef={videoRef}
            />

            {/* Effects & Customization Studio */}
            <EffectsStudio
              mode={mode}
              capabilities={capabilities}
              removeBg={removeBg}
              onRemoveBgChange={setRemoveBg}
              outlinePx={outlinePx}
              onOutlinePxChange={setOutlinePx}
              feather={feather}
              onFeatherChange={setFeather}
              flipH={flipH}
              onFlipHChange={setFlipH}
              reverse={reverse}
              onReverseChange={setReverse}
              boomerang={boomerang}
              onBoomerangChange={setBoomerang}
              captionText={captionText}
              onCaptionTextChange={setCaptionText}
              fontFamily={fontFamily}
              onFontFamilyChange={setFontFamily}
              fontSize={fontSize}
              onFontSizeChange={setFontSize}
              textColor={textColor}
              onTextColorChange={setTextColor}
              strokeColor={strokeColor}
              onStrokeColorChange={setStrokeColor}
              textPos={textPos}
              onTextPosChange={setTextPos}
              selectedEmoji={selectedEmoji}
              onSelectedEmojiChange={setSelectedEmoji}
              disabled={isConverting}
            />

            {/* Quality Presets */}
            <Presets
              selectedPreset={preset}
              onSelectPreset={setPreset}
              disabled={isConverting}
            />

            {/* Speed & duration advice */}
            {mode === 'animated' && (
              <div className="animated-extras">
                <div className="speed-selector">
                  <label className="control-label">Playback Speed: {speed}x</label>
                  <input
                    type="range"
                    min={0.5}
                    max={2.0}
                    step={0.25}
                    value={speed}
                    onChange={(e) => setSpeed(parseFloat(e.target.value))}
                    disabled={isConverting}
                    className="range-input"
                  />
                </div>

                {duration > 6.0 && (
                  <div className="advice-pill">
                    ⚠️ Clip duration ({duration.toFixed(1)}s) is on the longer side.
                    The optimizer may lower FPS to guarantee the ≤ 500 KB WhatsApp limit.
                  </div>
                )}
              </div>
            )}

            {/* Action Row */}
            <div className="action-row">
              {isConverting ? (
                <button
                  type="button"
                  className="cancel-btn"
                  onClick={handleCancel}
                >
                  Cancel Conversion
                </button>
              ) : (
                <button
                  type="button"
                  className="convert-btn"
                  onClick={() => handleConvert()}
                >
                  🚀 Convert to 512×512 WhatsApp Sticker
                </button>
              )}
            </div>

            {isConverting && (
              <div className="conversion-status">
                <span className="spinner" />
                <span>
                  Optimizing {mode} sticker to meet WhatsApp limit (
                  {mode === 'static' ? '≤ 100 KB' : '≤ 500 KB'})...
                </span>
              </div>
            )}
          </section>
        )}

        {packMessage && (
          <div className="status-banner info">
            {packMessage}
          </div>
        )}

        {/* Result Preview */}
        {result && (
          <section className="section-card preview-section">
            <Preview
              result={result}
              mode={mode}
              onReset={handleReset}
              onTrySmaller={handleTrySmaller}
              onAddToPack={handleAddToPack}
            />
          </section>
        )}

        {/* Sticker Pack Builder */}
        <section className="section-card">
          <PackBuilder onRefreshRequired={packRefreshKey} />
        </section>
      </main>

      <footer className="app-footer">
        <p>
          WhatsApp sticker standards: 512×512 WebP • Static ≤ 100 KB • Animated ≤ 500 KB, ≤ 10s.
        </p>
        <div className="footer-links">
          <button
            type="button"
            className="footer-link-btn"
            onClick={() => {
              setLegalTab('privacy');
              setLegalModalOpen(true);
            }}
          >
            Privacy Policy
          </button>
          <span>•</span>
          <button
            type="button"
            className="footer-link-btn"
            onClick={() => {
              setLegalTab('terms');
              setLegalModalOpen(true);
            }}
          >
            Terms &amp; Disclaimers
          </button>
        </div>
      </footer>

      <LegalModal
        isOpen={legalModalOpen}
        initialTab={legalTab}
        onClose={() => setLegalModalOpen(false)}
      />
    </div>
  );
}
