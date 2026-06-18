#!/usr/bin/env python3
"""
Detect local inference backends and list available models.

This script ONLY collects data. Model selection is done by the LLM.

Supports:
- Process scanning (ps/tasklist) to find actively running backend processes
- Port probing via OpenAI-compatible /v1/models, Ollama /api/tags, llama.cpp /health
- Gateway detection (llama-swap etc.) — promoted to highest priority
- Fallback to common default ports when nothing is found via processes

Usage:
  python detect_backend.py --json           # auto-scan then probe
  python detect_backend.py --ports 8080,11434 --json  # probe specific ports only
"""

import argparse
import json
import platform
import re
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass

try:
    import httpx
except ImportError:
    httpx = None


@dataclass
class BackendInfo:
    name: str
    family: str
    port: int
    url: str
    status: str
    is_gateway: bool
    models: list[str]
    vision_models: list[str]
    loaded_models: list[str]
    recommended_model: str | None
    recommendation_reason: str | None


# Gateway processes that proxy other backends - should be used preferentially
GATEWAY_HINTS = ("llama-swap", "llamaswap", "llama_swap")

# Keywords indicating vision-capable models
VISION_HINTS = (
    "smolvlm", "llava", "vision", "vlm", "minicpm-v", "qwen-vl", "qwen2-vl", "qwen2.5-vl",
    "qwen3vl", "qwen3.5", "qwen3.6", "gemma", "cogvlm", "moondream", "internvl",
    "phi-3.5-vision", "video",
)

HIGH_QUALITY_VISION_HINTS = (
    "qwen3.6-35b", "qwen3.6-27b", "qwen3.5-35b", "gemma-4-e4b",
    "gemma-4-26b", "gemma-4-31b", "minicpm-v-4.6", "qwen2.5-vl-7b",
)

# Known backend executables → (family, [default_ports])
BACKEND_PROCESS_HINTS: dict[str, tuple[str, list[int]]] = {
    "llama-swap":   ("gateway",          [8080, 8000]),
    "llamaswap":    ("gateway",          [8080, 8000]),
    "llama_swap":   ("gateway",          [8080, 8000]),
    "llama-server": ("llama.cpp-family", [8000, 8080]),
    "llama.cpp":    ("llama.cpp-family", [8000, 8080]),
    "lmstudio":     ("llama.cpp-family", [1234]),
    "lm-studio":    ("llama.cpp-family", [1234]),
    "ollama":       ("ollama",           [11434]),
    "vllm":         ("vllm",             [8000]),
    "lemonade":     ("llama.cpp-family", [13305]),
    "jan":          ("llama.cpp-family", [1337]),
}


def is_port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def is_gateway(server_header: str, models: list[str]) -> bool:
    """Check if this backend is a gateway/proxy like llama-swap."""
    h = (server_header or "").lower()
    if any(g in h for g in GATEWAY_HINTS):
        return True
    # llama-swap often exposes multiple diverse models
    if len(models) > 3:
        return True
    return False


def model_quality_score(model_name: str, loaded: bool = False) -> tuple[int, str]:
    """Score local models for video frame understanding.

    Running/loaded models are preferred because the user is likely already paying
    their memory/startup cost. Quality hints then break ties.
    """
    name = model_name.lower()
    score = 0
    if loaded:
        score += 1000
    for idx, hint in enumerate(HIGH_QUALITY_VISION_HINTS):
        if hint in name:
            score += 500 - idx * 10
            break
    if "35b" in name:
        score += 90
    elif "27b" in name or "26b" in name or "31b" in name:
        score += 70
    elif "9b" in name or "7b" in name or "8b" in name:
        score += 40
    elif "4b" in name:
        score += 25
    if "a3b" in name or "moe" in name:
        score += 30
    if "vision" in name or "vl" in name or "video" in name:
        score += 40
    if "qwen3.6" in name:
        score += 80
    elif "qwen3.5" in name:
        score += 60
    if "smol" in name or "tiny" in name or "500m" in name:
        score -= 30
    return score, model_name


def pick_recommended_model(models: list[str], vision_models: list[str], loaded_models: list[str]) -> tuple[str | None, str | None]:
    pool = list(dict.fromkeys(loaded_models + vision_models + models))
    if not pool:
        return None, None
    loaded_set = set(loaded_models)
    ranked = sorted(
        ((model_quality_score(m, m in loaded_set), m) for m in pool),
        key=lambda item: (-item[0][0], item[1].lower()),
    )
    best = ranked[0][1]
    if best in loaded_set:
        return best, "preferred because it is already loaded/running and has the highest local video-vision score"
    if best in vision_models:
        return best, "preferred because it is detected as vision-capable and has the highest local quality score"
    return best, "fallback recommendation from available models; verify it can accept image frames"


