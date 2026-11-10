import React from 'react';
import { SafeSenseProvider, useSafeSenseApp } from './context/SafeSenseContext';
import { Sidebar } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar';
import { DemoScenarioModal } from './components/modals/DemoScenarioModal';
import { AlertDetailModal } from './components/modals/AlertDetailModal';

// 9 Connected Pages (Requirement 3 & 8)
import { OverviewPage } from './pages/OverviewPage';
import { DeveloperTestingPage } from './pages/DeveloperTestingPage';
import { LiveMonitoringPage } from './pages/LiveMonitoringPage';
import { DigitalTwinPage } from './pages/DigitalTwinPage';
import { AlertsPage } from './pages/AlertsPage';
import { IncidentReviewPage } from './pages/IncidentReviewPage';
import { AnalyticsReportsPage } from './pages/AnalyticsReportsPage';
import { DevicesPage } from './pages/DevicesPage';
import { SettingsPage } from './pages/SettingsPage';

function AppContent() {
  const { activePage, monitoringView, backendError, isLiveMode, fastApiStatus, setIsLiveMode } = useSafeSenseApp();

  const privateAreaOpen=activePage==='digital_twin'&&monitoringView==='private_area';

  return (
    <div className="flex h-screen bg-[#F4F6F9] text-[#0F172A] font-sans antialiased overflow-hidden selection:bg-[#2563EB] selection:text-white">
      {/* 1. Fixed Dark Navy Left Sidebar (#0B1528) */}
      <Sidebar />

      {/* 2. Main Content Viewport */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Bar Header */}
        <TopBar />

        {/* Scrollable Page Body */}
        <main className="flex-1 overflow-y-auto p-3 md:p-8">
          <div className="max-w-7xl mx-auto pb-12">
            {!privateAreaOpen&&<button className="md:hidden mb-2 text-blue-700 underline text-sm" onClick={()=>setIsLiveMode(!isLiveMode)}>{isLiveMode ? "Switch to simulation" : "Switch to backend events"}</button>}
            {!privateAreaOpen && activePage !== 'live_monitoring' && <p className="mb-4 text-sm text-slate-600">{(activePage === 'analytics' || activePage === 'reports') ? 'Saved backend / SQLite records \u00b7 Tests and replays are labeled per incident.' : isLiveMode ? `Backend events \u00b7 ${fastApiStatus} \u00b7 Model analysis, recorded replay and simulation are labeled in incident evidence. Physical hardware connection is not verified.` : 'SIMULATION ONLY \u00b7 Illustrative alerts and telemetry; no model inference or connected hardware.'}</p>}
            {backendError && <p role="alert" className="mb-4 p-3 bg-red-50 text-red-800 border border-red-200 rounded-xl">{backendError}</p>}
            {activePage === 'developer_testing' && <DeveloperTestingPage />}
            {activePage === 'overview' && <OverviewPage />}
            {activePage === 'live_monitoring' && <LiveMonitoringPage />}
            {activePage === 'digital_twin' && <DigitalTwinPage />}
            {activePage === 'alerts' && <AlertsPage />}
            {activePage === 'incident_review' && <IncidentReviewPage />}
            {(activePage === 'analytics' || activePage === 'reports') && <AnalyticsReportsPage />}
            {activePage === 'devices' && <DevicesPage />}
            {activePage === 'settings' && <SettingsPage />}
          </div>
        </main>
      </div>

      {/* Global Interactive Modals */}
      <DemoScenarioModal />
      <AlertDetailModal />
    </div>
  );
}

export default function App() {
  return (
    <SafeSenseProvider>
      <AppContent />
    </SafeSenseProvider>
  );
}
