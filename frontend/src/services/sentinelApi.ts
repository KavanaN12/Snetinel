import apiClient from '../api/client';
import type {
  AttackPathAnalysisResponse,
  AuditLogResponse,
  ComplianceEvaluationResponse,
  DashboardSummaryResponse,
  DiscoveredCloudResourceResponse,
  DiscoveryRunResponse,
  DriftEventResponse,
  FindingEvaluationResponse,
  RagDocumentResponse,
  TokenResponse,
  UserResponse,
  WorkspaceResponse,
} from '../types/api';

export const authService = {
  login: (email: string, password: string) =>
    apiClient.post<TokenResponse>('/auth/login', { email, password }),
  register: (email: string, password: string) =>
    apiClient.post<UserResponse>('/auth/register', { email, password }),
  refresh: (refreshToken: string) =>
    apiClient.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken }),
  logout: (refreshToken: string) => apiClient.post('/auth/logout', { refresh_token: refreshToken }),
};

export const workspaceService = {
  list: () => apiClient.get<WorkspaceResponse[]>('/workspaces'),
  create: (name: string, description?: string) =>
    apiClient.post<WorkspaceResponse>('/workspaces', { name, description }),
  get: (workspaceId: string) => apiClient.get<WorkspaceResponse>(`/workspaces/${workspaceId}`),
};

export const dashboardService = {
  getSummary: (workspaceId: string) =>
    apiClient.get<DashboardSummaryResponse>(`/dashboard/workspaces/${workspaceId}/summary`),
};

export const discoveryService = {
  getRuns: (workspaceId: string) => apiClient.get<DiscoveryRunResponse[]>(`/discovery/workspaces/${workspaceId}/runs`),
  getResources: (workspaceId: string) =>
    apiClient.get<DiscoveredCloudResourceResponse[]>(`/discovery/workspaces/${workspaceId}/resources`),
  triggerDiscovery: (workspaceId: string) =>
    apiClient.post<DiscoveryRunResponse>(`/discovery/workspaces/${workspaceId}/discover`, {}),
};

export const attackPathService = {
  getPaths: (workspaceId: string) => apiClient.get<AttackPathAnalysisResponse>(`/attack-path/workspaces/${workspaceId}`),
  analyze: (workspaceId: string) => apiClient.post<AttackPathAnalysisResponse>(`/attack-path/workspaces/${workspaceId}/analyze`),
};

export const findingService = {
  getFindings: (workspaceId: string) => apiClient.get<FindingEvaluationResponse>(`/risk-scoring/workspaces/${workspaceId}/findings`),
};

export const complianceService = {
  evaluate: (workspaceId: string) => apiClient.post<ComplianceEvaluationResponse>(`/compliance/workspaces/${workspaceId}/evaluate`),
};

export const driftService = {
  getEvents: (workspaceId: string) => apiClient.get<DriftEventResponse[]>(`/drift/workspaces/${workspaceId}/events`),
};

export const auditService = {
  listLogs: () => apiClient.get<AuditLogResponse[]>('/audit/logs'),
};

export const ragService = {
  search: (query: string) => apiClient.get<RagDocumentResponse[]>(`/rag/search?query=${encodeURIComponent(query)}`),
  upload: (title: string, content: string, source: string) =>
    apiClient.post('/rag/documents', null, {
      params: { title, content, source },
    }),
};

export const graphService = {
  buildGraph: (workspaceId: string) => apiClient.post(`/graph/workspaces/${workspaceId}/build`),
};
