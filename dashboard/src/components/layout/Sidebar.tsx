import React from 'react';
import { useSafeSenseApp } from '../../context/SafeSenseContext';
import { PageId } from '../../types/safesense';
import {
  LayoutDashboard,
  Video,
  Box,
  BellRing,
  History,
  BarChart3,
  Cpu,
  Settings,
  ShieldCheck,
  Lock,
} from 'lucide-react';

interface NavItem {
  id: PageId;
  label: string;
  icon: React.ReactNode;
  badge?: number;
}

export const Sidebar: React.FC = () => {
  const { activePage, setActivePage, activeAlertsCount } = useSafeSenseApp();

  const navItems: NavItem[] = [
    {
      id: 'overview',
      label: 'Overview',
      icon: <LayoutDashboard className="w-5 h-5" />,
    },
    {
      id: 'live_monitoring',
      label: 'Live Monitoring',
      icon: <Video className="w-5 h-5" />,
    },
    {
      id: 'digital_twin',
      label: 'Digital Twin Map',
      icon: <Box className="w-5 h-5" />,
    },
    {
      id: 'alerts',
      label: 'Alerts',
      icon: <BellRing className="w-5 h-5" />,
      badge: activeAlertsCount,
    },
    {
      id: 'incident_review',
      label: 'Incident Review',
      icon: <History className="w-5 h-5" />,
    },
    {
      id: 'analytics',
      label: 'Analytics & Reports',
      icon: <BarChart3 className="w-5 h-5" />,
    },
    {
      id: 'devices',
      label: 'Devices & Sensors',
      icon: <Cpu className="w-5 h-5" />,
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: <Settings className="w-5 h-5" />,
    },
  ];

  return (
    <aside className="w-16 md:w-64 bg-[#0B1528] text-slate-300 flex flex-col shrink-0 border-r border-[#17253D] select-none">
      {/* Brand Header */}
      <div className="h-18 px-2 md:px-5 flex items-center gap-3 border-b border-[#17253D]">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#2563EB] to-cyan-500 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div className="min-w-0 hidden md:block">
          <div className="font-extrabold text-white text-base tracking-tight leading-tight truncate">
            SafeSense AI
          </div>
          <div className="text-[10px] text-cyan-400 font-semibold tracking-wide uppercase truncate mt-0.5">
            Campus Safety Intelligence
          </div>
        </div>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 px-1 md:px-3 py-4 space-y-1 overflow-y-auto">
        <div className="hidden md:block px-3 pb-2 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
          School Command Console
        </div>
        {navItems.map((item) => {
          const isActive = activePage === item.id;
          return (
            <button
              key={item.id} aria-label={item.label} title={item.label}
              onClick={() => setActivePage(item.id)}
              className={`w-full flex items-center justify-between px-3 md:px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                isActive
                  ? 'bg-[#2563EB] text-white shadow-sm shadow-blue-600/30'
                  : 'text-slate-400 hover:text-white hover:bg-[#14233D]'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className={isActive ? 'text-white' : 'text-slate-400'}>{item.icon}</span>
                <span className="hidden md:inline">{item.label}</span>
              </div>

              {item.badge !== undefined && item.badge > 0 && (
                <span
                  className={`hidden md:inline px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    isActive ? 'bg-white text-[#2563EB]' : 'bg-[#EF4444] text-white animate-pulse'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Privacy Architecture Bottom Card */}
      <div className="hidden md:block p-3.5 border-t border-[#17253D] bg-[#08101E]">
        <div className="p-3 rounded-xl bg-[#0E1A30] border border-[#1E304E] text-xs space-y-1">
          <div className="flex items-center gap-1.5 text-cyan-400 font-bold text-[11px]">
            <Lock className="w-3.5 h-3.5" />
            <span>Zero-CCTV Private Zones</span>
          </div>
          <p className="text-[10px] text-slate-400 leading-snug">
            Restrooms and blind spots protected by 60GHz radar & acoustic edge nodes only. No cameras.
          </p>
        </div>
      </div>
    </aside>
  );
};
