import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Search, UploadCloud } from 'lucide-react';
import { PageHeader } from '../components/common/PageHeader';
import { EmptyState } from '../components/common/EmptyState';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { ragService } from '../services/sentinelApi';

export function RagPage() {
  const [query, setQuery] = useState('');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [source, setSource] = useState('');
  const [results, setResults] = useState<Array<{ id: string; title: string; source: string }>>([]);

  const searchMutation = useMutation({
    mutationFn: async (searchValue: string) => (await ragService.search(searchValue)).data,
    onSuccess: (data) => setResults(data),
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      const response = await ragService.upload(title, content, source);
      return response.data;
    },
    onSuccess: () => {
      setTitle('');
      setContent('');
      setSource('');
      searchMutation.mutate('');
    },
  });

  return (
    <div>
      <PageHeader title="RAG knowledge base" description="Store and query policy, runbook, and security context directly from the backend document index." />
      <div className="grid gap-4 xl:grid-cols-[1fr_0.95fr]">
        <Card>
          <CardHeader>
            <CardTitle>Upload knowledge</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input placeholder="Document title" value={title} onChange={(event) => setTitle(event.target.value)} />
            <Input placeholder="Source" value={source} onChange={(event) => setSource(event.target.value)} />
            <textarea className="min-h-40 w-full rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-slate-200" placeholder="Document content" value={content} onChange={(event) => setContent(event.target.value)} />
            <Button onClick={() => void uploadMutation.mutateAsync()} className="w-full">
              <UploadCloud className="mr-2 h-4 w-4" /> Upload document
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Search knowledge base</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-slate-400">
              <Search className="h-4 w-4" />
              <Input value={query} onChange={(event) => setQuery(event.target.value)} className="h-8 border-0 bg-transparent p-0" placeholder="Search documents" />
            </label>
            <Button variant="secondary" onClick={() => void searchMutation.mutateAsync(query)} className="w-full">
              Search
            </Button>
            {results.length === 0 ? (
              <EmptyState title="No documents returned" description="Search the knowledge base to surface matched policy or incident context." />
            ) : (
              <div className="space-y-2">
                {results.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium text-slate-100">{item.title}</p>
                      <Badge>{item.source}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
