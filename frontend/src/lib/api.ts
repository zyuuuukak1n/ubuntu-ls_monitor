/**
 * Unified API Client for Ubuntu-LS Monitor
 */

export interface SystemMetrics {
  timestamp: number;
  uptime_seconds: number;
  cpu: {
    percent: number;
    cores_logical: number;
    cores_physical: number;
    load_avg: [number, number, number];
    temperatures: Array<{
      sensor: string;
      label: string;
      current: number;
      high?: number;
      critical?: number;
    }>;
  };
  memory: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
  };
  swap: {
    total_gb: number;
    used_gb: number;
    percent: number;
  };
  disks: Array<{
    device: string;
    mountpoint: string;
    fstype: string;
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
  }>;
  disk_io: {
    read_mb: number;
    write_mb: number;
  };
  network: {
    tx_kbs: number;
    rx_kbs: number;
    total_sent_mb: number;
    total_recv_mb: number;
  };
  top_processes: Array<{
    pid: number;
    name: string;
    username: string;
    cpu_percent: number;
    memory_percent: number;
    status: string;
  }>;
}

export interface ServiceStatus {
  name: string;
  description: string;
  active_state: string;
  sub_state: string;
  load_state: string;
  main_pid?: number | null;
  uptime?: string | null;
}

export interface DockerContainerStatus {
  id: string;
  name: string;
  image: string;
  status: string;
  state: string;
  created: string;
  ports?: string | null;
  cpu_percent?: number | null;
  memory_usage?: string | null;
}

export interface EditableFileInfo {
  path: string;
  label: string;
  description?: string | null;
  syntax: string;
  exists: boolean;
  size?: number | null;
  last_modified?: string | null;
}

export interface CredentialInfo {
  id: string;
  name: string;
  sign_count: number;
  transports?: string[] | null;
  created_at: string;
  last_used_at?: string | null;
}

export interface UserProfile {
  id: string;
  username: string;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(endpoint, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    credentials: 'include', // Ensure cookies are attached
  });

  if (!res.ok) {
    let errMessage = `HTTP Error ${res.status}`;
    try {
      const errData = await res.json();
      if (errData && errData.detail) {
        errMessage = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // ignore
    }
    const error = new Error(errMessage) as Error & { status: number };
    error.status = res.status;
    throw error;
  }

  return res.json() as Promise<T>;
}

export const api = {
  // Auth
  async checkSession(): Promise<{ authenticated: boolean; user?: UserProfile }> {
    try {
      return await request<{ authenticated: boolean; user: UserProfile }>('/api/auth/me');
    } catch (err: any) {
      if (err.status === 401) {
        return { authenticated: false };
      }
      throw err;
    }
  },

  async logout(): Promise<void> {
    await request('/api/auth/logout', { method: 'POST' });
  },

  async listCredentials(): Promise<CredentialInfo[]> {
    return request<CredentialInfo[]>('/api/auth/credentials');
  },

  async deleteCredential(credId: string): Promise<void> {
    await request(`/api/auth/credentials/${encodeURIComponent(credId)}`, { method: 'DELETE' });
  },

  async renameCredential(credId: string, name: string): Promise<void> {
    await request(`/api/auth/credentials/${encodeURIComponent(credId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    });
  },

  // Metrics
  async getCurrentMetrics(): Promise<SystemMetrics> {
    return request<SystemMetrics>('/api/metrics/current');
  },

  // Services & Docker
  async listServices(): Promise<ServiceStatus[]> {
    return request<ServiceStatus[]>('/api/system/services');
  },

  async restartService(name: string): Promise<{ success: boolean; message: string }> {
    return request<{ success: boolean; message: string }>(`/api/system/services/${encodeURIComponent(name)}/restart`, {
      method: 'POST',
    });
  },

  async listDockerContainers(): Promise<DockerContainerStatus[]> {
    return request<DockerContainerStatus[]>('/api/system/docker');
  },

  async restartDockerContainer(name: string): Promise<{ success: boolean; message: string }> {
    return request<{ success: boolean; message: string }>(`/api/system/docker/${encodeURIComponent(name)}/restart`, {
      method: 'POST',
    });
  },

  async rebootHost(confirmText: string): Promise<{ success: boolean; message: string }> {
    return request<{ success: boolean; message: string }>('/api/system/reboot', {
      method: 'POST',
      body: JSON.stringify({ confirm_text: confirmText }),
    });
  },

  // Editor
  async listEditableFiles(): Promise<EditableFileInfo[]> {
    return request<EditableFileInfo[]>('/api/editor/files');
  },

  async getFileContent(path: string): Promise<{ path: string; content: string; syntax: string }> {
    return request<{ path: string; content: string; syntax: string }>('/api/editor/file', {
      method: 'POST',
      body: JSON.stringify({ path }),
    });
  },

  async saveFile(path: string, content: string, backup: boolean = true): Promise<{
    success: boolean;
    message: string;
    backup_path?: string;
    validation_output?: string;
  }> {
    return request('/api/editor/save', {
      method: 'POST',
      body: JSON.stringify({ path, content, backup }),
    });
  },
};
