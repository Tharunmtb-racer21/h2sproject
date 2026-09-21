/**
 * SIH26168 Main Client Controller & Telemetry Streamer
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Renderers
  const speedometer = new SpeedometerGauge('speedGaugeCanvas');
  const compass = new CompassDial('compassCanvas');
  const map = new MapRenderer('navCanvas');

  // DOM Elements
  const sessionSelect = document.getElementById('sessionSelect');
  const modeBadge = document.getElementById('modeBadge');
  const systemClock = document.getElementById('systemClock');

  // Telemetry DOM
  const posEastVal = document.getElementById('posEastVal');
  const posNorthVal = document.getElementById('posNorthVal');
  const posErrorVal = document.getElementById('posErrorVal');
  const distVal = document.getElementById('distVal');
  const speedValue = document.getElementById('speedValue');
  const aiSpeedVal = document.getElementById('aiSpeedVal');
  const refSpeedVal = document.getElementById('refSpeedVal');
  const speedSourceVal = document.getElementById('speedSourceVal');
  const headingValue = document.getElementById('headingValue');
  const cardinalValue = document.getElementById('cardinalValue');
  const headingDegVal = document.getElementById('headingDegVal');
  const gyroVal = document.getElementById('gyroVal');
  const gnssStatusBadge = document.getElementById('gnssStatusBadge');
  const navModeVal = document.getElementById('navModeVal');
  const outageDurationVal = document.getElementById('outageDurationVal');
  const accelZVal = document.getElementById('accelZVal');
  const relTimeVal = document.getElementById('relTimeVal');
  const outageBanner = document.getElementById('outageBanner');
  const outageTimerBadge = document.getElementById('outageTimerBadge');

  // Control Buttons
  const btnPlay = document.getElementById('btnPlay');
  const btnPause = document.getElementById('btnPause');
  const btnStep = document.getElementById('btnStep');
  const btnReset = document.getElementById('btnReset');
  const btnOutageManual = document.getElementById('btnOutageManual');
  const btnOutage10 = document.getElementById('btnOutage10');
  const btnOutage30 = document.getElementById('btnOutage30');
  const btnOutage60 = document.getElementById('btnOutage60');
  const btnRestore = document.getElementById('btnRestore');
  const rateBtns = document.querySelectorAll('.rate-btn');

  // Map Buttons
  document.getElementById('btnZoomIn').addEventListener('click', () => map.zoomIn());
  document.getElementById('btnZoomOut').addEventListener('click', () => map.zoomOut());
  document.getElementById('btnRecenter').addEventListener('click', () => map.recenter());

  // System Clock
  setInterval(() => {
    const now = new Date();
    systemClock.textContent = now.toTimeString().split(' ')[0];
  }, 1000);

  // Load initial reference path
  function loadInitialPath() {
    fetch('/api/initial_path')
      .then(res => res.json())
      .then(data => {
        if (data.ref_path) {
          map.setReferencePath(data.ref_path);
        }
      })
      .catch(err => console.error('Error loading initial path:', err));
  }

  loadInitialPath();

  // Control Actions API Helper
  function sendControl(action, payload = {}) {
    fetch('/api/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, ...payload })
    }).catch(err => console.error('Control error:', err));
  }

  // Playback Button Handlers
  btnPlay.addEventListener('click', () => sendControl('play'));
  btnPause.addEventListener('click', () => sendControl('pause'));
  btnStep.addEventListener('click', () => sendControl('step'));
  btnReset.addEventListener('click', () => {
    sendControl('reset');
    map.reset();
  });

  // Playback Rate selector
  rateBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      rateBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const rate = parseFloat(btn.dataset.rate);
      sendControl('rate', { rate });
    });
  });

  // Outage Triggers
  function triggerOutage(durationS) {
    fetch('/api/outage/trigger', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ duration_s: durationS })
    }).catch(err => console.error('Outage trigger error:', err));
  }

  if (btnOutageManual) {
    btnOutageManual.addEventListener('click', () => triggerOutage(null)); // Continuous infinite outage
  }
  btnOutage10.addEventListener('click', () => triggerOutage(10));
  btnOutage30.addEventListener('click', () => triggerOutage(30));
  btnOutage60.addEventListener('click', () => triggerOutage(60));

  btnRestore.addEventListener('click', () => {
    fetch('/api/outage/restore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }).catch(err => console.error('Restore error:', err));
  });

  // Session selector change
  sessionSelect.addEventListener('change', (e) => {
    const sessionId = e.target.value;
    fetch('/api/session/load', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    })
    .then(res => res.json())
    .then(data => {
      map.reset();
      loadInitialPath();
    })
    .catch(err => console.error('Session load error:', err));
  });

  // Main 20Hz Telemetry Polling Loop
  setInterval(() => {
    fetch('/api/telemetry')
      .then(res => res.json())
      .then(data => {
        updateUI(data);
      })
      .catch(err => console.error('Telemetry fetch error:', err));
  }, 50); // 20 Hz

  function updateUI(data) {
    if (!data) return;

    // 1. Update Map
    map.updateVehicleState(
      data.active_east_m,
      data.active_north_m,
      data.ref_east_m,
      data.ref_north_m,
      data.heading_deg,
      data.outage_active
    );

    // 2. Update Gauges
    speedometer.update(data.ai_speed_kmh, data.ref_speed_kmh);
    compass.update(data.heading_deg);

    // 3. Update Text Readouts
    speedValue.textContent = data.displayed_speed_kmh.toFixed(1);
    aiSpeedVal.textContent = `${data.ai_speed_kmh.toFixed(1)} km/h`;
    refSpeedVal.textContent = `${data.ref_speed_kmh.toFixed(1)} km/h`;
    speedSourceVal.textContent = data.displayed_speed_source;

    headingValue.textContent = `${Math.round(data.heading_deg).toString().padStart(3, '0')}°`;
    cardinalValue.textContent = compass.getCardinalDirection(data.heading_deg);
    headingDegVal.textContent = `${data.heading_deg.toFixed(1)}°`;
    gyroVal.textContent = `${data.gyro_z.toFixed(4)} rad/s`;

    posEastVal.textContent = `${data.active_east_m.toFixed(2)} m`;
    posNorthVal.textContent = `${data.active_north_m.toFixed(2)} m`;
    posErrorVal.textContent = `${data.position_error_m.toFixed(2)} m`;
    
    // Total distance proxy
    distVal.textContent = `${(data.ref_east_m**2 + data.ref_north_m**2)**0.5 > 0 ? ((data.ref_east_m**2 + data.ref_north_m**2)**0.5).toFixed(1) : '0.0'} m`;

    relTimeVal.textContent = `${data.relative_time_s.toFixed(2)} s`;
    accelZVal.textContent = `${data.accel_z.toFixed(2)} m/s²`;
    navModeVal.textContent = data.nav_mode;

    // 4. Update GNSS & Outage Status Badges
    if (data.outage_active) {
      gnssStatusBadge.className = 'status-badge status-outage';
      gnssStatusBadge.textContent = 'GNSS OUTAGE / DEAD RECKONING';
      outageBanner.classList.remove('hidden');
      outageDurationVal.textContent = `${data.outage_elapsed_s.toFixed(1)} s`;
      outageTimerBadge.textContent = `${data.outage_elapsed_s.toFixed(1)}s`;
    } else if (data.is_blending) {
      gnssStatusBadge.className = 'status-badge status-restored';
      gnssStatusBadge.textContent = 'GNSS RESTORED (BLENDING)';
      outageBanner.classList.add('hidden');
      outageDurationVal.textContent = `Restored (${(data.blend_progress * 100).toFixed(0)}%)`;
    } else {
      gnssStatusBadge.className = 'status-badge status-available';
      gnssStatusBadge.textContent = 'GNSS AVAILABLE';
      outageBanner.classList.add('hidden');
      outageDurationVal.textContent = '0.0 s';
    }
  }
});
