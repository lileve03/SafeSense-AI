import React, { useState } from 'react';
import { useSafeSenseApp } from '../context/SafeSenseContext';
import { Modality } from '../types/safesense';
import {
  Cpu,
  Camera,
  Radio,
  Flame,
  Volume2,
  Lock,
  Power,
  CheckCircle2,
  XCircle,
  Activity,
  Filter,
  Search,
  Server,
  HelpCircle,
} from 'lucide-react';

export const DevicesPage: React.FC = () => {
  const { devices, toggleDeviceStatus, isLiveMode } = useSafeSenseApp();

  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredDevices = devices.filter((d) => {
    if (typeFilter !== 'all' && d.type !== typeFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const match =
        d.name.toLowerCase().includes(q) ||
        d.zoneName.toLowerCase().includes(q) ||
        d.id.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  const onlineCount = devices.filter((d) => d.status === 'online').length;
  const disconnectedCount = devices.filter((d) => d.status === 'offline').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="p-5 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-[#0F172A] flex items-center gap-2">
            <Cpu className="w-5 h-5 text-[#2563EB]" />
            <span>Devices & Sensor Network Telemetry</span>
          </h2>
          <p className="text-xs text-[#64748B] mt-1">
            Hardware connectivity is unavailable. Device controls operate only in explicit simulation mode.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1.5 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-bold">
            {onlineCount} Connected
          </span>
          {disconnectedCount > 0 && (
            <span className="px-3 py-1.5 rounded-xl bg-red-50 text-[#EF4444] border border-red-200 text-xs font-bold">
              {disconnectedCount} Disconnected
            </span>
          )}
          <span className="px-3 py-1.5 rounded-xl bg-blue-50 text-[#2563EB] border border-blue-200 text-xs font-bold">
            Simulated Edge Nodes
          </span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 bg-white rounded-2xl border border-[#E2E8F0] shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setTypeFilter('all')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              typeFilter === 'all'
                ? 'bg-[#0B1528] text-white shadow-xs'
                : 'text-[#64748B] hover:bg-slate-100'
            }`}
          >
            All Hardware ({devices.length})
          </button>
          <button
            onClick={() => setTypeFilter('cctv')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              typeFilter === 'cctv'
                ? 'bg-[#2563EB] text-white shadow-xs'
                : 'text-[#64748B] hover:bg-slate-100'
            }`}
          >
            <Camera className="w-3.5 h-3.5" />
            <span>CCTV Cameras ({devices.filter((d) => d.type === 'cctv').length})</span>
          </button>
          <button
            onClick={() => setTypeFilter('radar')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              typeFilter === 'radar'
                ? 'bg-teal-700 text-white shadow-xs'
                : 'text-[#64748B] hover:bg-slate-100'
            }`}
          >
            <Radio className="w-3.5 h-3.5" />
            <span>mmWave Radar ({devices.filter((d) => d.type === 'radar').length})</span>
          </button>
          <button
            onClick={() => setTypeFilter('acoustic')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              typeFilter === 'acoustic'
                ? 'bg-amber-600 text-white shadow-xs'
                : 'text-[#64748B] hover:bg-slate-100'
            }`}
          >
            <Volume2 className="w-3.5 h-3.5" />
            <span>Acoustic Nodes ({devices.filter((d) => d.type === 'acoustic').length})</span>
          </button>
          <button
            onClick={() => setTypeFilter('sos')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              typeFilter === 'sos'
                ? 'bg-rose-600 text-white shadow-xs'
                : 'text-[#64748B] hover:bg-slate-100'
            }`}
          >
            <Flame className="w-3.5 h-3.5" />
            <span>SOS Panic Buttons ({devices.filter((d) => d.type === 'sos').length})</span>
          </button>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search device name, location..."
            className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-slate-50 border border-[#E2E8F0] text-xs text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
          />
        </div>
      </div>

      {/* Device Cards Grid (Section 7) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredDevices.map((device) => {
          const isOnline = device.status === 'online';

          return (
            <div
              key={device.id}
              className={`p-5 rounded-2xl border transition-all flex flex-col justify-between shadow-xs bg-white ${
                isOnline
                  ? 'border-[#E2E8F0] hover:border-[#CBD5E1] hover:shadow-md'
                  : 'border-red-200 bg-red-50/20 opacity-85'
              }`}
            >
              <div>
                {/* Header */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                        device.type === 'cctv'
                          ? 'bg-blue-100 text-[#2563EB]'
                          : device.type === 'radar'
                          ? 'bg-teal-100 text-teal-800'
                          : device.type === 'acoustic'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-rose-100 text-[#EF4444]'
                      }`}
                    >
                      {device.type === 'cctv' && <Camera className="w-5 h-5" />}
                      {device.type === 'radar' && <Radio className="w-5 h-5" />}
                      {device.type === 'acoustic' && <Volume2 className="w-5 h-5" />}
                      {device.type === 'sos' && <Flame className="w-5 h-5" />}
                    </div>

                    <div className="min-w-0">
                      <h4 className="font-bold text-xs text-[#0F172A] truncate">{device.name}</h4>
                      <span className="font-mono text-[10px] text-[#64748B]">#{device.id}</span>
                    </div>
                  </div>

                  {/* Connection Status: Connected vs Disconnected (Section 7) */}
                  <span
                    className={`text-[10px] font-black px-2 py-0.5 rounded-full shrink-0 ${
                      isOnline
                        ? 'bg-emerald-50 text-[#10B981] border border-emerald-200'
                        : 'bg-red-50 text-[#EF4444] border border-red-200'
                    }`}
                  >
                    {isOnline ? 'CONNECTED' : 'DISCONNECTED'}
                  </span>
                </div>

                {/* Info Fields */}
                <div className="mt-3.5 space-y-2 text-xs">
                  <div className="flex justify-between text-[#64748B]">
                    <span>Location:</span>
                    <span className="font-bold text-[#0F172A]">{device.zoneName}</span>
                  </div>

                  <div className="flex justify-between text-[#64748B]">
                    <span>Source State:</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-[#2563EB] border border-blue-200">
                      Simulated Node
                    </span>
                  </div>

                  <div className="flex justify-between text-[#64748B]">
                    <span>Privacy Classification:</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        device.isPrivacyProtected
                          ? 'bg-teal-50 text-teal-800 border border-teal-200'
                          : 'bg-slate-100 text-[#0F172A]'
                      }`}
                    >
                      {device.isPrivacyProtected ? 'Zero-Camera Edge Only' : 'Public Area CCTV'}
                    </span>
                  </div>

                  {/* Reading Box */}
                  <div className="p-2.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] mt-2">
                    <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider block">
                      Live Telemetry Reading
                    </span>
                    <p className="text-xs font-semibold text-[#0F172A] mt-0.5 truncate">
                      {isOnline ? device.currentReading : 'Sensor signal loss (Offline)'}
                    </p>
                    <span className="text-[10px] text-[#64748B] font-mono mt-0.5 block">
                      Synced {device.lastUpdate} &bull; Firmware {device.firmwareVersion}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Button: Simulate Connection Toggle */}
              <div className="mt-4 pt-3 border-t border-[#F1F5F9] flex items-center justify-between text-xs">
                <span className="text-[11px] text-[#64748B] font-medium">Fault Testing:</span>

                <button
                  disabled={isLiveMode} title={isLiveMode ? "No physical device connection; switch to simulation for fault testing" : "Toggle simulated device"} onClick={() => toggleDeviceStatus(device.id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                    isOnline
                      ? 'bg-slate-100 hover:bg-rose-100 text-[#0F172A] hover:text-[#EF4444] border border-[#E2E8F0]'
                      : 'bg-[#10B981] hover:bg-emerald-600 text-white shadow-xs'
                  }`}
                >
                  <Power className="w-3.5 h-3.5" />
                  <span>{isOnline ? 'Simulate Disconnect' : 'Reconnect Node'}</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
