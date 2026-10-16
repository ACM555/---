from __future__ import annotations

import argparse
from datetime import datetime
import getpass
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import threading
import time
from urllib.parse import parse_qs

from dotenv import dotenv_values
import httpx


PROJECT = Path(__file__).resolve().parents[1]
ENVIRONMENT = PROJECT / "backend/.env"
MODEL = "deepseek-flash"
MODEL_CANDIDATES = (MODEL, "deepseek-vflash", "deepseek-v4.1-flash", "deepseek-4.1-flash", "deepseek-v4-flash")


def updated_environment(original: str, key: str, model: str = MODEL) -> str:
    changes = {"MODEL_PROVIDER": "glm", "DEEPSEEK_API_KEY": key, "DEEPSEEK_BASE_URL": "https://api.deepseek.com", "DEEPSEEK_MODEL": model}
    lines = []
    for line in original.splitlines():
        name = line.split("=", 1)[0].strip()
        if name not in changes:
            lines.append(line)
    lines.extend(f"{name}='{value}'" for name, value in changes.items())
    return "\n".join(lines) + "\n"


def atomic_write(path: Path, contents: str) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".private-config-", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(contents)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _require_success(response: httpx.Response, stage: str) -> None:
    if response.status_code < 400:
        return
    reason = {
        400: "模型或请求参数不受支持",
        401: "Key 无效或未获授权",
        402: "账户余额不足",
        403: "账户无权访问",
        404: "模型或接口不存在",
        429: "官方接口限流",
    }.get(response.status_code, "官方接口暂不可用")
    raise ValueError(f"{stage}失败：HTTP {response.status_code}（{reason}）；未保存密钥。")


def validate_key(key: str) -> str:
    if not 16 <= len(key) <= 256 or not all(character.isascii() and (character.isalnum() or character in "-_") for character in key):
        raise ValueError("Key 格式不正确，请只填写 DeepSeek 官方 API Key。")
    stage = "模型列表查询"
    try:
        headers = {"Authorization": "Bearer " + key}
        with httpx.Client(timeout=45, follow_redirects=False, trust_env=False) as client:
            try:
                models = client.get("https://api.deepseek.com/models", headers=headers)
            except httpx.RequestError:
                time.sleep(1)
                models = client.get("https://api.deepseek.com/models", headers=headers)
            _require_success(models, stage)
            supported = {item.get("id") for item in models.json().get("data", []) if isinstance(item, dict)}
            model = next((candidate for candidate in MODEL_CANDIDATES if candidate in supported), None)
            if model is None:
                raise ValueError("此账户的官方模型列表不含 DeepSeek Flash；未保存密钥，也不会自动改用其他型号。")
            stage = "模型调用"
            response = client.post("https://api.deepseek.com/chat/completions", headers=headers, json={"model": model, "messages": [{"role": "user", "content": "只回复 OK"}], "max_tokens": 16, "stream": False})
            _require_success(response, stage)
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("官方模型未返回有效内容，未保存密钥。")
            return model
    except httpx.RequestError as failure:
        raise ValueError(f"{stage}网络连接失败（{type(failure).__name__}）；未保存密钥。") from failure
    except (KeyError, IndexError, TypeError, AttributeError, json.JSONDecodeError) as failure:
        raise ValueError("官方 API 返回的数据格式不正确；未保存密钥。") from failure


def configure(key: str) -> str:
    model = validate_key(key)
    original = ENVIRONMENT.read_text(encoding="utf-8")
    if not dotenv_values(ENVIRONMENT).get("GLM_API_KEY"):
        raise ValueError("未配置 GLM 主模型，无法启用双模型协作。")
    atomic_write(ENVIRONMENT, updated_environment(original, key, model))
    try:
        subprocess.run(["systemctl", "restart", "chuhai-weishi.service"], check=True, timeout=25, capture_output=True)
        for attempt in range(15):
            time.sleep(1)
            try:
                with httpx.Client(timeout=3, trust_env=False) as client:
                    health = client.get("http://127.0.0.1:39013/api/health").json()
                tasks = health.get("aiTasks", {})
                if health.get("aiProvider") == "glm" and health.get("aiStatus") == "configured" and tasks.get("publicDataTranslation", {}).get("provider") == "deepseek" and tasks.get("publicDataTranslation", {}).get("model") == model:
                    receipt = PROJECT / "backend/data/deepseek-configuration.json"
                    atomic_write(receipt, json.dumps({"configuredAt": datetime.now().astimezone().isoformat(), "provider": "deepseek", "model": model, "verified": True}, ensure_ascii=False))
                    return "官方认证及小请求通过，已保存为权限 600 的服务器私有配置。GLM 继续负责正式助手，DeepSeek Flash 负责公开数据辅助翻译，故障时回退 GLM。密钥没有发送到公开 HTTP 站点或记录到日志。"
            except (httpx.HTTPError, ValueError):
                continue
        raise RuntimeError("双模型协作健康检查失败。")
    except (subprocess.SubprocessError, RuntimeError, OSError) as failure:
        atomic_write(ENVIRONMENT, original)
        subprocess.run(["systemctl", "restart", "chuhai-weishi.service"], timeout=25, capture_output=True, check=False)
        raise ValueError("配置失败，已恢复原配置；请查看服务状态。") from failure


