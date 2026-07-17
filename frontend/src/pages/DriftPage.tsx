import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Filter } from 'lucide-react';
import { PageHeader } from '../components/common/PageHeader';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { PageLoader } from '../components/common/PageLoader';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { driftService, workspaceService } from '../services/sentinelApi';
import { useWorkspaceStore } from '../store/workspace';

export function DriftPage() {
  const selectedWorkspaceId = useWorkspaceStore((state) => state.selectedWorkspaceId);
  const setSelectedWorkspaceId = useWorkspaceStore((state) => state.setSelectedWorkspaceId);
  const [resourceFilter, setResourceFilter] = useState('all');

  const { data: workspaceData, isLoading: workspacesLoading } = useQuery({ queryKey: ['workspaces'], queryFn: async () => (await workspaceService.list()).data });
  const workspace = workspaceData?.find((item) => item.id === selectedWorkspaceId) ?? workspaceData?.[0];

  const { data: driftData, isLoading, error, refetch } = useQuery({
    queryKey: ['drift', workspace?.id],
    queryFn: async () => (await driftService.getEvents(workspace!.id)).data,
    enabled: Boolean(workspace?.id),
  });

  const filteredEvents = useMemo(() => {
    if (resourceFilter === 'all') return driftData ?? [];
    return (driftData ?? []).filter((event) => event.resource_type === resourceFilter);
  }, [driftData, resourceFilter]);

  if (workspacesLoading || isLoading) return <PageLoader />;
  if (error) return <ErrorState message="Unable to load drift events." onRetry={() => void refetch()} />;

  return (
    <div>
      <PageHeader title="Drift detection" description="Track configuration deltas and compare previous and current states for sensitive cloud resources.">
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

      <Card>
        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <CardTitle>Drift timeline</CardTitle>
          <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-slate-400">
            <Filter className="h-4 w-4" />
            <select className="bg-transparent text-slate-200" value={resourceFilter} onChange={(event) => setResourceFilter(event.target.value)}>
              <option value="all">All resource types</option>
              <option value="virtual-machine">Virtual Machine</option>
              <option value="storage-account">Storage Account</option>
            </select>
          </label>
        </CardHeader>
        <CardContent>
          {filteredEvents.length === 0 ? (
            <EmptyState title="No drift events recorded" description="The backend has not reported any drift for this workspace yet." />
          ) : (
            <div className="space-y-3">
              {filteredEvents.map((event) => (
                <div key={event.id ?? `${event.resource_id}-${event.event_type}`} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-slate-100">{event.event_type}</p>
                      <p className="mt-1 text-sm text-slate-400">{event.resource_type} • {event.resource_id}</p>
                    </div>
                    <Badge tone="warning">Observed drift</Badge>
                  </div>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    <div className="rounded-xl border border-white/10 bg-slate-900/70 p-3">
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Previous</p>
                      <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-400">{JSON.stringify(event.previous_value ?? {}, null, 2)}</pre>
                    </div>
                    <div className="rounded-xl border border-white/10 bg-slate-900/70 p-3">
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Current</p>
                      <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-400">{JSON.stringify(event.current_value ?? {}, null, 2)}</pre>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
