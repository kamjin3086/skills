#!/usr/bin/env python3
import argparse
import json
import platform
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass


QUICK_PORTS = [8188, 8189, 8190]
DEEP_PORTS = [8188, 8189, 8190, 8288, 8000, 7860]
QUICK_HOSTS = ["127.0.0.1"]
DEEP_HOSTS = ["127.0.0.1", "localhost"]


@dataclass
class ProbeResult:
    url: str
    reachable: bool
    detail: str


def fetch_object_info(url: str, timeout: float) -> ProbeResult:
    target = f"{url.rstrip('/')}/object_info"
    try:
        with urllib.request.urlopen(target, timeout=timeout) as response:
            content_type = response.headers.get("content-type", "")
            body = response.read(2048)
        looks_like_json = "json" in content_type.lower() or body.startswith(b"{")
        if response.status == 200 and (b"CLIPTextEncode" in body or looks_like_json):
            return ProbeResult(url, True, "GET /object_info returned a ComfyUI-like response.")
        return ProbeResult(url, False, f"GET /object_info returned HTTP {response.status}, but response did not look like ComfyUI.")
    except urllib.error.HTTPError as error:
        return ProbeResult(url, False, f"HTTP {error.code} from /object_info.")
    except Exception as error:
        return ProbeResult(url, False, str(error))


def listening_process_hints(ports: list[int]) -> list[str]:
    system = platform.system().lower()
    if "windows" in system:
        commands = [
            ["powershell", "-NoProfile", "-Command", "Get-NetTCPConnection -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess | ConvertTo-Json -Compress"],
            ["cmd", "/c", "netstat -ano -p tcp"],
        ]
    else:
        commands = [["sh", "-lc", "ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null || lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null"]]

    hints = []
    for command in commands:
        try:
            output = subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL, timeout=3)
        except Exception:
            continue
        lower = output.lower()
        if any(str(port) in lower for port in ports) or "comfy" in lower:
            hints.append(output.strip()[:4000])
            break
    return hints


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect a reachable local ComfyUI endpoint.")
    parser.add_argument("--ports", default="", help="Comma-separated ports. Defaults to quick ComfyUI ports.")
    parser.add_argument("--timeout", type=float, default=0.45)
    parser.add_argument("--deep", action="store_true", help="Probe more ports/hosts and include listener hints.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    default_ports = DEEP_PORTS if args.deep else QUICK_PORTS
    ports = [int(item.strip()) for item in args.ports.split(",") if item.strip()] or default_ports
    hosts = DEEP_HOSTS if args.deep else QUICK_HOSTS

    results = []
    for port in ports:
        for host in hosts:
            result = fetch_object_info(f"http://{host}:{port}", args.timeout)
            results.append(result)
            if result.reachable:
                payload = {
                    "found": True,
                    "url": result.url,
                    "detail": result.detail,
                    "probes": [r.__dict__ for r in results],
                }
                print(json.dumps(payload, indent=2) if args.json else result.url)
                return

    payload = {
        "found": False,
        "url": None,
        "detail": "No reachable local ComfyUI endpoint found. Ask the user for a remote or LAN ComfyUI URL.",
        "process_hints": listening_process_hints(ports) if args.deep else [],
        "probes": [r.__dict__ for r in results],
    }
    print(json.dumps(payload, indent=2) if args.json else payload["detail"])
    sys.exit(1)


if __name__ == "__main__":
    main()
