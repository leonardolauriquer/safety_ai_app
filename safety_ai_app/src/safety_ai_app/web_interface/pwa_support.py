import base64
import json
import os
import logging

logger = logging.getLogger(__name__)

_PWA_CACHE: dict = {}

_APP_TITLE = "Safety AI - SST"
_APP_SHORT_NAME = "SafetyAI"
_APP_DESCRIPTION = "Assistente de IA para Segurança e Saúde do Trabalho"
_THEME_COLOR = "#4ADE80"
_BG_COLOR = "#020617"


def _load_icon_b64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception as e:
        logger.warning(f"PWA: could not load icon '{path}': {e}")
        return ""


def _build_manifest(project_root: str) -> str:
    pwa_dir = os.path.join(project_root, "assets", "pwa")
    icon_192 = _load_icon_b64(os.path.join(pwa_dir, "icon-192.png"))
    icon_512 = _load_icon_b64(os.path.join(pwa_dir, "icon-512.png"))

    icons = []
    if icon_192:
        icons.append({
            "src": f"data:image/png;base64,{icon_192}",
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "any maskable",
        })
    if icon_512:
        icons.append({
            "src": f"data:image/png;base64,{icon_512}",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "any maskable",
        })

    manifest = {
        "name": _APP_TITLE,
        "short_name": _APP_SHORT_NAME,
        "description": _APP_DESCRIPTION,
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait-primary",
        "background_color": _BG_COLOR,
        "theme_color": _THEME_COLOR,
        "lang": "pt-BR",
        "categories": ["business", "productivity", "utilities"],
        "prefer_related_applications": False,
        "icons": icons,
        "shortcuts": [
            {
                "name": "Chat IA",
                "short_name": "Chat",
                "description": "Consultar normas regulamentadoras com IA",
                "url": "/?page=chat",
                "icons": [{"src": f"data:image/png;base64,{icon_192}", "sizes": "192x192"}] if icon_192 else [],
            },
            {
                "name": "Consultas Rápidas",
                "short_name": "Consultas",
                "description": "CBO, CID, CNAE, CA/EPI e Multas NR",
                "url": "/?page=quick_queries_page",
                "icons": [{"src": f"data:image/png;base64,{icon_192}", "sizes": "192x192"}] if icon_192 else [],
            },
            {
                "name": "Dimensionamento",
                "short_name": "CIPA/SESMT",
                "description": "Dimensionar CIPA, SESMT e Brigada",
                "url": "/?page=sizing_page",
                "icons": [{"src": f"data:image/png;base64,{icon_192}", "sizes": "192x192"}] if icon_192 else [],
            },
        ],
    }
    return json.dumps(manifest, ensure_ascii=False)


def _load_apple_touch_icon_b64(project_root: str) -> str:
    path = os.path.join(project_root, "assets", "pwa", "icon-180.png")
    return _load_icon_b64(path)


