import React, { useState } from 'react';
import { useSafeSenseApp } from '../../context/SafeSenseContext';
import {
  X,
  AlertTriangle,
  Flame,
  ShieldCheck,
  CheckCircle2,
  Clock,
  MapPin,
  Send,
  UserCheck,
  RotateCcw,
  Activity,
  Lock,
} from 'lucide-react';
import { DispatchStaffModal } from './DispatchStaffModal';
import { IncidentEvidence } from '../incidents/IncidentEvidence';

export const AlertDetailModal: React.FC = () => {
  const {
    selectedAlertId,
    setSelectedAlertId,
    alerts,
    acknowledgeAlert,
    markVerified,
    markFalseAlarm,
    resolveIncident,
    isLiveMode,
  } = useSafeSenseApp();

  const [isDispatchOpen, setIsDispatchOpen] = useState(false);
  const [resolutionInput, setResolutionInput] = useState('');
  const [showResolvePrompt, setShowResolvePrompt] = useState(false);
  const [showFalseAlarmPrompt, setShowFalseAlarmPrompt] = useState(false);
  const [falseAlarmInput, setFalseAlarmInput] = useState('');

  if (!selectedAlertId) return null;

  const alert = alerts.find((a) => a.id === selectedAlertId);
  if (!alert) return null;

  const isCritical = alert.level === 'CRITICAL';
  const isHigh = alert.level === 'HIGH';
  const isWarning = alert.level === 'WARNING';
  const isObserve = alert.level === 'OBSERVE';
  const isResolved = alert.status === 'resolved' || alert.status === 'false_alarm';
  const needsAck = isLiveMode ? !alert.acknowledgedAt : alert.status==='new';

  const handleResolve = () => {
    resolveIncident(alert.id, resolutionInput || 'Verified safe by attending campus personnel.');
    setShowResolvePrompt(false);
    setResolutionInput('');
  };

  const handleFalseAlarm = () => {
    markFalseAlarm(alert.id, falseAlarmInput || 'Verified benign activity / accidental trigger.');
    setShowFalseAlarmPrompt(false);
    setFalseAlarmInput('');
  };

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
        <div className="w-full max-w-2xl bg-white rounded-3xl shadow-2xl border border-[#E2E8F0] overflow-hidden flex flex-col max-h-[92vh]">
          {/* Header */}
          <div className="px-6 py-4 bg-[#0B1528] text-white flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span
                className={`w-9 h-9 rounded-xl flex items-center justify-center ${
                  isCritical
                    ? 'bg-[#EF4444] text-white'
                    : isHigh
                    ? 'bg-[#F97316] text-white'
                    : isWarning || isObserve
                    ? 'bg-[#F59E0B] text-white'
                    : 'bg-[#10B981] text-white'
                }`}
              >
                {isCritical ? <Flame className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-base text-white">{alert.title}</h3>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      isCritical
                        ? 'bg-red-500 text-white'
                        : isHigh
                        ? 'bg-orange-500 text-white'
                        : isWarning || isObserve
                        ? 'bg-amber-500 text-white'
                        : 'bg-emerald-500 text-white'
                    }`}
                  >
                    {alert.level} ({alert.riskScore}/100)
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Incident #{alert.incidentNumber} &bull; Detected {alert.detectedTime}
                </p>
              </div>
            </div>

            <button
              onClick={() => setSelectedAlertId(null)}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="p-6 overflow-y-auto space-y-4">
            {isLiveMode && <IncidentEvidence key={alert.id} id={alert.id} />}
            {/* Metadata Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-2xl bg-[#F8FAFC] border border-[#E2E8F0] text-xs">
              <div>
                <span className="text-[11px] text-[#64748B] block">Location</span>
                <span className="font-bold text-[#0F172A] flex items-center gap-1 mt-0.5">
                  <MapPin className="w-3.5 h-3.5 text-[#2563EB]" />
                  <span className="truncate">{alert.zoneName}</span>
                </span>
              </div>

              <div>
                <span className="text-[11px] text-[#64748B] block">Status</span>
                <span className="font-bold capitalize text-[#2563EB] block mt-0.5">
                  {alert.status.replace('_', ' ')}
                </span>
              </div>

              <div>
                <span className="text-[11px] text-[#64748B] block">Assigned Responder</span>
                <span className="font-bold text-[#0F172A] block mt-0.5 truncate">
                  {alert.assignedStaff || 'Unassigned'}
                </span>
              </div>

              <div>
                <span className="text-[11px] text-[#64748B] block">Trigger Mechanism</span>
                <span className="font-bold text-[#0F172A] block mt-0.5 truncate">
                  {alert.triggerType}
                </span>
              </div>
            </div>

            {/* Explainable AI Decision Engine Summary */}
            <div className="p-4 rounded-2xl bg-white border border-[#E2E8F0] space-y-2">
              <span className="text-xs font-bold text-[#0F172A] block">
                Corroborating Evidence & Telemetry Rationale:
              </span>
              <p className="text-xs text-[#0F172A] leading-relaxed bg-[#F8FAFC] p-3 rounded-xl border border-[#E2E8F0]">
                {alert.reason}
              </p>
            </div>

            {/* Privacy Safeguard Verification */}
            <div className="p-3.5 rounded-2xl bg-teal-50 border border-teal-200 text-xs text-teal-900 flex items-start gap-2.5">
              <ShieldCheck className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold block text-teal-800">Privacy policy:</span>
                <p className="text-[11px] text-teal-700 mt-0.5">
                  Private zones retain sensor metadata only, with no video or speech recording. Authorized public-area evidence may contain identifiable people; pose overlays do not anonymize recordings.
                </p>
              </div>
            </div>

            {/* Inline Prompt for Resolution */}
            {showResolvePrompt && (
              <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-300 space-y-2 animate-in fade-in">
                <label className="block text-xs font-bold text-emerald-900">
                  Record resolution note to close this incident:
                </label>
                <input
                  type="text"
                  value={resolutionInput}
                  onChange={(e) => setResolutionInput(e.target.value)}
                  placeholder="e.g. Attending officer assisted student, verified no injury, area clear."
                  className="w-full px-3 py-2 rounded-xl bg-white border border-emerald-300 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium"
                />
                <div className="flex justify-end gap-2 pt-1">
                  <button
                    onClick={() => setShowResolvePrompt(false)}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-200 cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleResolve}
                    className="px-3 py-1.5 rounded-lg text-xs font-bold bg-[#10B981] hover:bg-emerald-600 text-white cursor-pointer"
                  >
                    Confirm Resolution
                  </button>
                </div>
              </div>
            )}

            {/* Inline Prompt for False Alarm */}
            {showFalseAlarmPrompt && (
              <div className="p-4 rounded-2xl bg-amber-50 border border-amber-300 space-y-2 animate-in fade-in">
                <label className="block text-xs font-bold text-amber-900">
                  Specify false alarm classification reason:
                </label>
                <input
                  type="text"
                  value={falseAlarmInput}
                  onChange={(e) => setFalseAlarmInput(e.target.value)}
                  placeholder="e.g. Playful cheer during recess / accidental drop."
                  className="w-full px-3 py-2 rounded-xl bg-white border border-amber-300 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-amber-500 font-medium"
                />
                <div className="flex justify-end gap-2 pt-1">
                  <button
                    onClick={() => setShowFalseAlarmPrompt(false)}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-200 cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleFalseAlarm}
                    className="px-3 py-1.5 rounded-lg text-xs font-bold bg-[#F59E0B] hover:bg-amber-600 text-white cursor-pointer"
                  >
                    Confirm False Alarm
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons Footer */}
          <div className="px-6 py-4 bg-slate-50 border-t border-[#E2E8F0] flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              {!isResolved && (
                <button
                  onClick={() => setShowFalseAlarmPrompt(!showFalseAlarmPrompt)}
                  className="text-xs font-semibold text-[#64748B] hover:text-[#0F172A] px-3 py-1.5 rounded-xl hover:bg-slate-200 transition-colors cursor-pointer"
                >
                  Mark False Alarm
                </button>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {/* Step 1: Acknowledge */}
              {!isResolved && needsAck && (
                <button
                  onClick={() => acknowledgeAlert(alert.id)}
                  className="px-3.5 py-2 rounded-xl bg-[#0B1528] hover:bg-slate-800 text-white text-xs font-bold transition-all shadow-xs flex items-center gap-1.5 cursor-pointer"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Acknowledge Alert</span>
                </button>
              )}

              {/* Step 2: Dispatch Staff */}
              {alert.status !== 'resolved' && alert.status !== 'false_alarm' && (
                <button
                  onClick={() => setIsDispatchOpen(true)}
                  className="px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-700 text-white text-xs font-bold shadow-xs transition-all flex items-center gap-1.5 cursor-pointer"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{alert.assignedStaff ? 'Re-Dispatch Staff' : 'Dispatch Staff'}</span>
                </button>
              )}

              {/* Step 3: Mark Verified */}
              {!needsAck && (alert.status === 'dispatched' || alert.status === 'acknowledged') && (
                <button
                  onClick={() => markVerified(alert.id)}
                  className="px-3.5 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold shadow-xs transition-all flex items-center gap-1.5 cursor-pointer"
                >
                  <UserCheck className="w-3.5 h-3.5" />
                  <span>Mark as Verified</span>
                </button>
              )}

              {/* Step 4: Resolve */}
              {!isResolved && (
                <button
                  onClick={() => setShowResolvePrompt(true)}
                  disabled={needsAck}
                  title={needsAck?'Acknowledge before resolving':'Record resolution'}
                  className="px-3.5 py-2 rounded-xl bg-[#10B981] hover:bg-emerald-600 text-white text-xs font-bold shadow-xs transition-all flex items-center gap-1.5 cursor-pointer"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Resolve Incident</span>
                </button>
              )}

              <button
                onClick={() => setSelectedAlertId(null)}
                className="px-3.5 py-2 rounded-xl text-xs font-semibold text-[#0F172A] hover:bg-slate-200 border border-[#E2E8F0] transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Staff Picker Modal */}
      <DispatchStaffModal alertId={isDispatchOpen ? alert.id : null} onClose={() => setIsDispatchOpen(false)} />
    </>
  );
};
