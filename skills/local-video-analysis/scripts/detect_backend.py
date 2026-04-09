#!/usr/bin/env python3
"""
Detect local inference backends.

Supports:
- Process-based port discovery via --ports
- Fallback scan of common ports when --ports is omitted
- Auto-scan common ports as fallback
"""

import argparse
import difflib
import json
import platform
import socket
import sys
from dataclasses import asdict, dataclass
from typing import Optional

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
    models: list[str]
    vision_models: list[str]


@dataclass
class Recommendation:
    backend_name: Optional[str]
    backend_family: Optional[str]
    model: Optional[str]
    base_url: Optional[str]
    score: float
    reason: str


FAMILY_PRIORITY = {
    "llama.cpp-family": 0,
    "vllm": 1,
    "ollama": 2,
    "transformers": 3,
    "unknown-openai": 4,
}

VISION_HINTS = ("smolvlm", "llava", "vision", "vlm", "minicpm-v", "qwen-vl", "cogvlm")
BASE_MODEL_ANCHOR = "smolvlm2500m"


def is_port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def classify_openai_backend(server_header: str, port: int) -> tuple[str, str]:
    h = (server_header or "").lower()
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
    return "openai-compatible", "unknown-openai"


def detect_ollama(host: str, port: int) -> BackendInfo:
    url = f"http://{host}:{port}"
    out = BackendInfo("ollama", "ollama", port, url, "not_running", [], [])
    if not is_port_open(host, port):
        return out
    try:
        resp = httpx.get(f"{url}/api/tags", timeout=5.0)
        resp.raise_for_status()
        out.status = "running"
        for m in resp.json().get("models", []):
            name = m.get("name", "")
            if name:
                out.models.append(name)
                if any(k in name.lower() for k in VISION_HINTS):
                    out.vision_models.append(name)
    except Exception:
        out.status = "unknown"
    return out


def detect_openai_endpoint(host: str, port: int) -> BackendInfo:
    url = f"http://{host}:{port}"
    out = BackendInfo(f"openai-{port}", "unknown-openai", port, url, "not_running", [], [])
    if not is_port_open(host, port):
        return out
    try:
        resp = httpx.get(f"{url}/v1/models", timeout=5.0)
        resp.raise_for_status()
        out.status = "running"
        out.name, out.family = classify_openai_backend(resp.headers.get("server", ""), port)
        for m in resp.json().get("data", []):
            mid = m.get("id", "")
            if mid:
                out.models.append(mid)
                if any(k in mid.lower() for k in VISION_HINTS):
                    out.vision_models.append(mid)
    except Exception:
        out.status = "unknown"
    return out


def detect_llamacpp_health(host: str, port: int) -> BackendInfo:
    url = f"http://{host}:{port}"
    out = BackendInfo("llama.cpp", "llama.cpp-family", port, url, "not_running", [], [])
    if not is_port_open(host, port):
        return out
    try:
        resp = httpx.get(f"{url}/health", timeout=4.0)
        if resp.status_code == 200:
            out.status = "running"
    except Exception:
        out.status = "unknown"
    return out


def detect_port(host: str, port: int) -> Optional[BackendInfo]:
    """Try to identify what's running on a port."""
    if not is_port_open(host, port):
        return None
    
    # Try Ollama first (port 11434 typical)
    if port == 11434:
        info = detect_ollama(host, port)
        if info.status == "running":
            return info
    
    # Try OpenAI-compatible /v1/models
    info = detect_openai_endpoint(host, port)
    if info.status == "running":
        return info
    
    # Try llama.cpp /health
    info = detect_llamacpp_health(host, port)
    if info.status == "running":
        return info
    
    # Try Ollama on non-standard port
    info = detect_ollama(host, port)
    if info.status == "running":
        return info
    
    return None


def normalize_model_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def model_targets_for_os(os_name: str) -> list[str]:
    if os_name == "darwin":
        return ["SmolVLM2-500M-Video-Instruct-mlx", "SmolVLM2-500M-Video-Instruct"]
    return ["SmolVLM2-500M-Video-Instruct-GGUF", "SmolVLM2-500M-Video-Instruct"]


