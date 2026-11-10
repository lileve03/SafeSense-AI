import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { useSafeSenseApp } from '../../context/SafeSenseContext';
import { X, Send, UserCheck, Shield, Phone } from 'lucide-react';

interface DispatchStaffModalProps {
  alertId: string | null;
  onClose: () => void;
}

export const DispatchStaffModal: React.FC<DispatchStaffModalProps> = ({ alertId, onClose }) => {
  const { staffMembers, dispatchStaff, alerts, isLiveMode } = useSafeSenseApp();
  const [selectedStaff, setSelectedStaff] = useState<string>('');
  const [routes,setRoutes]=useState<any[]>([]),[error,setError]=useState('');
  const zoneId=alerts.find(a=>a.id===alertId)?.zoneId;
  useEffect(()=>{
    if(!isLiveMode){setSelectedStaff(staffMembers[0].name);return;}
    let alive=true;setSelectedStaff('');setRoutes([]);setError('');
    if(alertId)api('/notifications/status').then(c=>{if(alive){const assigned=c.routes.filter((r:any)=>r.selected_for_zone&&r.zone_id===zoneId);setRoutes(assigned);setSelectedStaff(assigned[0]?.staff||'');}}).catch(e=>{if(alive)setError(String(e));});
    return()=>{alive=false;};
  },[alertId,zoneId,isLiveMode,staffMembers]);
  const choices:{id:string;name:string;role:string;phone:string;status:string}[]=isLiveMode ? routes.map((r,index)=>({id:String(index),name:r.staff,role:'Configured zone assignment',phone:'',status:'Configured active'})):staffMembers;

  if (!alertId) return null;

  const alert = alerts.find((a) => a.id === alertId);
  if (!alert) return null;

  const handleConfirm = () => {
    dispatchStaff(alertId, selectedStaff);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <Send className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-white">Dispatch Campus Responder</h3>
              <p className="text-[11px] text-slate-400">
                Incident #{alert.incidentNumber} &bull; {alert.zoneName}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Staff Selection List */}
        <div className="p-6 space-y-3">
          <label className="block text-xs font-semibold text-slate-700">
            {isLiveMode ? 'Configured on-duty zone assignment (delivery follows incident provenance and notification mode):':'Simulated staff selection:'}
          </label>

          <div className="space-y-2">
            {error && <p role="alert">{error}</p>}
            {isLiveMode && choices.length===0 && <p className="text-sm">No active zone assignment configured. Configure your private staff routing file; no staff availability or location is inferred.</p>}
            {choices.map((member) => {
              const isSelected = selectedStaff === member.name;
              return (
                <div
                  key={member.id}
                  onClick={() => setSelectedStaff(member.name)}
                  className={`p-3 rounded-2xl border cursor-pointer transition-all flex items-center justify-between ${
                    isSelected
                      ? 'border-blue-600 bg-blue-50/70 shadow-xs ring-1 ring-blue-500'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-9 h-9 rounded-xl flex items-center justify-center text-xs font-bold ${
                        isSelected ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {member.name.split(' ').map((n) => n[0]).join('')}
                    </div>
                    <div>
                      <h4 className="font-bold text-xs text-slate-900">{member.name}</h4>
                      <p className="text-[11px] text-slate-500 flex items-center gap-2">
                        <span>{member.role}</span>
                        <span>&bull;</span>
                        <span className="font-mono text-slate-400">{member.phone}</span>
                      </p>
                    </div>
                  </div>

                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      member.status === 'Available'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {member.status}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200 transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!selectedStaff}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-500/20 transition-all cursor-pointer flex items-center gap-1.5"
          >
            <UserCheck className="w-3.5 h-3.5" />
            <span>{isLiveMode?'Assign & queue notification':'Confirm simulated dispatch'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
