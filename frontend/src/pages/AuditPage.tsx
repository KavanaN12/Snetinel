import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { useState } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { PageLoader } from '../components/common/PageLoader';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { auditService } from '../services/sentinelApi';

export function AuditPage() {
  const [search, setSearch] = useState('');
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['audit-logs'], queryFn: async () => (await auditService.listLogs()).data });

  const filteredLogs = (data ?? []).filter((log) => [log.action, log.resource, log.method, log.path].join(' ').toLowerCase().includes(search.toLowerCase()));

  if (isLoading) return <PageLoader />;
  if (error) return <ErrorState message="Unable to load audit logs." onRetry={() => void refetch()} />;

  return (
    <div>
      <PageHeader title="Audit trail" description="Review authenticated actions, access patterns, and operational events captured by the backend middleware." />
      <Card>
        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <CardTitle>System activity</CardTitle>
          <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-slate-400">
            <Search className="h-4 w-4" />
            <Input value={search} onChange={(event) => setSearch(event.target.value)} className="h-8 w-44 border-0 bg-transparent p-0" placeholder="Filter audit logs" />
          </label>
        </CardHeader>
        <CardContent>
          {filteredLogs.length === 0 ? (
            <EmptyState title="No audit activity" description="No events matched your search term yet." />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Action</TableHead>
                    <TableHead>Resource</TableHead>
                    <TableHead>Method</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredLogs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell>{log.action}</TableCell>
                      <TableCell>{log.resource}</TableCell>
                      <TableCell><Badge>{log.method}</Badge></TableCell>
                      <TableCell>{log.status_code}</TableCell>
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
