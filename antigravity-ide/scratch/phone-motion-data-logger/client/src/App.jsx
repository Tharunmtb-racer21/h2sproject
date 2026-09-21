import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Smartphone, Laptop, Activity, Lock, Unlock } from 'lucide-react';
import { useSensors } from './sensors/useSensors';
import { PhoneLogger } from './components/PhoneLogger';
import { LaptopDashboard } from './components/LaptopDashboard';

export default function App() {
  // Determine mode from URL query ?mode=phone or ?mode=dashboard or mobile user agent
  const [viewMode, setViewMode] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    const modeParam = params.get('mode');
    if (modeParam === 'phone') return 'phone';
    if (modeParam === 'dashboard') return 'dashboard';

    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth < 768;
    return isMobile ? 'phone' : 'dashboard';
  });

  const sensors = useSensors();

  // Server Info & WebSocket State
  const [serverInfo, setServerInfo] = useState(null);
  const [wsStatus, setWsStatus] = useState('DISCONNECTED'); // DISCONNECTED | CONNECTING | CONNECTED
  const [wsError, setWsError] = useState(null);
  const [latestData, setLatestData] = useState(null);
  const [totalPackets, setTotalPackets] = useState(0);

  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);

  // Fetch backend info
  const fetchServerInfo = useCallback(async () => {
    try {
      const res = await fetch('/api/info');
      if (res.ok) {
        const data = await res.json();
        setServerInfo(data);
      }
    } catch (err) {
      console.warn('Backend server info fetch failed:', err.message);
    }
  }, []);

  // Setup WebSocket connection over WSS / WS
  const connectWebSocket = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    setWsStatus('CONNECTING');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Use host proxy endpoint or direct port
    const wsUrl = `${protocol}//${window.location.host}/ws?type=${viewMode === 'phone' ? 'phone' : 'dashboard'}`;

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('[WebSocket] Connected securely to:', wsUrl);
        setWsStatus('CONNECTED');
        setWsError(null);

        ws.send(JSON.stringify({
          type: 'REGISTER_TYPE',
          clientType: viewMode === 'phone' ? 'phone' : 'dashboard'
        }));
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'SYSTEM_STATUS' || msg.type === 'SYSTEM_INIT') {
            setServerInfo(prev => ({
              ...prev,
              phoneConnected: msg.phoneConnected,
              recording: msg.recording,
              rowCount: msg.rowCount,
              primaryIp: msg.lanIps?.[0]?.address || prev?.primaryIp
            }));
            if (msg.packetsReceived !== undefined) {
              setTotalPackets(msg.packetsReceived);
            }
          }

          if (msg.type === 'SENSOR_DATA') {
            setLatestData(msg.data);
            setTotalPackets(msg.totalPacketsReceived || 0);
            if (msg.rowCount !== undefined) {
              setServerInfo(prev => ({ ...prev, rowCount: msg.rowCount }));
            }
          }
        } catch (e) {
          console.error('[WebSocket] Parse error:', e);
        }
      };

      ws.onclose = () => {
        setWsStatus('DISCONNECTED');
        wsRef.current = null;
        reconnectTimerRef.current = setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (err) => {
        setWsError('WebSocket connection error');
        setWsStatus('DISCONNECTED');
      };

      wsRef.current = ws;
    } catch (err) {
      setWsStatus('DISCONNECTED');
      reconnectTimerRef.current = setTimeout(connectWebSocket, 3000);
    }
  }, [viewMode]);

  useEffect(() => {
    fetchServerInfo();
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, [fetchServerInfo, connectWebSocket]);

  const handleSendTelemetry = useCallback((snapshot) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(snapshot));
    }
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Navbar / Mode Switcher & Security Status */}
      <header className="sticky top-0 z-50 bg-slate-900/90 border-b border-slate-800 backdrop-blur-md px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-gradient-to-tr from-cyan-500 to-blue-600 rounded-xl text-slate-950 font-black shadow-lg shadow-cyan-500/20">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <span className="text-sm font-extrabold text-slate-100 tracking-tight">PHONE MOTION DATA LOGGER</span>
              <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                <span>Wi-Fi Telemetry</span>
                <span>•</span>
                {sensors.isSecureContext ? (
                  <span className="inline-flex items-center gap-1 font-bold text-emerald-400">
                    <Lock className="w-3 h-3" /> SECURE CONTEXT (HTTPS)
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 font-bold text-rose-400">
                    <Unlock className="w-3 h-3" /> INSECURE CONTEXT (HTTP)
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setViewMode('phone')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                viewMode === 'phone'
                  ? 'bg-cyan-500 text-slate-950 shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              <Smartphone className="w-4 h-4" /> Phone Mode
            </button>
            <button
              onClick={() => setViewMode('dashboard')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                viewMode === 'dashboard'
                  ? 'bg-cyan-500 text-slate-950 shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              <Laptop className="w-4 h-4" /> Laptop Dashboard
            </button>
          </div>
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 p-4 md:p-8">
        {viewMode === 'phone' ? (
          <PhoneLogger
            sensors={sensors}
            wsStatus={wsStatus}
            wsError={wsError}
            serverInfo={serverInfo}
            onSendTelemetry={handleSendTelemetry}
          />
        ) : (
          <LaptopDashboard
            serverInfo={serverInfo}
            wsStatus={wsStatus}
            latestData={latestData}
            totalPackets={totalPackets}
            isSecureContext={sensors.isSecureContext}
            onRefreshInfo={fetchServerInfo}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-slate-900/60 border-t border-slate-800/80 py-4 px-6 text-center text-xs text-slate-500 font-mono">
        Phone Motion Data Logger • Real Hardware Sensors • No Simulated Data • HTTPS/WSS 0.0.0.0
      </footer>
    </div>
  );
}
