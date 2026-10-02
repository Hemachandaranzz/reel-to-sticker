import React, { useState, useRef, useEffect, useCallback } from 'react';

export default function CropBox({
  videoWidth,
  videoHeight,
  containerWidth,
  containerHeight,
  cropMode, // 'contain' | 'cover' | 'custom'
  onCropModeChange,
  cropParams, // { x: 0, y: 0, size: 1.0 } normalized (0 to 1)
  onCropParamsChange,
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ mouseX: 0, mouseY: 0, cropX: 0, cropY: 0 });
  const boxRef = useRef(null);

  // Compute displayed video size inside container preserving aspect ratio
  const videoAspect = videoWidth && videoHeight ? videoWidth / videoHeight : 16 / 9;
  const containerAspect = containerWidth && containerHeight ? containerWidth / containerHeight : 1;

  let renderWidth = containerWidth;
  let renderHeight = containerHeight;
  let offsetX = 0;
  let offsetY = 0;

  if (videoAspect > containerAspect) {
    renderHeight = containerWidth / videoAspect;
    offsetY = (containerHeight - renderHeight) / 2;
  } else {
    renderWidth = containerHeight * videoAspect;
    offsetX = (containerWidth - renderWidth) / 2;
  }

  // Pixel dimensions of crop box inside rendered video
  const minDim = Math.min(renderWidth, renderHeight);
  const boxPixelSize = cropParams.size * minDim;
  const boxPixelX = offsetX + cropParams.x * renderWidth;
  const boxPixelY = offsetY + cropParams.y * renderHeight;

  const handleMouseDown = (e) => {
    if (cropMode !== 'custom') {
      onCropModeChange('custom');
    }
    setIsDragging(true);
    setDragStart({
      mouseX: e.clientX,
      mouseY: e.clientY,
      cropX: cropParams.x,
      cropY: cropParams.y,
    });
  };

  const handleMouseMove = useCallback(
    (e) => {
      if (!isDragging) return;

      const deltaX = (e.clientX - dragStart.mouseX) / renderWidth;
      const deltaY = (e.clientY - dragStart.mouseY) / renderHeight;

      const maxCropX = 1 - (cropParams.size * minDim) / renderWidth;
      const maxCropY = 1 - (cropParams.size * minDim) / renderHeight;

      const newX = Math.max(0, Math.min(maxCropX, dragStart.cropX + deltaX));
      const newY = Math.max(0, Math.min(maxCropY, dragStart.cropY + deltaY));

      onCropParamsChange({
        ...cropParams,
        x: Number(newX.toFixed(3)),
        y: Number(newY.toFixed(3)),
      });
    },
    [isDragging, dragStart, renderWidth, renderHeight, cropParams, minDim, onCropParamsChange]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return (
    <div className="crop-controls-wrapper">
      <div className="crop-mode-buttons">
        <button
          type="button"
          className={`mode-btn ${cropMode === 'contain' ? 'active' : ''}`}
          onClick={() => onCropModeChange('contain')}
        >
          🖼️ Fit (Pad)
        </button>
        <button
          type="button"
          className={`mode-btn ${cropMode === 'cover' ? 'active' : ''}`}
          onClick={() => onCropModeChange('cover')}
        >
          ✂️ Fill (Center Crop)
        </button>
        <button
          type="button"
          className={`mode-btn ${cropMode === 'custom' ? 'active' : ''}`}
          onClick={() => onCropModeChange('custom')}
        >
          📐 Custom Square
        </button>
      </div>

      {cropMode === 'custom' && (
        <div
          className="crop-overlay-container"
          style={{ width: containerWidth, height: containerHeight }}
        >
          <div
            ref={boxRef}
            className={`crop-box ${isDragging ? 'dragging' : ''}`}
            style={{
              left: `${boxPixelX}px`,
              top: `${boxPixelY}px`,
              width: `${boxPixelSize}px`,
              height: `${boxPixelSize}px`,
            }}
            onMouseDown={handleMouseDown}
          >
            <div className="crop-grid">
              <div className="grid-line horizontal h1" />
              <div className="grid-line horizontal h2" />
              <div className="grid-line vertical v1" />
              <div className="grid-line vertical v2" />
            </div>
            <span className="crop-drag-label">Drag to position 1:1</span>
          </div>
        </div>
      )}
    </div>
  );
}
