import React, { useState, useEffect, useRef, useCallback } from 'react';
import { formatDuration } from '../lib/format';

export default function Trimmer({
  file,
  duration,
  mode,
  // Static mode prop
  second,
  onSecondChange,
  // Animated mode props
  start,
  onStartChange,
  clipDuration,
  onClipDurationChange,
  // Video ref communication
  videoRef,
}) {
  const [thumbnails, setThumbnails] = useState([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const timelineRef = useRef(null);

  // Generate ~8 client-side thumbnails from the video file
  useEffect(() => {
    if (!file || !duration || duration <= 0) return;

    let isCancelled = false;
    const videoUrl = URL.createObjectURL(file);
    const hiddenVideo = document.createElement('video');
    hiddenVideo.src = videoUrl;
    hiddenVideo.crossOrigin = 'anonymous';
    hiddenVideo.muted = true;
    hiddenVideo.playsInline = true;

    const canvas = document.createElement('canvas');
    canvas.width = 96;
    canvas.height = 72;
    const ctx = canvas.getContext('2d');

    const numThumbs = Math.min(8, Math.max(4, Math.floor(duration)));
    const step = duration / Math.max(1, numThumbs);
    const times = [];
    for (let i = 0; i < numThumbs; i++) {
      times.push(Math.min(duration - 0.05, i * step + step * 0.1));
    }

    const thumbs = [];

    const captureThumb = (idx) => {
      if (isCancelled || idx >= times.length) {
        if (!isCancelled && thumbs.length > 0) {
          setThumbnails(thumbs);
        }
        URL.revokeObjectURL(videoUrl);
        return;
      }

      hiddenVideo.currentTime = times[idx];
      const onSeeked = () => {
        hiddenVideo.removeEventListener('seeked', onSeeked);
        if (isCancelled) return;
        try {
          ctx.drawImage(hiddenVideo, 0, 0, canvas.width, canvas.height);
          thumbs.push(canvas.toDataURL('image/jpeg', 0.6));
        } catch (e) {
          // ignore CORS / extraction issues
        }
        captureThumb(idx + 1);
      };

      hiddenVideo.addEventListener('seeked', onSeeked);
    };

    hiddenVideo.onloadedmetadata = () => {
      if (!isCancelled) {
        captureThumb(0);
      }
    };

    return () => {
      isCancelled = true;
      URL.revokeObjectURL(videoUrl);
    };
  }, [file, duration]);

  // Video loop handling for animated range preview
  const handleTimeUpdate = useCallback(() => {
    if (!videoRef.current) return;
    const curr = videoRef.current.currentTime;
    setCurrentTime(curr);

    if (mode === 'animated') {
      const end = start + clipDuration;
      if (curr >= end || curr < start) {
        videoRef.current.currentTime = start;
      }
    }
  }, [mode, start, clipDuration, videoRef]);

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;

    v.addEventListener('timeupdate', handleTimeUpdate);
    return () => {
      v.removeEventListener('timeupdate', handleTimeUpdate);
    };
  }, [handleTimeUpdate, videoRef]);

  // Sync video time when user changes start or second
  useEffect(() => {
    if (!videoRef.current) return;
    if (mode === 'static') {
      videoRef.current.currentTime = second;
    } else {
      videoRef.current.currentTime = start;
    }
  }, [mode, second, start, videoRef]);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      if (mode === 'animated' && (videoRef.current.currentTime >= start + clipDuration || videoRef.current.currentTime < start)) {
        videoRef.current.currentTime = start;
      }
      videoRef.current.play();
      setIsPlaying(true);
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  // Keyboard navigation: ArrowLeft/Right nudges by 0.1s
  const handleKeyDown = (e) => {
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      if (mode === 'static') {
        onSecondChange(Math.max(0, Number((second - 0.1).toFixed(2))));
      } else {
        onStartChange(Math.max(0, Number((start - 0.1).toFixed(2))));
      }
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      if (mode === 'static') {
        onSecondChange(Math.min(duration, Number((second + 0.1).toFixed(2))));
      } else {
        const maxStart = Math.max(0, duration - clipDuration);
        onStartChange(Math.min(maxStart, Number((start + 0.1).toFixed(2))));
      }
    } else if (e.key === ' ') {
      e.preventDefault();
      togglePlay();
    }
  };

  // Timeline click to scrub
  const handleTimelineClick = (e) => {
    if (!timelineRef.current || duration <= 0) return;
    const rect = timelineRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const fraction = Math.max(0, Math.min(1, clickX / rect.width));
    const targetSec = Number((fraction * duration).toFixed(2));

    if (mode === 'static') {
      onSecondChange(targetSec);
    } else {
      const maxStart = Math.max(0, duration - clipDuration);
      onStartChange(Math.min(maxStart, targetSec));
    }
  };

  // Animated mode: dual handle adjustments
  const handleStartSlider = (e) => {
    const newStart = parseFloat(e.target.value);
    const maxStart = Math.max(0, duration - 0.5);
    const clampedStart = Math.min(maxStart, newStart);
    onStartChange(clampedStart);

    // Keep duration within bounds and under 10s
    if (clampedStart + clipDuration > duration) {
      onClipDurationChange(Math.max(0.5, Number((duration - clampedStart).toFixed(1))));
    }
  };

  const handleDurationSlider = (e) => {
    const newDur = parseFloat(e.target.value);
    const maxAllowed = Math.min(10.0, duration - start);
    onClipDurationChange(Math.min(maxAllowed, Math.max(0.5, newDur)));
  };

  const end = Math.min(duration, start + clipDuration);
  const startPercent = duration > 0 ? (start / duration) * 100 : 0;
  const widthPercent = duration > 0 ? (clipDuration / duration) * 100 : 0;
  const secondPercent = duration > 0 ? (second / duration) * 100 : 0;

  return (
    <div className="trimmer-component" onKeyDown={handleKeyDown} tabIndex={0}>
      <div className="trimmer-header">
        <button
          type="button"
          className="play-toggle-btn"
          onClick={togglePlay}
          aria-label={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? '⏸️ Pause' : '▶️ Play'}
        </button>

        <div className="time-display">
          <span>{formatDuration(currentTime)}</span> / <span>{formatDuration(duration)}</span>
        </div>

        {mode === 'animated' ? (
          <span className={`duration-badge ${clipDuration > 8 ? 'warning' : ''}`}>
            Range: {clipDuration.toFixed(1)}s (Max 10s)
          </span>
        ) : (
          <span className="duration-badge">
            Frame at: {second.toFixed(2)}s
          </span>
        )}
      </div>

      {/* Thumbnail Timeline */}
      <div
        className="timeline-container"
        ref={timelineRef}
        onClick={handleTimelineClick}
      >
        <div className="thumbnails-track">
          {thumbnails.map((src, i) => (
            <img key={i} src={src} alt={`frame-${i}`} className="thumb-img" />
          ))}
        </div>

        {/* Static Mode Scrubber Line */}
        {mode === 'static' ? (
          <div
            className="scrubber-line"
            style={{ left: `${secondPercent}%` }}
          >
            <div className="scrubber-handle">📍</div>
          </div>
        ) : (
          /* Animated Mode Range Overlay */
          <div
            className="range-highlight"
            style={{
              left: `${startPercent}%`,
              width: `${Math.min(100 - startPercent, widthPercent)}%`,
            }}
          >
            <div className="range-handle left" title="Start" />
            <div className="range-handle right" title="End" />
          </div>
        )}
      </div>

      {/* Interactive Controls */}
      {mode === 'static' ? (
        <div className="slider-row">
          <input
            type="range"
            min={0}
            max={duration}
            step={0.05}
            value={second}
            onChange={(e) => onSecondChange(parseFloat(e.target.value))}
            className="range-slider"
          />
          <button
            type="button"
            className="use-frame-btn"
            onClick={() => onSecondChange(Number(currentTime.toFixed(2)))}
          >
            📌 Use Current Frame
          </button>
        </div>
      ) : (
        <div className="animated-slider-controls">
          <div className="slider-item">
            <label className="slider-label">Start Position: {start.toFixed(1)}s</label>
            <input
              type="range"
              min={0}
              max={Math.max(0, duration - 0.5)}
              step={0.1}
              value={start}
              onChange={handleStartSlider}
              className="range-slider"
            />
          </div>

          <div className="slider-item">
            <label className="slider-label">Clip Length: {clipDuration.toFixed(1)}s</label>
            <input
              type="range"
              min={0.5}
              max={Math.min(10.0, Math.max(0.5, duration - start))}
              step={0.25}
              value={clipDuration}
              onChange={handleDurationSlider}
              className="range-slider"
            />
          </div>
        </div>
      )}
    </div>
  );
}
