import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { RotateCw, ShieldAlert, ShieldCheck } from 'lucide-react';
import { Background, Controls, ReactFlow } from '@xyflow/react';
import { PageHeader } from '../components/common/PageHeader';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { PageLoader } from '../components/common/PageLoader';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { attackPathService, graphService, workspaceService } from '../services/sentinelApi';
import { useWorkspaceStore } from '../store/workspace';
import { formatDate } from '../lib/utils';
import '@xyflow/react/dist/style.css';

export function AttackPathsPage() {
  const selectedWorkspaceId = useWorkspaceStore((state) => state.selectedWorkspaceId);
  const setSelectedWorkspaceId = useWorkspaceStore((state) => state.setSelectedWorkspaceId);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: workspaceData, isLoading: workspacesLoading } = useQuery({ queryKey: ['workspaces'], queryFn: async () => (await workspaceService.list()).data });
  const workspace = workspaceData?.find((item) => item.id === selectedWorkspaceId) ?? workspaceData?.[0];

  const { data: pathsData, isLoading, error, refetch } = useQuery({
    queryKey: ['attack-paths', workspace?.id],
    queryFn: async () => (await attackPathService.getPaths(workspace!.id)).data,
    enabled: Boolean(workspace?.id),
  });

  const analyzeMutation = useMutation({
    mutationFn: async (workspaceId: string) => {
      await graphService.buildGraph(workspaceId);
      return (await attackPathService.analyze(workspaceId)).data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['attack-paths', workspace?.id] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-summary', workspace?.id] }),
        queryClient.invalidateQueries({ queryKey: ['findings', workspace?.id] }),
      ]);
    },
  });

  const pathList = pathsData?.paths ?? [];
  const selectedAttackPath = pathList.find((item) => item.id === selectedPath) ?? pathList[0];

  const initialNodes = useMemo(() => {
    const steps = selectedAttackPath?.steps ?? [];
    return steps.map((step, index) => ({
      id: String(step.id ?? `${selectedAttackPath?.id ?? 'path'}-${index}`),
      position: { x: 80 + index * 180, y: 100 + (index % 2) * 80 },
      data: { label: `${String(step?.name ?? `Step ${index + 1}`)} · ${String(step?.node_type ?? 'node')}` },
      style: { background: '#0f172a', border: '1px solid rgba(34,211,238,0.25)', color: '#e2e8f0', padding: 8 },
    }));
  }, [selectedAttackPath]);

  const initialEdges = useMemo(() => {
    const steps = selectedAttackPath?.steps ?? [];
    return steps.slice(1).map((_, index) => ({
      id: `edge-${index}`,
      source: String(steps[index]?.id ?? `${selectedAttackPath?.id ?? 'path'}-${index}`),
      target: String(steps[index + 1]?.id ?? `${selectedAttackPath?.id ?? 'path'}-${index + 1}`),
      animated: true,
      style: { stroke: '#22d3ee' },
    }));
  }, [selectedAttackPath]);

  if (workspacesLoading || isLoading) return <PageLoader />;
  if (error) return <ErrorState message="Unable to load attack path analysis." onRetry={() => void refetch()} />;

  return (
    <div>
      <PageHeader title="Attack path reasoning" description="Inspect exploitable chains, evaluate progression, and prioritize defensive actions with evidence-backed context.">
        <select
          aria-label="Workspace"
          className="rounded-xl border border-white/10 bg-slate-900/70 px-3 py-2 text-sm text-slate-200"
          value={workspace?.id ?? ''}
          onChange={(event) => setSelectedWorkspaceId(event.target.value)}
        >
          {workspaceData?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <Button
          disabled={!workspace?.id || analyzeMutation.isPending}
          onClick={() => workspace?.id && analyzeMutation.mutate(workspace.id)}
        >
          <RotateCw className={`mr-2 h-4 w-4 ${analyzeMutation.isPending ? 'animate-spin' : ''}`} />
          {analyzeMutation.isPending ? 'Analyzing…' : 'Build graph & analyze'}
        </Button>
      </PageHeader>

      {analyzeMutation.error ? (
        <div role="alert" className="mb-4 rounded-xl border border-rose-500/20 bg-rose-500/10 p-3 text-sm text-rose-200">
          Graph analysis failed: {analyzeMutation.error instanceof Error ? analyzeMutation.error.message : 'Request failed'}
        </div>
      ) : null}

      {pathList.length === 0 ? (
        <EmptyState title="No attack paths detected" description="Run cloud discovery, then build the current graph and analyze it to populate this view." />
      ) : (
        <div className="grid gap-4 xl:grid-cols-[0.95fr_0.95fr]">
          <Card className="overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Interactive graph</CardTitle>
              <Badge tone="danger">{pathList.length} routes</Badge>
            </CardHeader>
            <CardContent>
              <div className="h-[420px] rounded-2xl border border-white/10 bg-slate-950/60 p-2">
                <ReactFlow nodes={initialNodes} edges={initialEdges} fitView proOptions={{ hideAttribution: true }}>
                  <Background />
                  <Controls />
                </ReactFlow>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Path details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {pathList.map((path) => (
                <button key={path.id} onClick={() => setSelectedPath(path.id)} className={`w-full rounded-2xl border p-4 text-left transition ${selectedAttackPath?.id === path.id ? 'border-cyan-400/30 bg-cyan-500/10' : 'border-white/10 bg-slate-950/60'}`}>
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-slate-100">{path.attack_type}</p>
                    <Badge>{path.steps.length} steps</Badge>
                  </div>
                  <p className="mt-2 text-sm text-slate-400">{String(path.details?.summary ?? 'Attack path discovered from existing graph context.')}</p>
                </button>
              ))}
              <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                <div className="flex items-center gap-2 text-cyan-300">
                  <ShieldAlert className="h-4 w-4" />
                  <p className="font-medium text-slate-100">Risk explanation</p>
                </div>
                <p className="mt-3 text-sm text-slate-400">{String(selectedAttackPath?.details?.summary ?? 'No summary available.')}</p>
                <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
                  <span>Created {formatDate(selectedAttackPath?.created_at)}</span>
                  <Button variant="secondary" size="sm" onClick={() => navigate('/iam-agent')}>
                    <ShieldCheck className="mr-2 h-4 w-4" /> Open IAM agent
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
