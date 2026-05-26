import { useEffect, useRef } from 'react';
import WebGLFluid from 'webgl-fluid';

const FluidBackground = () => {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (canvasRef.current) {
      WebGLFluid(canvasRef.current, {
        IMMEDIATE: true, // Trigger immediately
        TRIGGER: 'hover', // Can be 'click' or 'hover'
        SIM_RESOLUTION: 128,
        DYE_RESOLUTION: 512,
        DENSITY_DISSIPATION: 1.5,
        VELOCITY_DISSIPATION: 0.2,
        PRESSURE: 0.8,
        PRESSURE_ITERATIONS: 20,
        CURL: 30,
        SPLAT_RADIUS: 0.25,
        SPLAT_FORCE: 6000,
        SHADING: true,
        COLORFUL: true,
        COLOR_UPDATE_SPEED: 10,
        COLOR_PALETTE: ['#6366f1', '#00f2fe', '#10b981'],
        PAUSED: false,
        BACK_COLOR: { r: 0, g: 0, b: 0 },
        TRANSPARENT: true, // We want the existing css background to show through!
        BLOOM: true,
        BLOOM_ITERATIONS: 8,
        BLOOM_RESOLUTION: 256,
        BLOOM_INTENSITY: 0.8,
        BLOOM_THRESHOLD: 0.6,
        BLOOM_SOFT_KNEE: 0.7,
        SUNRAYS: true,
        SUNRAYS_RESOLUTION: 196,
        SUNRAYS_WEIGHT: 1.0,
      });
    }
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 0,
        pointerEvents: 'auto', // Needs pointer events to react to mouse! But it might block clicks? 
        // Wait, if zIndex is 0 and it has pointerEvents: auto, it will receive mouse events only if nothing is above it.
        // Actually, to make it react to mouse without blocking clicks on the UI, the UI must have zIndex higher and pointerEvents: auto, 
        // but wait! If the UI covers the screen, the canvas won't receive hover events.
      }}
    />
  );
};

export default FluidBackground;
