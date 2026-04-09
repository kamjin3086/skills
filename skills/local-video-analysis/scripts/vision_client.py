#!/usr/bin/env python3
"""
Vision client for local backends.
Simple frame extraction and API calls. No complex logic.
"""

import base64
import json
import os
import shutil
import subprocess
import tempfile
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None


class VisionClient:
    def __init__(self, backend_family: str, base_url: str, model: str):
        self.backend_family = backend_family
        self.base_url = base_url.rstrip("/")
        self.model = model
        
        if httpx is None:
            raise RuntimeError("httpx not installed. Run: pip install httpx")

    def generate_multimodal(self, prompt: str, images: list[str]) -> str:
        """Send images + prompt to the backend."""
        if self.backend_family == "ollama":
            resp = httpx.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "images": images, "stream": False},
                timeout=180.0
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        
        # OpenAI-compatible (including gateways like llama-swap)
        content = [{"type": "text", "text": prompt}]
        for img in images:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}})
        
        resp = httpx.post(
            f"{self.base_url}/v1/chat/completions",
            json={"model": self.model, "messages": [{"role": "user", "content": content}], "max_tokens": 1024},
            timeout=180.0
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def generate_text(self, prompt: str) -> str:
        """Text-only generation."""
        return self.generate_multimodal(prompt, [])


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Direct call to vision backend.")
    parser.add_argument("--backend-family", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--image", action="append", help="Base64-encoded image (can repeat)")
    parser.add_argument("--prompt", default="Describe this image.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    client = VisionClient(args.backend_family, args.base_url, args.model)
    images = args.image or []
    answer = client.generate_multimodal(args.prompt, images)

    if args.json:
        print(json.dumps({"response": answer}, ensure_ascii=False))
    else:
        print(answer)


if __name__ == "__main__":
    main()