def _load_sw_code(project_root: str) -> str:
    """Lê o conteúdo do sw.js para injeção via blob URL.
    project_root = safety_ai_app/, sw.js em src/safety_ai_app/static/sw.js
    """
    sw_path = os.path.join(project_root, "src", "safety_ai_app", "static", "sw.js")
    try:
        with open(sw_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning(f"PWA: could not load sw.js '{sw_path}': {e}")
        return ""


def get_pwa_injection_html(project_root: str) -> str:
    """
    Injeta no <head> do documento pai:
    - Viewport meta com viewport-fit=cover (suporte a notch iPhone X+)
    - Meta tags para Android/Chrome e iOS/Safari
    - Web App Manifest (inline Blob URL)
    - Apple Touch Icon
    - Registro do Service Worker (offline support)
    - Listener para beforeinstallprompt (install prompt no Android)
    - JS para auto-expand sidebar em desktop (viewport > 1024px)

    Safe to call on every Streamlit re-render — deduplicado via data attributes.
    """
    cache_key = "pwa_html_v4"
    if cache_key in _PWA_CACHE:
        return _PWA_CACHE[cache_key]

    manifest_json = _build_manifest(project_root)
    apple_icon_b64 = _load_apple_touch_icon_b64(project_root)
    apple_icon_data_url = f"data:image/png;base64,{apple_icon_b64}" if apple_icon_b64 else ""
    sw_code = _load_sw_code(project_root)

    manifest_json_js = manifest_json.replace("\\", "\\\\").replace("`", "\\`")
    sw_code_js = sw_code.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

    apple_touch_js = ""
    if apple_icon_data_url:
        apple_touch_js = f"""
        addLink('apple-touch-icon', '{apple_icon_data_url}');
        addLink('apple-touch-icon-precomposed', '{apple_icon_data_url}');
"""

    html = f"""
<script>
(function() {{
    var doc = window.parent.document;
    var head = doc.head;
    if (!head) return;
    if (doc.querySelector('meta[name="safetyai-pwa-injected"]')) return;

    function addMeta(name, content, attr) {{
        attr = attr || 'name';
        if (doc.querySelector('meta[' + attr + '="' + name + '"]')) return;
        var m = doc.createElement('meta');
        m[attr] = name;
        m.content = content;
        head.appendChild(m);
    }}

    function addLink(rel, href, type_) {{
        if (doc.querySelector('link[rel="' + rel + '"]')) return;
        var l = doc.createElement('link');
        l.rel = rel;
        l.href = href;
        if (type_) l.type = type_;
        head.appendChild(l);
    }}

    /* --- Sentinel to prevent double-injection --- */
    addMeta('safetyai-pwa-injected', '1');

    /* --- Viewport com viewport-fit=cover (iPhone X+ notch) --- */
    (function() {{
        var vp = doc.querySelector('meta[name="viewport"]');
        var content = 'width=device-width, initial-scale=1.0, viewport-fit=cover';
        if (vp) {{ vp.content = content; }} else {{ addMeta('viewport', content); }}
    }})();

    /* --- Android / Chrome --- */
    addMeta('theme-color', '{_THEME_COLOR}');
    addMeta('mobile-web-app-capable', 'yes');

    /* --- iOS / Safari --- */
    addMeta('apple-mobile-web-app-capable', 'yes');
    addMeta('apple-mobile-web-app-status-bar-style', 'black-translucent');
    addMeta('apple-mobile-web-app-title', '{_APP_SHORT_NAME}');
    addMeta('format-detection', 'telephone=no');
    {apple_touch_js}

    /* --- Web App Manifest (Blob URL) --- */
    if (!doc.querySelector('link[rel="manifest"]')) {{
        try {{
            var manifestData = `{manifest_json_js}`;
            var blob = new Blob([manifestData], {{type: 'application/manifest+json'}});
            var manifestUrl = URL.createObjectURL(blob);
            addLink('manifest', manifestUrl, 'application/manifest+json');
        }} catch(e) {{
            console.warn('PWA manifest injection failed:', e);
        }}
    }}

    /* --- Service Worker Registration via Blob URL ---
       Blob URL bypasses the directory scope restriction, allowing scope: '/'
       regardless of where the SW file is physically served.              */
    if ('serviceWorker' in window.parent.navigator) {{
        window.parent.addEventListener('load', function() {{
            try {{
                var swSource = `{sw_code_js}`;
                var swBlob = new Blob([swSource], {{type: 'application/javascript'}});
                var swUrl = URL.createObjectURL(swBlob);
                window.parent.navigator.serviceWorker
                    .register(swUrl, {{ scope: '/' }})
                    .then(function(reg) {{
                        console.info('[SafetyAI PWA] Service worker registrado (blob):', reg.scope);
                    }})
                    .catch(function(err) {{
                        console.warn('[SafetyAI PWA] Service worker blob falhou:', err);
                    }});
            }} catch(e) {{
                console.warn('[SafetyAI PWA] Service worker não disponível:', e);
            }}
        }});
    }}

    /* --- Install Prompt (Android Chrome "Adicionar à tela inicial") --- */
    window.parent.__safetyai_installPrompt = null;
    window.parent.addEventListener('beforeinstallprompt', function(e) {{
        e.preventDefault();
        window.parent.__safetyai_installPrompt = e;
        /* Expõe flag no sessionStorage para o Streamlit detectar via JS snippet */
        try {{ sessionStorage.setItem('safetyai_can_install', '1'); }} catch(_) {{}}
        console.info('[SafetyAI PWA] Install prompt disponível.');
    }});
    window.parent.addEventListener('appinstalled', function() {{
        window.parent.__safetyai_installPrompt = null;
        try {{ sessionStorage.removeItem('safetyai_can_install'); }} catch(_) {{}}
        console.info('[SafetyAI PWA] App instalado com sucesso!');
    }});

    /* --- Auto-expand sidebar em desktop (viewport > 1024px) --- */
    (function() {{
        if (window.parent.innerWidth <= 1024) return;
        setTimeout(function() {{
            var btn = doc.querySelector('[data-testid="collapsedControl"]');
            if (btn) {{ btn.click(); }}
        }}, 400);
    }})();

}})();
</script>
"""
    _PWA_CACHE[cache_key] = html
    return html


def get_pwa_install_button_html() -> str:
    """
    Retorna HTML para um botão 'Instalar app' que dispara o install prompt do Chrome/Android.
    Deve ser renderizado via st.markdown(..., unsafe_allow_html=True).
    Fica visível apenas quando o install prompt está disponível.
    """
    return """
<div id="pwa-install-wrapper" style="display:none; margin: 8px 0;">
    <button id="pwa-install-btn"
        onclick="
            var p = window.parent.__safetyai_installPrompt;
            if (p) { p.prompt(); p.userChoice.then(function(r){ if(r.outcome==='accepted') document.getElementById('pwa-install-wrapper').style.display='none'; }); }
        "
        style="
            background: linear-gradient(135deg, #4ADE80, #22D3EE);
            border: none; border-radius: 10px; color: #020617;
            font-weight: 700; padding: 10px 20px; font-size: 0.9rem;
            cursor: pointer; width: 100%; display: flex; align-items: center;
            justify-content: center; gap: 8px;
        ">
        📲 Instalar SafetyAI no dispositivo
    </button>
</div>
<script>
(function() {
    var wrapper = document.getElementById('pwa-install-wrapper');
    if (!wrapper) return;
    var canInstall = false;
    try { canInstall = sessionStorage.getItem('safetyai_can_install') === '1'; } catch(_) {}
    if (canInstall || window.parent.__safetyai_installPrompt) {
        wrapper.style.display = 'block';
    }
    window.parent.addEventListener('beforeinstallprompt', function() {
        wrapper.style.display = 'block';
    });
    window.parent.addEventListener('appinstalled', function() {
        wrapper.style.display = 'none';
    });
})();
</script>
"""
