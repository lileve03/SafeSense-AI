import React, { useState } from 'react';
import { useSafeSenseApp } from '../context/SafeSenseContext';
import {
  History,
  Search,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  FileText,
  Clock,
  Eye,
  ShieldCheck,
  MapPin,
  Flame,
} from 'lucide-react';

export const IncidentReviewPage: React.FC = () => {
  const { alerts, setSelectedAlertId } = useSafeSenseApp();

  const [searchQuery, setSearchQuery] = useState('');
  const [outcomeFilter, setOutcomeFilter] = useState<'all' | 'resolved' | 'false_alarm'>('all');

  const historicalAlerts = alerts.filter((a) => {
    if (outcomeFilter === 'resolved' && a.status !== 'resolved') return false;
    if (outcomeFilter === 'false_alarm' && a.status !== 'false_alarm') return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const match =
        a.incidentNumber.toLowerCase().includes(q) ||
        a.title.toLowerCase().includes(q) ||
        a.zoneName.toLowerCase().includes(q) ||
        (a.resolutionNote && a.resolutionNote.toLowerCase().includes(q)) ||
        (a.falseAlarmReason && a.falseAlarmReason.toLowerCase().includes(q));
      if (!match) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="p-5 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-[#0F172A] flex items-center gap-2">
            <History className="w-5 h-5 text-[#2563EB]" />
            <span>Incident Review & Audit Archive</span>
          </h2>
          <p className="text-xs text-[#64748B] mt-1">
            Complete post-incident review logs, staff resolution statements, and false-alarm post-mortems for compliance and training.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-[#64748B] font-medium">
            Total Logged: <strong className="text-[#0F172A]">{alerts.length} Incidents</strong>
          </span>
        </div>
      </div>

      {/* Filter Tabs & Search Bar */}
      <div className="p-4 bg-white rounded-2xl border border-[#E2E8F0] shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={() => setOutcomeFilter('all')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              outcomeFilter === 'all'
                ? 'bg-[#0B1528] text-white shadow-xs'
                : 'text-[#64748B] hover:bg-slate-100'
            }`}
          >
            All Incident Logs ({alerts.length})
          </button>
          <button
            onClick={() => setOutcomeFilter('resolved')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              outcomeFilter === 'resolved'
                ? 'bg-[#10B981] text-white shadow-xs'
                : 'text-[#64748B] hover:bg-slate-100'
            }`}
          >
            Resolved ({alerts.filter((a) => a.status === 'resolved').length})
          </button>
          <button
            onClick={() => setOutcomeFilter('false_alarm')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              outcomeFilter === 'false_alarm'
                ? 'bg-[#F59E0B] text-white shadow-xs'
                : 'text-[#64748B] hover:bg-slate-100'
            }`}
          >
            False Alarms ({alerts.filter((a) => a.status === 'false_alarm').length})
          </button>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search notes, staff, incident #..."
            className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-slate-50 border border-[#E2E8F0] text-xs text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
          />
        </div>
      </div>

      {/* Audit Log Cards */}
      <div className="space-y-3">
        {historicalAlerts.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-2xl border border-[#E2E8F0] text-[#64748B]">
            No archived records matching current criteria.
          </div>
        ) : (
          historicalAlerts.map((alt) => {
            const isResolved = alt.status === 'resolved';
            const isFalseAlarm = alt.status === 'false_alarm';
            const isCritical = alt.level === 'CRITICAL';

            return (
              <div
                key={alt.id}
                className="p-5 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1.5 min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs font-black text-[#0F172A]">
                      #{alt.incidentNumber}
                    </span>

                    <span
                      className={`text-[9px] font-black px-2 py-0.5 rounded-full uppercase ${
                        isCritical
                          ? 'bg-red-100 text-[#EF4444]'
                          : alt.level === 'HIGH'
                          ? 'bg-orange-100 text-[#F97316]'
                          : 'bg-amber-100 text-[#F59E0B]'
                      }`}
                    >
                      {alt.level}
                    </span>

                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        isResolved
                          ? 'bg-emerald-50 text-[#10B981] border border-emerald-200'
                          : isFalseAlarm
                          ? 'bg-amber-50 text-[#F59E0B] border border-amber-200'
                          : 'bg-blue-50 text-[#2563EB] border border-blue-200'
                      }`}
                    >
                      {alt.status.replace('_', ' ').toUpperCase()}
                    </span>

                    <span className="text-[11px] font-mono text-[#64748B]">
                      {alt.detectedTime}
                    </span>
                  </div>

                  <h3 className="font-bold text-sm text-[#0F172A]">{alt.title}</h3>

                  <div className="flex items-center gap-1.5 text-xs text-[#64748B]">
                    <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>{alt.zoneName}</span>
                    <span>&bull;</span>
                    <span>Trigger: <strong className="text-[#0F172A]">{alt.triggerType}</strong></span>
                  </div>

                  {/* Closure Note if available */}
                  {(alt.resolutionNote || alt.falseAlarmReason) && (
                    <div className="mt-2 p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] text-xs">
                      <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider block">
                        Verified Audit Statement:
                      </span>
                      <p className="text-[#0F172A] font-medium mt-0.5">
                        &ldquo;{alt.resolutionNote || alt.falseAlarmReason}&rdquo;
                      </p>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0 md:pl-4 md:border-l md:border-[#E2E8F0]">
                  <button
                    onClick={() => setSelectedAlertId(alt.id)}
                    className="px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-[#0F172A] text-xs font-bold transition-colors flex items-center gap-1.5 cursor-pointer"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span>Audit Details</span>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
