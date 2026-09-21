/**
 * SIH26168 Compass Dial Renderer
 * Dynamic rotating compass heading dial on HTML5 Canvas
 */

class CompassDial {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.currentHeadingDeg = 0.0;
  }

  update(headingDeg) {
    this.currentHeadingDeg = headingDeg;
    this.draw();
  }

  getCardinalDirection(deg) {
    const d = (deg % 360 + 360) % 360;
    if (d >= 337.5 || d < 22.5) return 'N';
    if (d >= 22.5 && d < 67.5) return 'NE';
    if (d >= 67.5 && d < 112.5) return 'E';
    if (d >= 112.5 && d < 157.5) return 'SE';
    if (d >= 157.5 && d < 202.5) return 'S';
    if (d >= 202.5 && d < 247.5) return 'SW';
    if (d >= 247.5 && d < 292.5) return 'W';
    return 'NW';
  }

  draw() {
    const width = this.canvas.width;
    const height = this.canvas.height;
    const ctx = this.ctx;

    ctx.clearRect(0, 0, width, height);

    const centerX = width / 2;
    const centerY = height / 2 + 5;
    const radius = Math.min(centerX - 15, centerY - 15);

    // Outer Compass Ring
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.2)';
    ctx.lineWidth = 4;
    ctx.stroke();

    // Rotate context to simulate rotating compass card
    ctx.save();
    ctx.translate(centerX, centerY);
    const rad = (this.currentHeadingDeg * Math.PI) / 180.0;
    ctx.rotate(-rad);

    // Cardinal Points (N, E, S, W)
    const cardinals = [
      { text: 'N', angle: 0, color: '#ff3366' },
      { text: 'E', angle: 90, color: '#00f0ff' },
      { text: 'S', angle: 180, color: '#8a99ad' },
      { text: 'W', angle: 270, color: '#00f0ff' }
    ];

    ctx.font = 'bold 12px Orbitron';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    cardinals.forEach(item => {
      const a = (item.angle - 90) * (Math.PI / 180.0);
      const x = Math.cos(a) * (radius - 14);
      const y = Math.sin(a) * (radius - 14);
      ctx.fillStyle = item.color;
      ctx.fillText(item.text, x, y);
    });

    // Degree tick marks every 30 degrees
    for (let deg = 0; deg < 360; deg += 30) {
      const a = deg * (Math.PI / 180.0);
      const x1 = Math.cos(a) * (radius - 6);
      const y1 = Math.sin(a) * (radius - 6);
      const x2 = Math.cos(a) * (radius - 1);
      const y2 = Math.sin(a) * (radius - 1);

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    ctx.restore();

    // Fixed Top Arrow / Pointer (Vehicle Forward Direction)
    ctx.beginPath();
    ctx.moveTo(centerX, centerY - radius + 4);
    ctx.lineTo(centerX - 6, centerY - radius + 16);
    ctx.lineTo(centerX + 6, centerY - radius + 16);
    ctx.closePath();
    ctx.fillStyle = '#00f0ff';
    ctx.shadowColor = '#00f0ff';
    ctx.shadowBlur = 8;
    ctx.fill();
    ctx.shadowBlur = 0;

    // Center Crosshair
    ctx.beginPath();
    ctx.arc(centerX, centerY, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#fff';
    ctx.fill();
  }
}
