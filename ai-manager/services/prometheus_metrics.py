from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

inference_counter = Counter("ai_manager_inference_total", "Total inference events")
inference_duration = Histogram("ai_manager_inference_duration_seconds", "Inference duration in seconds")
server_state_gauge = Gauge("ai_manager_server_state", "Server state code")
ping_gauge = Gauge("ai_manager_ping_latency_ms", "Ping latency in milliseconds")
cpu_gauge = Gauge("ai_manager_cpu_percent", "CPU utilization percentage")
ram_gauge = Gauge("ai_manager_ram_percent", "RAM utilization percentage")
gpu_gauge = Gauge("ai_manager_gpu_percent", "GPU utilization percentage")
vram_gauge = Gauge("ai_manager_vram_percent", "VRAM utilization percentage")
energy_gauge = Gauge("ai_manager_energy_kwh", "Estimated energy consumed in kWh")


def render_prometheus() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST

