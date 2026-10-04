// ---------------------------------------------------------------------------
// VajraTwin GCS — TypeScript types mirroring the FastAPI backend responses.
// Source of truth: backend/app/schemas + service AnalysisResponse shape.
// ---------------------------------------------------------------------------

export type AdvisoryState =
  | "GO"
  | "GO WITH MONITORING"
  | "GO WITH DERATE"
  | "MAINTENANCE REQUIRED";

export type FaultClass =
  | "NORMAL"
  | "EGT_ANOMALY"
  | "CHT_OVERHEAT"
  | "OIL_PRESSURE_LOW"
  | "VIBRATION_ANOMALY"
  | "BOOST_TURBO_ANOMALY"
  | "SENSOR_ANOMALY"
  | "MULTI_PARAMETER_FAULT";

export type AnomalyStatus = "NOMINAL" | "WATCH" | "ANOMALY";
export type HealthTrend = "IMPROVING" | "STABLE" | "DEGRADING";
export type RiskLevel = "LOW" | "MODERATE" | "ELEVATED" | "HIGH";

// ── Telemetry echoed back by the analysis ──────────────────────────────────
export interface TelemetryEcho {
  rpm: number | null;
  map_kpa: number | null;
  oat_c: number | null;
  egt_avg_c: number | null;
  cht_avg_c: number | null;
  oil_temp_c: number | null;
  oil_pressure_psi: number | null;
  fuel_flow_lph: number | null;
  vibration_rms_g: number | null;
  throttle_pct: number | null;
  altitude_m: number | null;
  mission_phase: string | null;
}

export interface TwinStateBlock {
  rpm: number;
  map_kpa: number;
  oat_c: number;
  load_factor: number;
  volumetric_efficiency: number;
  mass_airflow_kg_s: number;
  inlet_temp_c: number;
}

export interface ExpectedBlock {
  egt_c: number;
  cht_c: number;
  oil_temp_c: number;
  oil_pressure_psi: number;
  vibration_rms_g: number;
}

export interface ResidualsBlock {
  delta_egt_c: number;
  delta_cht_c: number;
  delta_oil_temp_c: number;
  delta_oil_pressure_psi: number;
  delta_vibration_rms_g: number;
}

export interface ContributingFeature {
  channel: string;
  label: string;
  z: number;
  value: number;
  contribution: number;
}

export interface AnomalyBlock {
  anomaly_score: number; // 0..100
  anomaly_status: AnomalyStatus;
  rms_z: number;
  contributing_features: ContributingFeature[];
}

export interface FaultEvidence {
  channel: string;
  value: number;
  threshold: number;
  level: "WARN" | "CRIT";
  direction: string;
}

export interface FaultBlock {
  fault_class: FaultClass;
  fault_label: string;
  severity: number; // 0..1
  evidence: FaultEvidence[];
  active_channels: string[];
}

export interface DegradationContributor {
  factor: string;
  contribution_pct: number;
}

export interface HealthPoint {
  t: number;
  health: number;
}

export interface DegradationBlock {
  health_index: number; // 0..100
  instant_health: number;
  health_trend: HealthTrend;
  degradation_rate_per_min: number;
  major_contributors: DegradationContributor[];
  history: HealthPoint[];
}

export interface RulBlock {
  status: "OK" | "INSUFFICIENT_HISTORY" | "STABLE_NO_DECAY";
  rul_hours: number | null;
  confidence_interval: [number, number] | null;
  confidence_hours: number | null;
  degradation_trend_per_min: number;
  methodology: string;
  message?: string;
}

export interface AdvisoryBlock {
  state: AdvisoryState;
  severity: "NOMINAL" | "MODERATE" | "HIGH" | "CRITICAL";
  root_cause: string;
  evidence: FaultEvidence[];
  recommended_action: string;
  advisory_source: string;
}

export interface ExplanationBlock {
  explanation: string;
  explanation_source: string;
  references_evidence: boolean;
}

// ── Full analysis (POST /api/telemetry, simulation/tick.analysis) ───────────
export interface Analysis {
  engine_id: string;
  sim_time_s: number;
  tick: number;
  data_label: string;
  telemetry: TelemetryEcho;
  twin_state: TwinStateBlock;
  expected: ExpectedBlock;
  residuals: ResidualsBlock;
  anomaly: AnomalyBlock;
  fault: FaultBlock;
  degradation: DegradationBlock;
  rul: RulBlock;
  advisory: AdvisoryBlock;
  explanation: ExplanationBlock;
}

