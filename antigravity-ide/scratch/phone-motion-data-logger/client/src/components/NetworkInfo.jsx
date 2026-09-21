import React, { useState } from 'react';
import { Wifi, Smartphone, Laptop, AlertTriangle, Copy, Check, ShieldCheck, Lock, Unlock } from 'lucide-react';

export function NetworkInfo({ serverInfo, isSecureContext }) {
  const [copied, setCopied] = useState(false);

  const primaryIp = serverInfo?.primaryIp || window.location.hostname || '192.168.X.X';
  const phoneUrl = `https://${primaryIp}:5173/?mode=phone`;
  const laptopUrl = `https://localhost:5173`;

  const copyPhoneUrl = () => {
    navigator.clipboard.writeText(phoneUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-cyan-500/10 text-cyan-400 rounded-xl border border-cyan-500/20">
            <Wifi className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-100">Local Wi-Fi Network & HTTPS Setup</h3>
            <p className="text-xs text-slate-400">Connect phone and laptop over secure local HTTPS</p>
          </div>
        </div>

        <div>
          {isSecureContext ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <Lock className="w-3.5 h-3.5" /> SECURE CONTEXT (HTTPS)
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30 animate-pulse">
              <Unlock className="w-3.5 h-3.5" /> INSECURE CONTEXT (HTTP)
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Laptop Info Card */}
        <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800/80">
          <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <Laptop className="w-4 h-4 text-cyan-400" /> Laptop Dashboard HTTPS URL
          </div>
          <div className="font-mono text-xs font-bold text-cyan-300 bg-slate-900 px-3 py-2.5 rounded-lg border border-slate-800 flex items-center justify-between truncate">
            <span>{laptopUrl}</span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">Localhost</span>
          </div>
        </div>

        {/* Phone Info Card */}
        <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800/80">
          <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <Smartphone className="w-4 h-4 text-amber-400" /> Phone Accessible HTTPS URL
          </div>
          <div className="font-mono text-xs font-bold text-amber-300 bg-slate-900 px-3 py-2.5 rounded-lg border border-slate-800 flex items-center justify-between">
            <span className="truncate">{phoneUrl}</span>
            <button
              onClick={copyPhoneUrl}
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-md transition"
              title="Copy URL"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Android / iOS HTTPS Trust Steps */}
      <div className="mt-4 p-4 bg-slate-950/80 border border-slate-800 rounded-xl text-xs space-y-2">
        <div className="flex items-center gap-2 font-bold text-slate-200">
          <ShieldCheck className="w-4 h-4 text-cyan-400" /> First-Time Phone SSL Trust Steps:
        </div>
        <ol className="list-decimal pl-5 text-slate-400 space-y-1 font-sans leading-relaxed">
          <li>Open <code className="bg-slate-900 text-amber-300 px-1 py-0.5 rounded font-mono">{phoneUrl}</code> in Chrome/Safari on your phone.</li>
          <li>When Chrome shows <i>"Your connection is not private"</i>, tap <strong className="text-slate-200">"Advanced"</strong>.</li>
          <li>Tap <strong className="text-amber-400">"Proceed to {primaryIp} (unsafe)"</strong> to trust the local SSL cert.</li>
          <li>Tap <strong className="text-cyan-400">"START STREAMING"</strong> on the phone screen to enable sensors!</li>
        </ol>
      </div>
    </div>
  );
}
