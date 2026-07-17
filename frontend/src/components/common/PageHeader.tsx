import { motion } from 'framer-motion';

interface PageHeaderProps {
  title: string;
  description: string;
  children?: React.ReactNode;
}

export function PageHeader({ title, description, children }: PageHeaderProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-6 flex flex-col gap-4 rounded-2xl border border-white/10 bg-slate-900/60 p-6 shadow-[0_0_60px_rgba(14,165,233,0.1)] backdrop-blur xl:flex-row xl:items-end xl:justify-between"
    >
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-100">{title}</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">{description}</p>
      </div>
      {children ? <div className="flex flex-wrap gap-2">{children}</div> : null}
    </motion.div>
  );
}
