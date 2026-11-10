import React, { createContext, useContext, useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  PageId,
  Zone,
  SensorDevice,
  Alert,
  ActivityTimelineEvent,
  AlertStatus,
  RiskLevel,
  SystemSettings,
  DemoScenario,
  SensorObservation,
} from '../types/safesense';
import {
  INITIAL_ZONES,
  INITIAL_DEVICES,
  INITIAL_ALERTS,
  INITIAL_TIMELINE,
  INITIAL_STAFF_MEMBERS,
  DEMO_SCENARIOS,
  DEFAULT_SETTINGS,
} from '../data/schoolData';
import { api, post, toAlert, severityPriority } from '../lib/api';
import {isAnalyticsLocation,analyticsCanonicalUrl,operatorBaseUrl} from '../lib/analyticsReportsRoute';
import { playAlertChime } from '../lib/audio';

interface SafeSenseContextType {
  activePage: PageId;
  setActivePage: (page: PageId) => void;
  zones: Zone[];
  devices: SensorDevice[];
  alerts: Alert[];
  timeline: ActivityTimelineEvent[];
  sensorEvents: SensorObservation[];
  staffMembers: typeof INITIAL_STAFF_MEMBERS;
  settings: SystemSettings;
  updateSettings: (newSettings: Partial<SystemSettings>) => void;

  selectedZoneId: string | null;
  setSelectedZoneId: (id: string | null) => void;
  selectedAlertId: string | null;
  setSelectedAlertId: (id: string | null) => void;

  // Demo simulator state & controls
  isDemoRunnerOpen: boolean;
  setIsDemoRunnerOpen: (val: boolean) => void;
  activeScenarioId: string | null;
  runScenario: (scenarioId: string, zoneId?: string) => void;
  resetDemo: () => void;

  // Incident workflow actions
  acknowledgeAlert: (id: string) => void;
  dispatchStaff: (id: string, staffName: string) => void;
  markVerified: (id: string) => void;
  markFalseAlarm: (id: string, reason: string) => void;
  resolveIncident: (id: string, note: string) => void;

  // Device actions
  toggleDeviceStatus: (id: string) => void;

  // Export CSV
  exportIncidentsCsv: (subset?: Alert[]) => void;

  // Live Backend & FastAPI integration
  isLiveMode: boolean;
  setIsLiveMode: (live: boolean) => void;
  backendError: string | null;
  fastApiStatus: 'connected' | 'offline' | 'checking';
  checkFastApiConnection: () => Promise<void>;

  // Private Area Digital Twin Monitoring View
  monitoringView: 'school_map' | 'private_area';
  setMonitoringView: (view: 'school_map' | 'private_area') => void;
  openPrivateAreaMonitoring: (zoneId?: string) => void;
  closePrivateAreaMonitoring: () => void;

  // Derived KPI numbers
  activeAlertsCount: number;
  camerasOnlineCount: number;
  mmWaveSensorsOnlineCount: number;
  sosEventsTodayCount: number;
  avgResponseTimeDisplay: string;
  unreadAlertsCount: number;
}

const SafeSenseContext = createContext<SafeSenseContextType | null>(null);

