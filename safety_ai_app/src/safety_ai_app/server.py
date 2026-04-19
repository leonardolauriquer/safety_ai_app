"""
SafetyAI PWA Proxy Server

Thin aiohttp reverse proxy (port 5000) in front of Streamlit (port 5001).
Provides:
  - GET /sw.js          -> serve static/sw.js with Service-Worker-Allowed: /
                          so the SW can claim scope: '/' for offline support.
  - GET /_safetyai_offline -> inline offline fallback page
  - All other routes    -> proxied to Streamlit at localhost:5001
                          including WebSocket upgrade (required by Streamlit).
"""

import asyncio
import logging
import os
import signal
import subprocess
import sys

import aiohttp
from aiohttp import web

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("safetyai.proxy")

STREAMLIT_PORT = 5001
PROXY_PORT = int(os.environ.get("PORT", 5000))

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SW_PATH = os.path.join(_SCRIPT_DIR, "static", "sw.js")

_OFFLINE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SafetyAI — Offline</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{min-height:100vh;display:flex;align-items:center;justify-content:center;
         background:#020617;color:#F1F5F9;
         font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif;padding:24px}
    .card{background:rgba(15,23,42,.85);border:1px solid rgba(74,222,128,.3);
          border-radius:20px;padding:40px 32px;max-width:400px;width:100%;text-align:center;
          box-shadow:0 0 40px rgba(74,222,128,.15)}
    .icon{font-size:3rem;margin-bottom:16px}
    h1{font-size:1.5rem;color:#4ADE80;margin-bottom:12px;letter-spacing:.05em}
    p{color:#94A3B8;line-height:1.6;margin-bottom:24px}
    button{background:linear-gradient(135deg,#4ADE80,#22D3EE);border:none;
           border-radius:10px;color:#020617;font-weight:700;
           padding:12px 28px;font-size:1rem;cursor:pointer}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">\U0001f6e1\ufe0f</div>
    <h1>SafetyAI — Offline</h1>
    <p>Sem conex\xe3o com a internet. Reconecte-se para usar o assistente de SST.</p>
    <button onclick="window.location.reload()">Tentar novamente</button>
  </div>
</body>
</html>"""


async def handle_sw(request: web.Request) -> web.Response:
    try:
        with open(_SW_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        return web.Response(
            text=content,
            content_type="application/javascript",
            headers={
                "Service-Worker-Allowed": "/",
                "Cache-Control": "no-cache",
            },
        )
    except FileNotFoundError:
        logger.warning("sw.js not found at %s", _SW_PATH)
        return web.Response(status=404, text="Service worker not found")


async def handle_offline(request: web.Request) -> web.Response:
    return web.Response(text=_OFFLINE_HTML, content_type="text/html")


async def proxy_http(request: web.Request) -> web.StreamResponse:
    target = f"http://127.0.0.1:{STREAMLIT_PORT}{request.path_qs}"
    session: aiohttp.ClientSession = request.app["session"]

    try:
        headers = {k: v for k, v in request.headers.items()
                   if k.lower() not in ("host", "content-length")}
        data = await request.read()

        async with session.request(
            request.method,
            target,
            headers=headers,
            data=data,
            allow_redirects=False,
        ) as upstream:
            response = web.StreamResponse(
                status=upstream.status,
                headers={k: v for k, v in upstream.headers.items()
                         if k.lower() not in ("transfer-encoding",)},
            )
            await response.prepare(request)
            async for chunk in upstream.content.iter_chunked(65536):
                await response.write(chunk)
            await response.write_eof()
            return response
    except aiohttp.ClientConnectionError:
        return web.Response(status=502, text="Streamlit not ready yet")


async def proxy_ws(request: web.Request) -> web.WebSocketResponse:
    ws_client = web.WebSocketResponse()
    await ws_client.prepare(request)

    session: aiohttp.ClientSession = request.app["session"]
    target = f"ws://127.0.0.1:{STREAMLIT_PORT}{request.path_qs}"
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ("host", "upgrade", "connection",
                                    "sec-websocket-key", "sec-websocket-version",
                                    "sec-websocket-extensions")}
    try:
        async with session.ws_connect(target, headers=headers) as ws_upstream:
            async def forward_to_upstream():
                async for msg in ws_client:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await ws_upstream.send_str(msg.data)
                    elif msg.type == aiohttp.WSMsgType.BINARY:
                        await ws_upstream.send_bytes(msg.data)
                    elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                        break

            async def forward_to_client():
                async for msg in ws_upstream:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await ws_client.send_str(msg.data)
                    elif msg.type == aiohttp.WSMsgType.BINARY:
                        await ws_client.send_bytes(msg.data)
                    elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                        break

            await asyncio.gather(forward_to_upstream(), forward_to_client())
    except aiohttp.ClientConnectionError:
        pass

    return ws_client


async def route_handler(request: web.Request) -> web.StreamResponse:
    upgrade = request.headers.get("Upgrade", "").lower()
    if upgrade == "websocket":
        return await proxy_ws(request)
    return await proxy_http(request)


async def on_startup(app: web.Application) -> None:
    connector = aiohttp.TCPConnector(limit=200)
    app["session"] = aiohttp.ClientSession(connector=connector)
    logger.info("Proxy session ready — forwarding to Streamlit on port %d", STREAMLIT_PORT)


async def on_shutdown(app: web.Application) -> None:
    await app["session"].close()


def start_streamlit() -> subprocess.Popen:
    web_app = os.path.join(_SCRIPT_DIR, "web_app.py")
    cmd = [
        sys.executable, "-m", "streamlit", "run", web_app,
        "--server.port", str(STREAMLIT_PORT),
        "--server.address", "127.0.0.1",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
    ]
    logger.info("Starting Streamlit: %s", " ".join(cmd))
    return subprocess.Popen(cmd)


def main() -> None:
    streamlit_proc = start_streamlit()

    app = web.Application()
    app.router.add_get("/sw.js", handle_sw)
    app.router.add_get("/_safetyai_offline", handle_offline)
    app.router.add_route("*", "/{path_info:.*}", route_handler)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    def shutdown(sig, frame):
        logger.info("Shutting down (signal %s)", sig)
        streamlit_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("SafetyAI proxy listening on port %d", PROXY_PORT)
    web.run_app(app, host="0.0.0.0", port=PROXY_PORT, access_log=None)


if __name__ == "__main__":
    main()
