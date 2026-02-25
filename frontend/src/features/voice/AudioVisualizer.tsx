import { useEffect, useRef } from 'react';

interface AudioVisualizerProps {
  isActive: boolean;
  isSpeaking?: boolean;
  className?: string;
}

export function AudioVisualizer({ isActive, isSpeaking = false, className = '' }: AudioVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return () => {};

    const ctx = canvas.getContext('2d');
    if (!ctx) return () => {};

    // Set canvas resolution
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    const barCount = 32;
    const barWidth = width / barCount;

    let phase = 0;

    const draw = () => {
      // Clear canvas
      ctx.fillStyle = 'rgb(24, 24, 27)'; // zinc-950
      ctx.fillRect(0, 0, width, height);

      if (!isActive) {
        // Draw flat line when inactive
        ctx.strokeStyle = 'rgb(63, 63, 70)'; // zinc-700
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, height / 2);
        ctx.lineTo(width, height / 2);
        ctx.stroke();
      } else {
        // Animate bars
        for (let i = 0; i < barCount; i++) {
          const x = i * barWidth;

          // Create wave pattern
          const t = phase + (i / barCount) * Math.PI * 2;
          let barHeight: number;

          if (isSpeaking) {
            // More dynamic animation when AI is speaking
            barHeight = Math.abs(Math.sin(t) * Math.cos(t * 2) * (height / 2));
          } else {
            // Gentler animation when user is recording
            barHeight = Math.abs(Math.sin(t) * (height / 3));
          }

          // Gradient color based on height
          const gradient = ctx.createLinearGradient(x, height / 2 - barHeight, x, height / 2 + barHeight);

          if (isSpeaking) {
            gradient.addColorStop(0, 'rgb(59, 130, 246)'); // blue-500
            gradient.addColorStop(1, 'rgb(37, 99, 235)'); // blue-600
          } else {
            gradient.addColorStop(0, 'rgb(96, 165, 250)'); // blue-400
            gradient.addColorStop(1, 'rgb(59, 130, 246)'); // blue-500
          }

          ctx.fillStyle = gradient;

          // Draw bar
          const y = height / 2 - barHeight;
          const barHeightTotal = barHeight * 2;
          ctx.fillRect(x + 1, y, barWidth - 2, barHeightTotal);
        }

        phase += 0.05;
      }

      animationFrameRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isActive, isSpeaking]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{ width: '100%', height: '100%' }}
    />
  );
}
