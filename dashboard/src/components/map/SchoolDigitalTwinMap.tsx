import React, { useState, useMemo } from 'react';
import { useSafeSenseApp } from '../../context/SafeSenseContext';
import { Zone, RiskLevel } from '../../types/safesense';
import {
  Lock,
  Eye,
  Radio,
  Volume2,
  Flame,
  AlertTriangle,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Layers,
  ShieldCheck,
  Activity,
  ArrowRight,
  Video,
  X,
  MapPin,
  CheckCircle2,
  ChevronRight,
  Sliders,
} from 'lucide-react';

interface SchoolDigitalTwinMapProps {
  onSelectZone?: (zoneId: string) => void;
  compactMode?: boolean;
}

export const SchoolDigitalTwinMap: React.FC<SchoolDigitalTwinMapProps> = ({
  onSelectZone,
  compactMode = false,
}) => {
  const {
    zones,
    isLiveMode,
    selectedZoneId,
    setSelectedZoneId,
    alerts,
    setSelectedAlertId,
    setActivePage,
    openPrivateAreaMonitoring,
  } = useSafeSenseApp();

  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [showCameraOverlay, setShowCameraOverlay] = useState<boolean>(true);
  const [showBlindSpotOverlay, setShowBlindSpotOverlay] = useState<boolean>(true);
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(true);

  // Fallback to selected zone or default to Blind Spot
  const selectedZone = useMemo(
    () => zones.find((z) => z.id === selectedZoneId) || zones.find((z) => z.id === 'ZONE_TOILET_BLINDSPOT') || zones[0],
    [zones, selectedZoneId]
  );

  const activeAlertForZone = useMemo(
    () => alerts.find((a) => a.zoneId === selectedZone?.id && a.status !== 'resolved' && a.status !== 'false_alarm'),
    [alerts, selectedZone]
  );

  const handleSelectZone = (id: string) => {
    setSelectedZoneId(id);
    setIsInspectorOpen(true);
    if (onSelectZone) onSelectZone(id);
    if (zones.find(zone => zone.id === id)?.isPrivate) openPrivateAreaMonitoring(id);
  };

  const getSeverityInfo = (level: RiskLevel) => {
    switch (level) {
      case 'CRITICAL':
      case 'HIGH':
        return {
          dotColor: '#EF4444',
          dotClass: 'bg-[#EF4444]',
          badgeBg: 'bg-[#EF4444] text-white',
          label: level === 'CRITICAL' ? 'Critical' : 'Alert / High',
          textColor: 'text-[#EF4444]',
          hex: '#EF4444',
        };
      case 'WARNING':
      case 'OBSERVE':
        return {
          dotColor: '#F59E0B',
          dotClass: 'bg-[#F59E0B]',
          badgeBg: 'bg-[#F59E0B] text-white',
          label: 'Attention',
          textColor: 'text-[#F59E0B]',
          hex: '#F59E0B',
        };
      case 'LOW':
      default:
        return {
          dotColor: '#10B981',
          dotClass: 'bg-[#10B981]',
          badgeBg: 'bg-[#10B981] text-white',
          label: 'Normal',
          textColor: 'text-[#10B981]',
          hex: '#10B981',
        };
    }
  };

  // Mapped 6 zones with exact 2.5D Isometric Architectural Shapes:
  // 1. Entrance
  // 2. Corridor A
  // 3. Canteen
  // 4. Staircase
  // 5. School Hall
  // 6. Toilet Entrance / Blind Spot Zone
  const isoZones = [
    {
      id: 'ZONE_ENTRANCE',
      name: 'Entrance',
      subtitle: 'Main School Foyer & Turnstiles',
      isPrivate: false,
      pinX: 230,
      pinY: 260,
      labelX: 230,
      labelY: 295,
      // Isometric Top Polygon
      topPoly: '140,240 260,180 340,225 220,285',
      // Isometric Front/Side Walls
      frontWall: '220,285 340,225 340,265 220,325',
      leftWall: '140,240 220,285 220,325 140,280',
      doorPath: '170,270 195,283 195,310 170,296',
      detectionSource: 'YOLO Pose Camera + Optical AI',
    },
    {
      id: 'ZONE_CORRIDOR_A',
      name: 'Corridor A',
      subtitle: 'Central Circulation Spine',
      isPrivate: false,
      pinX: 470,
      pinY: 215,
      labelX: 470,
      labelY: 248,
      topPoly: '340,165 520,75 580,105 400,195',
      frontWall: '400,195 580,105 580,135 400,225',
      leftWall: '340,165 400,195 400,225 340,195',
      doorPath: null,
      detectionSource: 'Corridor CCTV Optical Flow + mmWave',
    },
    {
      id: 'ZONE_CANTEEN',
      name: 'Canteen',
      subtitle: 'Dining Hall & Food Service Area',
      isPrivate: false,
      pinX: 720,
      pinY: 195,
      labelX: 720,
      labelY: 230,
      topPoly: '580,135 720,65 850,130 710,200',
      frontWall: '710,200 850,130 850,170 710,240',
      leftWall: '580,135 710,200 710,240 580,175',
      doorPath: '630,215 655,227 655,250 630,237',
      detectionSource: 'Optical Crowd Density + Edge Acoustic',
    },
    {
      id: 'ZONE_SCHOOL_HALL',
      name: 'School Hall',
      subtitle: 'Multi-Purpose Auditorium',
      isPrivate: false,
      pinX: 350,
      pinY: 410,
      labelX: 350,
      labelY: 445,
      topPoly: '220,380 380,300 480,350 320,430',
      frontWall: '320,430 480,350 480,395 320,475',
      leftWall: '220,380 320,430 320,475 220,425',
      doorPath: '260,418 285,431 285,455 260,442',
      detectionSource: 'Acoustic Sound Field + Optical Vision',
    },
    {
      id: 'ZONE_STAIRCASE',
      name: 'Staircase',
      subtitle: 'Emergency Egress & South Stairwell',
      isPrivate: false,
      pinX: 535,
      pinY: 340,
      labelX: 535,
      labelY: 375,
      topPoly: '450,305 550,255 610,285 510,335',
      frontWall: '510,335 610,285 610,330 510,380',
      leftWall: '450,305 510,335 510,380 450,350',
      doorPath: null,
      detectionSource: 'Stairwell CCTV + Step Cadence Radar',
    },
    {
      id: 'ZONE_TOILET_BLINDSPOT',
      name: 'Blind Spot Zone',
      subtitle: 'Toilet Entrance / Privacy Blind Spot',
      isPrivate: true,
      pinX: 740,
      pinY: 360,
      labelX: 740,
      labelY: 395,
      topPoly: '620,320 760,250 860,300 720,370',
      frontWall: '720,370 860,300 860,345 720,415',
      leftWall: '620,320 720,370 720,415 620,365',
      doorPath: '660,358 685,370 685,395 660,382',
      detectionSource: '60GHz mmWave Radar + Acoustic AI (Zero CCTV)',
    },
  ];

  return (
    <div className="relative w-full h-full min-h-[560px] bg-[#F8FAFC] rounded-2xl overflow-hidden border border-[#E2E8F0] shadow-sm flex flex-col select-none">
      {/* 1. TOP TOOLBAR & CONTROLS */}
      <div className="px-5 py-3 bg-white border-b border-[#E2E8F0] flex flex-wrap items-center justify-between gap-3 z-20">
        {/* Left Title */}
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-blue-50 text-[#2563EB]">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-extrabold text-[#0F172A] leading-tight">
              2.5D Isometric Digital Twin School Map
            </h3>
            <span className="text-[10px] text-[#64748B] font-medium">
              Registered zone incidents; illustrative camera coverage and hardware locations
            </span>
          </div>
        </div>

        {/* Right Controls: Legend, Overlays, Zoom */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* Explicit Legend */}
          <div className="flex items-center gap-2.5 px-3 py-1 bg-slate-50 border border-[#E2E8F0] rounded-xl text-[11px] font-semibold text-[#0F172A]">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-[#10B981]" />
              <span>Normal</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-[#F59E0B]" />
              <span>Attention</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-[#EF4444] animate-pulse" />
              <span>Alert</span>
            </span>
          </div>

          <span className="w-px h-4 bg-[#E2E8F0]" />

          {/* Toggle Camera Overlay (Blue) */}
          <button
            onClick={() => setShowCameraOverlay(!showCameraOverlay)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-xl text-[11px] font-bold border transition-all cursor-pointer ${
              showCameraOverlay
                ? 'bg-blue-50 border-blue-300 text-[#2563EB] shadow-2xs'
                : 'bg-white border-slate-200 text-slate-400 opacity-60'
            }`}
            title="Toggle Blue Camera-Visible Coverage Overlay"
          >
            <Eye className="w-3 h-3" />
            <span>Camera Overlay</span>
          </button>

          {/* Toggle Privacy Blind Spot Overlay (Red Striped) */}
          <button
            onClick={() => setShowBlindSpotOverlay(!showBlindSpotOverlay)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-[11px] font-bold border transition-all cursor-pointer ${
              showBlindSpotOverlay
                ? 'bg-rose-50 border-rose-300 text-rose-800 shadow-2xs'
                : 'bg-white border-slate-200 text-slate-400 opacity-60'
            }`}
            title="Toggle Red Striped Privacy Blind Spot Overlay"
          >
            <span
              className="w-3 h-3 rounded-xs border border-rose-500"
              style={{
                background:
                  'repeating-linear-gradient(45deg, #EF4444 0, #EF4444 2px, #FEE2E2 2px, #FEE2E2 5px)',
              }}
            />
            <span>Privacy Overlay</span>
          </button>

          <span className="w-px h-4 bg-[#E2E8F0]" />

          {/* Zoom Controls */}
          <div className="flex items-center bg-slate-100 rounded-xl p-0.5 border border-[#E2E8F0]">
            <button
              onClick={() => setZoomLevel((prev) => Math.min(prev + 0.15, 1.45))}
              className="p-1 hover:bg-white rounded-lg text-[#0F172A] cursor-pointer"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoomLevel((prev) => Math.max(prev - 0.15, 0.85))}
              className="p-1 hover:bg-white rounded-lg text-[#0F172A] cursor-pointer"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoomLevel(1)}
              className="p-1 hover:bg-white rounded-lg text-[#0F172A] cursor-pointer"
              title="Reset View"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* 2. MAIN 2.5D ISOMETRIC ARCHITECTURAL CANVAS & COLLAPSIBLE SIDE INSPECTOR */}
      <div className="flex-1 relative overflow-hidden flex flex-col lg:flex-row items-stretch">
        {/* SVG ISOMETRIC ARCHITECTURAL MODEL CANVAS */}
        <div
          onClick={() => {
            // Clicking background deselects or keeps inspector closed
          }}
          className="flex-1 min-h-[280px] lg:min-h-0 h-full relative overflow-hidden flex items-center justify-center p-2 sm:p-4 bg-[#F8FAFC]"
        >
          {/* Subtle Isometric Coordinate Grid */}
          <div
            className="absolute inset-0 opacity-35 pointer-events-none"
            style={{
              backgroundImage:
                'linear-gradient(to right, #CBD5E1 1px, transparent 1px), linear-gradient(to bottom, #CBD5E1 1px, transparent 1px)',
              backgroundSize: '36px 36px',
            }}
          />

          <div
            style={{
              transform: `scale(${zoomLevel})`,
              transformOrigin: 'center center',
            }}
            className="w-full max-w-4xl h-full max-h-[580px] relative transition-transform duration-200"
          >
            <svg
              viewBox="0 0 1000 580"
              className="w-full h-full drop-shadow-md select-none"
              style={{ overflow: 'visible' }}
            >
              <defs>
                {/* Red Diagonal Stripes Pattern for Privacy-Sensitive Blind Spot Overlay */}
                <pattern
                  id="isoRedStripes"
                  width="14"
                  height="14"
                  patternTransform="rotate(45)"
                  patternUnits="userSpaceOnUse"
                >
                  <line
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="14"
                    stroke="#EF4444"
                    strokeWidth="3.5"
                    strokeOpacity="0.45"
                  />
                  <rect width="14" height="14" fill="#FEE2E2" fillOpacity="0.55" />
                </pattern>

                {/* Blue Translucent Gradient for Camera-Visible Areas */}
                <linearGradient id="cameraOverlayGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.22" />
                  <stop offset="100%" stopColor="#1D4ED8" stopOpacity="0.12" />
                </linearGradient>

                {/* Building Block Shadow */}
                <filter id="buildingShadow" x="-10%" y="-10%" width="130%" height="130%">
                  <feDropShadow dx="0" dy="12" stdDeviation="16" floodColor="#0F172A" floodOpacity="0.08" />
                </filter>
              </defs>

              {/* ISOMETRIC PODIUM / PLINTH (Ground Concrete Slab) */}
              <g id="groundPodium">
                {/* Podium Drop Shadow */}
                <polygon
                  points="110,310 510,80 910,280 510,510"
                  fill="#0F172A"
                  fillOpacity="0.06"
                />
                {/* Podium Top Face */}
                <polygon
                  points="100,290 500,70 900,270 500,490"
                  fill="#FFFFFF"
                  stroke="#CBD5E1"
                  strokeWidth="2"
                />
                {/* Podium Front Edge (Extrusion depth) */}
                <polygon
                  points="100,290 500,490 500,504 100,304"
                  fill="#E2E8F0"
                  stroke="#CBD5E1"
                  strokeWidth="1.5"
                />
                <polygon
                  points="500,490 900,270 900,284 500,504"
                  fill="#CBD5E1"
                  stroke="#94A3B8"
                  strokeWidth="1.5"
                />

                {/* Architectural Circulation Corridor Walkways */}
                <polygon
                  points="210,285 410,185 715,338 515,438"
                  fill="#F1F5F9"
                  stroke="#E2E8F0"
                  strokeWidth="1"
                  strokeDasharray="4 3"
                />
              </g>

              {/* RENDER THE 6 ARCHITECTURAL 2.5D SCHOOL BLOCKS */}
              {isoZones.map((room) => {
                const z = zones.find((item) => item.id === room.id);
                const isSelected = selectedZoneId === room.id;
                const level: RiskLevel = z ? z.level : 'LOW';
                const sev = getSeverityInfo(level);
                const isPrivate = room.isPrivate;

                // Base architectural room colors
                let topFill = '#FFFFFF';
                let leftFill = '#F1F5F9';
                let frontFill = '#E2E8F0';
                let strokeColor = '#94A3B8';
                let strokeWidth = '1.8';

                if (isSelected) {
                  strokeColor = isPrivate ? '#EF4444' : '#2563EB';
                  strokeWidth = '3';
                }

                // Apply Overlays
                if (isPrivate && showBlindSpotOverlay) {
                  topFill = 'url(#isoRedStripes)';
                  frontFill = '#FECDD3';
                  leftFill = '#FFE4E6';
                } else if (!isPrivate && showCameraOverlay) {
                  topFill = 'url(#cameraOverlayGrad)';
                  frontFill = '#BFDBFE';
                  leftFill = '#DBEAFE';
                }

                return (
                  <g
                    key={room.id} data-zone-id={room.id} data-risk-level={level} role="button" tabIndex={0} aria-label={`Select ${room.name}`} onKeyDown={e=>{if(e.key==='Enter')handleSelectZone(room.id);}}
                    id={`block-${room.id}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelectZone(room.id);
                    }}
                    className="cursor-pointer transition-all duration-150 group"
                  >
                    {/* Left Extrusion Wall */}
                    <polygon
                      points={room.leftWall}
                      fill={leftFill}
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                    />

                    {/* Front Extrusion Wall */}
                    <polygon
                      points={room.frontWall}
                      fill={frontFill}
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                    />

                    {/* Architectural Doorway opening if present */}
                    {room.doorPath && (
                      <polygon
                        points={room.doorPath}
                        fill="#0F172A"
                        fillOpacity="0.75"
                        stroke={strokeColor}
                        strokeWidth="1"
                      />
                    )}

                    {/* Top Roof / Floor Polygon */}
                    <polygon
                      points={room.topPoly}
                      fill={topFill}
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                      className="group-hover:brightness-95 transition-all"
                    />

                    {/* Architectural Features Inside Zones */}
                    {/* Staircase Steps Illustration */}
                    {room.id === 'ZONE_STAIRCASE' && (
                      <g stroke="#94A3B8" strokeWidth="1.5">
                        <line x1="480" y1="290" x2="520" y2="310" />
                        <line x1="495" y1="282" x2="535" y2="302" />
                        <line x1="510" y1="275" x2="550" y2="295" />
                        <line x1="525" y1="267" x2="565" y2="287" />
                      </g>
                    )}

                    {/* School Hall Seating Geometry */}
                    {room.id === 'ZONE_SCHOOL_HALL' && (
                      <g stroke="#CBD5E1" strokeWidth="1.2" strokeDasharray="2 2">
                        <line x1="260" y1="365" x2="330" y2="330" />
                        <line x1="285" y1="385" x2="355" y2="350" />
                        <line x1="310" y1="405" x2="380" y2="370" />
                      </g>
                    )}

                    {/* Canteen Dining Table Geometry */}
                    {room.id === 'ZONE_CANTEEN' && (
                      <g fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1">
                        <ellipse cx="680" cy="140" rx="16" ry="8" />
                        <ellipse cx="730" cy="115" rx="16" ry="8" />
                        <ellipse cx="740" cy="165" rx="16" ry="8" />
                      </g>
                    )}

                    {/* FLOATING INCIDENT / LOCATION PIN */}
                    <g
                      transform={`translate(${room.pinX}, ${room.pinY})`}
                      className="transition-transform group-hover:-translate-y-1"
                    >
                      {/* Ground Pin Shadow */}
                      <ellipse cx="0" cy="18" rx="8" ry="3.5" fill="#0F172A" fillOpacity="0.25" />

                      {/* Pulse Ping Ring for Active High/Critical Alerts */}
                      {level === 'CRITICAL' || level === 'HIGH' ? (
                        <circle
                          cx="0"
                          cy="0"
                          r="14"
                          fill="none"
                          stroke={sev.hex}
                          strokeWidth="2.5"
                          className="animate-ping origin-center opacity-75"
                        />
                      ) : null}

                      {/* Pin Stem */}
                      <line x1="0" y1="0" x2="0" y2="18" stroke={sev.hex} strokeWidth="2.5" strokeLinecap="round" />

                      {/* Pin Head */}
                      <circle cx="0" cy="0" r="10" fill={sev.hex} stroke="#FFFFFF" strokeWidth="2.5" />
                      {isPrivate ? (
                        <path
                          d="M -3,-2 L 3,-2 L 3,3 L -3,3 Z"
                          fill="#FFFFFF"
                        />
                      ) : (
                        <circle cx="0" cy="0" r="3" fill="#FFFFFF" />
                      )}
                    </g>

                    {/* ROUNDED WHITE ZONE LABEL WITH STATUS DOT (Minimal text on building) */}
                    <g
                      transform={`translate(${room.labelX}, ${room.labelY})`}
                      className="pointer-events-none"
                    >
                      {/* Label Background Pill */}
                      <rect
                        x="-65"
                        y="-12"
                        width="130"
                        height="24"
                        rx="12"
                        fill="#FFFFFF"
                        fillOpacity="0.96"
                        stroke={isSelected ? strokeColor : '#E2E8F0'}
                        strokeWidth={isSelected ? '2' : '1'}
                        filter="url(#buildingShadow)"
                      />

                      {/* Severity Status Dot */}
                      <circle cx="-50" cy="0" r="4.5" fill={sev.hex} />

                      {/* Clean Zone Name Text */}
                      <text
                        x="-38"
                        y="3.5"
                        fill="#0F172A"
                        fontSize="11"
                        fontWeight="800"
                        fontFamily="system-ui, sans-serif"
                      >
                        {room.name}
                      </text>

                      {/* Privacy Lock Icon if Blind Spot */}
                      {isPrivate && (
                        <g transform="translate(42, -5)">
                          <circle cx="4" cy="5" r="7" fill="#FEE2E2" />
                          <path
                            d="M 2,4 L 6,4 L 6,8 L 2,8 Z M 3,4 L 3,2 C 3,1 5,1 5,2 L 5,4"
                            stroke="#EF4444"
                            strokeWidth="1"
                            fill="none"
                          />
                        </g>
                      )}
                    </g>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        {/* 3. COLLAPSIBLE RIGHT-SIDE TELEMETRY INSPECTOR PANEL (No center obstruction!) */}
        {isInspectorOpen && selectedZone && (
          <div className="w-full lg:w-80 shrink-0 border-l border-[#E2E8F0] bg-white shadow-xl flex flex-col justify-between z-30 animate-in slide-in-from-right duration-200">
            {/* Inspector Header */}
            <div className="p-4 border-b border-[#F1F5F9] flex items-start justify-between">
              <div>
                <div className="flex items-center gap-1.5">
                  <h4 className="font-extrabold text-sm text-[#0F172A]">
                    {selectedZone.name}
                  </h4>
                  {selectedZone.isPrivate && (
                    <span className="p-0.5 rounded bg-rose-100 text-rose-700" title="Zero Camera Zone">
                      <Lock className="w-3 h-3" />
                    </span>
                  )}
                </div>
                <p
                  className={`text-[11px] font-bold mt-0.5 ${
                    selectedZone.isPrivate ? 'text-rose-600' : 'text-[#2563EB]'
                  }`}
                >
                  {selectedZone.isPrivate
                    ? 'Privacy Blind Spot • Radar + acoustic metadata only'
                    : 'Camera-Visible Circulation Zone'}
                </p>
              </div>

              <div className="flex items-center gap-1.5">
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-black ${
                    getSeverityInfo(selectedZone.level).badgeBg
                  }`}
                >
                  {selectedZone.level} ({selectedZone.riskScore}/100)
                </span>
                <button
                  onClick={() => setIsInspectorOpen(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
                  title="Close Inspector"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Inspector Body: Sensor Telemetry & Measured Attributes */}
            <div className="p-4 flex-1 overflow-y-auto space-y-3.5 text-xs">
              {/* Event Summary Card */}
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                  Latest Event
                </span>
                <p className="text-xs font-semibold text-[#0F172A] leading-snug">
                  {selectedZone.latestEventDesc}
                </p>
                <div className="flex items-center justify-between text-[10px] text-slate-500 mt-2 font-mono">
                  <span>Timestamp:</span>
                  <span className="font-bold text-slate-700">{selectedZone.lastEventTime}</span>
                </div>
              </div>

              {/* Hardware Sensor Correctness: Display only genuine measured inputs */}
              <div className="space-y-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                  Sensor event metadata · hardware unavailable
                </span>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[10px] text-slate-500 block">Occupancy</span>
                    <strong className="text-sm font-black text-[#0F172A]">
                      {isLiveMode ? 'Unavailable' : `${selectedZone.occupants} persons (simulated)`}
                    </strong>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[10px] text-slate-500 block">Fall Event</span>
                    <strong
                      className={`text-sm font-black ${
                        selectedZone.fallDetected ? 'text-[#EF4444]' : 'text-[#10B981]'
                      }`}
                    >
                      {selectedZone.fallDetected ? 'CANDIDATE' : 'No recorded candidate'}
                    </strong>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[10px] text-slate-500 block">Motion Cadence</span>
                    <strong className="text-xs font-bold text-[#0F172A]">
                      {selectedZone.motionLevel || 'Unavailable'}
                    </strong>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[10px] text-slate-500 block">Proximity Gap</span>
                    <strong className="text-xs font-bold text-[#0F172A]">
                      {selectedZone.interpersonalDistanceMeters
                        ? `${selectedZone.interpersonalDistanceMeters}m`
                        : 'Unavailable'}
                    </strong>
                  </div>
                </div>
              </div>

              {/* Detection Pipeline details */}
              <div className="p-3 rounded-xl bg-blue-50/60 border border-blue-200 text-xs space-y-1">
                <span className="text-[10px] font-bold text-[#2563EB] uppercase tracking-wider block">
                  Sensor Pipeline
                </span>
                <p className="text-[11px] text-[#0F172A] font-semibold">
                  {selectedZone.isPrivate
                    ? 'Permitted: radar + non-speech acoustic events (no hardware connected)'
                    : 'Edge YOLO Pose Skeletal Keypoints + mmWave Density'}
                </p>
                <p className="text-[10px] text-slate-600 leading-snug mt-1">
                  {selectedZone.isPrivate
                    ? 'Strict zero-camera zone. No image retention or personal biometrics.'
                    : 'Authorized public-area analysis. Pose overlays are not anonymization; annotations may contain identifiable people.'}
                </p>
              </div>

              {/* Linked Alert notice if available */}
              {activeAlertForZone && (
                <div className="p-3 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 text-xs">
                  <div className="flex items-center justify-between font-bold mb-1">
                    <span className="flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5 text-[#F59E0B]" />
                      <span>Active Incident #{activeAlertForZone.incidentNumber}</span>
                    </span>
                    <span className="text-[10px] font-mono">{activeAlertForZone.level}</span>
                  </div>
                  <p className="text-[11px] text-amber-800 line-clamp-2">
                    {activeAlertForZone.title}: {activeAlertForZone.reason}
                  </p>
                </div>
              )}
            </div>

            {/* Inspector Footer Actions */}
            <div className="p-4 border-t border-[#F1F5F9] space-y-2">
              {/* Direct entry into dedicated Private Area Monitoring View if private zone */}
              {selectedZone.isPrivate && (
                <button
                  onClick={() => openPrivateAreaMonitoring(selectedZone.id)}
                  className="w-full py-2.5 px-3 rounded-xl bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white font-black text-xs flex items-center justify-center gap-1.5 transition-all shadow-sm cursor-pointer active:scale-95"
                >
                  <Lock className="w-3.5 h-3.5" />
                  <span>Enter 3D Private Monitoring View &rarr;</span>
                </button>
              )}

              {activeAlertForZone && (
                <button
                  onClick={() => {
                    setSelectedAlertId(activeAlertForZone.id);
                    setActivePage('alerts');
                  }}
                  className="w-full py-2 px-3 rounded-xl bg-[#2563EB] hover:bg-blue-700 text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-all shadow-xs cursor-pointer"
                >
                  <span>Review Incident #{activeAlertForZone.incidentNumber}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              )}
              {!selectedZone.isPrivate && (
                <button
                  onClick={() => {
                    setSelectedZoneId(selectedZone.id);
                    setActivePage('live_monitoring');
                  }}
                  className="w-full py-2 px-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-[#0F172A] font-semibold text-xs flex items-center justify-center gap-1 transition-colors cursor-pointer"
                >
                  <span>Inspect Zone Feeds &rarr;</span>
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 4. BOTTOM ARCHITECTURAL SUMMARY BAR */}
      <div className="px-5 py-2.5 bg-white border-t border-[#E2E8F0] flex flex-wrap items-center justify-between text-xs text-[#64748B] gap-2 z-10">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold text-[#0F172A]">6 Mapped School Blocks:</span>
          <span className="text-[11px]">Entrance, Corridor A, Canteen, Staircase, School Hall, Blind Spot Zone</span>
        </div>
        <div className="flex items-center gap-2">
          {!isInspectorOpen && (
            <button
              onClick={() => setIsInspectorOpen(true)}
              className="text-[11px] text-[#2563EB] font-bold hover:underline cursor-pointer flex items-center gap-1"
            >
              <span>Open Zone Inspector</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