// ── Simulation status ───────────────────────────────────────────────────────
export interface ScenarioInfo {
  key: string;
  label: string;
  description: string;
}

export interface SimulationStatus {
  running: boolean;
  paused: boolean;
  scenario: string;
  fault_severity: number;
  speed: number;
  tick: number;
  sim_time_s: number;
  mission_phase: string;
  engine_id: string;
  available_scenarios: ScenarioInfo[];
}

export interface SimTickResponse {
  advanced: boolean;
  status: SimulationStatus;
  analysis: Analysis | null;
}

// ── Health / DB status ──────────────────────────────────────────────────────
export interface DbStatus {
  backend: string;
  demo_mode: boolean;
  uri: string | null;
  database: string;
  collections: string[];
}

export interface HealthResponse {
  service: string;
  version: string;
  status: string;
  database: DbStatus;
  ai_provider: string;
  physics_engine: string;
  data_label: string;
}

// ── Mission ─────────────────────────────────────────────────────────────────
export interface MissionRequest {
  engine_id?: string;
  mission_duration_hours: number;
  cruise_load: number;
  max_load: number;
  altitude_m: number;
  route_length_km?: number;
  environment: string;
}

export interface MissionResult {
  mission_id: string;
  engine_id: string;
  completion_probability: number;
  completion_probability_pct: number;
  risk_level: RiskLevel;
  limiting_factor: string;
  limiting_factor_key: string;
  factors: Record<string, number>;
  rul_note: string;
  recommendation: string;
  methodology: string;
  health_index_used: number;
  rul_hours_used: number | null;
}

// ── Dashboard summary ───────────────────────────────────────────────────────
export interface DashboardSummary {
  engine_id: string;
  db_status: DbStatus;
  simulation: SimulationStatus;
  health_history: HealthPoint[];
  has_data: boolean;
  data_label?: string;
  sim_time_s?: number;
  telemetry?: TelemetryEcho;
  twin_state?: TwinStateBlock;
  expected?: ExpectedBlock;
  residuals?: ResidualsBlock;
  anomaly?: AnomalyBlock;
  fault?: FaultBlock;
  degradation?: DegradationBlock;
  rul?: RulBlock;
  advisory?: AdvisoryBlock;
  explanation?: ExplanationBlock;
}

// ── Local chart buffer point (frontend-only) ────────────────────────────────
export interface ChartPoint {
  tick: number;
  time: string;
  // residuals
  delta_egt_c: number;
  delta_cht_c: number;
  delta_oil_temp_c: number;
  delta_oil_pressure_psi: number;
  delta_vibration_rms_g: number;
  // health / anomaly
  health_index: number;
  anomaly_score: number;
}

export type ConnectionStatus = "connecting" | "online" | "offline";

// ── Fleet operations ────────────────────────────────────────────────────────
export type FleetStatus = "HEALTHY" | "ATTENTION" | "CRITICAL";

export interface FleetAircraftState {
  uav_id: string;
  callsign: string;
  engine_id: string;
  status: FleetStatus;
  health_index: number;
  fault_class: FaultClass;
  fault_label: string;
  fault_severity: number;
  anomaly_score: number;
  rul_hours: number | null;
  rul_status: string;
  advisory_state: AdvisoryState;
  mission_risk: string | null;
  current_scenario: string;
  mission_phase: string;
  last_update_s: number;
  data_label: string;
  // present only on detail endpoint
  analysis?: Analysis | null;
  simulation?: SimulationStatus;
}

export interface MaintenancePriorityItem {
  rank: number;
  uav_id: string;
  callsign: string;
  status: FleetStatus;
  fault_class: FaultClass;
  health_index: number;
  rul_hours: number | null;
  advisory_state: AdvisoryState;
  reason: string;
}

export interface FleetSummary {
  fleet_name: string;
  data_label: string;
  total_aircraft: number;
  status_counts: { healthy: number; attention: number; critical: number };
  fleet_health: number;
  fleet_health_method: string;
  highest_risk: MaintenancePriorityItem | null;
  maintenance_priority: MaintenancePriorityItem[];
  fault_distribution: Record<string, number>;
  aircraft: FleetAircraftState[];
  generated_at: number;
}
