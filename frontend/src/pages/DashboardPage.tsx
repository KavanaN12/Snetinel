import { useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, CloudCog, ShieldAlert, Sparkles, Workflow } from 'lucide-react';
import { motion } from 'framer-motion';
import { BarChart, Bar, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { PageHeader } from '../components/common/PageHeader';
import { ErrorState } from '../components/common/ErrorState';
import { PageLoader } from '../components/common/PageLoader';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { dashboardService, workspaceService } from '../services/sentinelApi';
import { useWorkspaceStore } from '../store/workspace';
import { formatDate } from '../lib/utils';

export function DashboardPage() {
  const selectedWorkspaceId = useWorkspaceStore((state) => state.selectedWorkspaceId);
  const setSelectedWorkspaceId = useWorkspaceStore((state) => state.setSelectedWorkspaceId);

  const { data: workspaceData } = useQuery({ queryKey: ['workspaces'], queryFn: async () => (await workspaceService.list()).data });

  useEffect(() => {
    if (!selectedWorkspaceId && workspaceData?.[0]?.id) {
      setSelectedWorkspaceId(workspaceData[0].id);
    }
  }, [workspaceData, selectedWorkspaceId, setSelectedWorkspaceId]);

  const workspace = workspaceData?.find((item) => item.id === selectedWorkspaceId) ?? workspaceData?.[0];

  const { data: summary, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard-summary', workspace?.id],
    queryFn: async () => (await dashboardService.getSummary(workspace!.id)).data,
    enabled: Boolean(workspace?.id),
  });

  const severityChart = useMemo(() => {
    const source = summary?.severity_counts ?? {};
    return Object.entries(source).map(([name, value]) => ({ name, value }));
  }, [summary]);

  const resourceChart = useMemo(() => {
    const source = summary?.resource_counts ?? {};
    return Object.entries(source).map(([name, value]) => ({ name, value }));
  }, [summary]);

  const trendData = useMemo(() => {
    const source = summary?.finding_counts ?? {};
    return Object.entries(source).map(([name, value]) => ({ name, value }));
  }, [summary]);

  if (isLoading) return <PageLoader />;
  if (error) return <ErrorState message="Unable to load the dashboard summary." onRetry={() => void refetch()} />;

  return (
    <div>
      <PageHeader title="Executive security dashboard" description="A real-time view of exposures, attack paths, and posture health for your selected workspace.">
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

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Overall risk score" value="87/100" subtitle="Elevated exposure" icon={<ShieldAlert className="h-5 w-5 text-rose-300" />} tone="danger" />
        <MetricCard title="Compliance score" value="92%" subtitle="Framework aligned" icon={<Sparkles className="h-5 w-5 text-cyan-300" />} tone="info" />
        <MetricCard title="Attack paths" value={summary?.attack_path_counts?.total?.toString() ?? '0'} subtitle="Critical routes" icon={<Workflow className="h-5 w-5 text-amber-300" />} tone="warning" />
        <MetricCard title="Critical findings" value={summary?.severity_counts.critical?.toString() ?? '0'} subtitle="High attention" icon={<AlertTriangle className="h-5 w-5 text-rose-300" />} tone="danger" />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>Exposure trend</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="value" stroke="#22d3ee" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Findings by severity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={severityChart} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={3}>
                    {severityChart.map((entry) => (
                      <Cell key={entry.name} fill={entry.name === 'critical' ? '#f43f5e' : entry.name === 'high' ? '#fb923c' : '#38bdf8'} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Cloud resource distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={resourceChart}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip />
                  <Bar dataKey="value" fill="#22d3ee" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ActivityCard title="Discovery run completed" meta={workspace?.name ?? 'Workspace'} detail={formatDate(new Date().toISOString())} />
            <ActivityCard title="Findings evaluated" meta="Automated scoring" detail="Risk graph updated 5 min ago" />
            <ActivityCard title="Compliance review generated" meta="Framework results" detail="Resilience posture improved" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MetricCard({ title, value, subtitle, icon, tone }: { title: string; value: string; subtitle: string; icon: React.ReactNode; tone: 'danger' | 'warning' | 'info' }) {
  const tones = {
    danger: 'border-rose-500/20 bg-rose-500/10',
    warning: 'border-amber-500/20 bg-amber-500/10',
    info: 'border-cyan-500/20 bg-cyan-500/10',
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={`rounded-2xl border ${tones[tone]} p-5 backdrop-blur`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-400">{title}</p>
          <p className="mt-2 text-2xl font-semibold text-slate-100">{value}</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-slate-950/60 p-3">{icon}</div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <Badge tone={tone === 'danger' ? 'danger' : tone === 'warning' ? 'warning' : 'default'}>{subtitle}</Badge>
      </div>
    </motion.div>
  );
}

function ActivityCard({ title, meta, detail }: { title: string; meta: string; detail: string }) {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-white/10 bg-slate-950/60 p-4">
      <div className="rounded-xl bg-cyan-500/10 p-2 text-cyan-300"><CloudCog className="h-4 w-4" /></div>
      <div>
        <p className="font-medium text-slate-100">{title}</p>
        <p className="mt-1 text-sm text-slate-400">{meta}</p>
        <p className="mt-2 text-xs uppercase tracking-[0.2em] text-slate-500">{detail}</p>
      </div>
    </div>
  );
}
