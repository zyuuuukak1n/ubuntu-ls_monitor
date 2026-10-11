import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  api,
  SystemMetrics,
  ServiceStatus,
  DockerContainerStatus,
  EditableFileInfo,
  UserProfile,
} from './lib/api';
import { Header } from './components/Header';
import { MetricCards } from './components/MetricCards';
import { ProcessList } from './components/ProcessList';
import { SystemdControls } from './components/SystemdControls';
import { DockerControls } from './components/DockerControls';
import { ConfigEditor } from './components/ConfigEditor';
import { LogViewerModal } from './components/LogViewerModal';
import { ConfirmDialog } from './components/ConfirmDialog';
import { PasskeyManagerModal } from './components/PasskeyManagerModal';
import { AuthModal } from './components/AuthModal';
import { AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  // Auth state
  const [user, setUser] = useState<UserProfile | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  // System states
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [containers, setContainers] = useState<DockerContainerStatus[]>([]);
  const [editableFiles, setEditableFiles] = useState<EditableFileInfo[]>([]);

  // Connectivity & Tab state
  const [isLive, setIsLive] = useState(false);
  const [isBackgroundTab, setIsBackgroundTab] = useState(false);

  // Modals & Dialogs
  const [activeLog, setActiveLog] = useState<{ type: 'systemd' | 'docker'; name: string } | null>(null);
  const [showPasskeys, setShowPasskeys] = useState(false);
  const [showRebootDialog, setShowRebootDialog] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  // EventSource reference for metrics SSE
  const sseRef = useRef<EventSource | null>(null);

  // 1. Check existing session on boot
  useEffect(() => {
    api
      .checkSession()
      .then((res) => {
        if (res.authenticated && res.user) {
          setUser(res.user);
        }
      })
      .catch((err) => {
        console.error('Session check failed:', err);
      })
      .finally(() => {
        setAuthChecked(true);
      });
  }, []);

  // 2. Fetch non-streaming data (services, containers, editable files)
  const loadSystemStaticData = useCallback(async () => {
    if (!user) return;
    try {
      const [svcData, dkrData, filesData] = await Promise.allSettled([
        api.listServices(),
        api.listDockerContainers(),
        api.listEditableFiles(),
      ]);

      if (svcData.status === 'fulfilled') setServices(svcData.value);
      if (dkrData.status === 'fulfilled') setContainers(dkrData.value);
      if (filesData.status === 'fulfilled') setEditableFiles(filesData.value);
    } catch (err: any) {
      console.error('Error fetching system data:', err);
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      loadSystemStaticData();
    }
  }, [user, loadSystemStaticData]);

  // 3. Page Visibility listener to stop SSE stream in background tab
  useEffect(() => {
    const handleVisibilityChange = () => {
      const isHidden = document.hidden;
      setIsBackgroundTab(isHidden);
      if (isHidden && sseRef.current) {
        // Disconnect SSE while tab is in background to preserve server resources
        sseRef.current.close();
        sseRef.current = null;
        setIsLive(false);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  // 4. SSE Metrics stream management
  useEffect(() => {
    if (!user || isBackgroundTab) {
      if (sseRef.current) {
        sseRef.current.close();
        sseRef.current = null;
        setIsLive(false);
      }
      return;
    }

    // Connect SSE
    const es = new EventSource('/api/metrics/stream');
    sseRef.current = es;

    es.onopen = () => {
      setIsLive(true);
      setGlobalError(null);
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setMetrics(data);
      } catch (e) {
        console.error('Failed to parse SSE metric payload', e);
      }
    };

    es.onerror = () => {
      setIsLive(false);
      // Fallback: poll current metrics once
      api.getCurrentMetrics().then(setMetrics).catch(() => {});
    };

    return () => {
      es.close();
      sseRef.current = null;
      setIsLive(false);
    };
  }, [user, isBackgroundTab]);

  // Service actions
  const handleRestartService = async (name: string) => {
    try {
      await api.restartService(name);
      await loadSystemStaticData();
    } catch (err: any) {
      setGlobalError(err.message || `Failed to restart service ${name}`);
    }
  };

  const handleRestartContainer = async (name: string) => {
    try {
      await api.restartDockerContainer(name);
      await loadSystemStaticData();
    } catch (err: any) {
      setGlobalError(err.message || `Failed to restart container ${name}`);
    }
  };

  const handleRebootHost = async () => {
    try {
      await api.rebootHost('REBOOT');
      setShowRebootDialog(false);
      alert('Host reboot initiated. The server will become temporarily unreachable.');
    } catch (err: any) {
      setGlobalError(err.message || 'Host reboot failed.');
    }
  };

  const handleLogout = async () => {
    try {
      await api.logout();
      setUser(null);
      setMetrics(null);
    } catch (err) {
      console.error(err);
    }
  };

  if (!authChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0d14] text-slate-400">
        <div className="flex items-center space-x-3">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-medium">Authenticating server session...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0d14] text-slate-100 flex flex-col">
      {/* Header */}
      <Header
        user={user}
        uptimeSeconds={metrics?.uptime_seconds}
        isLive={isLive}
        isBackgroundTab={isBackgroundTab}
        onOpenPasskeys={() => setShowPasskeys(true)}
        onOpenReboot={() => setShowRebootDialog(true)}
        onLogout={handleLogout}
      />

      {/* Main Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 lg:px-8 pb-12">
        {globalError && (
          <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{globalError}</span>
            </div>
            <button onClick={() => setGlobalError(null)} className="text-rose-400 hover:text-white font-bold ml-4">
              Dismiss
            </button>
          </div>
        )}

        {/* 1. Hardware & Resource Metrics */}
        <MetricCards metrics={metrics} />

        {/* 2. Top Processes */}
        <ProcessList processes={metrics?.top_processes} />

        {/* 3. systemd Services */}
        <SystemdControls
          services={services}
          onRestart={handleRestartService}
          onViewLogs={(name) => setActiveLog({ type: 'systemd', name })}
        />

        {/* 4. Docker Containers */}
        <DockerControls
          containers={containers}
          onRestart={handleRestartContainer}
          onViewLogs={(name) => setActiveLog({ type: 'docker', name })}
        />

        {/* 5. Secure Configuration Editor */}
        <ConfigEditor files={editableFiles} onRefreshFiles={loadSystemStaticData} />
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-4 px-4 text-center text-xs text-slate-600">
        <p>Ubuntu-LS Monitor • Cloudflare Tunnel Ingress • MIT License © じゅーかきん</p>
      </footer>

      {/* Modals */}
      <AuthModal isOpen={!user} onSuccess={(loggedInUser) => setUser(loggedInUser)} />

      <LogViewerModal
        isOpen={!!activeLog}
        onClose={() => setActiveLog(null)}
        targetType={activeLog?.type || 'systemd'}
        targetName={activeLog?.name || ''}
      />

      <PasskeyManagerModal isOpen={showPasskeys} onClose={() => setShowPasskeys(false)} />

      <ConfirmDialog
        isOpen={showRebootDialog}
        title="Reboot Ubuntu Host Server"
        message="Are you certain you wish to restart the physical host? Active background processes and Cloudflare tunnels will be temporarily interrupted."
        requirePhrase="REBOOT"
        confirmButtonText="Reboot Server"
        isDangerous={true}
        onConfirm={handleRebootHost}
        onCancel={() => setShowRebootDialog(false)}
      />
    </div>
  );
};
