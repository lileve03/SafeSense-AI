import React from 'react';
import {
  Radio,
  Cpu,
  BellRing,
  CheckCircle2,
  Send,
  ShieldCheck,
  ChevronRight,
} from 'lucide-react';
import { useSafeSenseApp } from '../../context/SafeSenseContext';

export const WorkflowIndicator: React.FC = () => {
  const { alerts, activeAlertsCount } = useSafeSenseApp();

  const hasNew = alerts.some((a) => a.status === 'new');
  const hasAck = alerts.some((a) => a.status === 'acknowledged');
  const hasDispatched = alerts.some((a) => a.status === 'dispatched' || a.status === 'verified');
  const hasResolved = alerts.some((a) => a.status === 'resolved' || a.status === 'false_alarm');

  const steps = [
    {
      num: 1,
      id: 'detect',
      label: '1. Detect',
      sub: 'Multi-Modal Sensors',
      icon: <Radio className="w-3.5 h-3.5" />,
      color: 'text-[#2563EB] bg-blue-50 border-blue-200',
      activeColor: 'bg-[#2563EB] text-white border-[#2563EB] shadow-xs',
      isActive: true, // Always actively sensing
    },
    {
      num: 2,
      id: 'risk_score',
      label: '2. Risk Score',
      sub: 'Temporal State Engine',
      icon: <Cpu className="w-3.5 h-3.5" />,
      color: 'text-indigo-600 bg-indigo-50 border-indigo-200',
      activeColor: 'bg-indigo-600 text-white border-indigo-600 shadow-xs',
      isActive: true,
    },
    {
      num: 3,
      id: 'alert',
      label: '3. Alert',
      sub: activeAlertsCount > 0 ? `${activeAlertsCount} Active Alert${activeAlertsCount > 1 ? 's' : ''}` : 'Nominal Clear',
      icon: <BellRing className="w-3.5 h-3.5" />,
      color: 'text-[#EF4444] bg-red-50 border-red-200',
      activeColor: 'bg-[#EF4444] text-white border-[#EF4444] shadow-xs animate-pulse',
      isActive: hasNew,
    },
    {
      num: 4,
      id: 'acknowledge',
      label: '4. Acknowledge',
      sub: 'Staff Received',
      icon: <CheckCircle2 className="w-3.5 h-3.5" />,
      color: 'text-[#F59E0B] bg-amber-50 border-amber-200',
      activeColor: 'bg-[#F59E0B] text-white border-[#F59E0B] shadow-xs',
      isActive: hasAck,
    },
    {
      num: 5,
      id: 'dispatch',
      label: '5. Dispatch / Verify',
      sub: 'On-Site Human Check',
      icon: <Send className="w-3.5 h-3.5" />,
      color: 'text-purple-600 bg-purple-50 border-purple-200',
      activeColor: 'bg-purple-600 text-white border-purple-600 shadow-xs',
      isActive: hasDispatched,
    },
    {
      num: 6,
      id: 'closed',
      label: '6. Case Closed',
      sub: 'Logged & Audited',
      icon: <ShieldCheck className="w-3.5 h-3.5" />,
      color: 'text-[#10B981] bg-emerald-50 border-emerald-200',
      activeColor: 'bg-[#10B981] text-white border-[#10B981] shadow-xs',
      isActive: hasResolved,
    },
  ];

  return (
    <div className="bg-white rounded-2xl border border-[#E2E8F0] p-3.5 shadow-xs">
      <div className="flex items-center justify-between pb-2 mb-2.5 border-b border-[#F1F5F9] px-1">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#2563EB]" />
          <span className="text-[11px] font-bold text-[#0F172A] uppercase tracking-wider">
            Early Detection & Human-In-The-Loop Response Workflow
          </span>
        </div>
        <span className="text-[11px] text-[#64748B] font-medium">
          Zero Automated Accusations &bull; Verified by School Staff
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        {steps.map((st, index) => {
          return (
            <div
              key={st.id}
              className={`flex items-center justify-between p-2 rounded-xl border text-xs transition-all ${
                st.isActive ? st.activeColor : 'bg-slate-50 border-[#E2E8F0] text-[#64748B]'
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className={`p-1.5 rounded-lg ${st.isActive ? 'bg-white/20' : 'bg-white shadow-xs'}`}>
                  {st.icon}
                </span>
                <div className="min-w-0">
                  <div className="font-bold text-xs truncate leading-tight">{st.label}</div>
                  <div
                    className={`text-[10px] truncate leading-tight ${
                      st.isActive ? 'text-white/80' : 'text-[#64748B]'
                    }`}
                  >
                    {st.sub}
                  </div>
                </div>
              </div>

              {index < steps.length - 1 && (
                <ChevronRight
                  className={`w-3.5 h-3.5 shrink-0 hidden lg:block ${
                    st.isActive ? 'text-white/60' : 'text-slate-300'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
