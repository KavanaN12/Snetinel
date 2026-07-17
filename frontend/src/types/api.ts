export interface UserResponse {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface WorkspaceResponse {
  id: string;
  owner_id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface DashboardSummaryResponse {
  severity_counts: Record<string, number>;
  finding_counts: Record<string, number>;
  resource_counts: Record<string, number>;
  attack_path_counts: Record<string, number>;
}

export interface DiscoveryRunResponse {
  id: string;
  workspace_id: string;
  status: string;
  summary: string;
  resource_count: number;
  discovered_resources: Array<Record<string, string>>;
  started_at: string;
  completed_at?: string | null;
  created_at: string;
}

export interface DiscoveredCloudResourceResponse {
  id: string;
  workspace_id: string;
  discovery_run_id: string;
  resource_type: string;
  resource_id: string;
  name: string;
  arn?: string | null;
  details: Record<string, unknown>;
  created_at: string;
  updated_at?: string | null;
}

export interface AttackPathResponse {
  id: string;
  workspace_id: string;
  attack_type: string;
  steps: Array<Record<string, unknown>>;
  details: Record<string, unknown>;
  created_at: string;
}

export interface AttackPathAnalysisResponse {
  workspace_id: string;
  path_count: number;
  paths: AttackPathResponse[];
}

export interface FindingResponse {
  id: string;
  workspace_id: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  evidence_subgraph: Record<string, unknown>;
  affected_resource_ids: string[];
}

export interface FindingEvaluationResponse {
  workspace_id: string;
  finding_count: number;
  findings: FindingResponse[];
}

export interface ComplianceFindingResponse {
  id?: string | null;
  workspace_id?: string | null;
  check_id: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  remediation: string;
  framework: string;
  details: Record<string, unknown>;
}

export interface ComplianceEvaluationResponse {
  workspace_id?: string | null;
  summary: Record<string, unknown>;
  findings: ComplianceFindingResponse[];
}

export interface DriftEventResponse {
  id?: string | null;
  workspace_id?: string | null;
  event_type: string;
  resource_type: string;
  resource_id: string;
  previous_value?: Record<string, unknown> | null;
  current_value?: Record<string, unknown> | null;
}

export interface AuditLogResponse {
  id: string;
  actor_id: string;
  action: string;
  resource: string;
  method: string;
  path: string;
  status_code: number;
}

export interface RagDocumentResponse {
  id: string;
  title: string;
  source: string;
}
