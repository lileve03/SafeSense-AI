import React, { useState } from 'react';
import { useSafeSenseApp } from '../context/SafeSenseContext';
import { ActiveHistoricalIncidents } from '../components/incidents/ActiveHistoricalIncidents';
import { DispatchStaffModal } from '../components/modals/DispatchStaffModal';
import { WorkflowIndicator } from '../components/layout/WorkflowIndicator';

export const AlertsPage: React.FC = () => {
  const [dispatchAlertId, setDispatchAlertId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      {/* Alert Verification Workflow Progress */}
      <WorkflowIndicator />

      {/* Main Feature: Active & Historical Incidents Module */}
      <ActiveHistoricalIncidents
        onDispatchAlert={(id) => setDispatchAlertId(id)}
      />

      {/* Staff Dispatch Modal */}
      <DispatchStaffModal
        alertId={dispatchAlertId}
        onClose={() => setDispatchAlertId(null)}
      />
    </div>
  );
};