def model_similarity(candidate: str, targets: list[str], os_name: str) -> float:
    c = normalize_model_name(candidate)
    ratios = [difflib.SequenceMatcher(None, c, normalize_model_name(t)).ratio() for t in targets]
    score = max(ratios) if ratios else 0.0
    if BASE_MODEL_ANCHOR in c:
        score += 0.22
    if "smolvlm2" in c:
        score += 0.08
    if os_name == "darwin" and "mlx" in c:
        score += 0.08
    if os_name != "darwin" and "gguf" in c:
        score += 0.08
    return min(score, 1.0)


def select_best(backends: list[BackendInfo], os_name: str) -> Recommendation:
    running = [b for b in backends if b.status == "running" and b.models]
    targets = model_targets_for_os(os_name)
    
    if not running:
        return Recommendation(None, None, None, None, 0.0, "No running backend with models found.")
    
    best = None
    for b in running:
        pri = FAMILY_PRIORITY.get(b.family, 99)
        pool = b.vision_models or b.models
        if not pool:
            continue
        top_model, top_score = None, -1.0
        for m in pool:
            s = model_similarity(m, targets, os_name)
            if s > top_score:
                top_model, top_score = m, s
        cand = (pri, -top_score, b.name, top_model, top_score, b.family, b.url)
        if best is None or cand < best:
            best = cand
    
    if best is None:
        return Recommendation(None, None, None, None, 0.0, "No candidate model found.")
    
    pri, _, bname, model, score, family, url = best
    if score < 0.45:
        return Recommendation(bname, family, None, url, score,
            f"No similar model to {', '.join(targets)}. Download manually.")
    return Recommendation(bname, family, model, url, score, f"priority={pri}, similarity={score:.2f}")


def detect_all(ports: list[int], host: str = "127.0.0.1") -> tuple[list[BackendInfo], Recommendation]:
    """Detect backends on given ports."""
    if httpx is None:
        raise RuntimeError("httpx not installed. Run: pip install httpx")
    
    backends = []
    for port in ports:
        info = detect_port(host, port)
        if info:
            backends.append(info)
    
    os_name = platform.system().lower()
    return backends, select_best(backends, os_name)


def manual_guidance(os_name: str) -> str:
    if os_name == "darwin":
        return (
            "macOS recommended: SmolVLM2-500M-Video-Instruct-mlx\n"
            "Install: pip install -U mlx-vlm"
        )
    return (
        "Recommended: SmolVLM2-500M-Video-Instruct-GGUF\n"
        "Download and load in your backend."
    )


def main():
    parser = argparse.ArgumentParser(description="Detect local inference backends.")
    parser.add_argument("--ports", type=str, default="",
        help="Comma-separated ports to scan (from process detection)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    # Parse ports: explicit, or fallback to common defaults
    if args.ports:
        ports = [int(p.strip()) for p in args.ports.split(",") if p.strip().isdigit()]
    else:
        ports = [11434, 1234, 8000, 8080]  # fallback defaults
    
    backends, rec = detect_all(ports, args.host)
    os_name = platform.system().lower()
    
    if args.json:
        print(json.dumps({
            "os_name": os_name,
            "backends": [asdict(b) for b in backends],
            "recommendation": asdict(rec),
            "manual_guidance": manual_guidance(os_name),
        }, ensure_ascii=False, indent=2))
    else:
        print(f"OS: {os_name}, scanned ports: {ports}")
        for b in backends:
            print(f"  {b.name} [{b.family}] {b.url} models={len(b.models)}")
        if rec.model:
            print(f"Selected: {rec.backend_name} → {rec.model}")
        else:
            print(f"No suitable model. {rec.reason}")
            print(manual_guidance(os_name))
    
    sys.exit(0 if rec.model else 1)


if __name__ == "__main__":
    main()
