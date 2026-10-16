from __future__ import annotations

import argparse
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re
import secrets
import threading
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from configure_deepseek import configure


def serve(hostname: str, port: int) -> None:
    if not re.fullmatch(r"[a-z0-9-]+\.trycloudflare\.com", hostname):
        raise ValueError("临时 HTTPS 域名格式不正确。")

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    public_key = base64.b64encode(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    ).decode("ascii")
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    path = "/setup/" + token
    origin = "https://" + hostname
    expires = time.monotonic() + 3600
    state = {"configured": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def allowed(self) -> bool:
            return (
                self.path == path
                and self.headers.get("Host") == hostname
                and time.monotonic() < expires
                and not state["configured"]
            )

        def respond(self, status: int, payload: bytes, content_type: str, nonce: str = "") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; connect-src 'self'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'",
            )
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            if not self.allowed():
                self.respond(404, b"Not found", "text/plain; charset=utf-8")
                return
            nonce = secrets.token_urlsafe(18)
            page = f'''<!doctype html>
<html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>东盟 AI 密钥配置</title>
<style>body{{font:16px system-ui;max-width:600px;margin:48px auto;padding:20px}}input,button{{box-sizing:border-box;display:block;width:100%;padding:13px;margin:16px 0}}p{{line-height:1.7}}</style>
<h1>配置 DeepSeek Flash</h1>
<p>在这里输入 DeepSeek API Key。浏览器会先使用服务器公钥加密，再通过临时 HTTPS 链接提交。官方验证通过后，DeepSeek 用于公开数据辅助翻译，GLM 继续负责正式助手；DeepSeek 故障时可回退 GLM。此入口一小时后失效。</p>
<label for="key">DeepSeek API Key</label><input id="key" type="password" autocomplete="off" minlength="16" maxlength="256" autofocus>
<button id="submit" type="button">验证并配置</button><p id="status" role="status"></p>
<script nonce="{nonce}">
const publicKey = "{public_key}";
const csrf = "{csrf}";
document.querySelector('#submit').addEventListener('click', async () => {{
  const input = document.querySelector('#key');
  const button = document.querySelector('#submit');
  const status = document.querySelector('#status');
  if (!input.value || input.value.length < 16 || input.value.length > 256) {{ status.textContent = '请填写完整的 API Key。'; return; }}
  button.disabled = true;
  status.textContent = '正在加密并向 DeepSeek 官方验证，请稍候…';
  try {{
    const bytes = Uint8Array.from(atob(publicKey), character => character.charCodeAt(0));
    const key = await crypto.subtle.importKey('spki', bytes, {{ name: 'RSA-OAEP', hash: 'SHA-256' }}, false, ['encrypt']);
    const cipher = await crypto.subtle.encrypt({{ name: 'RSA-OAEP' }}, key, new TextEncoder().encode(input.value.trim()));
    const encryptedKey = btoa(String.fromCharCode(...new Uint8Array(cipher)));
    input.value = '';
    const response = await fetch(location.pathname, {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ csrf, encryptedKey }}), cache: 'no-store' }});
    const result = await response.json();
    status.textContent = result.message;
    if (!response.ok) button.disabled = false;
  }} catch {{ status.textContent = '提交失败，请检查网络或重新打开页面。'; button.disabled = false; }}
}});
</script></html>'''
            self.respond(200, page.encode("utf-8"), "text/html; charset=utf-8", nonce)

        def do_POST(self) -> None:
            if not self.allowed():
                self.respond(404, b"Not found", "text/plain; charset=utf-8")
                return
            if self.headers.get("Origin") != origin:
                self.json_response(403, "请求来源未通过校验。")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 1 <= length <= 2048 or self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
                    raise ValueError("请求格式不正确。")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict) or not secrets.compare_digest(payload.get("csrf", ""), csrf):
                    raise ValueError("安全校验失败。")
                encrypted = base64.b64decode(payload["encryptedKey"], validate=True)
                submitted_key = private_key.decrypt(
                    encrypted,
                    padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
                ).decode("ascii")
                message = configure(submitted_key)
                state["configured"] = True
                self.json_response(200, message)
                threading.Timer(5, server.shutdown).start()
            except (ValueError, TypeError, KeyError):
                self.json_response(400, "验证或保存失败。请检查 Key、账户余额和模型权限后重试。")

        def json_response(self, status: int, message: str) -> None:
            payload = json.dumps({"message": message}, ensure_ascii=False).encode("utf-8")
            self.respond(status, payload, "application/json; charset=utf-8")

    server = HTTPServer(("127.0.0.1", port), Handler)
    timer = threading.Timer(3600, server.shutdown)
    timer.daemon = True
    timer.start()
    print(origin + path, flush=True)
    try:
        server.serve_forever()
    finally:
        timer.cancel()
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--port", type=int, default=39015)
    arguments = parser.parse_args()
    serve(arguments.hostname, arguments.port)
