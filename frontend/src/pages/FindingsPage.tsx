import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { PageHeader } from '../components/common/PageHeader';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { PageLoader } from '../components/common/PageLoader';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { findingService, workspaceService } from '../services/sentinelApi';
import { useWorkspaceStore } from '../store/workspace';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Button } from '../components/ui/button';

export function FindingsPage() {
  const selectedWorkspaceId = useWorkspaceStore((state) => state.selectedWorkspaceId);
  const setSelectedWorkspaceId = useWorkspaceStore((state) => state.setSelectedWorkspaceId);
  const [search, setSearch] = useState('');
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);

  const { data: workspaceData, isLoading: workspacesLoading } = useQuery({ queryKey: ['workspaces'], queryFn: async () => (await workspaceService.list()).data });
  const workspace = workspaceData?.find((item) => item.id === selectedWorkspaceId) ?? workspaceData?.[0];

  const { data: findingsData, isLoading, error, refetch } = useQuery({
    queryKey: ['findings', workspace?.id],
    queryFn: async () => (await findingService.getFindings(workspace!.id)).data,
    enabled: Boolean(workspace?.id),
  });

  const filteredFindings = useMemo(() => {
    const term = search.toLowerCase();
    return (findingsData?.findings ?? []).filter((finding) => [finding.title, finding.description, finding.severity, finding.status].join(' ').toLowerCase().includes(term));
  }, [findingsData, search]);

  if (workspacesLoading || isLoading) return <PageLoader />;
  if (error) return <ErrorState message="Unable to load findings." onRetry={() => void refetch()} />;

  return (
    <div>
      <PageHeader title="Security findings" description="Prioritize remediation work and track the health of each finding from the backend’s risk engine.">
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
          <CardTitle>Findings queue</CardTitle>
          <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-slate-400">
            <Search className="h-4 w-4" />
            <Input value={search} onChange={(event) => setSearch(event.target.value)} className="h-8 w-44 border-0 bg-transparent p-0" placeholder="Search findings" />
          </label>
        </CardHeader>
        <CardContent>
          {filteredFindings.length === 0 ? (
            <EmptyState title="No findings available" description="This workspace has no findings yet. The risk scoring service will populate this page once new results are available." />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Finding</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Impact</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredFindings.map((finding) => (
                    <TableRow key={finding.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium text-slate-100">{finding.title}</p>
                          <p className="mt-1 text-xs text-slate-500">{finding.description}</p>
                        </div>
                      </TableCell>
                      <TableCell><Badge tone={finding.severity === 'critical' ? 'danger' : finding.severity === 'high' ? 'warning' : 'default'}>{finding.severity}</Badge></TableCell>
                      <TableCell><Badge>{finding.status}</Badge></TableCell>
                      <TableCell className="text-slate-400">{finding.affected_resource_ids.length} resources</TableCell>
                      <TableCell>
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button variant="secondary" size="sm" onClick={() => setSelectedFinding(finding)}>Open</Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>{selectedFinding?.title}</DialogTitle>
                              <DialogDescription>Evidence and resource context from the backend risk evaluation.</DialogDescription>
                            </DialogHeader>
                            <div className="space-y-3 text-sm text-slate-300">
                              <div className="rounded-xl border border-white/10 bg-slate-950/60 p-3">
                                <p className="text-slate-400">Description</p>
                                <p className="mt-1 text-slate-100">{selectedFinding?.description}</p>
                              </div>
                              <div className="rounded-xl border border-white/10 bg-slate-950/60 p-3">
                                <p className="text-slate-400">Affected resources</p>
                                <p className="mt-1 text-slate-100">{selectedFinding?.affected_resource_ids.join(', ')}</p>
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

type Finding = {
  id: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  affected_resource_ids: string[];
};