def serve(port: int) -> None:
    token = secrets.token_urlsafe(24)
    path = "/setup/" + token
    expires = time.monotonic() + 3600
    lock = threading.Lock()
    state = {"configured": False}
    host = f"127.0.0.1:{port}"
    allowed_hosts = {host, f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def page(self, status: int, message: str = "") -> None:
            form = "" if state["configured"] or status in {403, 404} else f'<form method="post" action="{path}"><input type="hidden" name="csrf" value="{token}"><label>DeepSeek 官方 API Key<input name="key" type="password" required minlength="16" maxlength="256" autocomplete="off" autofocus></label><button type="submit">验证并启用双模型协作</button></form>'
            body = (f'<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>东盟模型安全配置</title><style>body{{font:16px system-ui;max-width:640px;margin:48px auto;padding:20px}}input,button{{display:block;margin:16px 0;padding:12px;max-width:100%;box-sizing:border-box;width:100%}}p{{line-height:1.7}}</style><h1>东盟 AI 安全配置</h1><p>只在服务器本机或 SSH 加密隧道中打开。不要在公开 HTTP 页面输入 Key。提交后会向 DeepSeek 官方做一次认证和极小请求（可能产生极少量费用），通过后启用公开数据辅助翻译，GLM 保持正式助手主模型。数据采集仍只走许可开放接口，AI 不能代替法条审核。</p><p>{escape(message)}</p>{form}</html>').encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def allowed(self) -> bool:
            return self.path == path and self.headers.get("Host") in allowed_hosts and time.monotonic() < expires

        def do_GET(self) -> None:
            self.page(200 if self.allowed() else 404, "入口只在启动后 1 小时内有效。" if self.allowed() else "入口无效或已过期。")

        def do_POST(self) -> None:
            if not self.allowed() or state["configured"]:
                self.page(404, "入口无效、已过期或已经完成。")
                return
            origin = self.headers.get("Origin")
            if origin and origin not in {"http://" + address for address in allowed_hosts}:
                self.page(403, "请求来源不允许。")
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 1 <= size <= 2048 or self.headers.get("Content-Type", "").split(";", 1)[0] != "application/x-www-form-urlencoded":
                    raise ValueError("请求格式不正确。")
                fields = parse_qs(self.rfile.read(size).decode(), max_num_fields=3)
                if not secrets.compare_digest(fields.get("csrf", [""])[0], token):
                    raise ValueError("安全令牌校验失败。")
                if not lock.acquire(blocking=False):
                    raise ValueError("正在验证，请勿重复提交。")
                try:
                    message = configure(fields.get("key", [""])[0].strip())
                    state["configured"] = True
                finally:
                    lock.release()
                self.page(200, message)
                threading.Timer(5, server.shutdown).start()
            except (ValueError, UnicodeDecodeError):
                self.page(400, "验证或保存失败，现有配置未切换。请确认 Key、账户额度与官方 API 状态后重试。")

    server = HTTPServer(("127.0.0.1", port), Handler)
    timer = threading.Timer(3600, server.shutdown)
    timer.daemon = True
    timer.start()
    print(f"安全输入入口：http://{host}{path}", flush=True)
    print(f"本机不在服务器上时先执行：ssh -N -L {port}:127.0.0.1:{port} root@154.40.45.149", flush=True)
    try:
        server.serve_forever()
    finally:
        timer.cancel()
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=39014)
    parser.add_argument("--status", action="store_true")
    options = parser.parse_args()
    if options.status:
        configuration = dotenv_values(ENVIRONMENT)
        print(json.dumps({"provider": configuration.get("MODEL_PROVIDER", ""), "deepseekKeyConfigured": bool(configuration.get("DEEPSEEK_API_KEY")), "model": configuration.get("DEEPSEEK_MODEL", MODEL)}, ensure_ascii=False))
    elif options.serve:
        serve(options.port)
    else:
        try:
            print(configure(getpass.getpass("DeepSeek API Key（隐藏输入）：").strip()))
        except ValueError as failure:
            print(str(failure))
            raise SystemExit(1)


if __name__ == "__main__":
    main()
