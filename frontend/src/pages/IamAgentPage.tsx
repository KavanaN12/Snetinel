import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bot, CircleAlert, History, Play, RotateCw, ShieldCheck } from 'lucide-react';
import { getApiErrorMessage } from '../api/client';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { PageHeader } from '../components/common/PageHeader';
import { PageLoader } from '../components/common/PageLoader';
import { iamAgentService, workspaceService } from '../services/sentinelApi';
import { useWorkspaceStore } from '../store/workspace';

const lifecycleStages = [
  'OBSERVE',
  'ANALYSE',
  'PRIORITISE',
  'DECIDE',
  'PLAN',
  'EXECUTE',
  'VERIFY',
  'RE-PLAN',
  'REPORT',
];

export function IamAgentPage() {
  const queryClient = useQueryClient();
  const selectedWorkspaceId = useWorkspaceStore((state) => state.selectedWorkspaceId);
  const setSelectedWorkspaceId = useWorkspaceStore((state) => state.setSelectedWorkspaceId);
  const [maxAttempts, setMaxAttempts] = useState(3);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const { data: workspaces, isLoading: workspacesLoading } = useQuery({
    queryKey: ['workspaces'],
    queryFn: async () => (await workspaceService.list()).data,
  });

  useEffect(() => {
    if (!selectedWorkspaceId && workspaces?.[0]?.id) {
      setSelectedWorkspaceId(workspaces[0].id);
    }
  }, [selectedWorkspaceId, setSelectedWorkspaceId, workspaces]);

  const workspace = workspaces?.find((item) => item.id === selectedWorkspaceId) ?? workspaces?.[0];
  const {
    data: runs,
    isLoading: runsLoading,
    error: runsError,
    refetch,
  } = useQuery({
    queryKey: ['iam-agent-runs', workspace?.id],
    queryFn: async () => (await iamAgentService.listRuns(workspace!.id)).data,
    enabled: Boolean(workspace?.id),
  });

  const runMutation = useMutation({
    mutationFn: async () => (await iamAgentService.run(workspace!.id, maxAttempts)).data,
    onSuccess: async (run) => {
      setSelectedRunId(run.id);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['iam-agent-runs', workspace?.id] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-summary', workspace?.id] }),
        queryClient.invalidateQueries({ queryKey: ['findings', workspace?.id] }),
        queryClient.invalidateQueries({ queryKey: ['attack-paths', workspace?.id] }),
        queryClient.invalidateQueries({ queryKey: ['discovery-resources', workspace?.id] }),
      ]);
    },
  });

  const selectedRun = useMemo(
    () => runs?.find((run) => run.id === selectedRunId) ?? runs?.[0] ?? runMutation.data,
    [runMutation.data, runs, selectedRunId],
  );
  const lifecycleByStage = new Map(
    (selectedRun?.lifecycle ?? []).map((event) => [String(event.stage), event]),
  );
  const statusTone = selectedRun?.status === 'verified'
    ? 'success'
    : selectedRun?.status === 'no_findings'
      ? 'default'
      : selectedRun?.status === 'blocked'
        ? 'danger'
        : 'warning';
  const runError = runMutation.error ? getApiErrorMessage(runMutation.error) : null;

  if (workspacesLoading || (Boolean(workspace?.id) && runsLoading)) return <PageLoader />;
  if (runsError) {
    return <ErrorState message="Unable to load autonomous agent history." onRetry={() => void refetch()} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Autonomous IAM agent"
        description="Run evidence-based IAM analysis, controlled LocalStack remediation, fresh verification, and bounded adaptive re-planning."
      >
        {workspaces?.length ? (
          <select
            aria-label="Workspace"
            className="rounded-xl border border-white/10 bg-slate-900/70 px-3 py-2 text-sm text-slate-200"
            value={workspace?.id ?? ''}
            onChange={(event) => setSelectedWorkspaceId(event.target.value)}
          >
            {workspaces.map((item) => (
              <option key={item.id} value={item.id}>{item.name}</option>
            ))}
          </select>
        ) : null}
      </PageHeader>

      {!workspace ? (
        <EmptyState title="Create a workspace first" description="The agent runs against an owned workspace and its discovered AWS/LocalStack resources." />
      ) : (
        <>
          <Card className="border-amber-400/20 bg-amber-500/5">
            <CardContent className="flex items-start gap-3 py-4 text-sm text-amber-100">
              <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
              <p>Remediation is restricted by the backend to the configured LocalStack endpoint. It will not apply IAM changes to a live AWS account.</p>
            </CardContent>
          </Card>

          <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Bot className="h-5 w-5 text-cyan-300" /> Start an agent run</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <label className="block text-sm text-slate-300" htmlFor="max-attempts">
                  Maximum remediation attempts
                </label>
                <select
                  id="max-attempts"
                  className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-slate-100"
                  value={maxAttempts}
                  onChange={(event) => setMaxAttempts(Number(event.target.value))}
                >
                  {[1, 2, 3, 4, 5].map((attempts) => <option key={attempts} value={attempts}>{attempts}</option>)}
                </select>
                <Button
                  className="w-full"
                  disabled={runMutation.isPending}
                  onClick={() => runMutation.mutate()}
                >
                  {runMutation.isPending ? (
                    <><RotateCw className="mr-2 h-4 w-4 animate-spin" /> Running analysis and verification…</>
                  ) : (
                    <><Play className="mr-2 h-4 w-4" /> Run autonomous analysis</>
                  )}
                </Button>
                {runError ? <p role="alert" className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-3 text-sm text-rose-200">{runError}</p> : null}
                <p className="text-xs leading-5 text-slate-500">
                  Each run recollects the workspace, regenerates graph and attack-path findings, applies only validated targeted changes, and checks the result against a fresh snapshot.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2"><History className="h-5 w-5 text-cyan-300" /> Run history</CardTitle>
                <Button variant="secondary" size="sm" onClick={() => void refetch()}>
                  <RotateCw className="mr-2 h-4 w-4" /> Refresh
                </Button>
              </CardHeader>
              <CardContent className="space-y-3">
                {!runs?.length && !runMutation.data ? (
                  <p className="text-sm text-slate-400">No agent runs have been recorded for this workspace.</p>
                ) : (
                  (runs ?? (runMutation.data ? [runMutation.data] : [])).map((run) => (
                    <button
                      key={run.id}
                      className={`flex w-full items-center justify-between rounded-xl border p-3 text-left ${selectedRun?.id === run.id ? 'border-cyan-400/30 bg-cyan-500/10' : 'border-white/10 bg-slate-950/50'}`}
                      onClick={() => setSelectedRunId(run.id)}
                    >
                      <span>
                        <span className="block text-sm font-medium text-slate-100">{new Date(run.created_at).toLocaleString()}</span>
                        <span className="mt-1 block text-xs text-slate-400">{run.baseline_path_count} → {run.final_path_count} paths · {run.attempts.length} attempts</span>
                      </span>
                      <Badge tone={run.status === 'verified' ? 'success' : run.status === 'blocked' ? 'danger' : 'warning'}>{run.status.replaceAll('_', ' ')}</Badge>
                    </button>
                  ))
                )}
              </CardContent>
            </Card>
          </div>

          {selectedRun ? (
            <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-cyan-300" /> Latest outcome</CardTitle>
                  <Badge tone={statusTone}>{selectedRun.status.replaceAll('_', ' ')}</Badge>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <Outcome label="Attack paths" value={`${selectedRun.baseline_path_count} → ${selectedRun.final_path_count}`} />
                    <Outcome label="Path reduction" value={percent(selectedRun.evaluation.attack_path_reduction_percent)} />
                    <Outcome label="Risk reduction" value={percent(selectedRun.evaluation.risk_reduction_percent)} />
                    <Outcome label="Remediation success" value={percent(selectedRun.evaluation.remediation_success_rate == null ? null : selectedRun.evaluation.remediation_success_rate * 100)} />
                    <Outcome label="Verification success" value={percent(selectedRun.evaluation.verification_success_rate == null ? null : selectedRun.evaluation.verification_success_rate * 100)} />
                    <Outcome label="Re-planning attempts" value={String(selectedRun.evaluation.replanning_attempts)} />
                    <Outcome label="Unnecessary changes" value={String(selectedRun.evaluation.unnecessary_permission_changes)} />
                    <Outcome label="Execution time" value={`${selectedRun.evaluation.execution_time_seconds.toFixed(2)}s`} />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Lifecycle evidence</CardTitle></CardHeader>
                <CardContent className="space-y-2">
                  {lifecycleStages.map((stage) => {
                    const event = lifecycleByStage.get(stage);
                    return (
                      <div key={stage} className="flex items-start justify-between gap-4 rounded-xl border border-white/10 bg-slate-950/50 p-3">
                        <div>
                          <p className="text-sm font-medium text-slate-100">{stage}</p>
                          {event ? <p className="mt-1 text-xs text-slate-400">{lifecycleDetail(event)}</p> : null}
                        </div>
                        <Badge tone={event?.status === 'completed' ? 'success' : event?.status === 'failed' || event?.status === 'blocked' ? 'danger' : 'default'}>
                          {event?.status ?? 'not reached'}
                        </Badge>
                      </div>
                    );
                  })}
                </CardContent>
              </Card>

              <Card className="xl:col-span-2">
                <CardHeader><CardTitle>Remediation attempts and rollback data</CardTitle></CardHeader>
                <CardContent>
                  {selectedRun.attempts.length ? (
                    <div className="space-y-3">
                      {selectedRun.attempts.map((attempt) => (
                        <div key={`${attempt.attempt}-${attempt.action}`} className="rounded-xl border border-white/10 bg-slate-950/50 p-4">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-sm font-medium text-slate-100">Attempt {attempt.attempt}: {attempt.action}</p>
                            <Badge tone={attempt.verification_passed ? 'success' : 'warning'}>{attempt.verification_passed ? 'target path cleared' : 'target path remains'}</Badge>
                          </div>
                          <p className="mt-2 break-all text-xs text-slate-400">{attempt.principal_type} {attempt.principal_name} · {attempt.resource_arn}</p>
                          {typeof attempt.remaining_attack_paths === 'number' ? (
                            <p className="mt-2 text-xs text-slate-500">{attempt.remaining_attack_paths} total attack path(s) remain after verification.</p>
                          ) : null}
                          <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-400">{JSON.stringify(attempt.rollback, null, 2)}</pre>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-400">This run recorded no remediation attempts.</p>
                  )}
                </CardContent>
              </Card>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

function Outcome({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/50 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 font-medium text-slate-100">{value}</p>
    </div>
  );
}

function percent(value: number | null) {
  return value == null ? '—' : `${value.toFixed(1)}%`;
}

function lifecycleDetail(event: Record<string, unknown>) {
  return Object.entries(event)
    .filter(([key]) => !['stage', 'status', 'timestamp'].includes(key))
    .map(([key, value]) => `${key.replaceAll('_', ' ')}: ${String(value)}`)
    .join(' · ');
}
