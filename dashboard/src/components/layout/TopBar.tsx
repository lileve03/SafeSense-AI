import React, { useState } from 'react';
import { useSafeSenseApp } from '../../context/SafeSenseContext';
import {
  Bell,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  User,
  ShieldCheck,
  ChevronDown,
  Activity,
  Server,
} from 'lucide-react';

export const TopBar: React.FC = () => {
  const {
    activeAlertsCount,
    unreadAlertsCount,
    alerts,
    setIsDemoRunnerOpen,
    resetDemo,
    setSelectedAlertId,
    setActivePage,
    isLiveMode,
    setIsLiveMode,
    fastApiStatus,
    checkFastApiConnection,
  } = useSafeSenseApp();

  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <header className="dashboard-header bg-white border-b border-[#E2E8F0] shadow-xs select-none relative z-30">
      {/* Left: Titles & Taglines (Requirement 3) */}
      <div className="dashboard-header-brand">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-sm font-extrabold text-[#0F172A] tracking-tight">
              SafeSense AI Dashboard
            </h1>

          </div>
          <p className="text-[11px] text-[#64748B] font-medium leading-tight mt-0.5">
            Privacy-First Campus Safety Monitoring
          </p>
        </div>

        <span className="dashboard-header-slogan rounded-full bg-blue-50 border border-blue-200 text-[#2563EB] font-bold uppercase tracking-wider">Safer Schools. Smarter Decisions.</span>

        <div className="dashboard-header-status">
          {/* Backend Status indicator */}
          {isLiveMode ? (
            <div
              onClick={() => checkFastApiConnection()}
              className={`flex items-center gap-1 px-2 h-8 rounded-lg text-[11px] font-semibold cursor-pointer border transition-colors ${
                fastApiStatus === 'connected'
                  ? 'bg-emerald-50 border-emerald-200 text-[#10B981]'
                  : fastApiStatus === 'checking'
                  ? 'bg-amber-50 border-amber-200 text-amber-800'
                  : 'bg-rose-50 border-rose-200 text-[#EF4444]'
              }`}
              title="Click to re-check FastAPI service"
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  fastApiStatus === 'connected'
                    ? 'bg-[#10B981] animate-pulse'
                    : fastApiStatus === 'checking'
                    ? 'bg-[#F59E0B] animate-ping'
                    : 'bg-[#EF4444]'
                }`}
              />
              <span>
                {fastApiStatus === 'connected'
                  ? 'FastAPI Connected'
                  : fastApiStatus === 'checking'
                  ? 'Connecting...'
                  : 'FastAPI Offline'}
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1 px-2 h-8 rounded-lg bg-emerald-50 border border-emerald-200 text-[#10B981] text-[11px] font-semibold">
              <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" />
              <span className="text-emerald-800">Demo Engine Online</span>
            </div>
          )}

          {/* Mode Switcher Toggle Button */}
          <button
            onClick={() => {
              const nextMode = !isLiveMode;
              setIsLiveMode(nextMode);
              if (nextMode) checkFastApiConnection();
            }}
            className={`flex items-center gap-1 px-2 h-8 rounded-lg border text-[11px] font-semibold cursor-pointer transition-all shadow-xs ${
              isLiveMode
                ? 'bg-blue-600 text-white border-blue-700'
                : 'bg-amber-50 hover:bg-amber-100 border-amber-200 text-amber-800'
            }`}
            title="Toggle between Backend Events and Simulated Demo Mode"
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${isLiveMode ? 'bg-white' : 'bg-[#F59E0B]'}`}
            />
            <span>{isLiveMode ? 'Mode: Backend Events' : 'Mode: Simulated Demo'}</span>
          </button>
        </div>
      </div>

      {/* Right: Actions, Simulator trigger, Notifications, Admin Profile */}
      <div className="dashboard-header-actions">
        {/* Run Demo Scenarios Button */}
        <button
          onClick={() => { setIsLiveMode(false); setIsDemoRunnerOpen(true); }}
          className="flex items-center gap-1.5 px-2.5 h-8 rounded-xl bg-[#2563EB] hover:bg-blue-700 text-white text-xs font-bold shadow-xs active:scale-95 transition-all cursor-pointer"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>Run Demo Scenarios</span>
        </button>

        {/* Reset Demo button */}
        <button
          disabled={isLiveMode} onClick={resetDemo}
          className="h-8 w-8 flex items-center justify-center rounded-xl bg-slate-50 hover:bg-slate-100 text-[#64748B] border border-[#E2E8F0] transition-colors cursor-pointer"
          title={isLiveMode ? "Reset is available only in simulation mode" : "Reset demonstration state"}
        >
          <RotateCcw className="w-4 h-4" />
        </button>

        {/* Notification Bell Dropdown */}
        <div className="relative">
          <button
            aria-label="Notifications"
            onClick={() => setShowNotifications(!showNotifications)}
            className="h-8 w-8 flex items-center justify-center rounded-xl bg-slate-50 hover:bg-slate-100 text-[#0F172A] border border-[#E2E8F0] relative transition-colors cursor-pointer"
          >
            <Bell className="w-4 h-4" />
            {unreadAlertsCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[#EF4444] text-white text-[10px] font-bold flex items-center justify-center animate-pulse">
                {unreadAlertsCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <div
              className="absolute right-0 mt-2 w-80 bg-white rounded-2xl shadow-xl border border-[#E2E8F0] p-3 z-50 animate-in fade-in zoom-in-95 duration-150"
              onMouseLeave={() => setShowNotifications(false)}
            >
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <span className="text-xs font-bold text-[#0F172A]">Alert Notifications</span>
                <span className="text-[11px] text-[#2563EB] font-bold">
                  {alerts.length} Total
                </span>
              </div>

              <div className="mt-2 max-h-64 overflow-y-auto space-y-2">
                {alerts.slice(0, 4).map((alt) => (
                  <div
                    key={alt.id}
                    onClick={() => {
                      setSelectedAlertId(alt.id);
                      setActivePage('alerts');
                      setShowNotifications(false);
                    }}
                    className="p-2.5 rounded-xl hover:bg-slate-50 cursor-pointer border border-transparent hover:border-[#E2E8F0] transition-all text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[#0F172A] truncate max-w-[170px]">
                        {alt.title}
                      </span>
                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                          alt.level === 'CRITICAL'
                            ? 'bg-red-100 text-[#EF4444]'
                            : alt.level === 'HIGH'
                            ? 'bg-orange-100 text-[#F97316]'
                            : 'bg-amber-100 text-[#F59E0B]'
                        }`}
                      >
                        {alt.level}
                      </span>
                    </div>
                    <div className="flex justify-between text-[11px] text-[#64748B] mt-1">
                      <span>{alt.zoneName}</span>
                      <span>{alt.detectedTime}</span>
                    </div>
                  </div>
                ))}
              </div>

              <button
                onClick={() => {
                  setActivePage('alerts');
                  setShowNotifications(false);
                }}
                className="w-full mt-2 py-1.5 text-center text-xs text-[#2563EB] font-bold hover:bg-blue-50 rounded-lg transition-colors"
              >
                View all in Alerts Console &rarr;
              </button>
            </div>
          )}
        </div>

        {/* Admin Profile */}
        <div className="dashboard-header-profile flex items-center gap-1.5 pl-2 border-l border-[#E2E8F0]">
          <div className="w-7 h-7 shrink-0 rounded-full bg-[#0B1528] text-white flex items-center justify-center font-bold text-xs shadow-xs">
            SC
          </div>
          <div className="text-left">
            <div className="text-xs font-bold text-[#0F172A] leading-tight">Demo Operator</div>
            <div className="text-[10px] text-[#64748B] leading-tight">Local demo session</div>
          </div>
        </div>
      </div>
    </header>
  );
};
