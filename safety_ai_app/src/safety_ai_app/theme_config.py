"""Cyber-Neon Design System — SafetyAI public API.

Heavy content lives in dedicated modules:
  CSS  → web_interface/static/cyber_neon.css
  SVGs → web_interface/icons.py  (SVG_ICONS, ICON_ALIASES, get_icon)
  i18n → web_interface/i18n.py   (PHRASES)

All historical names are re-exported so existing imports keep working.
"""
import logging
import pathlib
from typing import Any, Dict

logger = logging.getLogger(__name__)

from safety_ai_app.web_interface.icons import (  # noqa: F401
    SVG_ICONS,
    ICON_ALIASES,
    get_icon,
)
from safety_ai_app.web_interface.i18n import PHRASES  # noqa: F401

THEME: Dict[str, Any] = {
    "colors": {
        "background_primary": "#020617",
        "background_secondary": "#0B1220",
        "background_surface": "#1E293B",
        "text_primary": "#F1F5F9",
        "text_secondary": "#94A3B8",
        "text_muted": "#64748B",
        "accent_green": "#4ADE80",
        "accent_green_hover": "#5EEAD4",
        "accent_green_shadow": "rgba(74, 222, 128, 0.4)",
        "accent_cyan": "#22D3EE",
        "accent_orange": "#F97316",
        "accent_purple": "#A855F7",
        "input_background": "#1E293B",
        "border_color": "rgba(148, 163, 184, 0.15)",
        "user_message_bg": "#4ADE80",
        "ai_message_bg": "rgba(15, 23, 42, 0.75)",
        "glass_bg": "rgba(15, 23, 42, 0.75)",
    },
    "fonts": {
        "display_family": "'Orbitron', sans-serif",
        "body_family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        "display_url": "https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&display=swap",
        "body_url": "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
    },
    "icons": ICON_ALIASES,
    "phrases": PHRASES,
    "images": {
        "login_background": "assets/login_background.jpg",
        "app_logo": "assets/app_logo.png",
        "page_icon": "assets/icon_logo.png",
    },
}

_CSS_FILE = pathlib.Path(__file__).parent / "web_interface" / "static" / "cyber_neon.css"


def _load_css() -> str:
    try:
        return f"<style>\n{_CSS_FILE.read_text(encoding='utf-8')}\n</style>"
    except FileNotFoundError:
        logger.error("cyber_neon.css not found at %s", _CSS_FILE)
        return ""


GLOBAL_STYLES: str = _load_css()


def inject_global_styles() -> None:
    """Inject the Cyber-Neon CSS into the current Streamlit page."""
    import streamlit as st
    st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)


def _get_material_icon_html(icon_key: str) -> str:
    """Legacy shim — delegates to get_icon()."""
    return get_icon(icon_key)


def _get_material_icon_html_for_button_css(button_key: str, icon_name: str) -> str:
    """Legacy shim — returns empty string (buttons use inline SVG now)."""
    return ""


def render_hero_section(title: str, subtitle: str = "", icon_key: str = "shield") -> str:
    """Render a glassmorphism hero banner."""
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    return (
        f'<div class="hero-section">'
        f'<div style="margin-bottom:16px">{get_icon(icon_key, "xl")}</div>'
        f"<h1>{title}</h1>{subtitle_html}</div>"
    )


def render_feature_card(icon_key: str, title: str, description: str) -> str:
    """Render a feature card with icon, title and description."""
    return (
        f'<div class="feature-card">'
        f'<div class="icon-container">{get_icon(icon_key)}</div>'
        f"<h3>{title}</h3><p>{description}</p></div>"
    )


def render_stat_card(value: str, label: str) -> str:
    """Render a statistics card."""
    return (
        f'<div class="stat-card">'
        f'<div class="stat-value">{value}</div>'
        f'<div class="stat-label">{label}</div></div>'
    )


def render_info_box(content: str, variant: str = "info") -> str:
    """Render a coloured info box. variant: 'info'|'success'|'warning'|'error'."""
    _icons = {"info": "info", "success": "check", "warning": "warning", "error": "x"}
    return (
        f'<div class="info-box {variant}">'
        f"{get_icon(_icons.get(variant, 'info'))}"
        f"<div>{content}</div></div>"
    )


def render_nav_item(icon_key: str, label: str, page_key: str, current_page: str) -> str:
    """Render a sidebar navigation item."""
    active = " active" if current_page == page_key else ""
    href = f"?page={page_key}&sync_done=true" if page_key != "sync_page" else f"?page={page_key}"
    return (
        f'<a href="{href}" class="nav-item{active}" target="_self">'
        f"{get_icon(icon_key)}<span>{label}</span></a>"
    )
