export type RiskLevel = 'LOW' | 'OBSERVE' | 'WARNING' | 'HIGH' | 'CRITICAL';

export type AlertStatus = 'new' | 'acknowledged' | 'dispatched' | 'verified' | 'resolved' | 'false_alarm';

export type Modality = 'cctv' | 'radar' | 'acoustic' | 'sos';

export type PageId =
  | 'developer_testing'
  | 'overview'
  | 'live_monitoring'
  | 'digital_twin'
  | 'alerts'
  | 'incident_review'
  | 'analytics'
  | 'devices'
  | 'reports'
  | 'settings';

export interface RadarTarget {
  id: string;
  x: number; // relative coordinate inside zone (0 - 100)
  y: number;
  vx: number;
  vy: number;
  speed: number; // m/s
  state: 'standing' | 'walking' | 'running' | 'fallen';
}

export interface Zone {
  id: string;
  name: string;
  name_zh: string;
  isPrivate: boolean; // Toilet Entrance / Blind Spot = true (Strictly no CCTV!)
  level: RiskLevel;
  riskScore: number; // 0 - 100
  sensorIds: string[];
  occupants: number;
  lastEventTime: string;
  latestEventDesc: string;
  // Radar targets for privacy zone tracking
  radarTargets?: RadarTarget[];
  interpersonalDistanceMeters?: number;
  motionLevel?: 'Low' | 'Moderate' | 'Rapid' | 'Violent';
  fallDetected?: boolean;
  acousticEvent?: string;
  // 3D coordinates in Three.js space
  position: [number, number, number];
  size: [number, number, number];
  // 2D floor-plan percentages
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface SensorDevice {
  id: string;
  name: string;
  type: Modality;
  zoneId: string;
  zoneName: string;
  status: 'online' | 'offline';
  lastUpdate: string;
  currentReading: string;
  isPrivacyProtected: boolean;
  isSimulated: boolean;
  batteryPercent?: number;
  firmwareVersion: string;
}

export interface AlertTimelineItem {
  time: string;
  event: string;
  actor?: string;
}

export interface Alert {
  notificationStatus?: string;
  acknowledgedAt?: string;
  processingMode?: string;
  source?: string;
  id: string;
  incidentNumber: string;
  zoneId: string;
  zoneName: string;
  level: RiskLevel;
  riskScore: number; // 0 - 100
  title: string;
  triggerType: string;
  reason: string;
  explainableFactors: string[];
  detectedTime: string;
  status: AlertStatus;
  assignedStaff?: string;
  dispatchTime?: string;
  verifiedTime?: string;
  resolvedTime?: string;
  resolutionNote?: string;
  isFalseAlarm?: boolean;
  falseAlarmReason?: string;
  triggeringSensors: string[];
  timeline: AlertTimelineItem[];
}

export interface IncidentHistoryItem extends Alert {
  archivedAt: string;
}

export interface ActivityTimelineEvent {
  id: string;
  time: string;
  zoneId: string;
  zoneName: string;
  description: string;
  type: 'alert' | 'sensor' | 'staff' | 'system';
  level: RiskLevel;
}

export interface DemoScenario {
  id: string;
  name: string;
  description: string;
  zoneId: string;
  expectedScore: number;
  expectedLevel: RiskLevel;
  factors: string[];
  explanation: string;
  radarState?: {
    targets: number;
    distance: number;
    motion: 'Low' | 'Moderate' | 'Rapid' | 'Violent';
    fall: boolean;
    acoustic: string;
  };
}

export interface RiskThresholds {
  low: number; // 0-24
  observe: number; // 25-49
  warning: number; // 50-74
  high: number; // 75-94
  critical: number; // 95-100
}

export interface SystemSettings {
  thresholds: RiskThresholds;
  audioAlerts: boolean;
  autoEscalateSOS: boolean;
  privacyStrictRadarOnly: boolean;
  schoolName: string;
  notificationsEnabled: boolean;
}


/** Non-identifying backend observations; no images, speech or inferred coordinates. */
export interface SensorObservation {
  id: string;
  level: RiskLevel;
  zone_id: string;
  timestamp: string;
  type: string;
  source: string;
  sensor_modality?: string;
  processing_mode: 'real_model' | 'recorded_sensor_replay' | 'simulation';
  reason: string;
  score?: number | null;
  model_version?: string | null;
  evidence_reference?: string | null;
}
