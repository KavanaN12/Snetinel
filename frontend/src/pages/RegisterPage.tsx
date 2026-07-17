import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';
import { ArrowRight, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { getApiErrorMessage } from '../api/client';
import { authService } from '../services/sentinelApi';

const registerSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

type RegisterFormValues = z.infer<typeof registerSchema>;

export function RegisterPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) });

  const onSubmit = async (values: RegisterFormValues) => {
    setError(null);
    try {
      await authService.register(values.email, values.password);
      setError(null);
      navigate('/login');
    } catch (err: unknown) {
      setError(getApiErrorMessage(err) || 'Unable to create an account');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.25),_transparent_30%),linear-gradient(135deg,_#020617,_#111827)] p-4">
      <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-4xl overflow-hidden rounded-[32px] border border-white/10 bg-slate-900/70 shadow-[0_0_120px_rgba(8,145,178,0.14)] backdrop-blur-xl">
        <div className="grid lg:grid-cols-[0.95fr_1.05fr]">
          <div className="bg-gradient-to-br from-cyan-500/15 via-slate-950/40 to-slate-900/80 p-8 lg:p-10">
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-sm text-cyan-300">
              <ShieldCheck className="h-4 w-4" /> Sentinel Cloud Defense OS
            </div>
            <h1 className="mt-6 text-3xl font-semibold text-slate-100">Build your secure operating posture.</h1>
            <p className="mt-4 text-sm leading-7 text-slate-400">Register to connect your workspace and start reviewing cloud exposure with enterprise-grade controls.</p>
          </div>
          <div className="p-8 lg:p-10">
            <h2 className="text-2xl font-semibold text-slate-100">Create your workspace</h2>
            <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)}>
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
                {isSubmitting ? 'Creating account…' : 'Register'} <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </form>
            <div className="mt-6 text-sm text-slate-400">
              Already have access? <Link className="font-medium text-cyan-300" to="/login">Sign in</Link>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