def classify_backend(server_header: str, port: int) -> tuple[str, str]:
    """Classify backend by server header."""
    h = (server_header or "").lower()
    if any(g in h for g in GATEWAY_HINTS):
        return "llama-swap", "gateway"
    if "lemonade" in h:
        return "lemonade", "llama.cpp-family"
    if "lm studio" in h or "lm-studio" in h or "lmstudio" in h:
        return "lmstudio", "llama.cpp-family"
    if "llama.cpp" in h or "llamacpp" in h:
        return "llama.cpp", "llama.cpp-family"
    if "vllm" in h:
        return "vllm", "vllm"
    if port == 1234:
        return "lmstudio", "llama.cpp-family"
    if port == 11434:
        return "ollama", "ollama"
    return "openai-compatible", "unknown"


def detect_ollama(host: str, port: int) -> BackendInfo | None:
    url = f"http://{host}:{port}"
    if not is_port_open(host, port):
        return None
    try:
        resp = httpx.get(f"{url}/api/tags", timeout=5.0)
        resp.raise_for_status()
        models = []
        vision = []
        for m in resp.json().get("models", []):
            name = m.get("name", "")
            if name:
                models.append(name)
                if any(k in name.lower() for k in VISION_HINTS):
                    vision.append(name)
        rec, reason = pick_recommended_model(models, vision, [])
        return BackendInfo("ollama", "ollama", port, url, "running", False, models, vision, [], rec, reason)
    except Exception:
        return None


def detect_openai_endpoint(host: str, port: int) -> BackendInfo | None:
    url = f"http://{host}:{port}"
    if not is_port_open(host, port):
        return None
    try:
        models_path = "/v1/models?show_all=true" if port == 13305 else "/v1/models"
        resp = httpx.get(f"{url}{models_path}", timeout=5.0)
        resp.raise_for_status()
        server_header = resp.headers.get("server", "")
        name, family = classify_backend(server_header, port)
        if port == 13305:
            name, family = "lemonade", "llama.cpp-family"
        models = []
        vision = []
        for m in resp.json().get("data", []):
            mid = m.get("id", "")
            if mid:
                models.append(mid)
                labels = m.get("labels") or []
                labels_text = " ".join(str(v).lower() for v in labels)
                combined = f"{mid.lower()} {labels_text}"
                if any(k in combined for k in VISION_HINTS):
                    vision.append(mid)
        loaded_models: list[str] = []
        try:
            health = httpx.get(f"{url}/v1/health", timeout=5.0)
            if health.status_code == 200:
                for item in health.json().get("all_models_loaded", []):
                    model_name = item.get("model_name", "")
                    if model_name:
                        loaded_models.append(model_name)
                        if model_name not in models:
                            models.append(model_name)
                        if any(k in model_name.lower() for k in VISION_HINTS) and model_name not in vision:
                            vision.append(model_name)
        except Exception:
            pass
        gateway = False if name == "lemonade" else is_gateway(server_header, models)
        if gateway:
            family = "gateway"
        rec, reason = pick_recommended_model(models, vision, loaded_models)
        return BackendInfo(name, family, port, url, "running", gateway, models, vision, loaded_models, rec, reason)
    except Exception:
        return None


def detect_llamacpp_health(host: str, port: int) -> BackendInfo | None:
    url = f"http://{host}:{port}"
    if not is_port_open(host, port):
        return None
    try:
        resp = httpx.get(f"{url}/health", timeout=4.0)
        if resp.status_code == 200:
            return BackendInfo("llama.cpp", "llama.cpp-family", port, url, "running", False, [], [], [], None, None)
    except Exception:
        pass
    return None


def detect_port(host: str, port: int) -> BackendInfo | None:
    """Try to identify what's running on a port."""
    if not is_port_open(host, port):
        return None
    
    # Try Ollama API first (port 11434 typical)
    if port == 11434:
        info = detect_ollama(host, port)
        if info:
            return info
    
    # Try OpenAI-compatible /v1/models
    info = detect_openai_endpoint(host, port)
    if info:
        return info
    
    # Try llama.cpp /health
    info = detect_llamacpp_health(host, port)
    if info:
        return info
    
    # Try Ollama on non-standard port
    info = detect_ollama(host, port)
    if info:
        return info
    
    return None


