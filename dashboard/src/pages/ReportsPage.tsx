import React, { useState } from 'react';
import { useSafeSenseApp } from '../context/SafeSenseContext';
import {
  FileText,
  Download,
  Printer,
  Calendar,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Flame,
  ShieldCheck,
  Building,
} from 'lucide-react';

export const ReportsPage: React.FC = () => {
  const { alerts, exportIncidentsCsv, setSelectedAlertId } = useSafeSenseApp();

  const [dateRange, setDateRange] = useState('today');
  const [reportFilter, setReportFilter] = useState('all');

  const filteredIncidents = alerts.filter((a) => {
    const days = dateRange === 'today' ? 1 : dateRange === '7days' ? 7 : dateRange === '30days' ? 30 : Infinity;
    const detected = Date.parse(a.detectedTime);
    if (Number.isFinite(detected) && Date.now()-detected > days*86400000) return false;
    if (reportFilter === 'resolved' && a.status !== 'resolved') return false;
    if (reportFilter === 'false_alarm' && a.status !== 'false_alarm') return false;
    return true;
  });

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="p-5 rounded-2xl bg-white border border-[#E2E8F0] shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-[#0F172A] flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#2563EB]" />
            <span>Campus Safety Compliance & Audit Reports</span>
          </h2>
          <p className="text-xs text-[#64748B] mt-1">
            Prototype safety logs, incident audit trails, and response verification records for campus administration.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Real Downloadable CSV Button */}
          <button
            onClick={()=>exportIncidentsCsv(filteredIncidents)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-700 text-white text-xs font-bold shadow-xs cursor-pointer transition-all active:scale-95"
          >
            <Download className="w-4 h-4" />
            <span>Export CSV</span>
          </button>

          {/* Print / Save as PDF Button */}
          <button
            onClick={handlePrint}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#0B1528] hover:bg-slate-800 text-white text-xs font-bold shadow-xs cursor-pointer transition-all"
          >
            <Printer className="w-4 h-4" />
            <span>Print / Save PDF</span>
          </button>
        </div>
      </div>

      {/* Filter Options */}
      <div className="p-4 bg-white rounded-2xl border border-[#E2E8F0] shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs">
          <Calendar className="w-4 h-4 text-[#64748B]" />
          <span className="font-semibold text-[#0F172A]">Date Range:</span>
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-slate-50 border border-[#E2E8F0] text-xs text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium cursor-pointer"
          >
            <option value="today">Today (Demo Session)</option>
            <option value="7days">Past 7 Days</option>
            <option value="30days">Current Academic Month</option>
            <option value="semester">Full Semester Archive</option>
          </select>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="font-semibold text-[#0F172A]">Status Classification:</span>
          <select
            value={reportFilter}
            onChange={(e) => setReportFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-slate-50 border border-[#E2E8F0] text-xs text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium cursor-pointer"
          >
            <option value="all">All Incident Outcomes ({alerts.length})</option>
            <option value="resolved">Resolved Only</option>
            <option value="false_alarm">False Alarms Only</option>
          </select>
        </div>
      </div>

      {/* Report Preview Document Card (Print-ready layout) */}
      <div className="p-8 rounded-3xl bg-white border border-[#E2E8F0] shadow-sm space-y-6 print:border-none print:shadow-none">
        {/* Document Header */}
        <div className="pb-6 border-b border-[#E2E8F0] flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-8 h-8 rounded-xl bg-[#2563EB] text-white flex items-center justify-center font-bold text-sm">
                SS
              </span>
              <h3 className="font-extrabold text-lg text-[#0F172A] tracking-tight">
                SafeSense AI Campus Safety Report
              </h3>
            </div>
            <p className="text-xs text-[#64748B] mt-1">
              Automated Incident Verification & Compliance Log &bull; St. Jude Academy Main Campus
            </p>
          </div>

          <div className="text-right text-xs text-[#64748B] space-y-0.5">
            <div>Generated: <strong className="text-[#0F172A]">{new Date().toLocaleDateString()}</strong></div>
            <div>Auditor: <strong className="text-[#0F172A]">Dashboard operator</strong></div>
            <div>Classification: <strong className="text-emerald-700">Prototype incident log</strong></div>
          </div>
        </div>

        {/* Executive Summary Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 rounded-2xl bg-[#F8FAFC] border border-[#E2E8F0] text-xs">
          <div>
            <span className="text-[#64748B] block">Total Processed:</span>
            <span className="text-xl font-black text-[#0F172A]">{filteredIncidents.length} Incidents</span>
          </div>
          <div>
            <span className="text-[#64748B] block">Resolved & Verified:</span>
            <span className="text-xl font-black text-[#10B981]">
              {filteredIncidents.filter((a) => a.status === 'resolved').length}
            </span>
          </div>
          <div>
            <span className="text-[#64748B] block">False Positives Filtered:</span>
            <span className="text-xl font-black text-[#F59E0B]">
              {filteredIncidents.filter((a) => a.status === 'false_alarm').length}
            </span>
          </div>
          <div>
            <span className="text-[#64748B] block">Privacy Compliance:</span>
            <span className="text-xl font-black text-teal-700">Private zones: no video</span>
          </div>
        </div>

        {/* Incident Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-[#64748B] font-bold uppercase text-[10px]">
              <tr>
                <th className="py-2.5 px-3">ID</th>
                <th className="py-2.5 px-3">Time</th>
                <th className="py-2.5 px-3">Location</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">Detection Source</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Investigating Staff</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredIncidents.map((inc) => (
                <tr key={inc.id} className="hover:bg-slate-50">
                  <td className="py-3 px-3 font-mono font-bold text-[#0F172A]"><button className="text-blue-700 underline" onClick={()=>setSelectedAlertId(inc.id)}>#{inc.incidentNumber} · Report & evidence</button></td>
                  <td className="py-3 px-3 font-mono text-[#64748B]">{inc.detectedTime}</td>
                  <td className="py-3 px-3 font-semibold text-[#0F172A]">{inc.zoneName}</td>
                  <td className="py-3 px-3">
                    <span
                      className={`text-[9px] font-black px-2 py-0.5 rounded-full uppercase ${
                        inc.level === 'CRITICAL'
                          ? 'bg-red-100 text-[#EF4444]'
                          : inc.level === 'HIGH'
                          ? 'bg-orange-100 text-[#F97316]'
                          : 'bg-amber-100 text-[#F59E0B]'
                      }`}
                    >
                      {inc.level}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-[#0F172A]">{inc.triggerType}</td>
                  <td className="py-3 px-3 capitalize font-bold text-[#2563EB]">
                    {inc.status.replace('_', ' ')}
                  </td>
                  <td className="py-3 px-3 text-[#0F172A]">{inc.assignedStaff || 'Unassigned'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Legal & Privacy Disclaimer */}
        <div className="p-4 rounded-xl bg-slate-50 border border-[#E2E8F0] text-[11px] text-[#64748B] leading-relaxed">
          <strong>Scope:</strong> Prototype incident log. Each incident includes its processing mode and evidence source. Hardware is not connected. Public-area model candidates require human review. Private areas prohibit video. Generated public-area annotations may include identifiable people; access is limited by the local demo token and runtime retention, not anonymization.

        </div>
      </div>
    </div>
  );
};
