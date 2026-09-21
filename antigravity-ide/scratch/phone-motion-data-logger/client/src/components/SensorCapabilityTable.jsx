import React from 'react';
import { Activity, Compass, MapPin, Gauge, Orbit, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

export function SensorCapabilityTable({ capabilities }) {
  const sensors = [
    {
      name: 'Accelerometer',
      desc: '3-Axis Linear Acceleration (m/s²)',
      icon: Activity,
      key: 'accelerometer'
    },
    {
      name: 'Gyroscope',
      desc: '3-Axis Rotation Rate (deg/s)',
      icon: Gauge,
      key: 'gyroscope'
    },
    {
      name: 'Device Orientation',
      desc: '3D Spatial Orientation (Alpha, Beta, Gamma)',
      icon: Orbit,
      key: 'orientation'
    },
    {
      name: 'Magnetometer',
      desc: '3-Axis Magnetic Field Sensor (μT)',
      icon: Compass,
      key: 'magnetometer'
    },
    {
      name: 'GPS / Geolocation',
      desc: 'Lat, Lon, Altitude, Speed & Heading',
      icon: MapPin,
      key: 'gps'
    }
  ];

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
        <div>
          <h3 className="text-base font-bold text-slate-100">Device Hardware Capability Detection</h3>
          <p className="text-xs text-slate-400">Automatic browser sensor API status check</p>
        </div>
        <span className="text-xs text-slate-400 font-mono">Real Browser APIs</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="text-slate-400 border-b border-slate-800 uppercase tracking-wider font-semibold">
              <th className="pb-3 pl-2">Sensor Component</th>
              <th className="pb-3">Description / API</th>
              <th className="pb-3 text-right pr-2">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {sensors.map((sensor) => {
              const Icon = sensor.icon;
              const statusRaw = capabilities[sensor.key] || 'NOT AVAILABLE';
              const isAvailable = statusRaw === 'AVAILABLE';
              const isDetecting = statusRaw === 'DETECTING';

              return (
                <tr key={sensor.key} className="hover:bg-slate-800/30 transition">
                  <td className="py-3 pl-2 font-semibold text-slate-200 flex items-center gap-2.5">
                    <div className="p-2 bg-slate-800 rounded-lg text-cyan-400">
                      <Icon className="w-4 h-4" />
                    </div>
                    {sensor.name}
                  </td>
                  <td className="py-3 text-slate-400 font-mono text-[11px]">{sensor.desc}</td>
                  <td className="py-3 text-right pr-2">
                    {isAvailable ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <CheckCircle2 className="w-3.5 h-3.5" /> AVAILABLE
                      </span>
                    ) : isDetecting ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
                        <AlertCircle className="w-3.5 h-3.5" /> CHECKING
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                        <XCircle className="w-3.5 h-3.5" /> {statusRaw}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
