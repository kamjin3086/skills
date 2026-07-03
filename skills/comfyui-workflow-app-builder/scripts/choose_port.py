#!/usr/bin/env python3
import argparse
import socket


COMMON_PORTS = {
    3000,
    3001,
    4200,
    5000,
    5001,
    5173,
    5174,
    5175,
    7860,
    8000,
    8080,
    8188,
}


def is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def choose_port(host: str, start: int, end: int) -> int:
    for port in range(start, end + 1):
        if port in COMMON_PORTS:
            continue
        if is_free(host, port):
            return port
    raise SystemExit(f"No free port found in {start}-{end} for {host}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Choose a free local port for a generated ComfyUI app.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--start", type=int, default=17000)
    parser.add_argument("--end", type=int, default=19000)
    args = parser.parse_args()
    print(choose_port(args.host, args.start, args.end))


if __name__ == "__main__":
    main()
