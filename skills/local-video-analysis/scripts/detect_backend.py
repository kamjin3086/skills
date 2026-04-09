#!/usr/bin/env python3
"""
Detect local inference backends and list available models.

This script ONLY collects data. Model selection is done by the LLM.

Supports:
- Gateway processes (llama-swap, etc.) - detected first as they proxy other backends
- Process-based port discovery via --ports
- Fallback scan of common ports when --ports is omitted
"""

import argparse
import json
import platform
import socket
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


# Gateway processes that proxy other backends - should be used preferentially
GATEWAY_HINTS = ("llama-swap", "llamaswap", "llama_swap")

# Keywords indicating vision-capable models
VISION_HINTS = ("smolvlm", "llava", "vision", "vlm", "minicpm-v", "qwen-vl", "cogvlm", "moondream")


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
        return BackendInfo("ollama", "ollama", port, url, "running", False, models, vision)
    except Exception:
        return None


def detect_openai_endpoint(host: str, port: int) -> BackendInfo | None:
    url = f"http://{host}:{port}"
    if not is_port_open(host, port):
        return None
    try:
        resp = httpx.get(f"{url}/v1/models", timeout=5.0)
        resp.raise_for_status()
        server_header = resp.headers.get("server", "")
        name, family = classify_backend(server_header, port)
        models = []
        vision = []
        for m in resp.json().get("data", []):
            mid = m.get("id", "")
            if mid:
                models.append(mid)
                if any(k in mid.lower() for k in VISION_HINTS):
                    vision.append(mid)
        gateway = is_gateway(server_header, models)
        if gateway:
            family = "gateway"
        return BackendInfo(name, family, port, url, "running", gateway, models, vision)
    except Exception:
        return None


def detect_llamacpp_health(host: str, port: int) -> BackendInfo | None:
    url = f"http://{host}:{port}"
    if not is_port_open(host, port):
        return None
    try:
        resp = httpx.get(f"{url}/health", timeout=4.0)
        if resp.status_code == 200:
            return BackendInfo("llama.cpp", "llama.cpp-family", port, url, "running", False, [], [])
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


def detect_all(ports: list[int], host: str = "127.0.0.1") -> list[BackendInfo]:
    """Detect backends on given ports. Returns list sorted by priority (gateways first)."""
    if httpx is None:
        raise RuntimeError("httpx not installed. Run: pip install httpx")
    
    backends = []
    for port in ports:
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
            "SmolVLM2-500M-Video-Instruct",
            "SmolVLM2-2.2B-Video-Instruct",
        ],
        "preferred_format": "mlx" if os_name == "darwin" else "GGUF",
        "download_guidance": {
            "darwin": "For macOS: pip install -U mlx-vlm; then use mlx-community/SmolVLM2-500M-Video-Instruct-mlx",
            "other": "Download SmolVLM2-500M-Video-Instruct-GGUF and load in your backend",
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Detect local inference backends and list models.")
    parser.add_argument("--ports", type=str, default="", help="Comma-separated ports (from process detection)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--json", action="store_true", help="Output JSON for LLM processing")
    args = parser.parse_args()
    
    if args.ports:
        ports = [int(p.strip()) for p in args.ports.split(",") if p.strip().isdigit()]
    else:
        ports = [8080, 11434, 1234, 8000]  # common defaults
    
    backends = detect_all(ports, args.host)
    recs = recommended_models()
    
    result = {
        "os": recs["os"],
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
        print(f"\nTarget models: {recs['target_models']}")
        print(f"Preferred format: {recs['preferred_format']}")
    
    sys.exit(0 if backends else 1)


if __name__ == "__main__":
    main()
