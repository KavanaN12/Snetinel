import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';
import { ArrowRight, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { getApiErrorMessage } from '../api/client';
import { authService } from '../services/sentinelApi';
import { useAuthStore } from '../store/auth';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';

const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (values: LoginFormValues) => {
    setError(null);
    try {
      const { data } = await authService.login(values.email, values.password);
      const user = { id: 'local-user', email: values.email, is_active: true, created_at: new Date().toISOString() };
      setAuth({ user, accessToken: data.access_token, refreshToken: data.refresh_token });
      navigate('/dashboard');
    } catch (err: unknown) {
      setError(getApiErrorMessage(err) || 'Unable to sign in');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.25),_transparent_30%),linear-gradient(135deg,_#020617,_#111827)] p-4">
      <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-5xl overflow-hidden rounded-[32px] border border-white/10 bg-slate-900/70 shadow-[0_0_120px_rgba(8,145,178,0.14)] backdrop-blur-xl">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr]">
          <div className="flex flex-col justify-between bg-gradient-to-br from-cyan-500/15 via-slate-950/40 to-slate-900/80 p-8 lg:p-10">
            <div>
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-sm text-cyan-300">
                <ShieldCheck className="h-4 w-4" /> Sentinel Cloud Defense OS
              </div>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-100">Operational cloud security, unified.</h1>
              <p className="mt-4 max-w-lg text-sm leading-7 text-slate-400">
                Review attack paths, prioritize critical findings, and drive compliance from a single secure control plane.
              </p>
            </div>
            <div className="mt-8 rounded-2xl border border-white/10 bg-slate-950/70 p-5 text-sm text-slate-300">
              <p className="font-medium text-slate-100">Why Sentinel</p>
              <ul className="mt-3 space-y-2 text-slate-400">
                <li>• Real-time posture monitoring</li>
                <li>• Guided attack path reasoning</li>
                <li>• Evidence-backed remediation</li>
              </ul>
            </div>
          </div>
          <div className="p-8 lg:p-10">
            <div className="mb-8">
              <p className="text-sm font-medium uppercase tracking-[0.25em] text-cyan-400">Secure access</p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-100">Sign in to Sentinel</h2>
            </div>
            <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
              <div>
                <label className="mb-2 block text-sm text-slate-400">Email</label>
                <Input {...register('email')} type="email" autoComplete="email" placeholder="ops@acme.com" />
                {errors.email ? <p className="mt-2 text-sm text-rose-300">{errors.email.message}</p> : null}
              </div>
              <div>
                <label className="mb-2 block text-sm text-slate-400">Password</label>
                <Input type="password" {...register('password')} placeholder="••••••••" />
                {errors.password ? <p className="mt-2 text-sm text-rose-300">{errors.password.message}</p> : null}
              </div>
              {error ? <p className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">{error}</p> : null}
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? 'Signing in…' : 'Continue'} <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </form>
            <div className="mt-6 text-sm text-slate-400">
              New to Sentinel? <Link className="font-medium text-cyan-300" to="/register">Create an account</Link>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
