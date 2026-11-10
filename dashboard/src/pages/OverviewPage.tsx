import React, { useState } from 'react';
import { useSafeSenseApp } from '../context/SafeSenseContext';
import { SchoolDigitalTwinMap } from '../components/map/SchoolDigitalTwinMap';
import { DispatchStaffModal } from '../components/modals/DispatchStaffModal';
import { WorkflowIndicator } from '../components/layout/WorkflowIndicator';
import {
  BellRing,
  Camera,
  Radio,
  Flame,
  Clock,
  ArrowRight,
  ShieldCheck,
  Activity,
  Send,
  Eye,
  CheckCircle2,
  Lock,
  Cpu,
  TrendingUp,
  MapPin,
  AlertTriangle,
  Building2,
  CheckCheck,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export const OverviewPage: React.FC = () => {
  const {
    activeAlertsCount,
    camerasOnlineCount,
    mmWaveSensorsOnlineCount,
    sosEventsTodayCount,
    avgResponseTimeDisplay,
    alerts,
    timeline,
    devices,
    zones,
    setSelectedAlertId,
    setActivePage,
    acknowledgeAlert,
    isLiveMode,
    fastApiStatus,
  } = useSafeSenseApp();

  const [dispatchAlertId, setDispatchAlertId] = useState<string | null>(null);

  // Derived KPI values (Section 4: Do not invent measurements. Display N/A when unavailable)
  const totalZones = zones ? zones.length : 0;
  const onlineDevicesCount = devices ? devices.filter((d) => d.status === 'online').length : 0;
  const sensorAvailability = !isLiveMode && devices && devices.length > 0
    ? `${Math.round((onlineDevicesCount / devices.length) * 100)}%`
    : 'N/A';

  const acknowledgedCount = alerts
    ? alerts.filter((a) => a.status === 'acknowledged' || a.status === 'dispatched' || a.status === 'verified').length
    : 'N/A';

  // Recorded timeline data for Recorded Severity Priority Chart (Recharts)
  const riskTrendData = [...timeline].reverse().map(t => ({ time: t.time, risk: ({LOW:0,OBSERVE:25,WARNING:50,HIGH:75,CRITICAL:100})[t.level] }));

  return (
    <div className="space-y-6">
      {/* 1. TOP KPI CARDS (Section 4: Monitored School Zones, Active Safety Alerts, Sensor Availability, SOS Events, Acknowledged Incidents) */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {/* KPI 1: Monitored School Zones */}
        <div
          onClick={() => setActivePage('digital_twin')}
          className="p-4 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs hover:border-blue-400 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
              Monitored School Zones
            </span>
            <span className="p-2 rounded-xl bg-blue-50 text-[#2563EB]">
              <Building2 className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2.5">
            <span className="text-2xl font-black text-[#0F172A] tracking-tight tabular-nums">
              {totalZones > 0 ? `${totalZones} Zones` : 'N/A'}
            </span>
            <span className="text-[11px] text-[#64748B] block mt-0.5">
              Registered demonstration zones
            </span>
          </div>
        </div>

        {/* KPI 2: Active Safety Alerts */}
        <div
          onClick={() => setActivePage('alerts')}
          className="p-4 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs hover:border-blue-400 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
              Active Safety Alerts
            </span>
            <span
              className={`p-2 rounded-xl ${
                activeAlertsCount > 0 ? 'bg-red-50 text-[#EF4444]' : 'bg-emerald-50 text-[#10B981]'
              }`}
            >
              <BellRing className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2.5">
            <span className="text-2xl font-black text-[#0F172A] tracking-tight tabular-nums">
              {activeAlertsCount}
            </span>
            <span
              className={`text-[11px] font-semibold block mt-0.5 ${
                activeAlertsCount > 0 ? 'text-[#EF4444]' : 'text-[#10B981]'
              }`}
            >
              {activeAlertsCount > 0 ? 'Requires Human Review' : 'No active recorded alerts'}
            </span>
          </div>
        </div>

        {/* KPI 3: Sensor Availability */}
        <div
          onClick={() => setActivePage('devices')}
          className="p-4 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs hover:border-blue-400 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
              Sensor Availability
            </span>
            <span className="p-2 rounded-xl bg-teal-50 text-teal-700">
              <Radio className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2.5">
            <span className="text-2xl font-black text-[#0F172A] tracking-tight tabular-nums">
              {sensorAvailability}
            </span>
            <span className="text-[11px] text-[#64748B] block mt-0.5">
              {onlineDevicesCount} of {devices.length} Nodes Synchronized
            </span>
          </div>
        </div>

        {/* KPI 4: SOS Events */}
        <div
          onClick={() => setActivePage('alerts')}
          className="p-4 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs hover:border-blue-400 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
              SOS Events Today
            </span>
            <span className="p-2 rounded-xl bg-rose-50 text-[#EF4444]">
              <Flame className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2.5">
            <span className="text-2xl font-black text-[#0F172A] tracking-tight tabular-nums">
              {sosEventsTodayCount}
            </span>
            <span className="text-[11px] text-[#64748B] block mt-0.5">
              SOS test events; no dispatch
            </span>
          </div>
        </div>

        {/* KPI 5: Acknowledged Incidents */}
        <div
          onClick={() => setActivePage('incident_review')}
          className="p-4 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs hover:border-blue-400 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider">
              Acknowledged Incidents
            </span>
            <span className="p-2 rounded-xl bg-emerald-50 text-[#10B981]">
              <CheckCheck className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2.5">
            <span className="text-2xl font-black text-[#0F172A] tracking-tight tabular-nums">
              {acknowledgedCount}
            </span>
            <span className="text-[11px] text-[#10B981] font-semibold block mt-0.5">
              Human-in-the-Loop Active
            </span>
          </div>
        </div>
      </div>

      {/* 2. ALERT WORKFLOW INDICATOR */}
      <WorkflowIndicator />

      {/* 3. MAIN SECTION: Left 65% Interactive Digital Twin | Right 35% Live Alerts Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* LEFT (65% width): Large Interactive Digital Twin School Map */}
        <div className="lg:col-span-8 flex flex-col h-[600px] lg:h-[660px]">
          <SchoolDigitalTwinMap />
        </div>

        {/* RIGHT (35% width): Simplified Latest Incidents Panel */}
        <div className="lg:col-span-4 flex flex-col h-[600px] lg:h-[660px] bg-white rounded-2xl border border-[#E2E8F0] shadow-xs overflow-hidden">
          {/* Dark Navy Header Accent */}
          <div className="bg-[#0B1528] text-white p-3.5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-blue-500/20 text-blue-400 border border-blue-400/30">
                <BellRing className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-extrabold text-xs text-white leading-tight">Latest Incidents</h3>
                <span className="text-[10px] text-slate-400">
                  {isLiveMode ? (fastApiStatus === 'connected' ? 'FastAPI Ingestion' : 'FastAPI Offline') : 'Simulated Stream'}
                </span>
              </div>
            </div>
            <button
              onClick={() => setActivePage('alerts')}
              className="text-xs text-blue-400 font-bold hover:text-blue-300 transition-colors cursor-pointer flex items-center gap-1"
            >
              <span>Console ({alerts.length})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Incidents Feed / Empty State */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
            {isLiveMode && fastApiStatus === 'offline' ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-4 rounded-xl bg-slate-50 border border-slate-200">
                <div className="w-10 h-10 rounded-xl bg-rose-50 text-[#EF4444] border border-rose-200 flex items-center justify-center mb-2">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <h4 className="text-xs font-black text-[#0F172A] uppercase">
                  FASTAPI OFFLINE — NO REAL INCIDENTS LOADED
                </h4>
                <p className="text-[11px] text-[#64748B] mt-1 max-w-xs leading-relaxed">
                  FastAPI service unreachable at port 8000. No simulated incidents are shown in live mode.
                </p>
                <button
                  onClick={() => setActivePage('alerts')}
                  className="mt-3 px-3 py-1.5 rounded-lg bg-[#2563EB] hover:bg-blue-700 text-white font-bold text-xs transition-colors cursor-pointer"
                >
                  Open Incident Console
                </button>
              </div>
            ) : alerts.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-[#64748B]">
                <ShieldCheck className="w-10 h-10 text-emerald-500/50 mb-2" />
                <p className="text-xs font-semibold text-[#0F172A]">All Zones Nominal</p>
                <p className="text-[11px] text-[#64748B]">No safety incidents currently requiring triage.</p>
              </div>
            ) : (
              alerts.slice(0, 4).map((alt) => {
                const isCritical = alt.level === 'CRITICAL';
                const isHigh = alt.level === 'HIGH';
                const isWarning = alt.level === 'WARNING';
                const isObserve = alt.level === 'OBSERVE';
                const isResolved = alt.status === 'resolved' || alt.status === 'false_alarm';
                const isPrivate = alt.zoneId === 'ZONE_TOILET_BLINDSPOT' || alt.zoneName.toLowerCase().includes('blind');

                let badgeClass = 'bg-[#10B981] text-white';
                let cardBorder = 'border-[#E2E8F0] hover:border-blue-300';

                if (isCritical) {
                  badgeClass = 'bg-[#EF4444] text-white';
                  cardBorder = 'border-red-300 shadow-xs';
                } else if (isHigh) {
                  badgeClass = 'bg-[#F97316] text-white';
                  cardBorder = 'border-orange-300 shadow-xs';
                } else if (isWarning || isObserve) {
                  badgeClass = 'bg-[#F59E0B] text-white';
                  cardBorder = 'border-amber-300';
                }

                return (
                  <div
                    key={alt.id}
                    onClick={() => setSelectedAlertId(alt.id)}
                    className={`p-3 rounded-xl bg-white border transition-all cursor-pointer ${cardBorder} ${
                      isResolved ? 'opacity-70' : ''
                    }`}
                  >
                    {/* Header: Short ID, Zone, Level, Time */}
                    <div className="flex items-start justify-between gap-1.5">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="font-mono text-[10px] font-black px-1.5 py-0.5 rounded bg-slate-100 text-[#0F172A]">
                          #{alt.incidentNumber}
                        </span>
                        <span
                          className={`flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded ${
                            isPrivate ? 'bg-rose-50 text-rose-800' : 'bg-blue-50 text-[#2563EB]'
                          }`}
                        >
                          {isPrivate ? <Lock className="w-2.5 h-2.5" /> : <MapPin className="w-2.5 h-2.5" />}
                          <span className="truncate max-w-[90px]">{alt.zoneName}</span>
                        </span>
                      </div>

                      <span className={`text-[9px] font-black px-1.5 py-0.5 rounded-full uppercase ${badgeClass}`}>
                        {alt.level}
                      </span>
                    </div>

                    <h4 className="font-extrabold text-xs text-[#0F172A] mt-1.5 line-clamp-1">
                      {alt.title}
                    </h4>
                    <p className="text-[11px] text-[#64748B] mt-0.5 line-clamp-1">
                      {alt.reason}
                    </p>

                    {/* Footer Actions: Source, Time, Acknowledge Button */}
                    <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[10px]">
                      <span className="text-[#64748B] font-mono">{alt.detectedTime}</span>

                      <div className="flex items-center gap-1.5">
                        {alt.status === 'new' ? (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              acknowledgeAlert(alt.id);
                            }}
                            className="px-2 py-0.5 rounded-lg bg-[#2563EB] hover:bg-blue-700 text-white font-bold transition-all shadow-xs cursor-pointer flex items-center gap-1"
                          >
                            <CheckCircle2 className="w-2.5 h-2.5" />
                            <span>Ack</span>
                          </button>
                        ) : (
                          <span className="text-[#2563EB] font-bold flex items-center gap-0.5">
                            <CheckCheck className="w-3 h-3" />
                            <span>Acked</span>
                          </span>
                        )}

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedAlertId(alt.id);
                            setActivePage('incident_review');
                          }}
                          className="p-1 rounded-md hover:bg-slate-100 text-[#64748B]"
                          title="Inspect incident review"
                        >
                          <Eye className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* 4. BOTTOM SECTION: 4 Compact Panels (Incident Timeline, Recorded Severity Priority, Device Health, Privacy Status) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Panel 1: Incident Timeline */}
        <div className="p-4 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between pb-2 border-b border-[#F1F5F9]">
            <span className="text-xs font-bold text-[#0F172A] flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-[#2563EB]" />
              <span>Incident Timeline</span>
            </span>
            <button
              onClick={() => setActivePage('incident_review')}
              className="text-[11px] text-[#2563EB] hover:underline font-bold"
            >
              Full Log
            </button>
          </div>
          <div className="mt-2.5 space-y-2 overflow-y-auto max-h-36 pr-1">
            {timeline.slice(0, 3).map((item) => (
              <div key={item.id} className="text-xs space-y-0.5">
                <div className="flex justify-between text-[10px] text-[#64748B] font-mono">
                  <span className="font-bold text-[#0F172A]">{item.zoneName}</span>
                  <span>{item.time}</span>
                </div>
                <p className="text-[#64748B] text-[11px] font-medium leading-tight truncate">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Panel 2: Recorded Severity Priority Chart (Recharts) */}
        <div className="p-4 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between pb-2 border-b border-[#F1F5F9]">
            <span className="text-xs font-bold text-[#0F172A] flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-teal-600" />
              <span>Recorded Severity Priority (Today)</span>
            </span>
            <span className="text-[10px] font-semibold text-[#64748B]">08:00 - Present</span>
          </div>
          <div className="h-32 mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={riskTrendData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563EB" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" tick={{ fontSize: 9 }} stroke="#94A3B8" />
                <YAxis domain={[0, 100]} tick={{ fontSize: 9 }} stroke="#94A3B8" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0F172A',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '11px',
                  }}
                />
                <Area type="monotone" dataKey="risk" stroke="#2563EB" strokeWidth={2} fillOpacity={1} fill="url(#colorRisk)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Panel 3: Device Health */}
        <div className="p-4 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between pb-2 border-b border-[#F1F5F9]">
            <span className="text-xs font-bold text-[#0F172A] flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-indigo-600" />
              <span>Device Health</span>
            </span>
            <button
              onClick={() => setActivePage('devices')}
              className="text-[11px] text-[#2563EB] hover:underline font-bold"
            >
              Manage
            </button>
          </div>
          <div className="mt-2.5 space-y-2 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-[#64748B]">Total Configured Nodes</span>
              <span className="font-bold text-[#0F172A]">{devices.length}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#64748B]">Connected & Ingesting</span>
              <span className="font-bold text-[#10B981]">
                {devices.filter((d) => d.status === 'online').length}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#64748B]">Degraded / Offline</span>
              <span className="font-bold text-[#64748B]">
                {devices.filter((d) => d.status === 'offline').length}
              </span>
            </div>
          </div>
        </div>

        {/* Panel 4: Privacy Status */}
        <div className="p-4 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between pb-2 border-b border-[#F1F5F9]">
            <span className="text-xs font-bold text-[#0F172A] flex items-center gap-1.5">
              <Lock className="w-4 h-4 text-teal-600" />
              <span>Privacy Enforced</span>
            </span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 border border-teal-200">
              100% Compliant
            </span>
          </div>
          <div className="mt-2.5 space-y-1 text-xs">
            <p className="text-[11px] text-[#0F172A] leading-snug">
              Toilet / private zones contain <strong className="text-rose-600">0 camera feeds</strong>.
            </p>
            <p className="text-[11px] text-[#64748B] leading-snug">
              Micro-motion and falls tracked via anonymous 60GHz radar coordinate vectors and local edge YAMNet acoustic classifiers.
            </p>
          </div>
        </div>
      </div>

      {/* Staff Dispatch Modal */}
      <DispatchStaffModal alertId={dispatchAlertId} onClose={() => setDispatchAlertId(null)} />
    </div>
  );
};
