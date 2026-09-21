/**
 * SIH26168 Speedometer Gauge Renderer
 * High-resolution dual-needle Canvas speed gauge
 */

class SpeedometerGauge {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.currentSpeed = 0.0;
    this.refSpeed = 0.0;
    this.maxSpeed = 140; // km/h
  }

  update(aiSpeedKmh, refSpeedKmh) {
    this.currentSpeed = aiSpeedKmh;
    this.refSpeed = refSpeedKmh;
    this.draw();
  }

  draw() {
    const width = this.canvas.width;
    const height = this.canvas.height;
    const ctx = this.ctx;

    ctx.clearRect(0, 0, width, height);

    const centerX = width / 2;
    const centerY = height - 15;
    const radius = Math.min(centerX - 15, centerY - 10);

    const startAngle = Math.PI * 0.85;
    const endAngle = Math.PI * 2.15;
    const totalAngle = endAngle - startAngle;

    // Outer Background Arc
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, startAngle, endAngle);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
    ctx.lineWidth = 10;
    ctx.stroke();

    // Active Speed Glow Arc (Cyan)
    const speedRatio = Math.min(1.0, Math.max(0.0, this.currentSpeed / this.maxSpeed));
    const activeAngle = startAngle + speedRatio * totalAngle;

    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, startAngle, activeAngle);
    ctx.strokeStyle = '#00f0ff';
    ctx.lineWidth = 10;
    ctx.shadowColor = '#00f0ff';
    ctx.shadowBlur = 12;
    ctx.stroke();
    ctx.shadowBlur = 0; // reset

    // Draw Major & Minor Ticks
    for (let speed = 0; speed <= this.maxSpeed; speed += 20) {
      const angle = startAngle + (speed / this.maxSpeed) * totalAngle;
      const x1 = centerX + Math.cos(angle) * (radius - 12);
      const y1 = centerY + Math.sin(angle) * (radius - 12);
      const x2 = centerX + Math.cos(angle) * (radius - 2);
      const y2 = centerY + Math.sin(angle) * (radius - 2);

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Tick text
      const tx = centerX + Math.cos(angle) * (radius - 24);
      const ty = centerY + Math.sin(angle) * (radius - 24);
      ctx.fillStyle = '#8a99ad';
      ctx.font = '10px Rajdhani';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(speed.toString(), tx, ty);
    }

    // Draw Reference Speed Needle Marker (Green line)
    const refRatio = Math.min(1.0, Math.max(0.0, this.refSpeed / this.maxSpeed));
    const refAngle = startAngle + refRatio * totalAngle;
    const rx = centerX + Math.cos(refAngle) * (radius + 2);
    const ry = centerY + Math.sin(refAngle) * (radius + 2);
    ctx.beginPath();
    ctx.arc(rx, ry, 4, 0, Math.PI * 2);
    ctx.fillStyle = '#00ff88';
    ctx.shadowColor = '#00ff88';
    ctx.shadowBlur = 6;
    ctx.fill();
    ctx.shadowBlur = 0;

    // Draw AI Speed Needle (Cyan)
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    const nx = centerX + Math.cos(activeAngle) * (radius - 8);
    const ny = centerY + Math.sin(activeAngle) * (radius - 8);
    ctx.lineTo(nx, ny);
    ctx.strokeStyle = '#00f0ff';
    ctx.lineWidth = 3;
    ctx.shadowColor = '#00f0ff';
    ctx.shadowBlur = 8;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Center Hub Pin
    ctx.beginPath();
    ctx.arc(centerX, centerY, 6, 0, Math.PI * 2);
    ctx.fillStyle = '#fff';
    ctx.fill();
  }
}
