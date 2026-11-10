import React, { useState, useMemo } from 'react';
import { useSafeSenseApp } from '../../context/SafeSenseContext';
import {sourceLabels} from '../../lib/incidentAnalytics';
import { Alert, RiskLevel, AlertStatus } from '../../types/safesense';
import {
  BellRing,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Flame,
  Send,
  Eye,
  RotateCcw,
  UserCheck,
  ShieldAlert,
  MapPin,
  Clock,
  Radio,
  Volume2,
  Video,
  Lock,
  ArrowUpDown,
  CheckCheck,
  ServerOff,
  Server,
  Play,
  ArrowRight,
  Loader2,
} from 'lucide-react';

interface ActiveHistoricalIncidentsProps {
  compact?: boolean;
  maxItems?: number;
  onDispatchAlert?: (id: string) => void;
}

export const ActiveHistoricalIncidents: React.FC<ActiveHistoricalIncidentsProps> = ({
  compact = false,
  maxItems,
  onDispatchAlert,
}) => {
  const {
    alerts,
    setSelectedAlertId,
    setActivePage,
    acknowledgeAlert,
    isLiveMode,
    setIsLiveMode,
    fastApiStatus,
    checkFastApiConnection,
    setIsDemoRunnerOpen,
    zones,
  } = useSafeSenseApp();

  const [activeTab, setActiveTab] = useState<'all' | 'pending' | 'acknowledged'>('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedZone, setSelectedZone] = useState<string>('all');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'newest' | 'oldest' | 'severity'>('newest');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [ackLoadingId, setAckLoadingId] = useState<string | null>(null);
  const [ackError, setAckError] = useState<string | null>(null);

  // Tab counts
  const totalCount = alerts.length;
  const pendingCount = useMemo(() => alerts.filter((a) => a.status === 'new').length, [alerts]);
  const acknowledgedCount = useMemo(
    () => alerts.filter((a) => a.status !== 'new' && a.status !== 'resolved' && a.status !== 'false_alarm').length,
    [alerts]
  );

  // Filter & Sort Logic (Newest / Oldest / Severity)
  const filteredIncidents = useMemo(() => {
    let result = alerts.filter((inc) => {
      if (sourceFilter !== 'all' && inc.source !== sourceFilter) return false;
      if (statusFilter !== 'all' && inc.status !== statusFilter) return false;
      // Tab filter:
      if (activeTab === 'pending' && inc.status !== 'new') return false;
      if (
        activeTab === 'acknowledged' &&
        (inc.status === 'new' || inc.status === 'resolved' || inc.status === 'false_alarm')
      )
        return false;

      // Zone filter:
      if (selectedZone !== 'all') {
        if (selectedZone === 'ZONE_TOILET_BLINDSPOT') {
          if (inc.zoneId !== 'ZONE_TOILET_BLINDSPOT' && !inc.zoneName.toLowerCase().includes('blind'))
            return false;
        } else if (inc.zoneId !== selectedZone) {
          return false;
        }
      }

      // Severity filter:
      if (selectedSeverity !== 'all') {
        if (selectedSeverity === 'CRITICAL' && inc.level !== 'CRITICAL') return false;
        if (selectedSeverity === 'HIGH' && inc.level !== 'HIGH') return false;
        if (selectedSeverity === 'WARNING' && inc.level !== 'WARNING' && inc.level !== 'OBSERVE') return false;
        if (selectedSeverity === 'LOW' && inc.level !== 'LOW') return false;
      }

      // Search box: incident id, zone, title, reason, source
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const match =
          inc.incidentNumber.toLowerCase().includes(q) ||
          inc.zoneName.toLowerCase().includes(q) ||
          inc.title.toLowerCase().includes(q) ||
          inc.reason.toLowerCase().includes(q) ||
          inc.triggerType.toLowerCase().includes(q) ||
          (inc.assignedStaff && inc.assignedStaff.toLowerCase().includes(q));
        if (!match) return false;
      }

      return true;
    });

    // Sorting: Newest / Oldest / Severity
    if (sortBy === 'severity') {
      result = [...result].sort((a, b) => b.riskScore - a.riskScore);
    } else if (sortBy === 'oldest') {
      result = [...result].reverse();
    }
    // 'newest' is already default natural order

    return result.slice(0, maxItems || undefined);
  }, [alerts, sourceFilter, statusFilter, activeTab, selectedZone, selectedSeverity, sortBy, searchQuery, maxItems]);

  // Acknowledge Action:
  // In LIVE mode: calls POST /incidents/{id}/ack and ONLY updates after backend confirms success.
  // In DEMO mode: calls acknowledgeAlert directly.
  const handleAcknowledge = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setAckLoadingId(id);
    setAckError(null);

    try {
      // Update state upon confirmed success
      await acknowledgeAlert(id);
    } catch (err: any) {
      console.warn('Acknowledge failed:', err);
      if (isLiveMode) {
        setAckError(`Backend ACK failed: ${err.message || 'FastAPI service offline'}`);
      } else {
        // Fallback for demo
        await acknowledgeAlert(id);
      }
    } finally {
      setAckLoadingId(null);
    }
  };

  const getSeverityBadge = (level: RiskLevel) => {
    switch (level) {
      case 'CRITICAL':
        return {
          bg: 'bg-red-50 text-[#EF4444] border-red-200',
          dot: 'bg-[#EF4444]',
          label: 'Critical',
        };
      case 'HIGH':
        return {
          bg: 'bg-orange-50 text-[#F97316] border-orange-200',
          dot: 'bg-[#F97316]',
          label: 'High',
        };
      case 'WARNING':
      case 'OBSERVE':
        return {
          bg: 'bg-amber-50 text-[#F59E0B] border-amber-200',
          dot: 'bg-[#F59E0B]',
          label: 'Attention',
        };
      case 'LOW':
      default:
        return {
          bg: 'bg-emerald-50 text-[#10B981] border-emerald-200',
          dot: 'bg-[#10B981]',
          label: 'Normal',
        };
    }
  };

  const getStatusBadge = (status: AlertStatus) => {
    switch (status) {
      case 'new':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
            Pending Review
          </span>
        );
      case 'acknowledged':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-900 border border-blue-300">
            Acknowledged
          </span>
        );
      case 'dispatched':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-900 border border-purple-300">
            Staff Dispatched
          </span>
        );
      case 'verified':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 text-indigo-900 border border-indigo-300">
            On-Site Verified
          </span>
        );
      case 'resolved':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
            Resolved
          </span>
        );
      case 'false_alarm':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-300">
            False Alarm
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-sm overflow-hidden flex flex-col">
      {/* 1. DARK NAVY ROUNDED HEADER (Exact Reference Style) */}
      <div className="bg-[#0B1528] text-white px-6 py-4.5 rounded-t-2xl">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Title & Total Count Pill */}
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-blue-500/20 text-[#2563EB] border border-blue-400/30">
              <BellRing className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-base font-black text-white tracking-wide uppercase">
                  ACTIVE & HISTORICAL INCIDENTS
                </h2>
                <span className="px-2.5 py-0.5 rounded-full bg-white/10 text-slate-300 text-xs font-mono font-bold">
                  {totalCount} Incidents
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {isLiveMode
                  ? 'Real-time FastAPI incident ingestion stream • Live verification log'
                  : 'Multi-modal edge sensor fusion simulation • Duty operator triage log'}
              </p>
            </div>
          </div>

          {/* Right Controls: Mode Toggle & Quick Simulation */}
          <div className="flex items-center gap-3">
            {/* Mode Switch Badge */}
            <button
              onClick={() => {
                const next = !isLiveMode;
                setIsLiveMode(next);
                if (next) checkFastApiConnection();
              }}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-bold border transition-all cursor-pointer shadow-xs ${
                isLiveMode
                  ? 'bg-blue-600 hover:bg-blue-700 text-white border-blue-500'
                  : 'bg-slate-800/80 hover:bg-slate-800 text-amber-300 border-slate-700'
              }`}
              title="Click to toggle between Live FastAPI and Demo Mode"
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isLiveMode
                    ? fastApiStatus === 'connected'
                      ? 'bg-emerald-400 animate-pulse'
                      : 'bg-rose-400'
                    : 'bg-amber-400'
                }`}
              />
              <span>{isLiveMode ? 'Live FastAPI Backend' : 'Simulated Demo Mode'}</span>
            </button>

            {/* Quick Demo Simulator Trigger */}
            <button
              onClick={() => {setIsLiveMode(false);setIsDemoRunnerOpen(true);}}
              className="px-3.5 py-1.5 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white font-bold text-xs flex items-center gap-1.5 shadow-xs transition-all cursor-pointer active:scale-95"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Simulate Incident</span>
            </button>
          </div>
        </div>
      </div>

      {/* 2. LARGE HORIZONTAL SEARCH/FILTER TOOLBAR */}
      <div className="p-4 bg-slate-50/90 border-b border-[#E2E8F0] flex flex-wrap items-center justify-between gap-3">
        {/* Three Tabs: All, Pending, Acknowledged */}
        <div className="flex items-center bg-white rounded-xl p-1 border border-[#E2E8F0] shadow-2xs">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'all'
                ? 'bg-[#0B1528] text-white shadow-xs'
                : 'text-[#64748B] hover:text-[#0F172A]'
            }`}
          >
            <span>All</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                activeTab === 'all' ? 'bg-white/20 text-white' : 'bg-slate-100 text-[#64748B]'
              }`}
            >
              {totalCount}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('pending')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'pending'
                ? 'bg-[#0B1528] text-white shadow-xs'
                : 'text-[#64748B] hover:text-[#0F172A]'
            }`}
          >
            <span>Pending</span>
            {pendingCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-red-500 text-white font-black animate-pulse">
                {pendingCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('acknowledged')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'acknowledged'
                ? 'bg-[#0B1528] text-white shadow-xs'
                : 'text-[#64748B] hover:text-[#0F172A]'
            }`}
          >
            <span>Acknowledged</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                activeTab === 'acknowledged' ? 'bg-white/20 text-white' : 'bg-slate-100 text-[#64748B]'
              }`}
            >
              {acknowledgedCount}
            </span>
          </button>
        </div>

        {/* Search, Zone Dropdown, Severity Dropdown, Sorting Dropdown */}
        <div className="flex flex-wrap items-center gap-2.5 flex-1 justify-end">
          {/* Search box: ID, zone or event title */}
          <div className="relative min-w-[200px] max-w-xs flex-1">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by ID, zone, or event title..."
              className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-white border border-[#E2E8F0] text-xs text-[#0F172A] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium shadow-2xs"
            />
          </div>

          <label className="flex items-center gap-2 text-xs font-medium text-[#64748B]">
            Source
            <select aria-label="Incident source" value={sourceFilter} onChange={e=>setSourceFilter(e.target.value)} className="max-w-full px-3 py-1.5 rounded-xl bg-white border border-[#E2E8F0] text-xs font-medium text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-2xs">
              <option value="all">All Sources</option>
              {Array.from(new Set(alerts.map(a=>a.source).filter((source):source is string=>!!source))).map(source=><option key={source} value={source}>{sourceLabels[source]||source}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2 text-xs font-medium text-[#64748B]">
            Status
            <select aria-label="Incident status" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)} className="max-w-full px-3 py-1.5 rounded-xl bg-white border border-[#E2E8F0] text-xs font-medium text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-2xs">
              <option value="all">All Statuses</option>
              {['new','acknowledged','dispatched','verified','resolved','false_alarm'].map(status=><option key={status} value={status}>{status.charAt(0).toUpperCase()+status.slice(1).replaceAll('_',' ')}</option>)}
            </select>
          </label>

          {/* Zone Dropdown */}
          <select
            value={selectedZone}
            onChange={(e) => setSelectedZone(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-white border border-[#E2E8F0] text-xs font-medium text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-2xs"
          >
            <option value="all">All Zones</option>
            <option value="ZONE_ENTRANCE">Entrance</option>
            <option value="ZONE_CORRIDOR_A">Corridor A</option>
            <option value="ZONE_CANTEEN">Canteen</option>
            <option value="ZONE_STAIRCASE">Staircase</option>
            <option value="ZONE_SCHOOL_HALL">School Hall</option>
            <option value="ZONE_TOILET_BLINDSPOT">Toilet Entrance / Blind Spot</option>
          </select>

          {/* Severity Dropdown */}
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-white border border-[#E2E8F0] text-xs font-medium text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-2xs"
          >
            <option value="all">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="WARNING">Attention / Observe</option>
            <option value="LOW">Normal</option>
          </select>

          {/* Sorting Dropdown: Newest / Oldest / Severity */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-3 py-1.5 rounded-xl bg-white border border-[#E2E8F0] text-xs font-semibold text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-2xs"
          >
            <option value="newest">Sort: Newest</option>
            <option value="oldest">Sort: Oldest</option>
            <option value="severity">Sort: Severity</option>
          </select>
        </div>
      </div>

      {/* Optional ACK error banner */}
      {ackError && (
        <div className="px-6 py-2 bg-red-50 border-b border-red-200 text-xs text-[#EF4444] font-medium flex items-center justify-between">
          <span>{ackError}</span>
          <button onClick={() => setAckError(null)} className="underline font-bold cursor-pointer">
            Dismiss
          </button>
        </div>
      )}

      {/* 3. STRUCTURED INCIDENT ROWS / CARDS OR COMPACT EMPTY STATE */}
      <div className="p-4 flex-1">
        {/* COMPACT EMPTY STATE WHEN FASTAPI IS OFFLINE IN LIVE MODE */}
        {isLiveMode && fastApiStatus === 'offline' ? (
          <div className="p-6 text-center rounded-2xl bg-slate-50 border border-slate-200 my-2">
            <div className="flex items-center justify-center gap-2 text-rose-600 mb-2">
              <ServerOff className="w-5 h-5" />
              <span className="font-extrabold text-sm uppercase">FastAPI Offline (Port 8000)</span>
            </div>
            <p className="text-xs text-[#64748B] max-w-md mx-auto leading-relaxed">
              No live FastAPI incidents loaded. As specified, simulated data is not displayed in Live Mode.
              Start the backend service or switch to Simulated Demo Mode to test incident workflows.
            </p>
            <div className="flex items-center justify-center gap-3 mt-4">
              <button
                onClick={() => checkFastApiConnection()}
                className="px-3.5 py-1.5 rounded-xl bg-white border border-slate-300 hover:bg-slate-100 text-[#0F172A] font-bold text-xs transition-colors cursor-pointer"
              >
                Retry Connection
              </button>
              <button
                onClick={() => setIsLiveMode(false)}
                className="px-3.5 py-1.5 rounded-xl bg-[#2563EB] hover:bg-blue-700 text-white font-bold text-xs transition-all shadow-xs cursor-pointer"
              >
                Switch to Demo Mode
              </button>
            </div>
          </div>
        ) : filteredIncidents.length === 0 ? (
          /* Empty Filter State */
          <div className="py-12 px-6 text-center rounded-2xl bg-slate-50 border border-slate-200 my-2">
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-[#2563EB] flex items-center justify-center mx-auto mb-2">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <h4 className="text-sm font-bold text-[#0F172A]">No Incidents Found</h4>
            <p className="text-xs text-[#64748B] max-w-sm mx-auto mt-1">
              No safety incidents match the selected criteria. Try adjusting your search query or filters.
            </p>
            {(searchQuery || selectedZone !== 'all' || selectedSeverity !== 'all' || activeTab !== 'all') && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSelectedZone('all');
                  setSelectedSeverity('all');
                  setActiveTab('all');
                }}
                className="mt-3 px-3.5 py-1.5 rounded-xl bg-white border border-[#E2E8F0] text-xs font-bold text-[#0F172A] hover:bg-slate-100 transition-colors cursor-pointer"
              >
                Reset Filters
              </button>
            )}
          </div>
        ) : (
          /* Structured Incident Cards */
          <div className="space-y-2.5">
            {filteredIncidents.map((incident) => {
              const sev = getSeverityBadge(incident.level);
              const isPending = incident.status === 'new';
              const isPrivateZone =
                incident.zoneId === 'ZONE_TOILET_BLINDSPOT' ||
                incident.zoneName.toLowerCase().includes('blind') ||
                incident.zoneName.toLowerCase().includes('toilet');

              return (
                <div
                  key={incident.id}
                  onClick={() => setSelectedAlertId(incident.id)}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-3.5 hover:shadow-md ${
                    isPending
                      ? 'bg-white border-amber-300 ring-1 ring-amber-400/20'
                      : 'bg-white border-[#E2E8F0] hover:border-blue-300'
                  }`}
                >
                  {/* Left Column: ID, Zone, Title, Reason */}
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    {/* Severity colored icon box */}
                    <div
                      className={`p-2.5 rounded-xl shrink-0 mt-0.5 border ${sev.bg}`}
                      title={`Risk Severity: ${incident.level}`}
                    >
                      {incident.level === 'CRITICAL' ? (
                        <Flame className="w-5 h-5 text-[#EF4444] animate-bounce" />
                      ) : incident.level === 'HIGH' ? (
                        <AlertTriangle className="w-5 h-5 text-[#F97316]" />
                      ) : incident.level === 'WARNING' || incident.level === 'OBSERVE' ? (
                        <ShieldAlert className="w-5 h-5 text-[#F59E0B]" />
                      ) : (
                        <CheckCircle2 className="w-5 h-5 text-[#10B981]" />
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        {/* Incident ID */}
                        <span className="font-mono text-xs font-black px-2 py-0.5 rounded-md bg-slate-100 text-[#0F172A] border border-[#E2E8F0]">
                          #{incident.incidentNumber}
                        </span>

                        {/* Zone with icon */}
                        <span
                          className={`flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md ${
                            isPrivateZone
                              ? 'bg-rose-50 text-rose-800 border border-rose-200'
                              : 'bg-blue-50 text-[#2563EB] border border-blue-200'
                          }`}
                        >
                          {isPrivateZone ? (
                            <Lock className="w-3 h-3 text-rose-600" />
                          ) : (
                            <MapPin className="w-3 h-3 text-[#2563EB]" />
                          )}
                          <span>{incident.zoneName}</span>
                        </span>

                        {/* Severity level badge */}
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${sev.bg}`}
                        >
                          {sev.label} ({incident.riskScore}/100)
                        </span>

                        {/* Status badge */}
                        {getStatusBadge(incident.status)}
                      </div>

                      {/* Event Title & Reason */}
                      <h4 className="text-sm font-extrabold text-[#0F172A] leading-snug">
                        {incident.title}
                      </h4>
                      <p className="text-xs text-[#64748B] mt-0.5 line-clamp-1">
                        {incident.reason}
                      </p>

                      {/* Metadata: Sensor Source & Timestamp */}
                      <div className="flex flex-wrap items-center gap-3 mt-2 text-[11px] text-[#64748B]">
                        <span className="flex items-center gap-1 font-semibold text-slate-700">
                          {incident.triggerType.toLowerCase().includes('radar') || isPrivateZone ? (
                            <Radio className="w-3.5 h-3.5 text-teal-600" />
                          ) : incident.triggerType.toLowerCase().includes('sos') ? (
                            <Flame className="w-3.5 h-3.5 text-rose-600" />
                          ) : incident.triggerType.toLowerCase().includes('acoustic') ? (
                            <Volume2 className="w-3.5 h-3.5 text-amber-600" />
                          ) : (
                            <Video className="w-3.5 h-3.5 text-[#2563EB]" />
                          )}
                          <span>Sensor: {incident.triggerType}</span>
                        </span>
                        {incident.notificationStatus && <span>Notification: {incident.notificationStatus}</span>}

                        <span className="flex items-center gap-1 font-mono">
                          <Clock className="w-3 h-3 text-slate-400" />
                          <span>{incident.detectedTime}</span>
                        </span>

                        {incident.assignedStaff && (
                          <span className="flex items-center gap-1 text-purple-700 font-semibold">
                            <UserCheck className="w-3 h-3" />
                            <span>Responder: {incident.assignedStaff}</span>
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Actions (Acknowledge Button & Details) */}
                  <div className="flex items-center gap-2 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100 shrink-0">
                    {/* Acknowledge Button */}
                    {isPending ? (
                      <button
                        onClick={(e) => handleAcknowledge(incident.id, e)}
                        disabled={ackLoadingId === incident.id}
                        className="px-3.5 py-1.5 rounded-xl bg-[#2563EB] hover:bg-blue-700 active:scale-95 text-white font-bold text-xs flex items-center gap-1.5 shadow-xs transition-all cursor-pointer disabled:opacity-50"
                        title="Acknowledge alert and alert duty staff"
                      >
                        {ackLoadingId === incident.id ? (
                          <>
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            <span>Acking...</span>
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Acknowledge</span>
                          </>
                        )}
                      </button>
                    ) : (
                      <span className="px-3 py-1.5 rounded-xl bg-blue-50 border border-blue-200 text-[#2563EB] text-xs font-bold flex items-center gap-1.5">
                        <CheckCheck className="w-3.5 h-3.5" />
                        <span>Acknowledged</span>
                      </span>
                    )}

                    {/* Dispatch Staff button */}
                    {onDispatchAlert && incident.status !== 'resolved' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDispatchAlert(incident.id);
                        }}
                        className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-[#0F172A] font-semibold text-xs flex items-center gap-1 transition-colors cursor-pointer"
                        title="Dispatch on-site campus staff"
                      >
                        <Send className="w-3 h-3" />
                        <span>Dispatch</span>
                      </button>
                    )}

                    {/* View Details button */}
                    <button
                      onClick={() => {
                        setSelectedAlertId(incident.id);
                        setActivePage('incident_review');
                      }}
                      className="p-1.5 rounded-xl hover:bg-slate-100 text-[#64748B] hover:text-[#0F172A] transition-colors cursor-pointer"
                      title="Inspect Full Incident Review Dossier"
                    >
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer info bar */}
      <div className="px-5 py-2.5 bg-slate-50 border-t border-[#E2E8F0] flex flex-wrap items-center justify-between text-[11px] text-[#64748B]">
        <span>
          Showing <strong>{filteredIncidents.length}</strong> of <strong>{totalCount}</strong> incidents
        </span>
        <span className="font-medium">
          FastAPI Protocol: <code className="font-mono text-[#2563EB]">POST /incidents/{'{id}'}/ack</code>
        </span>
      </div>
    </div>
  );
};
