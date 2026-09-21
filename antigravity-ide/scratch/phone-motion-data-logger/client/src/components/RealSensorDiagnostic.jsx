import React from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Info,
  Smartphone,
  Compass,
  Radio,
  Activity,
  Gauge,
  Orbit,
  MapPin,
  Lock,
  Unlock,
  Terminal
} from 'lucide-react';

export function RealSensorDiagnostic({ env, counts, statuses, isListening, permissionError }) {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-2xl backdrop-blur-md space-y-5">
      {/* Title */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-cyan-400" />
          <h2 className="text-base font-bold text-slate-100 uppercase tracking-wide">
            REAL SENSOR DIAGNOSTIC PANEL
          </h2>
        </div>
        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
          Hardware Inspection
        </span>
      </div>

      {/* 1. Environment & API Support Matrix */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5 text-slate-400" /> 1. Browser API & Security Inspection
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
          <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80 flex items-center justify-between">
            <span className="text-slate-400">window.isSecureContext:</span>
            {env.isSecureContext ? (
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> TRUE
              </span>
            ) : (
              <span className="text-rose-400 font-bold flex items-center gap-1">
                <XCircle className="w-3.5 h-3.5" /> FALSE
              </span>
            )}
          </div>

          <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80 flex items-center justify-between">
            <span className="text-slate-400">Protocol:</span>
            <span className="text-cyan-300 font-bold">{env.protocol}</span>
          </div>

          <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80 flex items-center justify-between">
            <span className="text-slate-400">DeviceMotionEvent Exists:</span>
            {env.hasDeviceMotion ? (
              <span className="text-emerald-400 font-bold">YES</span>
            ) : (
              <span className="text-rose-400 font-bold">NO</span>
            )}
          </div>

          <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80 flex items-center justify-between">
            <span className="text-slate-400">DeviceOrientationEvent Exists:</span>
            {env.hasDeviceOrientation ? (
              <span className="text-emerald-400 font-bold">YES</span>
            ) : (
              <span className="text-rose-400 font-bold">NO</span>
            )}
          </div>

          <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80 flex items-center justify-between">
            <span className="text-slate-400">DeviceMotionEvent.requestPermission:</span>
            {env.hasMotionPermissionApi ? (
              <span className="text-purple-400 font-bold">YES (iOS 13+)</span>
            ) : (
              <span className="text-slate-400">NO (Android Standard)</span>
            )}
          </div>

          <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80 flex items-center justify-between">
            <span className="text-slate-400">DeviceOrientationEvent.requestPermission:</span>
            {env.hasOrientationPermissionApi ? (
              <span className="text-purple-400 font-bold">YES (iOS 13+)</span>
            ) : (
              <span className="text-slate-400">NO (Android Standard)</span>
            )}
          </div>

          <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80 flex items-center justify-between">
            <span className="text-slate-400">navigator.geolocation Exists:</span>
            {env.hasGeolocation ? (
              <span className="text-emerald-400 font-bold">YES</span>
            ) : (
              <span className="text-rose-400 font-bold">NO</span>
            )}
          </div>

          <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80 flex items-center justify-between">
            <span className="text-slate-400">AbsoluteOrientationSensor Exists:</span>
            {env.hasAbsoluteOrientationSensor ? (
              <span className="text-emerald-400 font-bold">YES</span>
            ) : (
              <span className="text-slate-500">NO (Optional)</span>
            )}
          </div>

          <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80 flex items-center justify-between sm:col-span-2">
            <span className="text-slate-400">Magnetometer Exists:</span>
            {env.hasMagnetometer ? (
              <span className="text-emerald-400 font-bold">YES</span>
            ) : (
              <span className="text-slate-500">NO (Optional Generic Sensor API)</span>
            )}
          </div>
        </div>

        {/* User Agent Sub-box */}
        <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80 text-[11px] font-mono text-slate-400 break-all">
          <span className="text-slate-500 block text-[10px] uppercase font-bold">Browser User Agent:</span>
          {env.userAgent}
        </div>
      </div>

      {/* 2. Live Event Counters Matrix */}
      <div className="space-y-2 pt-2 border-t border-slate-800">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          <Radio className="w-3.5 h-3.5 text-cyan-400" /> 2. Real Event Listener Received Indicators
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 font-mono text-xs">
          <div className={`p-2.5 rounded-xl border flex flex-col justify-between ${
            counts.motion > 0
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
              : 'bg-slate-950 border-slate-800 text-slate-400'
          }`}>
            <span className="text-[10px] text-slate-400">devicemotion</span>
            <div className="flex items-center justify-between mt-1">
              <span className="font-bold">{counts.motion > 0 ? 'YES' : 'NO'}</span>
              <span className="text-[10px] bg-slate-900 px-1.5 py-0.5 rounded text-cyan-400">
                {counts.motion} events
              </span>
            </div>
          </div>

          <div className={`p-2.5 rounded-xl border flex flex-col justify-between ${
            counts.orientation > 0
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
              : 'bg-slate-950 border-slate-800 text-slate-400'
          }`}>
            <span className="text-[10px] text-slate-400">deviceorientation</span>
            <div className="flex items-center justify-between mt-1">
              <span className="font-bold">{counts.orientation > 0 ? 'YES' : 'NO'}</span>
              <span className="text-[10px] bg-slate-900 px-1.5 py-0.5 rounded text-amber-400">
                {counts.orientation} events
              </span>
            </div>
          </div>

          <div className={`p-2.5 rounded-xl border flex flex-col justify-between ${
            counts.gps > 0
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
              : 'bg-slate-950 border-slate-800 text-slate-400'
          }`}>
            <span className="text-[10px] text-slate-400">geolocation</span>
            <div className="flex items-center justify-between mt-1">
              <span className="font-bold">{counts.gps > 0 ? 'YES' : 'NO'}</span>
              <span className="text-[10px] bg-slate-900 px-1.5 py-0.5 rounded text-sky-400">
                {counts.gps} updates
              </span>
            </div>
          </div>

          <div className={`p-2.5 rounded-xl border flex flex-col justify-between ${
            counts.absOrientation > 0
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
              : 'bg-slate-950 border-slate-800 text-slate-400'
          }`}>
            <span className="text-[10px] text-slate-400">orientationabsolute</span>
            <div className="flex items-center justify-between mt-1">
              <span className="font-bold">{counts.absOrientation > 0 ? 'YES' : 'NO'}</span>
              <span className="text-[10px] bg-slate-900 px-1.5 py-0.5 rounded text-purple-400">
                {counts.absOrientation} events
              </span>
            </div>
          </div>

          <div className={`p-2.5 rounded-xl border flex flex-col justify-between sm:col-span-2 ${
            counts.magnetometer > 0
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
              : 'bg-slate-950 border-slate-800 text-slate-400'
          }`}>
            <span className="text-[10px] text-slate-400">magnetometer</span>
            <div className="flex items-center justify-between mt-1">
              <span className="font-bold">{counts.magnetometer > 0 ? 'YES' : 'NO'}</span>
              <span className="text-[10px] bg-slate-900 px-1.5 py-0.5 rounded text-emerald-400">
                {counts.magnetometer} readings
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Detailed Failure Reasons & Status Explanations */}
      <div className="space-y-2 pt-2 border-t border-slate-800">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> 3. Detailed Sensor Diagnostics & Status Messages
        </h3>

        <div className="space-y-2 text-xs font-sans">
          {Object.entries(statuses).map(([sensorKey, info]) => {
            const isAvailable = info.status === 'AVAILABLE';
            const isListening = info.status === 'LISTENING';
            const isIdle = info.status === 'IDLE';

            return (
              <div
                key={sensorKey}
                className={`p-3 rounded-xl border space-y-1 ${
                  isAvailable
                    ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-300'
                    : isListening
                    ? 'bg-amber-950/30 border-amber-500/30 text-amber-300 animate-pulse'
                    : isIdle
                    ? 'bg-slate-950 border-slate-800 text-slate-400'
                    : 'bg-rose-950/30 border-rose-500/30 text-rose-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold capitalize font-mono text-slate-200">{sensorKey}:</span>
                  <span className={`text-[10px] font-mono font-extrabold px-2 py-0.5 rounded ${
                    isAvailable
                      ? 'bg-emerald-900 text-emerald-300'
                      : isListening
                      ? 'bg-amber-900 text-amber-300'
                      : isIdle
                      ? 'bg-slate-800 text-slate-400'
                      : 'bg-rose-900 text-rose-300'
                  }`}>
                    {info.status}
                  </span>
                </div>
                <p className="text-[11px] leading-relaxed opacity-90">{info.message}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Android Chrome Troubleshooting Tip Box */}
      <div className="p-4 bg-slate-950/90 border border-amber-500/30 rounded-xl text-xs text-slate-300 space-y-2">
        <div className="flex items-center gap-2 font-bold text-amber-400">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
          <span>Android Chrome Self-Signed Certificate Troubleshooting Note:</span>
        </div>
        <p className="text-slate-400 text-[11px] leading-relaxed">
          If <code>isSecureContext</code> is TRUE but Android Chrome emits 0 events or returns null values, Android Chrome's internal security policy blocks hardware sensors on untrusted local IPs (<code>https://192.168.1.7:5173</code>).
        </p>
        <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800 font-mono text-[10px] text-amber-300 space-y-1">
          <div className="font-bold text-slate-200">Quick Android Chrome Fix Steps:</div>
          <div>1. Open Chrome address bar and type: <code>chrome://flags/#unsafely-treat-insecure-origin-as-secure</code></div>
          <div>2. Add <code>https://192.168.1.7:5173</code> to the text box and set to <strong>Enabled</strong>.</div>
          <div>3. Tap <strong>Relaunch Chrome</strong>. Now Chrome treats your laptop IP as 100% secure!</div>
        </div>
      </div>
    </div>
  );
}