export const SafeSenseProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const lastOperatorPage = useRef<PageId>('overview');
  const [activePage, setActivePageState] = useState<PageId>(() => window.location.hash === '#/developer/testing' ? 'developer_testing' : isAnalyticsLocation(window.location) ? 'analytics' : 'overview');
  const setActivePage = useCallback((page: PageId) => {
    page = page === 'reports' ? 'analytics' : page;
    setActivePageState(page);
    if(page === 'analytics'){
      lastOperatorPage.current=page;
      if(window.location.hash!=='#/analytics-reports')window.location.hash='/analytics-reports';
      window.history.replaceState(null,'',analyticsCanonicalUrl(window.location));
    } else if (page === 'developer_testing') {
      if (window.location.hash !== '#/developer/testing') window.location.hash = '/developer/testing';
    } else {
      lastOperatorPage.current = page;
      if (window.location.hash === '#/developer/testing' || isAnalyticsLocation(window.location)) window.history.replaceState(null, '', operatorBaseUrl(window.location));
    }
  }, []);
  useEffect(() => {
    const navigate = () => {
      if(isAnalyticsLocation(window.location)){
        window.history.replaceState(null,'',analyticsCanonicalUrl(window.location));
        setActivePageState('analytics');
      }else setActivePageState(previous => window.location.hash === '#/developer/testing' ? 'developer_testing' : previous === 'developer_testing' ? lastOperatorPage.current : previous === 'analytics' ? 'overview' : previous);
    };
    navigate();
    window.addEventListener('hashchange', navigate);
    window.addEventListener('popstate', navigate);
    return () => {window.removeEventListener('hashchange', navigate);window.removeEventListener('popstate', navigate);};
  }, []);
  const [zones, setZones] = useState<Zone[]>(() => JSON.parse(JSON.stringify(INITIAL_ZONES)));
  const [devices, setDevices] = useState<SensorDevice[]>(() => JSON.parse(JSON.stringify(INITIAL_DEVICES)));
  const [alerts, setAlerts] = useState<Alert[]>(() => JSON.parse(JSON.stringify(INITIAL_ALERTS)));
  const [timeline, setTimeline] = useState<ActivityTimelineEvent[]>(() => JSON.parse(JSON.stringify(INITIAL_TIMELINE)));
  const [staffMembers] = useState(INITIAL_STAFF_MEMBERS);
  const [settings, setSettings] = useState<SystemSettings>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('safesense_settings');
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch {}
      }
    }
    return DEFAULT_SETTINGS;
  });

  const [selectedZoneId, setSelectedZoneId] = useState<string | null>('ZONE_TOILET_BLINDSPOT');
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [isDemoRunnerOpen, setIsDemoRunnerOpen] = useState(false);
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);

  // Private Area Digital Twin Monitoring View
  const [monitoringView, setMonitoringView] = useState<'school_map' | 'private_area'>('school_map');

  const openPrivateAreaMonitoring = useCallback((zoneId?: string) => {
    if (zoneId) setSelectedZoneId(zoneId);
    else setSelectedZoneId('ZONE_TOILET_BLINDSPOT');
    setActivePage('digital_twin');
    setMonitoringView('private_area');
  }, []);

  const closePrivateAreaMonitoring = useCallback(() => {
    setMonitoringView('school_map');
  }, []);

  // FastAPI Live Mode vs Simulated Demo Mode
  const [isLiveMode, setIsLiveMode] = useState<boolean>(true);
  const [fastApiStatus, setFastApiStatus] = useState<'connected' | 'offline' | 'checking'>('offline');
  const [liveAlerts, setLiveAlerts] = useState<Alert[]>([]);

  const [backendError, setBackendError] = useState<string | null>(null);
  const [backendEvents, setBackendEvents] = useState<SensorObservation[]>([]);
  const checkFastApiConnection = useCallback(async () => {
    try {
      const state = await api('/state');
      setLiveAlerts(state.incidents.map((i: any) => toAlert(i, INITIAL_ZONES)));
      setBackendEvents(state.events);
      setFastApiStatus('connected');
      setBackendError(null);
    } catch (error) {
      setFastApiStatus('offline');
      setBackendError(String(error));
    }
  }, []);
  useEffect(() => {
    if (!isLiveMode) return;
    checkFastApiConnection();
    const timer = setInterval(checkFastApiConnection, 2000);
    return () => clearInterval(timer);
  }, [isLiveMode, checkFastApiConnection]);

  const backendAction = useCallback(async (id: string, status: string, note = '', staff = 'Dashboard operator') => {
    try {
      if (status === 'ACKNOWLEDGED') await post(`/incidents/${id}/ack`, { staff });
      else await post(`/incidents/${id}/review`, { status, staff, note });
      await checkFastApiConnection();
    } catch (error) { setBackendError(String(error)); }
  }, [checkFastApiConnection]);

  const effectiveZones = useMemo(() => !isLiveMode ? zones : INITIAL_ZONES.map(z => {
    const active = liveAlerts.filter(a => a.zoneId === z.id && !['resolved', 'false_alarm'].includes(a.status));
    const highest = [...active].sort((a,b) => b.riskScore-a.riskScore)[0];
    const last = backendEvents.find(e => e.zone_id === z.id);
    return { ...z, level: highest?.level || 'LOW' as RiskLevel, riskScore: highest?.riskScore || 0,
      occupants: 0, radarTargets: [], interpersonalDistanceMeters: undefined, motionLevel: undefined,
      fallDetected: active.some(a => a.explainableFactors.some(f => f.startsWith('fall ('))),
      acousticEvent: undefined, lastEventTime: last?.timestamp || 'No recorded event',
      latestEventDesc: highest?.reason || last?.reason || 'No recorded observation; hardware telemetry unavailable' };
  }), [isLiveMode,zones,liveAlerts,backendEvents]);
  const effectiveTimeline = useMemo(() => !isLiveMode ? timeline : backendEvents.map(e => ({
    id: e.id, time: e.timestamp, zoneId: e.zone_id,
    zoneName: INITIAL_ZONES.find(z => z.id === e.zone_id)?.name || e.zone_id,
    description: `${e.reason} | ${e.processing_mode} | ${e.source}`, type: 'sensor' as const, level: e.level,
  })), [isLiveMode,timeline,backendEvents]);
  const effectiveDevices = useMemo(() => !isLiveMode ? devices : devices.map(d => ({...d,
    status: 'offline' as const, currentReading: 'No live hardware connection verified', lastUpdate: 'Unavailable', isSimulated: true,
  })), [isLiveMode,devices]);

  // When in live mode: do NOT show fake alerts; show real liveAlerts (or empty if offline)
  const effectiveAlerts = useMemo(
    () => (isLiveMode ? liveAlerts : alerts),
    [isLiveMode, liveAlerts, alerts, backendAction]
  );

  // Derived counts based on effectiveAlerts
  const activeAlertsCount = useMemo(
    () => effectiveAlerts.filter((a) => a.status !== 'resolved' && a.status !== 'false_alarm').length,
    [effectiveAlerts]
  );

  const unreadAlertsCount = useMemo(
    () => effectiveAlerts.filter((a) => a.status === 'new').length,
    [effectiveAlerts]
  );

  const camerasOnlineCount = useMemo(
    () => effectiveDevices.filter((d) => d.type === 'cctv' && d.status === 'online').length,
    [effectiveDevices]
  );

  const mmWaveSensorsOnlineCount = useMemo(
    () => effectiveDevices.filter((d) => d.type === 'radar' && d.status === 'online').length,
    [effectiveDevices]
  );

  const sosEventsTodayCount = useMemo(
    () => effectiveAlerts.filter((a) => (a.level === 'CRITICAL' || a.triggerType.toLowerCase().includes('sos')) && (!isLiveMode || new Date(a.detectedTime).toLocaleDateString('en-CA', {timeZone:'Asia/Singapore'}) === new Date().toLocaleDateString('en-CA', {timeZone:'Asia/Singapore'}))).length,
    [effectiveAlerts, isLiveMode]
  );

  const avgResponseTimeDisplay = isLiveMode ? 'Not measured' : 'Simulation: 1m 24s';

  const updateSettings = useCallback((newSettings: Partial<SystemSettings>) => {
    const updated = { ...settings, ...newSettings, privacyStrictRadarOnly: true };
    localStorage.setItem('safesense_settings', JSON.stringify(updated));
    setSettings(updated);
  }, [settings]);

  // Workflow Action 1: Acknowledge
  const acknowledgeAlert = useCallback(
    async (id: string) => {
      if (isLiveMode) { await backendAction(id, 'ACKNOWLEDGED'); return; }

      const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setAlerts((prev) =>
        prev.map((a) => {
          if (a.id !== id) return a;
          return {
            ...a,
            status: 'acknowledged' as AlertStatus,
            timeline: [...a.timeline, { time: nowStr, event: 'Alert acknowledged by duty officer' }],
          };
        })
      );

      const target = (isLiveMode ? liveAlerts : alerts).find((a) => a.id === id);
      if (target) {
        setTimeline((prev) => [
          {
            id: `EVT_${Date.now()}`,
            time: nowStr,
            zoneId: target.zoneId,
            zoneName: target.zoneName,
            description: `Alert #${target.incidentNumber} acknowledged by duty operator`,
            type: 'staff',
            level: target.level,
          },
          ...prev,
        ]);
      }

      playAlertChime('CONFIRM');
    },
    [isLiveMode, liveAlerts, alerts, backendAction]
  );

  // Workflow Action 2: Dispatch Staff
  const dispatchStaff = useCallback(
    (id: string, staffName: string) => {
      if (isLiveMode) { void backendAction(id, 'DISPATCHED', 'Operator recorded zone assignment; notification delivery is recorded separately', staffName); return; }
      const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setAlerts((prev) =>
        prev.map((a) => {
          if (a.id !== id) return a;
          return {
            ...a,
            status: 'dispatched' as AlertStatus,
            assignedStaff: staffName,
            dispatchTime: nowStr,
            timeline: [
              ...a.timeline,
              { time: nowStr, event: `Responder dispatched: ${staffName}` },
            ],
          };
        })
      );

      const target = alerts.find((a) => a.id === id);
      if (target) {
        setTimeline((prev) => [
          {
            id: `EVT_${Date.now()}`,
            time: nowStr,
            zoneId: target.zoneId,
            zoneName: target.zoneName,
            description: `${staffName} dispatched to ${target.zoneName} for Incident #${target.incidentNumber}`,
            type: 'staff',
            level: target.level,
          },
          ...prev,
        ]);
      }

      playAlertChime('CONFIRM');
    },
    [alerts, isLiveMode, backendAction]
  );

  // Workflow Action 3: Mark Verified
  const markVerified = useCallback(
    (id: string) => {
      if (isLiveMode) { void backendAction(id, 'VERIFIED', 'Operator marked reviewed'); return; }
      const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setAlerts((prev) =>
        prev.map((a) => {
          if (a.id !== id) return a;
          return {
            ...a,
            status: 'verified' as AlertStatus,
            verifiedTime: nowStr,
            timeline: [
              ...a.timeline,
              { time: nowStr, event: 'On-site responder arrived and physically verified situation' },
            ],
          };
        })
      );

      const target = alerts.find((a) => a.id === id);
      if (target) {
        setTimeline((prev) => [
          {
            id: `EVT_${Date.now()}`,
            time: nowStr,
            zoneId: target.zoneId,
            zoneName: target.zoneName,
            description: `On-site inspection in progress for Incident #${target.incidentNumber}`,
            type: 'staff',
            level: target.level,
          },
          ...prev,
        ]);
      }

      playAlertChime('CONFIRM');
    },
    [alerts, isLiveMode, backendAction]
  );

  // Workflow Action 4: Mark False Alarm
  const markFalseAlarm = useCallback(
    (id: string, reason: string) => {
      if (isLiveMode) { void backendAction(id, 'FALSE_ALARM', reason); return; }
      const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const target = alerts.find((a) => a.id === id);

      setAlerts((prev) =>
        prev.map((a) => {
          if (a.id !== id) return a;
          return {
            ...a,
            status: 'false_alarm' as AlertStatus,
            isFalseAlarm: true,
            falseAlarmReason: reason,
            resolvedTime: nowStr,
            timeline: [
              ...a.timeline,
              { time: nowStr, event: `Incident classified as False Alarm: ${reason}` },
            ],
          };
        })
      );

      if (target) {
        // Lower zone risk level if no other open alerts in zone
        setZones((prev) =>
          prev.map((z) => {
            if (z.id !== target.zoneId) return z;
            return {
              ...z,
              level: 'LOW',
              riskScore: Math.min(z.riskScore, 18),
              latestEventDesc: `False alarm verified benign: ${reason}`,
            };
          })
        );

        setTimeline((prev) => [
          {
            id: `EVT_${Date.now()}`,
            time: nowStr,
            zoneId: target.zoneId,
            zoneName: target.zoneName,
            description: `Incident #${target.incidentNumber} closed as False Alarm: ${reason}`,
            type: 'system',
            level: 'LOW',
          },
          ...prev,
        ]);
      }

      playAlertChime('CONFIRM');
    },
    [alerts, isLiveMode, backendAction]
  );

  // Workflow Action 5: Resolve Incident
  const resolveIncident = useCallback(
    (id: string, note: string) => {
      if (isLiveMode) { void backendAction(id, 'RESOLVED', note); return; }
      const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const target = alerts.find((a) => a.id === id);

      setAlerts((prev) =>
        prev.map((a) => {
          if (a.id !== id) return a;
          return {
            ...a,
            status: 'resolved' as AlertStatus,
            resolutionNote: note,
            resolvedTime: nowStr,
            timeline: [
              ...a.timeline,
              { time: nowStr, event: `Incident resolved: ${note}` },
            ],
          };
        })
      );

      if (target) {
        setZones((prev) =>
          prev.map((z) => {
            if (z.id !== target.zoneId) return z;
            return {
              ...z,
              level: 'LOW',
              riskScore: 14,
              fallDetected: false,
              motionLevel: 'Low',
              latestEventDesc: 'Incident resolved by staff on-site. Baseline normal.',
            };
          })
        );

        setTimeline((prev) => [
          {
            id: `EVT_${Date.now()}`,
            time: nowStr,
            zoneId: target.zoneId,
            zoneName: target.zoneName,
            description: `Incident #${target.incidentNumber} resolved: ${note}`,
            type: 'staff',
            level: 'LOW',
          },
          ...prev,
        ]);
      }

      playAlertChime('CONFIRM');
    },
    [alerts, isLiveMode, backendAction]
  );

  // Device Toggle Online/Offline
  const toggleDeviceStatus = useCallback((id: string) => {
    if (isLiveMode) { setBackendError('Hardware unavailable. Device toggles work only in explicit simulation mode.'); return; }
    setDevices((prev) =>
      prev.map((d) => {
        if (d.id !== id) return d;
        const newStatus = d.status === 'online' ? 'offline' : 'online';
        return {
          ...d,
          status: newStatus,
          lastUpdate: 'Just now',
          currentReading: newStatus === 'offline' ? 'No telemetry received / Disconnected' : 'Connected & Active',
        };
      })
    );
  }, [isLiveMode]);

  // Hackathon Scenario Simulator Engine
  const runScenario = useCallback(
    (scenarioId: string, zoneId?: string) => {
      if (isLiveMode) { setBackendError('Switch to Simulated Demo mode to run local illustrated scenarios. Use Video Analysis for real models.'); return; }
      const originalScenario = DEMO_SCENARIOS.find((s) => s.id === scenarioId);
      if (!originalScenario || (zoneId && !zones.some(zone => zone.id === zoneId))) return;
      const score = originalScenario.expectedScore;
      const bands = settings.thresholds;
      const level: RiskLevel = originalScenario.expectedLevel === 'CRITICAL' ? 'CRITICAL'
        : score <= bands.low ? 'LOW' : score <= bands.observe ? 'OBSERVE'
        : score <= bands.warning ? 'WARNING' : score <= bands.high ? 'HIGH' : 'CRITICAL';
      const sc = { ...originalScenario, zoneId: zoneId || originalScenario.zoneId, expectedLevel: level };

      setActiveScenarioId(scenarioId);
      const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      // 1. Update Target Zone
      setZones((prev) =>
        prev.map((z) => {
          if (z.id !== sc.zoneId) return z;
          return {
            ...z,
            level: sc.expectedLevel,
            riskScore: sc.expectedScore,
            lastEventTime: nowStr,
            latestEventDesc: sc.explanation,
            interpersonalDistanceMeters: sc.radarState?.distance,
            motionLevel: sc.radarState?.motion,
            fallDetected: sc.radarState?.fall,
            acousticEvent: sc.radarState?.acoustic,
            radarTargets:
              sc.radarState && sc.radarState.targets > 0
                ? [
                    { id: 'T1', x: 42, y: 50, vx: 0.1, vy: 0.1, speed: 0.3, state: sc.radarState.fall ? 'fallen' : 'walking' },
                    ...(sc.radarState.targets > 1
                      ? [
                          {
                            id: 'T2',
                            x: 48,
                            y: 48,
                            vx: 0.8,
                            vy: 0.3,
                            speed: sc.radarState.motion === 'Violent' ? 2.5 : 1.2,
                            state: (sc.radarState.motion === 'Violent' ? 'running' : 'standing') as 'running' | 'standing',
                          },
                        ]
                      : []),
                  ]
                : z.radarTargets,
          };
        })
      );

      // Select this zone so user immediately sees it
      setSelectedZoneId(sc.zoneId);

      // 2. If warning, high, or critical, generate a real Alert
      if (sc.expectedLevel === 'WARNING' || sc.expectedLevel === 'HIGH' || sc.expectedLevel === 'CRITICAL') {
        const incNum = `INC-${Math.floor(100 + Math.random() * 900)}`;
        const targetZone = zones.find((z) => z.id === sc.zoneId);
        const zoneName = targetZone ? targetZone.name : 'Target Zone';

        const newAlert: Alert = {
          id: `ALT-SIM-${Date.now()}`,
          incidentNumber: incNum,
          zoneId: sc.zoneId,
          zoneName,
          level: sc.expectedLevel,
          riskScore: sc.expectedScore,
          title: sc.name.replace(/^\d+\.\s*/, ''),
          triggerType: sc.expectedLevel === 'CRITICAL' ? 'Hardware SOS Panic Trigger' : 'Multimodal Sensor Fusion',
          reason: sc.explanation,
          explainableFactors: sc.factors,
          detectedTime: 'Just now',
          status: 'new',
          triggeringSensors: targetZone ? targetZone.sensorIds : [],
          timeline: [
            { time: nowStr, event: `Event triggered: ${sc.name}` },
            { time: nowStr, event: `Risk engine evaluated score: ${sc.expectedScore}/100 (${sc.expectedLevel})` },
            { time: nowStr, event: 'Human verification alert broadcast to duty console' },
          ],
        };

        setAlerts((prev) => [newAlert, ...prev]);
        setSelectedAlertId(newAlert.id);

        if (settings.audioAlerts) {
          playAlertChime(sc.expectedLevel);
        }
      } else {
        playAlertChime('CONFIRM');
      }

      // 3. Add to activity timeline
      const targetZone = zones.find((z) => z.id === sc.zoneId);
      setTimeline((prev) => [
        {
          id: `EVT_${Date.now()}`,
          time: nowStr,
          zoneId: sc.zoneId,
          zoneName: targetZone ? targetZone.name : sc.zoneId,
          description: `Scenario ran: ${sc.name} â€” ${sc.explanation}`,
          type: sc.expectedLevel === 'LOW' ? 'system' : 'alert',
          level: sc.expectedLevel,
        },
        ...prev,
      ]);
    },
    [zones, settings.audioAlerts, settings.thresholds, isLiveMode]
  );

  // Reset demo to baseline
  const resetDemo = useCallback(() => {
    if (isLiveMode) { setBackendError('Reset is available only for local simulation. Backend incident history is preserved.'); return; }
    setZones(JSON.parse(JSON.stringify(INITIAL_ZONES)));
    setDevices(JSON.parse(JSON.stringify(INITIAL_DEVICES)));
    setAlerts(JSON.parse(JSON.stringify(INITIAL_ALERTS)));
    setTimeline(JSON.parse(JSON.stringify(INITIAL_TIMELINE)));
    setSelectedZoneId('ZONE_TOILET_BLINDSPOT');
    setSelectedAlertId(null);
    setActiveScenarioId(null);
    playAlertChime('CONFIRM');
  }, [isLiveMode]);

  // Export CSV of alerts & incidents
  const exportIncidentsCsv = useCallback((subset?: Alert[]) => {
    const headers = [
      'Incident Number',
      'Alert ID',
      'Location',
      'Risk Level',
      'Risk Score',
      'Title',
      'Trigger Type',
      'Detected Time',
      'Status',
      'Assigned Staff',
      'Resolution Note',
      'Processing Mode',
      'Evidence',
    ];

    const rows = (subset || effectiveAlerts).map((a) => [
      `"${a.incidentNumber}"`,
      `"${a.id}"`,
      `"${a.zoneName}"`,
      `"${a.level}"`,
      a.riskScore,
      `"${a.title.replace(/"/g, '""')}"`,
      `"${a.triggerType.replace(/"/g, '""')}"`,
      `"${a.detectedTime}"`,
      `"${a.status}"`,
      `"${a.assignedStaff || 'Unassigned'}"`,
      `"${(a.resolutionNote || a.falseAlarmReason || '').replace(/"/g, '""')}"`,
      `"${a.processingMode || 'simulation'}"`,
      `"${a.explainableFactors.join('; ').replace(/"/g, '""')}"`,
    ]);

    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `SafeSense_Incidents_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [effectiveAlerts]);

  return (
    <SafeSenseContext.Provider
      value={{
        activePage,
        setActivePage,
        zones: effectiveZones,
        devices: effectiveDevices,
        alerts: effectiveAlerts,
        timeline: effectiveTimeline,
        sensorEvents: isLiveMode ? backendEvents : [],
        staffMembers,
        settings,
        updateSettings,
        selectedZoneId,
        setSelectedZoneId,
        selectedAlertId,
        setSelectedAlertId,
        isDemoRunnerOpen,
        setIsDemoRunnerOpen,
        activeScenarioId,
        runScenario,
        resetDemo,
        acknowledgeAlert,
        dispatchStaff,
        markVerified,
        markFalseAlarm,
        resolveIncident,
        toggleDeviceStatus,
        exportIncidentsCsv,
        isLiveMode,
        setIsLiveMode,
        fastApiStatus,
        backendError,
        checkFastApiConnection,
        monitoringView,
        setMonitoringView,
        openPrivateAreaMonitoring,
        closePrivateAreaMonitoring,
        activeAlertsCount,
        camerasOnlineCount,
        mmWaveSensorsOnlineCount,
        sosEventsTodayCount,
        avgResponseTimeDisplay,
        unreadAlertsCount,
      }}
    >
      {children}
    </SafeSenseContext.Provider>
  );
};

export const useSafeSenseApp = () => {
  const ctx = useContext(SafeSenseContext);
  if (!ctx) throw new Error('useSafeSenseApp must be used within SafeSenseProvider');
  return ctx;
};
