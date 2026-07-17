import * as React from 'react';

export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-center text-slate-200">
          <div className="max-w-md rounded-2xl border border-rose-500/30 bg-rose-500/10 p-8">
            <h1 className="mb-3 text-xl font-semibold">Something went wrong</h1>
            <p className="text-sm text-slate-400">The Sentinel UI hit an unexpected state. Please refresh and try again.</p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
