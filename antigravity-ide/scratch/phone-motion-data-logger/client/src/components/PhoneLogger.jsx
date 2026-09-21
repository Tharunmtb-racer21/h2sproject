import React, { useState, useEffect, useRef } from 'react';
import { Play, Square, ShieldCheck, Wifi, WifiOff, Activity, Gauge, Orbit, Compass, MapPin, Sliders, AlertTriangle, Zap, CheckCircle2 } from 'lucide-react';
import { RealSensorDiagnostic } from './RealSensorDiagnostic';

export function PhoneLogger({
  sensors,
  wsStatus,
  wsError,
  serverInfo,
  onSendTelemetry
}) {
  const [streaming, setStreaming] = useState(false);
  const [samplingRate, setSamplingRate] = useState(10); // Default 10 Hz
  const [packetsSent, setPacketsSent] = useState(0);

  const samplerIntervalRef = useRef(null);

  // Enable Sensors Button Handler
  const handleEnableSensors = async () => {
    await sensors.startListening();
  };

  // Toggle Streaming over WebSocket
  const handleToggleStreaming = async () => {
    if (!streaming) {
      if (!sensors.isListening) {
        await sensors.startListening();
      }
      setStreaming(true);
    } else {
      setStreaming(false);
      if (samplerIntervalRef.current) {
        clearInterval(samplerIntervalRef.current);
        samplerIntervalRef.current = null;
      }
    }
  };

  // Manage Sampling Interval Timer
  useEffect(() => {
    if (streaming) {
      const intervalMs = Math.round(1000 / samplingRate);
      if (samplerIntervalRef.current) {
        clearInterval(samplerIntervalRef.current);
      }

      samplerIntervalRef.current = setInterval(() => {
        const snapshot = sensors.getSnapshot();
        onSendTelemetry(snapshot);
        setPacketsSent((prev) => prev + 1);
      }, intervalMs);
    } else {
      if (samplerIntervalRef.current) {
        clearInterval(samplerIntervalRef.current);
        samplerIntervalRef.current = null;
      }
    }

    return () => {
      if (samplerIntervalRef.current) {
        clearInterval(samplerIntervalRef.current);
      }
    };
  }, [streaming, samplingRate, sensors, onSendTelemetry]);

  const live = sensors.displayReadings;
  const status = sensors.sensorStatus;

  return (
    <div className="max-w-xl mx-auto space-y-5 pb-12 font-sans">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border border-slate-800 rounded-2xl p-5 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/5 rounded-full blur-2xl"></div>

        <div className="flex items-center justify-between">
          <div>
            <span className="text-[10px] font-mono font-bold tracking-widest text-cyan-400 uppercase bg-cyan-950 px-2 py-0.5 rounded border border-cyan-800">
              Mobile Sensor Node
            </span>
            <h1 className="text-xl font-extrabold text-slate-100 mt-1">PHONE SENSOR LOGGER</h1>
          </div>
          <div className="text-right">
            {wsStatus === 'CONNECTED' ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <Wifi className="w-3.5 h-3.5 animate-pulse" /> Connected
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <WifiOff className="w-3.5 h-3.5" /> Waiting Wi-Fi
              </span>
            )}
          </div>
        </div>

        {/* Server & Packets Bar */}
        <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 font-mono">
          <div>
            Server IP: <span className="text-slate-200 font-bold">{serverInfo?.primaryIp || window.location.hostname}</span>
          </div>
          <div>
            Packets Sent: <span className="text-cyan-400 font-bold">{packetsSent}</span>
          </div>
        </div>
      </div>

      {/* Primary Action Button: ENABLE PHONE SENSORS */}
      <div className="space-y-2">
        <button
          onClick={handleEnableSensors}
          className={`w-full py-4 rounded-2xl font-black text-sm uppercase tracking-wider flex items-center justify-center gap-2.5 shadow-xl transition active:scale-[0.98] ${
            sensors.isListening
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-emerald-950/40'
              : 'bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 shadow-cyan-950/40 hover:from-cyan-400 hover:to-blue-500'
          }`}
        >
          {sensors.isListening ? (
            <>
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              SENSORS INITIALIZED (LISTENING ACTIVE)
            </>
          ) : (
            <>
              <Zap className="w-5 h-5 fill-slate-950" />
              ENABLE PHONE SENSORS
            </>
          )}
        </button>

        {sensors.permissionError && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-300 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{sensors.permissionError}</span>
          </div>
        )}
      </div>

      {/* Main Telemetry Streaming Controls */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-2xl backdrop-blur-md space-y-4">
        <button
          onClick={handleToggleStreaming}
          disabled={!sensors.isListening}
          className={`w-full py-4 rounded-2xl font-extrabold text-base flex items-center justify-center gap-3 shadow-xl transition-all transform active:scale-95 ${
            !sensors.isListening
              ? 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
              : streaming
              ? 'bg-gradient-to-r from-rose-600 to-red-600 text-white shadow-rose-900/40 hover:from-rose-500 hover:to-red-500 animate-pulse'
              : 'bg-emerald-500 text-slate-950 font-black shadow-emerald-900/30 hover:bg-emerald-400'
          }`}
        >
          {streaming ? (
            <>
              <Square className="w-5 h-5 fill-white" />
              STOP STREAMING TO LAPTOP
            </>
          ) : (
            <>
              <Play className="w-5 h-5 fill-slate-950" />
              START STREAMING TO LAPTOP
            </>
          )}
        </button>

        {/* Controls Bar: Sampling Rate & Simulation Mode */}
        <div className="pt-2 border-t border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
              <Sliders className="w-4 h-4 text-cyan-400" />
              <span>Sampling Rate:</span>
            </div>
            <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
              {[1, 5, 10, 20].map((rate) => (
                <button
                  key={rate}
                  onClick={() => setSamplingRate(rate)}
                  className={`px-3 py-1 rounded-lg text-xs font-mono font-bold transition ${
                    samplingRate === rate
                      ? 'bg-cyan-500 text-slate-950 shadow-md'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  {rate} Hz
                </button>
              ))}
            </div>
          </div>

          {/* Test / Simulation Mode Toggle (OFF by default) */}
          <div className="flex items-center justify-between pt-2 border-t border-slate-800/60">
            <div className="text-xs font-semibold text-slate-300">
              <span>Simulation Mode (For Diagnostic Testing Only):</span>
            </div>
            <button
              onClick={() => sensors.setSimulatedMode(!sensors.simulatedMode)}
              className={`px-3 py-1 rounded-lg text-xs font-mono font-bold border transition ${
                sensors.simulatedMode
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  : 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-800'
              }`}
            >
              {sensors.simulatedMode ? '🧪 SIMULATION ON' : 'OFF (PHYSICAL)'}
            </button>
          </div>
        </div>
      </div>

      {/* Raw Real Sensor Telemetry Cards */}
      <div className="space-y-3">
        {/* Accelerometer Card */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 mb-3">
            <div className="flex items-center gap-2 font-bold text-sm text-slate-200">
              <Activity className="w-4 h-4 text-cyan-400" /> Accelerometer (m/s²)
            </div>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
              status.accelerometer.status === 'AVAILABLE'
                ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                : 'bg-slate-800 text-slate-400'
            }`}>
              {status.accelerometer.status}
            </span>
          </div>
          {live.accelerometer ? (
            <div className="grid grid-cols-3 gap-2 font-mono text-center">
              <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold">X</div>
                <div className="text-base font-extrabold text-cyan-300">{live.accelerometer.x}</div>
              </div>
              <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Y</div>
                <div className="text-base font-extrabold text-cyan-300">{live.accelerometer.y}</div>
              </div>
              <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Z</div>
                <div className="text-base font-extrabold text-cyan-300">{live.accelerometer.z}</div>
              </div>
            </div>
          ) : (
            <div className="p-3 bg-slate-950 rounded-lg text-xs font-mono text-slate-400 leading-relaxed border border-slate-800">
              {status.accelerometer.message}
            </div>
          )}
        </div>

        {/* Gyroscope Card */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 mb-3">
            <div className="flex items-center gap-2 font-bold text-sm text-slate-200">
              <Gauge className="w-4 h-4 text-amber-400" /> Gyroscope (deg/s)
            </div>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
              status.gyroscope.status === 'AVAILABLE'
                ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                : 'bg-slate-800 text-slate-400'
            }`}>
              {status.gyroscope.status}
            </span>
          </div>
          {live.gyroscope ? (
            <div className="grid grid-cols-3 gap-2 font-mono text-center">
              <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Alpha (Z)</div>
                <div className="text-base font-extrabold text-amber-300">{live.gyroscope.alpha}</div>
              </div>
              <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Beta (X)</div>
                <div className="text-base font-extrabold text-amber-300">{live.gyroscope.beta}</div>
              </div>
              <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Gamma (Y)</div>
                <div className="text-base font-extrabold text-amber-300">{live.gyroscope.gamma}</div>
              </div>
            </div>
          ) : (
            <div className="p-3 bg-slate-950 rounded-lg text-xs font-mono text-slate-400 leading-relaxed border border-slate-800">
              {status.gyroscope.message}
            </div>
          )}
        </div>

        {/* Orientation Card */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 mb-3">
            <div className="flex items-center gap-2 font-bold text-sm text-slate-200">
              <Orbit className="w-4 h-4 text-purple-400" /> Device Orientation (deg)
            </div>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
              status.orientation.status === 'AVAILABLE'
                ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                : 'bg-slate-800 text-slate-400'
            }`}>
              {status.orientation.status}
            </span>
          </div>
          {live.orientation ? (
            <div className="grid grid-cols-3 gap-2 font-mono text-center">
              <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Alpha</div>
                <div className="text-base font-extrabold text-purple-300">{live.orientation.alpha}</div>
              </div>
              <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Beta</div>
                <div className="text-base font-extrabold text-purple-300">{live.orientation.beta}</div>
              </div>
              <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Gamma</div>
                <div className="text-base font-extrabold text-purple-300">{live.orientation.gamma}</div>
              </div>
            </div>
          ) : (
            <div className="p-3 bg-slate-950 rounded-lg text-xs font-mono text-slate-400 leading-relaxed border border-slate-800">
              {status.orientation.message}
            </div>
          )}
        </div>

        {/* Magnetometer Card (Optional) */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 mb-3">
            <div className="flex items-center gap-2 font-bold text-sm text-slate-200">
              <Compass className="w-4 h-4 text-emerald-400" /> Magnetometer (μT)
            </div>
            <span className="text-[10px] font-mono text-slate-400">Optional API</span>
          </div>
          {live.magnetometer ? (
            <div className="grid grid-cols-3 gap-2 font-mono text-center">
              <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold">X</div>
                <div className="text-base font-extrabold text-emerald-300">{live.magnetometer.x}</div>
              </div>
              <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Y</div>
                <div className="text-base font-extrabold text-emerald-300">{live.magnetometer.y}</div>
              </div>
              <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold">Z</div>
                <div className="text-base font-extrabold text-emerald-300">{live.magnetometer.z}</div>
              </div>
            </div>
          ) : (
            <div className="p-3 bg-slate-950 rounded-lg text-xs font-mono text-slate-400 leading-relaxed border border-slate-800">
              {status.magnetometer.message}
            </div>
          )}
        </div>

        {/* GPS Card */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 mb-3">
            <div className="flex items-center gap-2 font-bold text-sm text-slate-200">
              <MapPin className="w-4 h-4 text-sky-400" /> Geolocation / GPS
            </div>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
              status.gps.status === 'AVAILABLE'
                ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                : 'bg-slate-800 text-slate-400'
            }`}>
              {status.gps.status}
            </span>
          </div>
          {live.gps ? (
            <div className="grid grid-cols-2 gap-2 font-mono text-xs">
              <div className="bg-slate-950/80 p-2 rounded-lg border border-slate-800">
                <span className="text-slate-500 block text-[10px]">Lat / Lon</span>
                <span className="font-bold text-sky-300">{live.gps.latitude}, {live.gps.longitude}</span>
              </div>
              <div className="bg-slate-950/80 p-2 rounded-lg border border-slate-800">
                <span className="text-slate-500 block text-[10px]">Speed / Heading</span>
                <span className="font-bold text-sky-300">
                  {live.gps.speed !== null ? `${live.gps.speed} m/s` : 'N/A'}, {live.gps.heading !== null ? `${live.gps.heading}°` : 'N/A'}
                </span>
              </div>
              <div className="bg-slate-950/80 p-2 rounded-lg border border-slate-800">
                <span className="text-slate-500 block text-[10px]">Altitude</span>
                <span className="font-bold text-sky-300">{live.gps.altitude !== null ? `${live.gps.altitude} m` : 'N/A'}</span>
              </div>
              <div className="bg-slate-950/80 p-2 rounded-lg border border-slate-800">
                <span className="text-slate-500 block text-[10px]">Accuracy</span>
                <span className="font-bold text-sky-300">{live.gps.accuracy !== null ? `±${live.gps.accuracy} m` : 'N/A'}</span>
              </div>
            </div>
          ) : (
            <div className="p-3 bg-slate-950 rounded-lg text-xs font-mono text-slate-400 leading-relaxed border border-slate-800">
              {status.gps.message}
            </div>
          )}
        </div>
      </div>

      {/* Real Sensor Diagnostic Panel Component */}
      <RealSensorDiagnostic
        env={sensors.envDiagnostics}
        counts={sensors.eventCounts}
        statuses={status}
        isListening={sensors.isListening}
        permissionError={sensors.permissionError}
      />
    </div>
  );
}
