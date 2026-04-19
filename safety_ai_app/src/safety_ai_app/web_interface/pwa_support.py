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
        "icons": icons,
    }
    return json.dumps(manifest, ensure_ascii=False)


def _load_apple_touch_icon_b64(project_root: str) -> str:
    path = os.path.join(project_root, "assets", "pwa", "icon-180.png")
    return _load_icon_b64(path)


def get_pwa_injection_html(project_root: str) -> str:
    """
    Returns an HTML snippet containing a <script> block that injects PWA
    meta tags and a web-app manifest into the parent document's <head>.

    Safe to call on every Streamlit re-render — the script checks for
    existing tags before inserting to avoid duplicates.
    """
    cache_key = "pwa_html"
    if cache_key in _PWA_CACHE:
        return _PWA_CACHE[cache_key]

    manifest_json = _build_manifest(project_root)
    apple_icon_b64 = _load_apple_touch_icon_b64(project_root)
    apple_icon_data_url = f"data:image/png;base64,{apple_icon_b64}" if apple_icon_b64 else ""

    manifest_json_js = manifest_json.replace("\\", "\\\\").replace("`", "\\`")

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

    /* --- Android / Chrome --- */
    addMeta('theme-color', '{_THEME_COLOR}');
    addMeta('mobile-web-app-capable', 'yes');

    /* --- iOS / Safari --- */
    addMeta('apple-mobile-web-app-capable', 'yes');
    addMeta('apple-mobile-web-app-status-bar-style', 'black-translucent');
    addMeta('apple-mobile-web-app-title', '{_APP_SHORT_NAME}');
    addMeta('format-detection', 'telephone=no');
    {apple_touch_js}
    /* --- Web App Manifest --- */
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
}})();
</script>
"""
    _PWA_CACHE[cache_key] = html
    return html
