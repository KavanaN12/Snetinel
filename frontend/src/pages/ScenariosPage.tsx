import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FlaskConical, Play, RotateCcw, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageHeader } from '../components/common/PageHeader';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { PageLoader } from '../components/common/PageLoader';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  attackPathService,
  discoveryService,
  graphService,
  iamAgentService,
  scenarioService,
  workspaceService,
} from '../services/sentinelApi';
import type { ScenarioAssertionResponse, ScenarioDefinitionResponse } from '../types/api';
import { useWorkspaceStore } from '../store/workspace';

const difficultyOrder = ['easy', 'intermediate', 'advanced', 'edge'];

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'The request failed.';
}

async function waitForDiscovery(workspaceId: string, runId: string): Promise<void> {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    await new Promise((resolve) => window.setTimeout(resolve, 500));
    const runs = (await discoveryService.getRuns(workspaceId)).data;
    const run = runs.find((item) => item.id === runId);
    if (run?.status === 'completed') return;
    if (run?.status === 'failed') throw new Error(run.summary || 'LocalStack discovery failed.');
  }
  throw new Error('Discovery did not complete within 20 seconds.');
}

export function ScenariosPage() {
  const selectedWorkspaceId = useWorkspaceStore((state) => state.selectedWorkspaceId);
  const setSelectedWorkspaceId = useWorkspaceStore((state) => state.setSelectedWorkspaceId);
  const [assertions, setAssertions] = useState<Record<string, ScenarioAssertionResponse>>({});
  const queryClient = useQueryClient();

  const { data: workspaces = [], isLoading: workspacesLoading } = useQuery({
    queryKey: ['workspaces'],
    queryFn: async () => (await workspaceService.list()).data,
  });
  const workspace = workspaces.find((item) => item.id === selectedWorkspaceId) ?? workspaces[0];
  const { data: catalog = [], isLoading: catalogLoading, error: catalogError, refetch } = useQuery({
    queryKey: ['scenario-catalog'],
    queryFn: async () => (await scenarioService.listCatalog()).data,
  });
  const { data: runs = [], isLoading: runsLoading, error: runsError } = useQuery({
    queryKey: ['scenario-runs', workspace?.id],
    queryFn: async () => (await scenarioService.listRuns(workspace!.id)).data,
    enabled: Boolean(workspace?.id),
  });

  const activeRun = runs.find((run) => ['loaded', 'seeding', 'failed'].includes(run.status));
  const activeScenario = catalog.find((scenario) => scenario.scenario_id === activeRun?.scenario_id);

  const refreshWorkspaceData = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['scenario-runs', workspace?.id] }),
      queryClient.invalidateQueries({ queryKey: ['discovery-resources', workspace?.id] }),
      queryClient.invalidateQueries({ queryKey: ['discovery-runs', workspace?.id] }),
      queryClient.invalidateQueries({ queryKey: ['attack-paths', workspace?.id] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary', workspace?.id] }),
      queryClient.invalidateQueries({ queryKey: ['iam-agent-runs', workspace?.id] }),
      queryClient.invalidateQueries({ queryKey: ['findings', workspace?.id] }),
    ]);
  };

  const loadMutation = useMutation({
    mutationFn: async (scenarioId: string) => {
      if (!workspace) throw new Error('Select a workspace first.');
      return (await scenarioService.load(workspace.id, scenarioId)).data;
    },
    onSuccess: async () => {
      setAssertions({});
      await refreshWorkspaceData();
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      if (!workspace?.id || !activeRun) throw new Error('Load a scenario into an empty workspace first.');
      const discoveryRun = (await discoveryService.triggerDiscovery(workspace.id)).data;
      await waitForDiscovery(workspace.id, discoveryRun.id);
      await graphService.buildGraph(workspace.id);
      await attackPathService.analyze(workspace.id);
      const result = (await scenarioService.assert(workspace.id, activeRun.id, 'baseline')).data;
      return result;
    },
    onSuccess: async (result) => {
      setAssertions((current) => ({ ...current, baseline: result }));
      await refreshWorkspaceData();
    },
  });

  const agentMutation = useMutation({
    mutationFn: async () => {
      if (!workspace?.id || !activeRun) throw new Error('Load and analyze a scenario first.');
      const run = (await iamAgentService.run(workspace.id)).data;
      const result = (await scenarioService.assert(workspace.id, activeRun.id, 'post_remediation')).data;
      return { run, result };
    },
    onSuccess: async ({ result }) => {
      setAssertions((current) => ({ ...current, post_remediation: result }));
      await refreshWorkspaceData();
    },
  });

  const resetMutation = useMutation({
    mutationFn: async () => {
      if (!workspace?.id || !activeRun) throw new Error('There is no active scenario to reset.');
      return (await scenarioService.reset(workspace.id, activeRun.id)).data;
    },
    onSuccess: async () => {
      setAssertions({});
      await refreshWorkspaceData();
    },
  });

  const groupedScenarios = useMemo(
    () => difficultyOrder.map((difficulty) => ({
      difficulty,
      scenarios: catalog.filter((scenario) => scenario.difficulty === difficulty),
    })).filter((group) => group.scenarios.length > 0),
    [catalog],
  );

  if (workspacesLoading || catalogLoading || (workspace && runsLoading)) return <PageLoader />;
  if (catalogError) return <ErrorState message="Unable to load the scenario catalog." onRetry={() => void refetch()} />;
  if (runsError) return <ErrorState message="Unable to load scenario history for this workspace." onRetry={() => void queryClient.invalidateQueries({ queryKey: ['scenario-runs', workspace?.id] })} />;

  const errors = [loadMutation.error, analyzeMutation.error, agentMutation.error, resetMutation.error].filter(Boolean);

  return (
    <div>
      <PageHeader title="LocalStack scenario library" description="Load isolated IAM fixtures, run the real discovery and analysis pipeline, execute bounded remediation, compare assertions, and reset only the selected scenario.">
        <select
          aria-label="Scenario workspace"
          className="rounded-xl border border-white/10 bg-slate-900/70 px-3 py-2 text-sm text-slate-200"
          value={workspace?.id ?? ''}
          onChange={(event) => setSelectedWorkspaceId(event.target.value)}
        >
          {workspaces.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
      </PageHeader>

      <div role="note" className="mb-5 rounded-xl border border-amber-400/20 bg-amber-400/5 p-4 text-sm text-amber-100">
        Scenarios mutate LocalStack only. Use a dedicated empty workspace for each run; discovery is filtered to that run’s exact resource manifest. A reset removes only its manifested IAM policies, principals, bucket object, and bucket.
      </div>

      {!workspace ? (
        <div>
          <EmptyState title="Create a dedicated workspace" description="Scenario data is isolated by workspace. Create an empty workspace in Settings before loading a fixture." />
          <Link className="mt-3 inline-block text-sm text-cyan-300 underline" to="/settings">Open Settings</Link>
        </div>
      ) : null}

      {errors.map((error, index) => (
        <div key={index} role="alert" className="mb-4 rounded-xl border border-rose-500/20 bg-rose-500/10 p-3 text-sm text-rose-200">
          {errorMessage(error)}
        </div>
      ))}

      {activeRun && activeScenario ? (
        <Card className="mb-6 border-cyan-400/20">
          <CardHeader>
            <CardTitle className="flex items-center justify-between gap-3">
              <span>{activeScenario.name}</span>
              <Badge>{activeRun.status}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-slate-400">{activeScenario.description}</p>
            <div className="flex flex-wrap gap-2">
              <Button
                disabled={analyzeMutation.isPending || activeRun.status !== 'loaded'}
                onClick={() => analyzeMutation.mutate()}
              >
                <Play className="mr-2 h-4 w-4" />
                {analyzeMutation.isPending ? 'Discovering and analyzing…' : 'Discover, graph and analyze'}
              </Button>
              <Button
                variant="secondary"
                disabled={agentMutation.isPending || activeRun.status !== 'loaded'}
                onClick={() => agentMutation.mutate()}
              >
                <ShieldCheck className="mr-2 h-4 w-4" />
                {agentMutation.isPending ? 'Running agent…' : 'Run autonomous agent'}
              </Button>
              <Button
                variant="secondary"
                disabled={resetMutation.isPending}
                onClick={() => resetMutation.mutate()}
              >
                <RotateCcw className="mr-2 h-4 w-4" />
                {resetMutation.isPending ? 'Resetting…' : 'Reset scenario'}
              </Button>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {(['baseline', 'post_remediation'] as const).map((phase) => {
                const result = assertions[phase] ?? (
                  activeRun.actual_results?.[phase] as ScenarioAssertionResponse | undefined
                );
                return (
                  <div key={phase} className="rounded-xl border border-white/10 bg-slate-950/60 p-4">
                    <p className="text-sm font-medium text-slate-100">{phase === 'baseline' ? 'Before remediation' : 'After remediation'}</p>
                    {result ? (
                      <p className={`mt-2 text-sm ${result.passed ? 'text-emerald-300' : 'text-rose-300'}`}>
                        {result.passed ? 'Assertions passed' : 'Assertions failed'} · {String(result.actual.attack_path_count)} attack path(s)
                      </p>
                    ) : <p className="mt-2 text-sm text-slate-500">Not measured yet</p>}
                    {result ? <pre className="mt-3 whitespace-pre-wrap text-xs text-slate-400">{JSON.stringify(result.actual, null, 2)}</pre> : null}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {groupedScenarios.map(({ difficulty, scenarios }) => (
        <section key={difficulty} className="mb-8">
          <h2 className="mb-3 text-lg font-semibold capitalize text-slate-100">{difficulty} scenarios</h2>
          <div className="grid gap-4 xl:grid-cols-2">
            {scenarios.map((scenario: ScenarioDefinitionResponse) => (
              <Card key={scenario.scenario_id}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FlaskConical className="h-4 w-4 text-cyan-300" />
                    {scenario.name}
                  </CardTitle>
                  <p className="text-sm text-slate-400">{scenario.description}</p>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    <Badge>Expected paths: {scenario.expected_attack_paths}</Badge>
                    <Badge>Risk: {scenario.expected_risk}</Badge>
                    {scenario.expected_vulnerabilities.map((vulnerability) => <Badge key={vulnerability}>{vulnerability}</Badge>)}
                  </div>
                  <p className="text-xs text-slate-400">Resources: {scenario.expected_resources.join(', ')}</p>
                  <p className="text-xs text-slate-400">Remediation: {scenario.expected_remediation}</p>
                  <p className="text-xs text-slate-400">Expected end state: {scenario.expected_post_state}</p>
                  <Button
                    variant="secondary"
                    disabled={!workspace || Boolean(activeRun) || loadMutation.isPending}
                    onClick={() => loadMutation.mutate(scenario.scenario_id)}
                  >
                    Load into LocalStack
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      ))}

      {catalog.length === 0 ? <EmptyState title="No executable scenarios" description="The scenario catalog is empty." /> : null}
      {runs.some((run) => run.status === 'reset') ? (
        <Card>
          <CardHeader><CardTitle>Previous runs</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {runs.filter((run) => run.status === 'reset').map((run) => (
              <p key={run.id} className="text-sm text-slate-400">{run.scenario_id} · reset · {new Date(run.created_at).toLocaleString()}</p>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
