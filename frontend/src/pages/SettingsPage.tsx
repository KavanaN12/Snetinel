import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PlusCircle, ShieldCheck } from 'lucide-react';
import { PageHeader } from '../components/common/PageHeader';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { workspaceService } from '../services/sentinelApi';
import { useAuthStore } from '../store/auth';

export function SettingsPage() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const queryClient = useQueryClient();

  const { data: workspaces = [] } = useQuery({
    queryKey: ['workspaces'],
    queryFn: async () => (await workspaceService.list()).data,
  });

  const createWorkspace = useMutation({
    mutationFn: async () => (await workspaceService.create(name, description)).data,
    onSuccess: () => {
      setName('');
      setDescription('');
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    },
  });

  const handleLogout = () => {
    logout();
    window.location.assign('/login');
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Workspace settings" description="Manage workspaces, review access status, and keep your Sentinel environment aligned to your operating model." />

      <div className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Create workspace</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input placeholder="Workspace name" value={name} onChange={(event) => setName(event.target.value)} />
            <Input placeholder="Optional description" value={description} onChange={(event) => setDescription(event.target.value)} />
            <Button className="w-full" onClick={() => void createWorkspace.mutateAsync()}>
              <PlusCircle className="mr-2 h-4 w-4" /> Create workspace
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Account access</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
              <div className="flex items-center gap-2 text-cyan-300">
                <ShieldCheck className="h-4 w-4" />
                <p className="font-medium text-slate-100">Signed in as</p>
              </div>
              <p className="mt-3 text-sm text-slate-400">{user?.email ?? 'Operator'}</p>
            </div>
            <Button variant="secondary" className="w-full" onClick={handleLogout}>
              Sign out
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Available workspaces</CardTitle>
        </CardHeader>
        <CardContent>
          {workspaces.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 p-8 text-center text-sm text-slate-400">
              No workspaces are available yet.
            </div>
          ) : (
            <div className="flex flex-wrap gap-3">
              {workspaces.map((workspace) => (
                <div key={workspace.id} className="rounded-2xl border border-white/10 bg-slate-950/60 px-4 py-3">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-slate-100">{workspace.name}</p>
                    <Badge>{workspace.description ? 'Configured' : 'Ready'}</Badge>
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
