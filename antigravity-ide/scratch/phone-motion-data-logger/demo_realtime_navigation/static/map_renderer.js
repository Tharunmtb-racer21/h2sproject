/**
 * SIH26168 2D Local ENU Map Canvas Renderer
 * Renders reference trajectory, dead-reckoned trajectory, vehicle heading, and outage zones
 */

class MapRenderer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    
    this.refPath = []; // [[E, N], ...]
    this.drPath = [];  // [[E, N], ...]
    this.outageSegments = []; // [{startIdx, endIdx}, ...]
    
    this.currentPos = { east: 0, north: 0, headingDeg: 0 };
    this.refPos = { east: 0, north: 0 };
    
    // Viewport transform
    this.zoom = 1.0;
    this.autoFollow = true;
    this.bounds = { minE: -500, maxE: 500, minN: -500, maxN: 500 };

    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  resizeCanvas() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width;
    this.canvas.height = rect.height;
    this.draw();
  }

  setReferencePath(pathPoints) {
    this.refPath = pathPoints || [];
    if (this.refPath.length > 0) {
      let minE = Infinity, maxE = -Infinity, minN = Infinity, maxN = -Infinity;
      for (const [e, n] of this.refPath) {
        if (e < minE) minE = e;
        if (e > maxE) maxE = e;
        if (n < minN) minN = n;
        if (n > maxN) maxN = n;
      }
      this.bounds = { minE, maxE, minN, maxN };
    }
    this.draw();
  }

  updateVehicleState(activeEast, activeNorth, refEast, refNorth, headingDeg, isOutage) {
    this.currentPos = { east: activeEast, north: activeNorth, headingDeg, isOutage };
    this.refPos = { east: refEast, north: refNorth };

    // Append to live DR trace
    this.drPath.push([activeEast, activeNorth, isOutage]);
    if (this.drPath.length > 3000) {
      this.drPath.shift();
    }

    this.draw();
  }

  reset() {
    this.drPath = [];
    this.draw();
  }

  zoomIn() {
    this.zoom = Math.min(5.0, this.zoom * 1.3);
    this.draw();
  }

  zoomOut() {
    this.zoom = Math.max(0.2, this.zoom / 1.3);
    this.draw();
  }

  recenter() {
    this.autoFollow = true;
    this.zoom = 1.0;
    this.draw();
  }

  // Convert East/North metres to Screen Pixel coordinates
  worldToScreen(e, n, centerX, centerY, scale) {
    const sx = centerX + (e - this.currentPos.east) * scale;
    const sy = centerY - (n - this.currentPos.north) * scale; // invert Y for screen
    return { x: sx, y: sy };
  }

  draw() {
    const width = this.canvas.width;
    const height = this.canvas.height;
    const ctx = this.ctx;

    ctx.clearRect(0, 0, width, height);

    const centerX = width / 2;
    const centerY = height / 2;

    // Dynamic scale (pixels per metre)
    const baseScale = 0.15; // default scale
    const scale = baseScale * this.zoom;

    // 1. Draw Grid Lines (every 500m / 1000m)
    const gridSpacingMeters = 500;
    const gridPixelSpacing = gridSpacingMeters * scale;

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
    ctx.lineWidth = 1;

    const startX = (centerX % gridPixelSpacing);
    for (let x = startX; x < width; x += gridPixelSpacing) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    const startY = (centerY % gridPixelSpacing);
    for (let y = startY; y < height; y += gridPixelSpacing) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // 2. Draw Full Reference Trajectory (Green)
    if (this.refPath.length > 1) {
      ctx.beginPath();
      const first = this.worldToScreen(this.refPath[0][0], this.refPath[0][1], centerX, centerY, scale);
      ctx.moveTo(first.x, first.y);

      for (let i = 1; i < this.refPath.length; i++) {
        const pt = this.worldToScreen(this.refPath[i][0], this.refPath[i][1], centerX, centerY, scale);
        ctx.lineTo(pt.x, pt.y);
      }

      ctx.strokeStyle = 'rgba(0, 255, 136, 0.4)';
      ctx.lineWidth = 2.5;
      ctx.stroke();
    }

    // 3. Draw Active Dead-Reckoned Trajectory Trail (Cyan / Red during Outage)
    if (this.drPath.length > 1) {
      for (let i = 1; i < this.drPath.length; i++) {
        const p1 = this.worldToScreen(this.drPath[i - 1][0], this.drPath[i - 1][1], centerX, centerY, scale);
        const p2 = this.worldToScreen(this.drPath[i][0], this.drPath[i][1], centerX, centerY, scale);
        const isOutagePt = this.drPath[i][2];

        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.strokeStyle = isOutagePt ? '#ff3366' : '#00f0ff';
        ctx.lineWidth = isOutagePt ? 4 : 3;
        if (isOutagePt) {
          ctx.shadowColor = '#ff3366';
          ctx.shadowBlur = 8;
        }
        ctx.stroke();
        ctx.shadowBlur = 0;
      }
    }

    // 4. Draw Ground Truth Vehicle Reference Marker (Green Dot)
    const refScreen = this.worldToScreen(this.refPos.east, this.refPos.north, centerX, centerY, scale);
    ctx.beginPath();
    ctx.arc(refScreen.x, refScreen.y, 6, 0, Math.PI * 2);
    ctx.fillStyle = '#00ff88';
    ctx.shadowColor = '#00ff88';
    ctx.shadowBlur = 8;
    ctx.fill();
    ctx.shadowBlur = 0;

    // 5. Draw Active Dead Reckoning Vehicle Heading Icon (Rotated Jet/Car Icon)
    const curScreen = this.worldToScreen(this.currentPos.east, this.currentPos.north, centerX, centerY, scale);
    
    ctx.save();
    ctx.translate(curScreen.x, curScreen.y);
    const headingRad = (this.currentPos.headingDeg * Math.PI) / 180.0;
    ctx.rotate(headingRad); // Rotate to heading angle

    // Vehicle Triangle
    ctx.beginPath();
    ctx.moveTo(0, -14);
    ctx.lineTo(9, 10);
    ctx.lineTo(0, 5);
    ctx.lineTo(-9, 10);
    ctx.closePath();

    ctx.fillStyle = this.currentPos.isOutage ? '#ff3366' : '#00f0ff';
    ctx.shadowColor = this.currentPos.isOutage ? '#ff3366' : '#00f0ff';
    ctx.shadowBlur = 14;
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();

    // 6. Scale bar (in bottom-left)
    const scaleBarMeters = 500;
    const scaleBarPx = scaleBarMeters * scale;
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.fillRect(16, height - 36, scaleBarPx + 20, 24);
    ctx.strokeStyle = '#00f0ff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(26, height - 20);
    ctx.lineTo(26 + scaleBarPx, height - 20);
    ctx.stroke();

    ctx.fillStyle = '#fff';
    ctx.font = '10px Rajdhani';
    ctx.textAlign = 'center';
    ctx.fillText(`${scaleBarMeters} m`, 26 + scaleBarPx / 2, height - 24);
  }
}
