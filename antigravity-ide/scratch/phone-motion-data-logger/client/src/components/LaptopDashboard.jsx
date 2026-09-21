import React, { useState, useEffect } from 'react';
import {
  Activity,
  Gauge,
  Orbit,
  Compass,
  MapPin,
  Wifi,
  WifiOff,
  Server,
  FileSpreadsheet,
  Download,
  Play,
  Square,
  RefreshCw,
  Clock,
  Radio,
  Smartphone,
  CheckCircle2,
  XCircle,
  HardDrive
} from 'lucide-react';
import { NetworkInfo } from './NetworkInfo';
import { SensorCapabilityTable } from './SensorCapabilityTable';

export function LaptopDashboard({
  serverInfo,
  wsStatus,
  latestData,
  totalPackets,
  isSecureContext,
  onRefreshInfo
}) {
  const [currentTimestamp, setCurrentTimestamp] = useState(new Date().toISOString());

  // Update current live time display
  useEffect(() => {
    const timer = setInterval(() => setCurrentTimestamp(new Date().toISOString()), 1000);
    return () => clearInterval(timer);
  }, []);

  // CSV Control Handlers
  const handleToggleRecording = async (start) => {
    const endpoint = start ? '/api/recording/start' : '/api/recording/stop';
    try {
      await fetch(endpoint, { method: 'POST' });
      onRefreshInfo();
    } catch (e) {
      console.error('Failed to toggle recording:', e);
    }
  };

  const handleClearCSV = async () => {
    if (!window.confirm('Are you sure you want to clear sensor_data.csv? All existing records will be wiped.')) return;
    try {
      await fetch('/api/recording/clear', { method: 'POST' });
      onRefreshInfo();
    } catch (e) {
      console.error('Failed to clear CSV:', e);
    }
  };

  const handleDownloadCSV = () => {
    window.open('/api/download-csv', '_blank');
  };

  const data = latestData || {};
  const phoneConnected = serverInfo?.phoneConnected || false;
  const isRecording = serverInfo?.recording !== false;
  const rowCount = serverInfo?.rowCount || 0;

  // Sensor availability matrix from latest received phone packet or default
  const availability = data.availability || {
    accelerometer: Boolean(data.accelerometer),
    gyroscope: Boolean(data.gyroscope),
    orientation: Boolean(data.orientation),
    magnetometer: Boolean(data.magnetometer),
    gps: Boolean(data.gps)
  };

  const formattedCaps = {
    accelerometer: availability.accelerometer ? 'AVAILABLE' : 'NOT AVAILABLE',
    gyroscope: availability.gyroscope ? 'AVAILABLE' : 'NOT AVAILABLE',
    orientation: availability.orientation ? 'AVAILABLE' : 'NOT AVAILABLE',
    magnetometer: availability.magnetometer ? 'AVAILABLE' : 'NOT AVAILABLE ON THIS BROWSER/DEVICE',
    gps: availability.gps ? 'AVAILABLE' : 'NOT AVAILABLE'
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Top Header & System Overview */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/90 border border-slate-800 p-6 rounded-2xl shadow-xl">
        <div>
          <div className="flex items-center gap-2">
            <Radio className="w-5 h-5 text-cyan-400 animate-pulse" />
            <h1 className="text-2xl font-black text-slate-100 tracking-tight">PHONE MOTION DATA LOGGER</h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono bg-cyan-950 text-cyan-400 border border-cyan-800">
              LIVE LAPTOP DASHBOARD
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time local Wi-Fi telemetry stream & CSV recorder • Listening on 0.0.0.0:3001
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Phone Connection Badge */}
          <div className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold border ${
            phoneConnected
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
          }`}>
            <Smartphone className="w-4 h-4" />
            <span>{phoneConnected ? 'PHONE CONNECTED' : 'WAITING FOR PHONE'}</span>
          </div>

          {/* WebSocket Status Badge */}
          <div className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold border ${
            wsStatus === 'CONNECTED'
              ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
              : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
          }`}>
            {wsStatus === 'CONNECTED' ? <Wifi className="w-4 h-4 animate-pulse" /> : <WifiOff className="w-4 h-4" />}
            <span>WS {wsStatus}</span>
          </div>
        </div>
      </div>

      {/* Network Setup & LAN Discovery Card */}
      <NetworkInfo serverInfo={serverInfo} isSecureContext={isSecureContext} />

      {/* Control Panel Bar: CSV & Telemetry Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Stat Cards */}
        <div className="lg:col-span-2 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
            <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase">
              <Server className="w-3.5 h-3.5 text-cyan-400" /> Total Packets
            </div>
            <div className="text-2xl font-black font-mono text-cyan-300 mt-2">{totalPackets}</div>
            <div className="text-[10px] text-slate-500 mt-0.5">Telemetry Frames Received</div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
            <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase">
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" /> CSV Rows Written
            </div>
            <div className="text-2xl font-black font-mono text-emerald-300 mt-2">{rowCount}</div>
            <div className="text-[10px] text-slate-500 mt-0.5">Records in sensor_data.csv</div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
            <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase">
              <Clock className="w-3.5 h-3.5 text-amber-400" /> Server Start Time
            </div>
            <div className="text-xs font-bold font-mono text-amber-300 mt-2 truncate">
              {serverInfo?.startTime ? new Date(serverInfo.startTime).toLocaleTimeString() : 'N/A'}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Uptime Baseline</div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
            <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase">
              <Radio className="w-3.5 h-3.5 text-purple-400" /> Current Clock
            </div>
            <div className="text-xs font-bold font-mono text-purple-300 mt-2 truncate">
              {new Date(currentTimestamp).toLocaleTimeString()}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Laptop System Time</div>
          </div>
        </div>

        {/* CSV Controls Box */}
        <div className="bg-slate-900/90 border border-slate-800 p-5 rounded-xl shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
              <div className="flex items-center gap-2 font-bold text-sm text-slate-200">
                <HardDrive className="w-4 h-4 text-emerald-400" /> CSV Recording Controls
              </div>
              <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded border ${
                isRecording
                  ? 'bg-emerald-950 text-emerald-400 border-emerald-800 animate-pulse'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}>
                {isRecording ? 'CSV RECORDING ACTIVE' : 'RECORDING PAUSED'}
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono space-y-1 mb-4">
              <div>File: <span className="text-slate-200 font-bold">data/sensor_data.csv</span></div>
              <div>Rows Written: <span className="text-emerald-400 font-bold">{rowCount}</span></div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {isRecording ? (
              <button
                onClick={() => handleToggleRecording(false)}
                className="py-2.5 px-3 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition"
              >
                <Square className="w-3.5 h-3.5 fill-rose-300" /> Pause CSV
              </button>
            ) : (
              <button
                onClick={() => handleToggleRecording(true)}
                className="py-2.5 px-3 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition"
              >
                <Play className="w-3.5 h-3.5 fill-emerald-300" /> Resume CSV
              </button>
            )}

            <button
              onClick={handleDownloadCSV}
              className="py-2.5 px-3 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/30 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition"
            >
              <Download className="w-3.5 h-3.5" /> Download CSV
            </button>
          </div>
        </div>
      </div>

      {/* Live Physical Telemetry Stream Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* 1. Accelerometer Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
            <div className="flex items-center gap-2 font-bold text-slate-100">
              <Activity className="w-5 h-5 text-cyan-400" /> Accelerometer
            </div>
            <span className="text-[10px] font-mono bg-slate-800 text-cyan-300 px-2 py-0.5 rounded">m/s²</span>
          </div>
          {data.accelerometer ? (
            <div className="space-y-3 font-mono">
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-500 block font-bold">ACCEL X</span>
                  <span className="text-lg font-black text-cyan-300">{data.accelerometer.x ?? 'N/A'}</span>
                </div>
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-500 block font-bold">ACCEL Y</span>
                  <span className="text-lg font-black text-cyan-300">{data.accelerometer.y ?? 'N/A'}</span>
                </div>
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-500 block font-bold">ACCEL Z</span>
                  <span className="text-lg font-black text-cyan-300">{data.accelerometer.z ?? 'N/A'}</span>
                </div>
              </div>
              {data.accelerometer.noGravity && (
                <div className="pt-2 border-t border-slate-800 text-[11px]">
                  <span className="text-slate-400 block mb-1">Without Gravity:</span>
                  <div className="grid grid-cols-3 gap-1 text-center text-slate-300">
                    <div>X: {data.accelerometer.noGravity.x ?? 'N/A'}</div>
                    <div>Y: {data.accelerometer.noGravity.y ?? 'N/A'}</div>
                    <div>Z: {data.accelerometer.noGravity.z ?? 'N/A'}</div>
                  </div>
                </div>
              )}
            </div>
          ) : totalPackets === 0 ? (
            <div className="text-center py-6 font-mono text-xs font-bold text-amber-400 bg-amber-950/20 border border-amber-900/30 rounded-xl">
              <span className="animate-pulse block">⏳ WAITING FOR TELEMETRY</span>
              <span className="text-[10px] text-slate-400 font-sans font-normal mt-1 block">Tap "START STREAMING" on Phone</span>
            </div>
          ) : (
            <div className="text-center py-6 font-mono text-xs font-bold text-rose-400 bg-rose-950/20 border border-rose-900/30 rounded-xl">
              NOT AVAILABLE
            </div>
          )}
        </div>

        {/* 2. Gyroscope Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
            <div className="flex items-center gap-2 font-bold text-slate-100">
              <Gauge className="w-5 h-5 text-amber-400" /> Gyroscope
            </div>
            <span className="text-[10px] font-mono bg-slate-800 text-amber-300 px-2 py-0.5 rounded">deg/s</span>
          </div>
          {data.gyroscope ? (
            <div className="grid grid-cols-3 gap-2 font-mono text-center">
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-500 block font-bold">ALPHA (Z)</span>
                <span className="text-lg font-black text-amber-300">{data.gyroscope.alpha ?? 'N/A'}</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-500 block font-bold">BETA (X)</span>
                <span className="text-lg font-black text-amber-300">{data.gyroscope.beta ?? 'N/A'}</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-500 block font-bold">GAMMA (Y)</span>
                <span className="text-lg font-black text-amber-300">{data.gyroscope.gamma ?? 'N/A'}</span>
              </div>
            </div>
          ) : totalPackets === 0 ? (
            <div className="text-center py-6 font-mono text-xs font-bold text-amber-400 bg-amber-950/20 border border-amber-900/30 rounded-xl">
              <span className="animate-pulse block">⏳ WAITING FOR TELEMETRY</span>
              <span className="text-[10px] text-slate-400 font-sans font-normal mt-1 block">Tap "START STREAMING" on Phone</span>
            </div>
          ) : (
            <div className="text-center py-6 font-mono text-xs font-bold text-rose-400 bg-rose-950/20 border border-rose-900/30 rounded-xl">
              NOT AVAILABLE
            </div>
          )}
        </div>

        {/* 3. Device Orientation Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
            <div className="flex items-center gap-2 font-bold text-slate-100">
              <Orbit className="w-5 h-5 text-purple-400" /> Device Orientation
            </div>
            <span className="text-[10px] font-mono bg-slate-800 text-purple-300 px-2 py-0.5 rounded">degrees</span>
          </div>
          {data.orientation ? (
            <div className="grid grid-cols-3 gap-2 font-mono text-center">
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-500 block font-bold">ALPHA</span>
                <span className="text-lg font-black text-purple-300">{data.orientation.alpha ?? 'N/A'}</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-500 block font-bold">BETA</span>
                <span className="text-lg font-black text-purple-300">{data.orientation.beta ?? 'N/A'}</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-500 block font-bold">GAMMA</span>
                <span className="text-lg font-black text-purple-300">{data.orientation.gamma ?? 'N/A'}</span>
              </div>
            </div>
          ) : totalPackets === 0 ? (
            <div className="text-center py-6 font-mono text-xs font-bold text-amber-400 bg-amber-950/20 border border-amber-900/30 rounded-xl">
              <span className="animate-pulse block">⏳ WAITING FOR TELEMETRY</span>
              <span className="text-[10px] text-slate-400 font-sans font-normal mt-1 block">Tap "START STREAMING" on Phone</span>
            </div>
          ) : (
            <div className="text-center py-6 font-mono text-xs font-bold text-rose-400 bg-rose-950/20 border border-rose-900/30 rounded-xl">
              NOT AVAILABLE
            </div>
          )}
        </div>

        {/* 4. Magnetometer Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
            <div className="flex items-center gap-2 font-bold text-slate-100">
              <Compass className="w-5 h-5 text-emerald-400" /> Magnetometer
            </div>
            <span className="text-[10px] font-mono bg-slate-800 text-emerald-300 px-2 py-0.5 rounded">μT</span>
          </div>
          {data.magnetometer ? (
            <div className="grid grid-cols-3 gap-2 font-mono text-center">
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-500 block font-bold">MAG X</span>
                <span className="text-lg font-black text-emerald-300">{data.magnetometer.x ?? 'N/A'}</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-500 block font-bold">MAG Y</span>
                <span className="text-lg font-black text-emerald-300">{data.magnetometer.y ?? 'N/A'}</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-500 block font-bold">MAG Z</span>
                <span className="text-lg font-black text-emerald-300">{data.magnetometer.z ?? 'N/A'}</span>
              </div>
            </div>
          ) : totalPackets === 0 ? (
            <div className="text-center py-6 font-mono text-xs font-bold text-amber-400 bg-amber-950/20 border border-amber-900/30 rounded-xl">
              <span className="animate-pulse block">⏳ WAITING FOR TELEMETRY</span>
              <span className="text-[10px] text-slate-400 font-sans font-normal mt-1 block">Tap "START STREAMING" on Phone</span>
            </div>
          ) : (
            <div className="text-center py-6 font-mono text-xs font-bold text-rose-400 bg-rose-950/20 border border-rose-900/30 rounded-xl">
              NOT AVAILABLE ON THIS BROWSER/DEVICE
            </div>
          )}
        </div>

        {/* 5. Geolocation / GPS Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl lg:col-span-2">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
            <div className="flex items-center gap-2 font-bold text-slate-100">
              <MapPin className="w-5 h-5 text-sky-400" /> Geolocation / GPS
            </div>
            <span className="text-[10px] font-mono bg-slate-800 text-sky-300 px-2 py-0.5 rounded">Position API</span>
          </div>
          {data.gps ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 font-mono text-xs">
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-slate-500 block text-[10px] font-bold">LATITUDE</span>
                <span className="text-sm font-bold text-sky-300">{data.gps.latitude ?? 'N/A'}</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-slate-500 block text-[10px] font-bold">LONGITUDE</span>
                <span className="text-sm font-bold text-sky-300">{data.gps.longitude ?? 'N/A'}</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-slate-500 block text-[10px] font-bold">ALTITUDE</span>
                <span className="text-sm font-bold text-sky-300">{data.gps.altitude !== null ? `${data.gps.altitude} m` : 'N/A'}</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-slate-500 block text-[10px] font-bold">SPEED</span>
                <span className="text-sm font-bold text-sky-300">{data.gps.speed !== null ? `${data.gps.speed} m/s` : 'N/A'}</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-slate-500 block text-[10px] font-bold">HEADING</span>
                <span className="text-sm font-bold text-sky-300">{data.gps.heading !== null ? `${data.gps.heading}°` : 'N/A'}</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                <span className="text-slate-500 block text-[10px] font-bold">ACCURACY</span>
                <span className="text-sm font-bold text-sky-300">{data.gps.accuracy !== null ? `±${data.gps.accuracy} m` : 'N/A'}</span>
              </div>
            </div>
          ) : totalPackets === 0 ? (
            <div className="text-center py-6 font-mono text-xs font-bold text-amber-400 bg-amber-950/20 border border-amber-900/30 rounded-xl">
              <span className="animate-pulse block">⏳ WAITING FOR TELEMETRY STREAM</span>
              <span className="text-[10px] text-slate-400 font-sans font-normal mt-1 block">Tap "START STREAMING" on Phone</span>
            </div>
          ) : (
            <div className="text-center py-6 font-mono text-xs font-bold text-rose-400 bg-rose-950/20 border border-rose-900/30 rounded-xl">
              NOT AVAILABLE / PERMISSION DENIED
            </div>
          )}
        </div>
      </div>

      {/* Sensor Availability Matrix */}
      <SensorCapabilityTable capabilities={formattedCaps} />
    </div>
  );
}
