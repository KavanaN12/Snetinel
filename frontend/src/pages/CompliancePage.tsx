import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { PageHeader } from '../components/common/PageHeader';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { PageLoader } from '../components/common/PageLoader';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { complianceService, workspaceService } from '../services/sentinelApi';
import { useWorkspaceStore } from '../store/workspace';

export function CompliancePage() {
  const selectedWorkspaceId = useWorkspaceStore((state) => state.selectedWorkspaceId);
  const setSelectedWorkspaceId = useWorkspaceStore((state) => state.setSelectedWorkspaceId);

  const { data: workspaceData, isLoading: workspacesLoading } = useQuery({ queryKey: ['workspaces'], queryFn: async () => (await workspaceService.list()).data });
  const workspace = workspaceData?.find((item) => item.id === selectedWorkspaceId) ?? workspaceData?.[0];

  const { data: complianceData, isLoading, error, refetch } = useQuery({
    queryKey: ['compliance', workspace?.id],
    queryFn: async () => (await complianceService.evaluate(workspace!.id)).data,
    enabled: Boolean(workspace?.id),
  });

  const chartData = useMemo(() => {
    const summary = complianceData?.summary as Record<string, unknown> | undefined;
    if (!summary) return [];
    return Object.entries(summary).map(([name, value]) => ({ name, value: Number(value) || 0 }));
  }, [complianceData]);

  if (workspacesLoading || isLoading) return <PageLoader />;
  if (error) return <ErrorState message="Unable to evaluate compliance posture." onRetry={() => void refetch()} />;

  return (
    <div>
      <PageHeader title="Compliance posture" description="Assess policy health, framework coverage, and remediation backlog for the selected workspace.">
        <select
          className="rounded-xl border border-white/10 bg-slate-900/70 px-3 py-2 text-sm text-slate-200"
          value={workspace?.id ?? ''}
          onChange={(event) => setSelectedWorkspaceId(event.target.value)}
        >
          {workspaceData?.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </PageHeader>

      {chartData.length === 0 && (complianceData?.findings?.length ?? 0) === 0 ? (
        <EmptyState title="No compliance results" description="The backend has not generated any compliance findings for this workspace yet." />
      ) : (
        <div className="grid gap-4 xl:grid-cols-[0.95fr_0.95fr]">
          <Card>
            <CardHeader>
              <CardTitle>Framework overview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                    <XAxis dataKey="name" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip />
                    <Bar dataKey="value" fill="#38bdf8" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Compliance findings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {complianceData?.findings?.map((finding) => (
                <div key={finding.check_id} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium text-slate-100">{finding.title}</p>
                    <Badge tone={finding.severity === 'high' ? 'warning' : 'default'}>{finding.severity}</Badge>
                  </div>
                  <p className="mt-2 text-sm text-slate-400">{finding.remediation}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge>{finding.framework}</Badge>
                    <Badge>{finding.status}</Badge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
