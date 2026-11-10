import React from 'react';
import { useSafeSenseApp } from '../../context/SafeSenseContext';
import { DEMO_SCENARIOS } from '../../data/schoolData';
import {
  X,
  Play,
  RotateCcw,
  Sparkles,
  AlertTriangle,
  Flame,
  ShieldCheck,
  CheckCircle2,
  Info,
} from 'lucide-react';

export const DemoScenarioModal: React.FC = () => {
  const {
    isDemoRunnerOpen,
    setIsDemoRunnerOpen,
    activeScenarioId,
    runScenario,
    resetDemo,
  } = useSafeSenseApp();

  if (!isDemoRunnerOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-3xl bg-white rounded-3xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center shadow-md">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Interactive Scenario Simulator</h2>
              <p className="text-xs text-slate-400">
                Test multi-modal sensor fusion rules, risk scoring, and real-time alerts
              </p>
            </div>
          </div>

          <button
            onClick={() => setIsDemoRunnerOpen(false)}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Banner note */}
        <div className="px-6 py-2.5 bg-blue-50 border-b border-blue-100 flex items-center justify-between text-xs text-blue-900">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-blue-600 shrink-0" />
            <span>
              Click any scenario below to update the Digital Twin, Risk Engine, and Live Alert Feed in real time.
            </span>
          </div>
          <button
            onClick={() => resetDemo()}
            className="flex items-center gap-1 font-semibold text-blue-700 hover:text-blue-900 underline"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Demo</span>
          </button>
        </div>

        {/* Scenarios Grid */}
        <div className="p-6 overflow-y-auto space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {DEMO_SCENARIOS.map((sc) => {
              const isActive = activeScenarioId === sc.id;
              const isCritical = sc.expectedLevel === 'CRITICAL';
              const isHigh = sc.expectedLevel === 'HIGH';
              const isWarning = sc.expectedLevel === 'WARNING';
              const isObserve = sc.expectedLevel === 'OBSERVE';

              return (
                <div
                  key={sc.id}
                  className={`p-4 rounded-2xl border transition-all flex flex-col justify-between ${
                    isActive
                      ? 'border-blue-600 bg-blue-50/50 shadow-md ring-2 ring-blue-500/20'
                      : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-xs'
                  }`}
                >
                  <div>
                    {/* Header */}
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="font-bold text-sm text-slate-900">{sc.name}</h4>
                      <span
                        className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full uppercase tracking-wider shrink-0 ${
                          isCritical
                            ? 'bg-red-100 text-red-800 border border-red-200'
                            : isHigh
                            ? 'bg-rose-100 text-rose-800 border border-rose-200'
                            : isWarning
                            ? 'bg-amber-100 text-amber-800 border border-amber-200'
                            : isObserve
                            ? 'bg-yellow-100 text-yellow-800 border border-yellow-200'
                            : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                        }`}
                      >
                        {sc.expectedLevel} ({sc.expectedScore}/100)
                      </span>
                    </div>

                    <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">
                      {sc.description}
                    </p>

                    {/* Sensor Factors chips */}
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {sc.factors.map((factor, idx) => (
                        <span
                          key={idx}
                          className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md font-medium"
                        >
                          {factor}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Footer Action */}
                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                    <span className="text-[11px] text-slate-500 font-medium">
                      Target: <span className="font-semibold text-slate-700">{sc.zoneId.replace('ZONE_', '')}</span>
                    </span>

                    <button
                      onClick={() => {
                        runScenario(sc.id);
                        setIsDemoRunnerOpen(false);
                      }}
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                        isActive
                          ? 'bg-blue-600 text-white shadow-sm'
                          : 'bg-slate-900 hover:bg-blue-600 text-white'
                      }`}
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>{isActive ? 'Re-Run Scenario' : 'Run Scenario'}</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer controls */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <div className="text-xs text-slate-500">
            Rule engine: <span className="font-semibold text-slate-700">Deterministic Temporal Fusion v2</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => resetDemo()}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-200 border border-slate-300 transition-colors cursor-pointer flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset to Baseline</span>
            </button>
            <button
              onClick={() => setIsDemoRunnerOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-white transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
