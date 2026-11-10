export interface MotionAnalysis {
  rule_version:string;source_mode:string;status:string;reason:string;notice:string;timestamp?:string;
  temporal_supported:boolean;highlighted_track_ids:string[];
  excluded_track_ids?:string[];
  rules:{proximity_distance_m:number;proximity_duration_seconds:number;window_seconds:number;min_reversals:number;
    min_observation_span_seconds:number;min_leg_displacement_m:number;min_leg_duration_seconds:number;
    min_motion_speed_mps:number;reversal_angle_degrees:number;max_gap_seconds:number;min_path_length_m:number;max_net_path_ratio:number};
  nearest_pair:{track_ids:string[];distance_m:number;proximity_duration_seconds:number;proximity_candidate:boolean}|null;
  candidates:{rule:string;track_ids:string[];reason:string}[];
  tracks:{id:string;sample_count:number;observed_span_seconds:number;speed_mps:number|null;velocity_origin:string;
    velocity_mps:{x:number;y:number;z:number}|null;acceleration_magnitude_mps2:number|null;
    heading_degrees:number|null;direction_change_degrees:number|null;reversals_in_window:number;
    meaningful_legs:number;path_length_m:number;net_path_ratio:number|null;repeated_motion_candidate:boolean}[];
}
