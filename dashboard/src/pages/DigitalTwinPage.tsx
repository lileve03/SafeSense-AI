import React from 'react';
import { useSafeSenseApp } from '../context/SafeSenseContext';
import { SchoolDigitalTwinMap } from '../components/map/SchoolDigitalTwinMap';
import { PrivateAreaMonitoringView } from '../components/private-area/PrivateAreaMonitoringView';
import {
  Layers,
  Lock,
  Eye,
  Radio,
  Volume2,
  Flame,
  AlertTriangle,
  Play,
  RotateCcw,
  ShieldCheck,
  ArrowRight,
  Shield,
  Video,
  Box,
} from 'lucide-react';

export const DigitalTwinPage: React.FC = () => {
  const {
    zones,
    selectedZoneId,
    setSelectedZoneId,
    alerts,
    setSelectedAlertId,
    setIsDemoRunnerOpen,
    runScenario,
    resetDemo,
    monitoringView,
    setMonitoringView,
    openPrivateAreaMonitoring,
    closePrivateAreaMonitoring,
    setActivePage,
    isLiveMode,
  } = useSafeSenseApp();

  const selectedZone = zones.find((z) => z.id === selectedZoneId) || zones[0];
  const activeAlert = alerts.find(
    (a) => a.zoneId === selectedZone.id && a.status !== 'resolved' && a.status !== 'false_alarm'
  );

  // If in dedicated Private Area Monitoring View, render it full-page
  if (monitoringView === 'private_area') {
    return <PrivateAreaMonitoringView />;
  }

  // Otherwise render Campus Digital Twin Map with tab navigation
  return (
    <div className="space-y-6">
      {/* Header with View Switcher Tabs */}
      <div className="p-5 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-[#0F172A] flex items-center gap-2">
            <Layers className="w-5 h-5 text-[#2563EB]" />
            <span>Interactive Campus Digital Twin</span>
          </h2>
          <p className="text-xs text-[#64748B] mt-1">
            Real-time spatial visualization correlating multi-modal sensor telemetry across public and privacy-protected zones.
          </p>
        </div>

        {/* View Switcher: Campus Map vs Private Area 3D Monitoring */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-[#E2E8F0]">
            <button
              onClick={() => closePrivateAreaMonitoring()}
              className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all bg-white text-[#0F172A] shadow-xs flex items-center gap-1.5 cursor-pointer"
            >
              <Layers className="w-3.5 h-3.5 text-[#2563EB]" />
              <span>Campus Map</span>
            </button>
            <button
              onClick={() => openPrivateAreaMonitoring('ZONE_TOILET_BLINDSPOT')}
              className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all text-[#64748B] hover:text-[#0F172A] flex items-center gap-1.5 cursor-pointer"
            >
              <Lock className="w-3.5 h-3.5 text-rose-600" />
              <span>Private Area 3D View</span>
            </button>
          </div>

          <button
            onClick={() => setIsDemoRunnerOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-700 text-white text-xs font-bold shadow-xs cursor-pointer active:scale-95 transition-all"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Simulate Incident</span>
          </button>
          <button
            onClick={resetDemo}
            className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-[#0F172A] border border-[#E2E8F0] transition-colors cursor-pointer"
            title="Reset Model State"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Zone Quick-Selector Bar with Zone Type Distinction */}
      <div className="flex flex-wrap items-center gap-2 p-3.5 bg-white rounded-2xl border border-[#E2E8F0] shadow-xs">
        <span className="text-xs font-bold text-[#64748B] uppercase tracking-wider mr-2 pl-2">
          Select Zone:
        </span>
        {zones.map((z) => {
          const isSelected = selectedZoneId === z.id;
          return (
            <button
              key={z.id}
              onClick={() => {
                setSelectedZoneId(z.id);
                if (z.isPrivate) {
                  openPrivateAreaMonitoring(z.id);
                }
              }}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                isSelected
                  ? z.isPrivate
                    ? 'bg-[#EF4444] text-white shadow-xs'
                    : 'bg-[#2563EB] text-white shadow-xs'
                  : z.isPrivate
                  ? 'bg-rose-50 hover:bg-rose-100 text-rose-800 border border-rose-200'
                  : 'bg-slate-100 hover:bg-slate-200 text-[#0F172A]'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  z.level === 'CRITICAL'
                    ? 'bg-[#EF4444] animate-pulse'
                    : z.level === 'HIGH'
                    ? 'bg-[#F97316]'
                    : z.level === 'WARNING' || z.level === 'OBSERVE'
                    ? 'bg-[#F59E0B]'
                    : 'bg-[#10B981]'
                }`}
              />
              <span>{z.name}</span>
              {z.isPrivate ? (
                <Lock className={`w-3 h-3 ${isSelected ? 'text-white' : 'text-rose-600'}`} />
              ) : (
                <Eye className={`w-3 h-3 ${isSelected ? 'text-white' : 'text-[#2563EB]'}`} />
              )}
            </button>
          );
        })}
      </div>

      {/* Main Grid: 65% Interactive Map & 35% Selected Zone Deep Inspection */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className="lg:col-span-8 flex flex-col h-[600px] lg:h-[680px]">
          <SchoolDigitalTwinMap />
        </div>

        {/* Selected Zone Details Drawer */}
        <div className="lg:col-span-4 flex flex-col h-[600px] lg:h-[680px] bg-white rounded-2xl border border-[#E2E8F0] p-5 shadow-xs overflow-y-auto space-y-4">
          <div className="flex items-start justify-between pb-3 border-b border-[#F1F5F9]">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-base text-[#0F172A]">{selectedZone.name}</h3>
                {selectedZone.isPrivate ? (
                  <span className="p-1 rounded-md bg-rose-100 text-rose-800">
                    <Lock className="w-3.5 h-3.5" />
                  </span>
                ) : (
                  <span className="p-1 rounded-md bg-blue-100 text-[#2563EB]">
                    <Eye className="w-3.5 h-3.5" />
                  </span>
                )}
              </div>
              <p
                className={`text-xs font-semibold mt-0.5 ${
                  selectedZone.isPrivate ? 'text-rose-600' : 'text-[#2563EB]'
                }`}
              >
                {selectedZone.isPrivate
                  ? 'Privacy-Sensitive Blind Spot (No CCTV &bull; Radar Only)'
                  : 'Public Circulation Area (CCTV Keypoint Monitored)'}
              </p>
            </div>

            <span
              className={`text-xs font-black px-2.5 py-1 rounded-full uppercase ${
                selectedZone.level === 'CRITICAL'
                  ? 'bg-red-100 text-[#EF4444] border border-red-200'
                  : selectedZone.level === 'HIGH'
                  ? 'bg-orange-100 text-[#F97316] border border-orange-200'
                  : selectedZone.level === 'WARNING' || selectedZone.level === 'OBSERVE'
                  ? 'bg-amber-100 text-[#F59E0B] border border-amber-200'
                  : 'bg-emerald-100 text-[#10B981] border border-emerald-200'
              }`}
            >
              {selectedZone.level} ({selectedZone.riskScore}/100)
            </span>
          </div>

          {/* Privacy Protocol Badge if Private Zone */}
          {selectedZone.isPrivate ? (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-900 space-y-2">
              <div className="font-bold flex items-center gap-1.5 text-rose-800">
                <ShieldCheck className="w-4 h-4 text-rose-600" />
                <span>Strict Privacy Safeguards Active</span>
              </div>
              <p className="text-[11px] text-rose-700 leading-snug">
                Zero cameras, no speech transcription, and no identifiable biometrics. Monitoring is exclusively accomplished through anonymous 60GHz mmWave radar target vectors and on-device acoustic classifications.
              </p>
              <button
                onClick={() => openPrivateAreaMonitoring(selectedZone.id)}
                className="w-full mt-1 py-2 px-3 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-all shadow-xs cursor-pointer active:scale-95"
              >
                <Box className="w-3.5 h-3.5" />
                <span>Open Dedicated 3D Digital Twin View &rarr;</span>
              </button>
            </div>
          ) : (
            <div className="p-3.5 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-900 space-y-1">
              <div className="font-bold flex items-center gap-1.5 text-[#2563EB]">
                <Video className="w-4 h-4 text-[#2563EB]" />
                <span>Authorized Public-area Video Analysis</span>
              </div>
              <p className="text-[11px] text-blue-700 leading-snug">
                Recorded research video with real offline inference. Pose overlays are not anonymization. Candidate evidence is retained under the local access token and retention policy.
              </p>
              <button className="text-blue-700 underline" onClick={()=>setActivePage('live_monitoring')}>Open zone video monitoring</button>
            </div>
          )}

          {/* Real-time Diagnostics */}
          <div className="space-y-2 text-xs">
            <h4 className="font-bold text-[#0F172A] uppercase tracking-wider text-[11px]">
              Zone Telemetry & Inferences
            </h4>

            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] space-y-2">
              <div className="flex justify-between">
                <span className="text-[#64748B]">Occupancy Count:</span>
                <span className="font-bold text-[#0F172A]">{isLiveMode ? 'Unavailable (no count telemetry)':`${selectedZone.occupants} Individual(s) · simulation`}</span>
              </div>
              {selectedZone.isPrivate && (
                <>
                  <div className="flex justify-between">
                    <span className="text-[#64748B]">Estimated Target Distance:</span>
                    <span className="font-bold text-[#EF4444]">
                      {selectedZone.interpersonalDistanceMeters ?? 0.8} meters
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#64748B]">Kinematic Motion State:</span>
                    <span className="font-bold text-[#F59E0B]">
                      {selectedZone.motionLevel || 'Nominal'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#64748B]">Vertical Fall Indicator:</span>
                    <span
                      className={`font-bold ${
                        selectedZone.fallDetected ? 'text-[#EF4444]' : 'text-[#10B981]'
                      }`}
                    >
                      {selectedZone.fallDetected ? 'FALL CONFIRMED' : 'Clear (Standing)'}
                    </span>
                  </div>
                </>
              )}
              <div className="flex justify-between pt-1 border-t border-[#E2E8F0]">
                <span className="text-[#64748B]">Last Telemetry Sync:</span>
                <span className="font-mono text-[#0F172A]">{selectedZone.lastEventTime}</span>
              </div>
            </div>
          </div>

          {/* Active alert link if exists */}
          {activeAlert && (
            <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs text-red-900 space-y-2">
              <div className="flex items-center justify-between font-bold">
                <span className="flex items-center gap-1.5 text-red-800">
                  <AlertTriangle className="w-4 h-4 text-[#EF4444]" />
                  <span>Open Alert #{activeAlert.incidentNumber}</span>
                </span>
                <span className="text-[10px] bg-red-200 text-red-800 px-1.5 py-0.5 rounded">
                  {activeAlert.level}
                </span>
              </div>
              <p className="text-[11px] text-red-700 leading-snug">{activeAlert.title}</p>
              <button
                onClick={() => setSelectedAlertId(activeAlert.id)}
                className="w-full py-1.5 px-3 rounded-lg bg-[#2563EB] hover:bg-blue-700 text-white font-bold text-xs transition-colors flex items-center justify-center gap-1 cursor-pointer shadow-xs active:scale-95"
              >
                <span>Manage Alert & Dispatch</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Quick scenario triggers are available only for private zones. */}
          {selectedZone.isPrivate && (
            <div className="pt-2 border-t border-[#F1F5F9]">
              <h4 className="font-bold text-[#0F172A] text-[11px] uppercase tracking-wider mb-2">
                Quick Test In This Zone:
              </h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <button
                  onClick={() => runScenario('SCENARIO_7_MOTION_SCREAM')}
                  className="p-2.5 rounded-xl bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-800 font-bold text-left transition-colors cursor-pointer"
                >
                  Fall + Scream
                </button>
                <button
                  onClick={() => runScenario('SCENARIO_8_SOS_EMERGENCY')}
                  className="p-2.5 rounded-xl bg-red-50 hover:bg-red-100 border border-red-200 text-red-800 font-bold text-left transition-colors cursor-pointer"
                >
                  SOS Emergency
                </button>
                <button
                  onClick={() => runScenario('SCENARIO_4_RAPID_APPROACH')}
                  className="p-2.5 rounded-xl bg-amber-50 hover:bg-amber-100 border border-amber-200 text-amber-800 font-bold text-left transition-colors cursor-pointer"
                >
                  Rapid Approach
                </button>
                <button
                  onClick={() => runScenario('SCENARIO_1_NORMAL')}
                  className="p-2.5 rounded-xl bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-emerald-800 font-bold text-left transition-colors cursor-pointer"
                >
                  Normal Flow
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
