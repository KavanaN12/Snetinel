import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { PageHeader } from '../components/common/PageHeader';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { PageLoader } from '../components/common/PageLoader';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { discoveryService, workspaceService } from '../services/sentinelApi';
import { useWorkspaceStore } from '../store/workspace';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { formatDate } from '../lib/utils';

export function DiscoveryPage() {
  const selectedWorkspaceId = useWorkspaceStore((state) => state.selectedWorkspaceId);
  const setSelectedWorkspaceId = useWorkspaceStore((state) => state.setSelectedWorkspaceId);
  const [search, setSearch] = useState('');
  const [selectedResource, setSelectedResource] = useState<DiscoveredResource | null>(null);

  const { data: workspaceData, isLoading: workspacesLoading } = useQuery({ queryKey: ['workspaces'], queryFn: async () => (await workspaceService.list()).data });
  const workspace = workspaceData?.find((item) => item.id === selectedWorkspaceId) ?? workspaceData?.[0];

  const { data: resourceData, isLoading, error, refetch } = useQuery({
    queryKey: ['discovery-resources', workspace?.id],
    queryFn: async () => (await discoveryService.getResources(workspace!.id)).data,
    enabled: Boolean(workspace?.id),
  });

  const filteredResources = useMemo(() => {
    const term = search.toLowerCase();
    return (resourceData ?? []).filter((resource) =>
      [resource.name, resource.resource_type, resource.resource_id, resource.arn ?? ''].join(' ').toLowerCase().includes(term),
    );
  }, [resourceData, search]);

  if (workspacesLoading || isLoading) return <PageLoader />;
  if (error) return <ErrorState message="Unable to load cloud resources." onRetry={() => void refetch()} />;

  return (
    <div>
      <PageHeader title="Cloud discovery inventory" description="Review discovered resources, investigate posture details, and inspect the latest inventory snapshots.">
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
          <CardTitle>Discovered resources</CardTitle>
          <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-slate-400">
            <Search className="h-4 w-4" />
            <Input value={search} onChange={(event) => setSearch(event.target.value)} className="h-8 w-44 border-0 bg-transparent p-0" placeholder="Search inventory" />
          </label>
        </CardHeader>
        <CardContent>
          {filteredResources.length === 0 ? (
            <EmptyState title="No resources found" description="This workspace has no discovered assets yet, or the current filters don’t match any results." />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Resource</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Identifier</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredResources.map((resource) => (
                    <TableRow key={resource.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium text-slate-100">{resource.name}</p>
                          <p className="text-xs text-slate-500">{resource.arn ?? 'No ARN attached'}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge>{resource.resource_type}</Badge>
                      </TableCell>
                      <TableCell className="text-slate-400">{resource.resource_id}</TableCell>
                      <TableCell className="text-slate-400">{formatDate(resource.created_at)}</TableCell>
                      <TableCell>
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button variant="secondary" size="sm" onClick={() => setSelectedResource(resource)}>
                              Inspect
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>{selectedResource?.name}</DialogTitle>
                              <DialogDescription>Inventory metadata and posture context captured by the discovery pipeline.</DialogDescription>
                            </DialogHeader>
                            <div className="space-y-3 text-sm text-slate-300">
                              <div className="rounded-xl border border-white/10 bg-slate-950/60 p-3">
                                <p className="text-slate-400">Resource type</p>
                                <p className="mt-1 font-medium text-slate-100">{selectedResource?.resource_type}</p>
                              </div>
                              <div className="rounded-xl border border-white/10 bg-slate-950/60 p-3">
                                <p className="text-slate-400">Identifier</p>
                                <p className="mt-1 font-medium text-slate-100">{selectedResource?.resource_id}</p>
                              </div>
                              <div className="rounded-xl border border-white/10 bg-slate-950/60 p-3">
                                <p className="text-slate-400">Details</p>
                                <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-400">{JSON.stringify(selectedResource?.details ?? {}, null, 2)}</pre>
                              </div>
                            </div>
                          </DialogContent>
                        </Dialog>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

type DiscoveredResource = {
  id: string;
  name: string;
  resource_type: string;
  resource_id: string;
  arn?: string | null;
  created_at: string;
  details: Record<string, unknown>;
};
