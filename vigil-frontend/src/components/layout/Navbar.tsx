import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Shield, GitPullRequest, Layers, User, Activity } from 'lucide-react';
import { request } from '../../services/api';
import { Badge } from '../common/Badge';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      try {
        const res = await request<{ status: string; database?: string }>('/health');
        if (isMounted) {
          setBackendHealthy(res.status === 'ok');
        }
      } catch {
        if (isMounted) {
          setBackendHealthy(false);
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const navLinks = [
    { label: 'Repositories', path: '/repositories', icon: <Layers className="w-4 h-4" /> },
    { label: 'Review Queue', path: '/review-queue', icon: <GitPullRequest className="w-4 h-4" /> },
  ];

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-8">
          <Link to="/repositories" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-lg bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 group-hover:bg-indigo-600/30 group-hover:border-indigo-400 transition-all">
              <Shield className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-slate-100 text-sm tracking-tight">SecurePR</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  AI
                </span>
              </div>
              <span className="text-[11px] text-slate-400 font-medium block">VIGIL Engine</span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive =
                location.pathname === link.path ||
                (link.path === '/repositories' && location.pathname.startsWith('/repositories'));
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-slate-800/80 text-white border border-slate-700'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                  }`}
                >
                  {link.icon}
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right side controls */}
        <div className="flex items-center gap-3">
          {/* Health indicator */}
          <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-xs">
            <Activity className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">API:</span>
            {backendHealthy === null ? (
              <span className="text-slate-500 text-[11px]">Connecting...</span>
            ) : backendHealthy ? (
              <span className="flex items-center gap-1 text-emerald-400 text-[11px]">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Online
              </span>
            ) : (
              <span className="flex items-center gap-1 text-amber-400 text-[11px]">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                Dev Mode
              </span>
            )}
          </div>

          {/* User / Session */}
          <Link
            to="/login"
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-slate-900 text-slate-300 transition-colors border border-transparent hover:border-slate-800"
          >
            <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
              <User className="w-3.5 h-3.5" />
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-xs font-medium text-slate-200 leading-none">Member 6</p>
              <p className="text-[10px] text-slate-400 mt-0.5 leading-none">Security Reviewer</p>
            </div>
            <Badge variant="outline" className="hidden lg:inline-flex text-[10px] py-0">
              Entra ID
            </Badge>
          </Link>
        </div>
      </div>
    </header>
  );
};
