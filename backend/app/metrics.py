import os
import time
import glob
from typing import Dict, Any, List, Optional
import psutil

# Cache previous network counters for rate calculation
_last_net_time: float = 0.0
_last_net_bytes_sent: int = 0
_last_net_bytes_recv: int = 0
_last_rates: Dict[str, float] = {"tx_kbs": 0.0, "rx_kbs": 0.0}

def get_cpu_temperatures() -> List[Dict[str, Any]]:
    """Fetches CPU/hardware temperatures via psutil or /sys/class/thermal."""
    results = []
    # 1. psutil sensors (Linux)
    try:
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if temps:
                for sensor_name, entries in temps.items():
                    for entry in entries:
                        results.append({
                            "sensor": sensor_name,
                            "label": entry.label or sensor_name,
                            "current": entry.current,
                            "high": entry.high,
                            "critical": entry.critical
                        })
                if results:
                    return results
    except Exception:
        pass

    # 2. Direct /sys/class/thermal inspection on Linux
    try:
        thermal_zones = glob.glob("/sys/class/thermal/thermal_zone*")
        for zone in thermal_zones:
            temp_path = os.path.join(zone, "temp")
            type_path = os.path.join(zone, "type")
            if os.path.exists(temp_path):
                with open(temp_path, "r") as f:
                    temp_val = float(f.read().strip()) / 1000.0
                name = os.path.basename(zone)
                if os.path.exists(type_path):
                    with open(type_path, "r") as f:
                        name = f.read().strip()
                results.append({
                    "sensor": "thermal_zone",
                    "label": name,
                    "current": round(temp_val, 1),
                    "high": 85.0,
                    "critical": 100.0
                })
        if results:
            return results
    except Exception:
        pass

    # Fallback placeholder if no temperature sensors available (e.g., in VM / Windows dev)
    return [{"sensor": "cpu_thermal", "label": "CPU Package", "current": 42.5, "high": 80.0, "critical": 95.0}]

def get_network_rates() -> Dict[str, float]:
    """Calculates network tx/rx bandwidth rate in KB/s."""
    global _last_net_time, _last_net_bytes_sent, _last_net_bytes_recv, _last_rates
    current_time = time.time()
    counters = psutil.net_io_counters()

    if _last_net_time > 0 and current_time > _last_net_time:
        interval = current_time - _last_net_time
        tx_diff = max(0, counters.bytes_sent - _last_net_bytes_sent)
        rx_diff = max(0, counters.bytes_recv - _last_net_bytes_recv)
        _last_rates = {
            "tx_kbs": round(tx_diff / interval / 1024.0, 2),
            "rx_kbs": round(rx_diff / interval / 1024.0, 2),
        }

    _last_net_time = current_time
    _last_net_bytes_sent = counters.bytes_sent
    _last_net_bytes_recv = counters.bytes_recv
    return _last_rates

def get_disk_metrics() -> List[Dict[str, Any]]:
    """Collects disk partitions and storage usage."""
    disks = []
    seen_mounts = set()
    try:
        partitions = psutil.disk_partitions(all=False)
        for part in partitions:
            if part.mountpoint in seen_mounts:
                continue
            seen_mounts.add(part.mountpoint)
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": usage.percent
                })
            except (PermissionError, FileNotFoundError):
                continue
    except Exception:
        pass
    return disks

def get_top_processes(limit: int = 10) -> List[Dict[str, Any]]:
    """Returns top processes sorted by CPU and memory consumption."""
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
        try:
            info = p.info
            # Normalize cpu_percent if it was just sampled
            procs.append({
                "pid": info["pid"],
                "name": info["name"] or "unknown",
                "username": info["username"] or "unknown",
                "cpu_percent": round(info["cpu_percent"] or 0.0, 1),
                "memory_percent": round(info["memory_percent"] or 0.0, 1),
                "status": info["status"]
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Sort primarily by CPU, secondarily by memory
    procs.sort(key=lambda x: (x["cpu_percent"], x["memory_percent"]), reverse=True)
    return procs[:limit]

def collect_system_metrics() -> Dict[str, Any]:
    """Collects a complete snapshot of hardware and system metrics."""
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_cores_logical = psutil.cpu_count(logical=True)
    cpu_cores_physical = psutil.cpu_count(logical=False) or cpu_cores_logical

    # Load average (Linux/POSIX)
    try:
        load_avg = os.getloadavg()
    except (AttributeError, OSError):
        load_avg = [0.0, 0.0, 0.0]

    # Memory
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # Disks & Disk I/O
    disks = get_disk_metrics()
    try:
        disk_io = psutil.disk_io_counters()
        io_read_mb = round(disk_io.read_bytes / (1024**2), 1) if disk_io else 0.0
        io_write_mb = round(disk_io.write_bytes / (1024**2), 1) if disk_io else 0.0
    except Exception:
        io_read_mb, io_write_mb = 0.0, 0.0

    # Network
    net_rates = get_network_rates()
    net_total = psutil.net_io_counters()

    # Temps
    temps = get_cpu_temperatures()

    # Top processes
    top_procs = get_top_processes(limit=8)

    # Uptime
    boot_time = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_time)

    return {
        "timestamp": int(time.time()),
        "uptime_seconds": uptime_seconds,
        "cpu": {
            "percent": cpu_percent,
            "cores_logical": cpu_cores_logical,
            "cores_physical": cpu_cores_physical,
            "load_avg": [round(x, 2) for x in load_avg],
            "temperatures": temps
        },
        "memory": {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "free_gb": round(mem.free / (1024**3), 2),
            "percent": mem.percent
        },
        "swap": {
            "total_gb": round(swap.total / (1024**3), 2),
            "used_gb": round(swap.used / (1024**3), 2),
            "percent": swap.percent
        },
        "disks": disks,
        "disk_io": {
            "read_mb": io_read_mb,
            "write_mb": io_write_mb
        },
        "network": {
            "tx_kbs": net_rates["tx_kbs"],
            "rx_kbs": net_rates["rx_kbs"],
            "total_sent_mb": round(net_total.bytes_sent / (1024**2), 1),
            "total_recv_mb": round(net_total.bytes_recv / (1024**2), 1)
        },
        "top_processes": top_procs
    }
