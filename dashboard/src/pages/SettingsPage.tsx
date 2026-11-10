import React, { useState } from 'react';
import { DEFAULT_SETTINGS } from '../data/schoolData';
import { useSafeSenseApp } from '../context/SafeSenseContext';
import {
  Settings,
  Sliders,
  Volume2,
  Lock,
  ShieldCheck,
  Save,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { settings, updateSettings, isLiveMode } = useSafeSenseApp();

  const [thresholds, setThresholds] = useState(settings.thresholds);
  const [audioAlerts, setAudioAlerts] = useState(settings.audioAlerts);
  const [message, setMessage] = useState('');
  const persist = (nextThresholds = thresholds, nextAudio = audioAlerts) => {
    try {
      updateSettings({ thresholds: nextThresholds, audioAlerts: nextAudio, privacyStrictRadarOnly: true });
      setThresholds(nextThresholds);
      setAudioAlerts(nextAudio);
      setMessage('Simulation preferences saved in this browser.');
    } catch {
      setMessage('Could not save preferences. Browser storage is unavailable.');
    }
  };
  const handleSave = () => persist();
  const handleRestoreDefaults = () => persist({ ...DEFAULT_SETTINGS.thresholds }, DEFAULT_SETTINGS.audioAlerts);

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="p-5 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-[#0F172A] flex items-center gap-2">
            <Settings className="w-5 h-5 text-[#2563EB]" />
            <span>AI Settings</span>
          </h2>
          <p className="text-xs text-[#64748B] mt-1">
            Local simulation preferences.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            disabled={isLiveMode} onClick={handleRestoreDefaults}
            className="px-3.5 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-[#0F172A] text-xs font-semibold border border-[#E2E8F0] transition-colors cursor-pointer"
          >
            Restore Defaults
          </button>
          <button
            disabled={isLiveMode} title={isLiveMode ? "Switch to simulation mode to configure illustrated scenarios" : "Save simulation preferences"} onClick={handleSave}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-700 text-white text-xs font-bold shadow-xs cursor-pointer transition-all active:scale-95"
          >
            <Save className="w-4 h-4" />
            <span>Save Settings</span>
          </button>
        </div>
      </div>

      {message && (
        <div className={`p-3.5 rounded-2xl border text-xs font-bold flex items-center gap-2 ${message.startsWith('Could not') ? 'bg-red-50 border-red-200 text-red-800' : 'bg-emerald-50 border-emerald-200 text-emerald-800'}`}>
          <ShieldCheck className="w-4 h-4" />
          <span role="status">{message}</span>
        </div>
      )}

      {/* 1. Risk Engine Thresholds */}
      <div className="p-6 rounded-3xl bg-white border border-[#E2E8F0] shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#F1F5F9]">
          <div>
            <h3 className="font-bold text-sm text-[#0F172A] flex items-center gap-2">
              <Sliders className="w-4 h-4 text-[#2563EB]" />
              <span>Simulation Risk Bands (0 - 100)</span>
            </h3>
            <p className="text-xs text-[#64748B] mt-0.5">
              Apply to new local illustrated scenarios only. Real AI thresholds and backend fusion rules are unchanged.
            </p>
          </div>
          <span className="text-[10px] bg-blue-50 text-[#2563EB] font-bold px-2.5 py-1 rounded-full border border-blue-200">
            Simulation only
          </span>
        </div>

        <div className="space-y-4 text-xs">
          {/* Low */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="font-bold text-[#0F172A] flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#10B981]" />
                <span>Low Risk Ceiling (Nominal Baseline)</span>
              </span>
              <span className="font-mono font-bold text-[#64748B]">0 - {thresholds.low}</span>
            </div>
            <input disabled={isLiveMode}
              type="range"
              min="10"
              max="35"
              aria-label="Simulation Low risk ceiling"
              value={thresholds.low}
              onChange={(e) => setThresholds({ ...thresholds, low: parseInt(e.target.value) })}
              className="w-full accent-emerald-600 cursor-pointer"
            />
          </div>

          {/* Observe */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="font-bold text-[#0F172A] flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]" />
                <span>Observe Ceiling (Single Isolated Anomalies)</span>
              </span>
              <span className="font-mono font-bold text-[#64748B]">
                {thresholds.low + 1} - {thresholds.observe}
              </span>
            </div>
            <input disabled={isLiveMode}
              type="range"
              min="36"
              max="60"
              aria-label="Simulation Observe ceiling"
              value={thresholds.observe}
              onChange={(e) => setThresholds({ ...thresholds, observe: parseInt(e.target.value) })}
              className="w-full accent-amber-500 cursor-pointer"
            />
          </div>

          {/* Warning */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="font-bold text-[#0F172A] flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]" />
                <span>Warning Ceiling (Moderate Corroborated Risk)</span>
              </span>
              <span className="font-mono font-bold text-[#64748B]">
                {thresholds.observe + 1} - {thresholds.warning}
              </span>
            </div>
            <input disabled={isLiveMode}
              type="range"
              min="61"
              max="80"
              aria-label="Simulation Warning ceiling"
              value={thresholds.warning}
              onChange={(e) => setThresholds({ ...thresholds, warning: parseInt(e.target.value) })}
              className="w-full accent-amber-600 cursor-pointer"
            />
          </div>

          {/* High */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="font-bold text-[#0F172A] flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#F97316]" />
                <span>High Risk Ceiling (Multi-Modal Event In Same Zone)</span>
              </span>
              <span className="font-mono font-bold text-[#64748B]">
                {thresholds.warning + 1} - {thresholds.high}
              </span>
            </div>
            <input disabled={isLiveMode}
              type="range"
              min="81"
              max="95"
              aria-label="Simulation High risk ceiling"
              value={thresholds.high}
              onChange={(e) => setThresholds({ ...thresholds, high: parseInt(e.target.value) })}
              className="w-full accent-orange-600 cursor-pointer"
            />
          </div>

          {/* Critical */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="font-bold text-[#0F172A] flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444] animate-pulse" />
                <span>Critical Risk / SOS (Simulation)</span>
              </span>
              <span className="font-mono font-bold text-[#64748B]">{thresholds.high + 1} - 100</span>
            </div>
            <p className="text-[11px] text-[#64748B]">
              Simulated SOS always remains Critical. Backend SOS policy is fixed.
            </p>
          </div>
        </div>
      </div>

      {/* 2. Notification & Dispatch Audio Controls */}
      <div className="p-6 rounded-3xl bg-white border border-[#E2E8F0] shadow-xs space-y-4">
        <div className="pb-3 border-b border-[#F1F5F9]">
          <h3 className="font-bold text-sm text-[#0F172A] flex items-center gap-2">
            <Volume2 className="w-4 h-4 text-[#2563EB]" />
            <span>Simulation Audio Alerts</span>
          </h3>
          <p className="text-xs text-[#64748B] mt-0.5">
            Play a browser chime for new simulated incidents.
          </p>
        </div>

        <div className="space-y-3 text-xs">
          <label className="flex items-center justify-between p-3.5 rounded-2xl bg-[#F8FAFC] border border-[#E2E8F0] cursor-pointer">
            <div>
              <span className="font-bold text-[#0F172A] block">Enable Audio Alerts</span>
              <span className="text-[11px] text-[#64748B]">
                Applies only to local illustrated scenarios.
              </span>
            </div>
            <input disabled={isLiveMode}
              type="checkbox"
              checked={audioAlerts}
              onChange={(e) => setAudioAlerts(e.target.checked)}
              className="w-5 h-5 rounded text-[#2563EB] focus:ring-blue-500 cursor-pointer"
            />
          </label>


        </div>
      </div>

      {/* 3. Strict Privacy Boundaries */}
      <div className="p-6 rounded-3xl bg-white border border-[#E2E8F0] shadow-xs space-y-4">
        <div className="pb-3 border-b border-[#F1F5F9]">
          <h3 className="font-bold text-sm text-[#0F172A] flex items-center gap-2">
            <Lock className="w-4 h-4 text-teal-600" />
            <span>Private-Zone Privacy Policy</span>
          </h3>
          <p className="text-xs text-[#64748B] mt-0.5">
            Fixed policy: no CCTV or vision input in private zones.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-teal-50 border border-teal-200 text-xs text-teal-900 space-y-2">
          <div className="flex items-center gap-2 font-bold text-teal-800">
            <ShieldCheck className="w-4 h-4 text-teal-600" />
            <span>Strict Privacy Mode Enforced (Non-Negotiable)</span>
          </div>
          <p className="text-[11px] text-teal-700 leading-relaxed">
            Private zones allow radar, acoustic event metadata and SOS inputs only. This page cannot relax the policy.
          </p>
        </div>
      </div>
    </div>
  );
};