def scan_processes() -> list[int]:
    """Scan running processes for known backend executables.
    
    Returns a list of likely ports derived from process command lines.
    Uses ps on Unix/macOS, tasklist + wmic on Windows.
    """
    found_ports: set[int] = set()
    try:
        if platform.system() == "Windows":
            # wmic gives us the full command line on Windows
            result = subprocess.run(
                ["wmic", "process", "get", "Name,CommandLine"],
                capture_output=True, text=True, timeout=8
            )
            lines = result.stdout.splitlines()
        else:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True, text=True, timeout=8
            )
            lines = result.stdout.splitlines()

        for line in lines:
            line_lower = line.lower()
            for hint, (family, default_ports) in BACKEND_PROCESS_HINTS.items():
                if hint in line_lower:
                    # Try to extract explicit --port / -p from the command line
                    port_match = re.search(r'(?:--port|-p)\s+(\d{4,5})', line)
                    if port_match:
                        found_ports.add(int(port_match.group(1)))
                    else:
                        found_ports.update(default_ports)
                    break  # one match per line is enough
    except Exception:
        pass
    return sorted(found_ports)


def detect_all(ports: list[int], host: str = "127.0.0.1") -> list[BackendInfo]:
    """Detect backends on given ports. Returns list sorted by priority (gateways first)."""
    if httpx is None:
        raise RuntimeError("httpx not installed. Run: pip install httpx")
    
    backends = []
    seen_ports: set[int] = set()
    for port in ports:
        if port in seen_ports:
            continue
        seen_ports.add(port)
        info = detect_port(host, port)
        if info:
            backends.append(info)
    
    # Sort: gateways first, then by family priority
    family_order = {"gateway": 0, "llama.cpp-family": 1, "vllm": 2, "ollama": 3, "unknown": 4}
    backends.sort(key=lambda b: (0 if b.is_gateway else 1, family_order.get(b.family, 99)))
    
    return backends


def recommended_models() -> dict:
    """Return recommended model names for the LLM to look for."""
    os_name = platform.system().lower()
    return {
        "os": os_name,
        "target_models": [
            "Qwen3.6-35B-A3B",        # highest quality when already running
            "Qwen3.6-27B-MTP",
            "Gemma-4-E4B-instruct",   # strong local trade-off
            "Qwen2.5-VL-7B-Instruct",
            "MiniCPM-V-4.6",
            "SmolVLM2-500M-Video-Instruct",
        ],
        "preferred_format": "mlx" if os_name == "darwin" else "GGUF",
        "download_guidance": {
            "darwin": "macOS: load via LM Studio → GGUF, or mlx-community GGUF models",
            "linux": "Linux: load GGUF in llama-server or llama-swap; or use Ollama pull",
            "windows": "Windows: LM Studio (GGUF) or llama-swap; any vision model from Hugging Face",
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Detect local inference backends and list models.")
    parser.add_argument("--ports", type=str, default="", help="Comma-separated ports (from process detection)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--json", action="store_true", help="Output JSON for LLM processing")
    args = parser.parse_args()
    
    # Discover ports: explicit args > process scan > common defaults
    process_ports: list[int] = []
    if args.ports:
        ports = [int(p.strip()) for p in args.ports.split(",") if p.strip().isdigit()]
    else:
        process_ports = scan_processes()
        fallback = [8080, 13305, 11434, 1234, 8101, 1337]
        # merge: process-discovered first, then fallback (deduped)
        ports = process_ports + [p for p in fallback if p not in process_ports]
    
    backends = detect_all(ports, args.host)
    recs = recommended_models()
    
    result = {
        "os": recs["os"],
        "process_discovered_ports": process_ports if not args.ports else [],
        "scanned_ports": ports,
        "backends": [asdict(b) for b in backends],
        "target_models": recs["target_models"],
        "preferred_format": recs["preferred_format"],
        "download_guidance": recs["download_guidance"],
    }
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"OS: {recs['os']}, scanned: {ports}")
        if not backends:
            print("No backends detected.")
        for b in backends:
            gw = " [GATEWAY]" if b.is_gateway else ""
            print(f"  {b.name} [{b.family}]{gw} {b.url}")
            print(f"    models: {b.models[:5]}{'...' if len(b.models) > 5 else ''}")
        if b.vision_models:
            print(f"    vision: {b.vision_models}")
        if b.loaded_models:
            print(f"    loaded: {b.loaded_models}")
        if b.recommended_model:
            print(f"    recommended: {b.recommended_model} ({b.recommendation_reason})")
        print(f"\nTarget models: {recs['target_models']}")
        print(f"Preferred format: {recs['preferred_format']}")
    
    sys.exit(0 if backends else 1)


if __name__ == "__main__":
    main()
