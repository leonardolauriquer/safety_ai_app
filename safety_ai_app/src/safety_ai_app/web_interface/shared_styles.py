"""Shared CSS styles for clean, minimal page design."""

GLASS_PANEL_CSS = """
<style>
[data-testid="stVerticalBlock"] > div:has(.page-glass) {
    background: rgba(11,18,32,0.75);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(74,222,128,0.15);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.page-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
}
.page-header h1 {
    color: #4ADE80;
    font-size: 1.4em;
    font-weight: 600;
    margin: 0;
}
.page-header svg { color: #4ADE80; width: 26px; height: 26px; }
.page-subtitle {
    color: #64748B;
    font-size: 0.85em;
    margin-bottom: 16px;
}
.section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #4ADE80;
    font-size: 1em;
    font-weight: 500;
    margin: 16px 0 10px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(74,222,128,0.1);
}
.section-title svg { width: 18px; height: 18px; }
.result-card {
    background: rgba(15,23,42,0.5);
    border: 1px solid rgba(74,222,128,0.08);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 8px;
    transition: all 0.12s;
}
.result-card:hover {
    background: rgba(74,222,128,0.04);
    border-color: rgba(74,222,128,0.15);
}
.result-title {
    color: #E2E8F0;
    font-size: 0.95em;
    font-weight: 500;
    margin-bottom: 4px;
}
.result-code {
    color: #4ADE80;
    font-family: monospace;
    font-size: 0.88em;
}
.result-meta {
    color: #64748B;
    font-size: 0.78em;
    margin-top: 4px;
}
.result-detail {
    color: #94A3B8;
    font-size: 0.82em;
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid rgba(74,222,128,0.06);
}
.stats-line {
    color: #64748B;
    font-size: 0.8em;
    margin: 8px 0;
}
.stats-line b { color: #4ADE80; }
.empty-state {
    text-align: center;
    padding: 32px;
    color: #64748B;
    font-size: 0.9em;
}
.empty-state svg { opacity: 0.3; margin-bottom: 10px; }
.info-hint {
    background: rgba(34,211,238,0.08);
    border: 1px solid rgba(34,211,238,0.15);
    border-radius: 8px;
    padding: 10px 14px;
    color: #94A3B8;
    font-size: 0.82em;
    margin-top: 12px;
}
.info-hint b { color: #22D3EE; }
.badge-valid {
    background: linear-gradient(90deg, #166534, #15803D);
    color: #FFF;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.82em;
}
.badge-expired {
    background: linear-gradient(90deg, #991B1B, #B91C1C);
    color: #FFF;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.82em;
}
.badge-neutral {
    background: linear-gradient(90deg, #334155, #475569);
    color: #FFF;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.82em;
}
.detail-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 4px 0;
    color: #CBD5E1;
    font-size: 0.85em;
}
.detail-row svg { color: #4ADE80; width: 16px; height: 16px; flex-shrink: 0; margin-top: 2px; }
.detail-label {
    color: #64748B;
    min-width: 100px;
}
.detail-value {
    color: #E2E8F0;
}
.hierarchy-list {
    margin: 8px 0 0 20px;
    padding: 0;
    list-style: none;
    font-size: 0.82em;
    color: #94A3B8;
}
.hierarchy-list li {
    padding: 3px 0;
    border-left: 2px solid rgba(74,222,128,0.2);
    padding-left: 10px;
    margin-bottom: 2px;
}
.hierarchy-list li strong {
    color: #4ADE80;
}
/* === CNAE CARD === */
.cnae-card {
    background: rgba(15,23,42,0.5);
    border: 1px solid rgba(74,222,128,0.08);
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 8px;
    transition: all 0.12s;
}
.cnae-card:hover { background: rgba(74,222,128,0.04); border-color: rgba(74,222,128,0.15); }
.cnae-title { color: #E2E8F0; font-size: 0.92em; font-weight: 500; margin-bottom: 5px; }
.cnae-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
.cnae-code { color: #4ADE80; font-family: monospace; font-size: 0.85em; font-weight: 600; }
.cnae-level-badge {
    background: rgba(74,222,128,0.08);
    border: 1px solid rgba(74,222,128,0.15);
    border-radius: 4px;
    color: #4ADE80;
    font-size: 0.72em;
    padding: 1px 6px;
    font-weight: 500;
}
.risk-badge {
    border-radius: 4px;
    font-size: 0.72em;
    padding: 1px 7px;
    font-weight: 700;
    color: #0F172A;
}
.breadcrumb { color: #475569; font-size: 0.75em; margin-top: 5px; line-height: 1.5; }
.bc-part { color: #64748B; }
.bc-sep { color: #334155; margin: 0 3px; }
.act-list { margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(74,222,128,0.06); }
.act-item { color: #94A3B8; font-size: 0.78em; padding: 2px 0; }
.act-more { color: #475569; font-size: 0.75em; font-style: italic; }
/* === HUB CARD (Quick Queries, Sizing, etc.) === */
.hub-card {
    border-radius: 12px;
    padding: 18px 16px 48px 16px;
    position: relative;
    overflow: hidden;
    margin-bottom: 2px;
    transition: all 0.15s ease;
    min-height: 150px;
}
.hub-card:hover { transform: translateY(-1px); }
.hub-card-icon { margin-bottom: 10px; }
.hub-card-icon svg { width: 22px; height: 22px; }
.hub-card-title {
    font-size: 1.1em;
    font-weight: 700;
    margin-bottom: 2px;
}
.hub-card-label {
    color: #94A3B8;
    font-size: 0.72em;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
}
.hub-card-desc {
    color: #64748B;
    font-size: 0.79em;
    line-height: 1.45;
}
/* === BACK NAV BUTTON === */
.safetyai-back-btn {
    background: transparent !important;
    color: #64748B !important;
    border: 1px solid rgba(148,163,184,0.2) !important;
    box-shadow: none !important;
    font-size: 0.8em !important;
    padding: 5px 12px !important;
    min-height: 30px !important;
    font-weight: 400 !important;
    transform: none !important;
    letter-spacing: 0 !important;
}
.safetyai-back-btn:hover {
    color: #4ADE80 !important;
    border-color: rgba(74,222,128,0.35) !important;
    background: rgba(74,222,128,0.05) !important;
    box-shadow: none !important;
    transform: none !important;
}
</style>
"""

_BACK_BTN_JS = """
<script>
(function() {
    var doc = window.parent ? window.parent.document : document;
    function styleBackBtns() {
        doc.querySelectorAll('button').forEach(function(btn) {
            var txt = btn.innerText || btn.textContent || '';
            if (txt.trim().startsWith('←') || txt.trim().startsWith('\u2190')) {
                if (!btn.classList.contains('safetyai-back-btn')) {
                    btn.classList.add('safetyai-back-btn');
                }
            }
        });
    }
    styleBackBtns();
    setTimeout(styleBackBtns, 150);
    setTimeout(styleBackBtns, 500);
})();
</script>
"""


def inject_glass_styles():
    """Inject glass panel CSS into the page."""
    import streamlit as st
    st.markdown(GLASS_PANEL_CSS, unsafe_allow_html=True)


def glass_marker():
    """Returns HTML marker for glass panel CSS selector."""
    return '<div class="page-glass"></div>'


def render_back_button(label: str, target_page: str, key: str) -> None:
    """Renders a ghost-style back navigation button and injects JS to style it."""
    import streamlit as st
    if st.button(label, key=key):
        st.session_state.current_page = target_page
        st.rerun()
    st.markdown(_BACK_BTN_JS, unsafe_allow_html=True)
