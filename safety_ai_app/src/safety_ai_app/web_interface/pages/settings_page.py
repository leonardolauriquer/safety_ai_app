import streamlit as st
import logging
import json
import copy
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from safety_ai_app.theme_config import get_icon, render_hero_section, _get_material_icon_html
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker

logger = logging.getLogger(__name__)


def _alert(msg: str, kind: str = "info") -> None:
    _CFG = {
        "error":   {"bg": "rgba(239,68,68,0.12)",  "border": "#EF4444", "color": "#FCA5A5", "icon": "error"},
        "warning": {"bg": "rgba(245,158,11,0.12)", "border": "#F59E0B", "color": "#FCD34D", "icon": "warning"},
        "info":    {"bg": "rgba(34,211,238,0.12)",  "border": "#22D3EE", "color": "#67E8F9", "icon": "info"},
        "success": {"bg": "rgba(74,222,128,0.12)", "border": "#4ADE80", "color": "#86EFAC", "icon": "check_circle"},
    }
    c = _CFG.get(kind, _CFG["info"])
    st.markdown(
        f'<div style="background:{c["bg"]};border-left:3px solid {c["border"]};'
        f'padding:0.5rem 0.75rem;border-radius:6px;margin:0.25rem 0;'
        f'color:{c["color"]};font-size:0.85rem;">'
        f'{_get_material_icon_html(c["icon"])} {msg}</div>',
        unsafe_allow_html=True,
    )


DEFAULT_SETTINGS = {
    "accessibility": {
        "font_size": "medium",
        "high_contrast": False,
        "reading_mode": False,
        "keyboard_shortcuts": True
    },
    "theme": {
        "mode": "dark",
        "accent_color": "#4ADE80",
        "interface_density": "comfortable"
    },
    "subscription": {
        "plan": "premium",
        "start_date": "2024-01-01",
        "end_date": "2025-12-31",
        "status": "active",
        "auto_renewal": True
    },
    "general": {
        "language": "pt-BR",
        "notifications": True,
        "cache_enabled": True,
        "analytics": True
    },
    "admin": {
        "auto_sync_interval_minutes": 30
    }
}

VALID_SYNC_INTERVALS = [15, 30, 60, 120]


def load_user_settings() -> Dict[str, Any]:
    try:
        settings_file = Path("user_settings.json")
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
                settings = copy.deepcopy(DEFAULT_SETTINGS)
                for category, values in user_settings.items():
                    if category in settings:
                        settings[category].update(values)
                return settings
        return copy.deepcopy(DEFAULT_SETTINGS)
    except Exception as e:
        logger.error(f"Erro ao carregar configuracoes: {e}")
        return copy.deepcopy(DEFAULT_SETTINGS)


def save_user_settings(settings: Dict[str, Any]) -> bool:
    try:
        settings_file = Path("user_settings.json")
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar configuracoes: {e}")
        return False


def get_subscription_status(settings: Dict[str, Any]) -> Dict[str, Any]:
    try:
        sub = settings["subscription"]
        end_date = datetime.strptime(sub["end_date"], "%Y-%m-%d")
        today = datetime.now()
        days_remaining = (end_date - today).days
        
        if days_remaining < 0:
            return {
                "status": "expired",
                "text": "Expirada",
                "icon": "x",
                "color": "#EF4444",
                "days_remaining": 0,
                "end_date": end_date.strftime("%d/%m/%Y")
            }
        elif days_remaining <= 30:
            return {
                "status": "expiring",
                "text": f"Expira em {days_remaining} dias",
                "icon": "warning",
                "color": "#F97316",
                "days_remaining": days_remaining,
                "end_date": end_date.strftime("%d/%m/%Y")
            }
        else:
            return {
                "status": "active",
                "text": f"Ativa - {days_remaining} dias restantes",
                "icon": "check",
                "color": "#4ADE80",
                "days_remaining": days_remaining,
                "end_date": end_date.strftime("%d/%m/%Y")
            }
    except Exception as e:
        logger.error(f"Erro ao calcular status: {e}")
        return {
            "status": "error",
            "text": "Erro ao verificar",
            "icon": "warning",
            "color": "#EF4444",
            "days_remaining": 0,
            "end_date": "N/A"
        }


def render_settings_card(title: str, icon_key: str) -> str:
    return f"""
    <div class="neo-card" style="margin-bottom: 20px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid var(--border-subtle);">
            <span style="color: var(--neon-green);">{get_icon(icon_key)}</span>
            <h3 style="font-family: var(--font-display); color: var(--neon-green); margin: 0; font-size: 1.2rem;">{title}</h3>
        </div>
    </div>
    """


def render_accessibility_section(settings: Dict[str, Any]) -> Dict[str, Any]:
    accessibility = copy.deepcopy(settings["accessibility"])
    
    st.markdown(render_settings_card("Acessibilidade", "user"), unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        font_options = {"small": "Pequeno", "medium": "Médio", "large": "Grande"}
        font_size = st.selectbox(
            "Tamanho da Fonte",
            options=list(font_options.keys()),
            index=list(font_options.keys()).index(accessibility.get("font_size", "medium")),
            format_func=lambda x: font_options[x],
            key="settings_font_size"
        )
        accessibility["font_size"] = font_size
        
        accessibility["high_contrast"] = st.toggle(
            "Alto Contraste",
            value=accessibility.get("high_contrast", False),
            help="Aumenta o contraste para melhor legibilidade",
            key="settings_high_contrast"
        )
    
    with col2:
        accessibility["reading_mode"] = st.toggle(
            "Modo de Leitura",
            value=accessibility.get("reading_mode", False),
            help="Interface simplificada para foco na leitura",
            key="settings_reading_mode"
        )
        
        accessibility["keyboard_shortcuts"] = st.toggle(
            "Atalhos de Teclado",
            value=accessibility.get("keyboard_shortcuts", True),
            help="Navegação rápida por teclado",
            key="settings_keyboard"
        )
    
    if accessibility["keyboard_shortcuts"]:
        with st.expander("Ver Atalhos Disponíveis"):
            st.markdown("""
            | Atalho | Ação |
            |--------|------|
            | `Ctrl + /` | Abrir/fechar menu lateral |
            | `Ctrl + Enter` | Enviar mensagem no chat |
            | `Esc` | Cancelar ação atual |
            | `Tab` | Navegar entre elementos |
            | `F1` | Abrir ajuda |
            """)
    
    return accessibility


def render_theme_section(settings: Dict[str, Any]) -> Dict[str, Any]:
    theme = copy.deepcopy(settings["theme"])
    
    st.markdown(render_settings_card("Tema e Aparência", "sparkles"), unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        mode_options = {"dark": "Escuro", "light": "Claro"}
        mode = st.selectbox(
            "Modo do Tema",
            options=list(mode_options.keys()),
            index=list(mode_options.keys()).index(theme.get("mode", "dark")),
            format_func=lambda x: mode_options[x],
            key="settings_theme_mode"
        )
        theme["mode"] = mode
        
        density_options = {
            "compact": "Compacta",
            "comfortable": "Confortável",
            "spacious": "Espaçosa"
        }
        density = st.selectbox(
            "Densidade da Interface",
            options=list(density_options.keys()),
            index=list(density_options.keys()).index(theme.get("interface_density", "comfortable")),
            format_func=lambda x: density_options[x],
            key="settings_density"
        )
        theme["interface_density"] = density
    
    with col2:
        st.markdown("**Intensidade do Verde Neon**")
        
        color_options = {
            "#4ADE80": "Verde Neon (Padrão)",
            "#22C55E": "Verde Esmeralda",
            "#16A34A": "Verde Floresta",
            "#15803D": "Verde Escuro"
        }
        
        current_color = theme.get("accent_color", "#4ADE80")
        if current_color not in color_options:
            current_color = "#4ADE80"
        
        selected_color = st.radio(
            "Escolha a intensidade",
            options=list(color_options.keys()),
            index=list(color_options.keys()).index(current_color),
            format_func=lambda x: color_options[x],
            key="settings_accent_color",
            horizontal=False
        )
        theme["accent_color"] = selected_color
        
        st.markdown(f"""
        <div style="
            width: 100%;
            height: 40px;
            background: linear-gradient(135deg, {selected_color} 0%, {selected_color}88 100%);
            border-radius: var(--radius-md);
            margin-top: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #000000;
            font-weight: 600;
            box-shadow: 0 0 20px {selected_color}40;
        ">Preview da Cor</div>
        """, unsafe_allow_html=True)
    
    return theme


def render_subscription_section(settings: Dict[str, Any]) -> Dict[str, Any]:
    subscription = copy.deepcopy(settings["subscription"])
    status_info = get_subscription_status(settings)
    
    st.markdown(render_settings_card("Assinatura", "trophy"), unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="neo-card glow" style="text-align: center; padding: 30px;">
        <div style="margin-bottom: 16px; color: {status_info['color']};">
            {get_icon(status_info['icon'], 'xl')}
        </div>
        <p style="font-family: var(--font-display); font-size: 1.4em; color: {status_info['color']}; margin: 0 0 8px 0;">
            {status_info['text']}
        </p>
        <p style="color: var(--text-muted); margin: 0 0 16px 0;">
            Vencimento: <strong style="color: var(--text-primary);">{status_info['end_date']}</strong>
        </p>
        <span style="
            display: inline-block;
            background: linear-gradient(135deg, #4ADE80 0%, #22C55E 100%);
            color: #000000;
            padding: 8px 20px;
            border-radius: var(--radius-full);
            font-weight: 700;
            font-size: 0.9em;
        ">✨ {subscription['plan'].upper()}</span>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f'<div class="section-title">{_get_material_icon_html("receipt_long")} Detalhes do Plano</div>', unsafe_allow_html=True)
        start_date = datetime.strptime(subscription['start_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
        st.markdown(f"""
        - **Plano:** {subscription['plan'].title()}
        - **Início:** {start_date}
        - **Término:** {status_info['end_date']}
        """)
    
    with col2:
        st.markdown(f'<div class="section-title">{_get_material_icon_html("verified")} Benefícios Inclusos</div>', unsafe_allow_html=True)
        st.markdown("""
        - ✅ Chat ilimitado com IA
        - ✅ Biblioteca completa de NRs
        - ✅ Geração de documentos
        - ✅ Consultas rápidas
        """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Renovar", use_container_width=True, type="primary"):
            st.session_state.show_renewal = True
    
    with col2:
        subscription["auto_renewal"] = st.toggle(
            "Renovacao Automatica",
            value=subscription.get("auto_renewal", True),
            key="settings_auto_renewal"
        )
    
    with col3:
        if st.button("Cancelar Plano", use_container_width=True, key="cancel_plan_btn"):
            st.session_state.show_cancel = True
    
    if st.session_state.get("show_renewal", False):
        with st.container():
            st.markdown(f'<div class="section-title">{_get_material_icon_html("autorenew")} Renovar Assinatura</div>', unsafe_allow_html=True)
            
            period = st.selectbox(
                "Período de renovação:",
                options=["1_month", "3_months", "6_months", "12_months"],
                format_func=lambda x: {
                    "1_month": "1 mês - R$ 29,90",
                    "3_months": "3 meses - R$ 79,90 (11% off)",
                    "6_months": "6 meses - R$ 149,90 (16% off)",
                    "12_months": "12 meses - R$ 279,90 (22% off)"
                }[x],
                key="renewal_period"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Confirmar", use_container_width=True, type="primary"):
                    _alert("Renovação processada com sucesso!", "success")
                    st.session_state.show_renewal = False
            with col2:
                if st.button("Voltar", use_container_width=True, key="cancel_renewal"):
                    st.session_state.show_renewal = False
                    st.rerun()
    
    if st.session_state.get("show_cancel", False):
        with st.container():
            st.markdown(f'<div class="section-title">{_get_material_icon_html("cancel")} Cancelar Assinatura</div>', unsafe_allow_html=True)
            _alert("Ao cancelar, você perderá acesso aos recursos premium.", "warning")
            
            confirm = st.checkbox("Confirmo que desejo cancelar a assinatura", key="confirm_cancel")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Confirmar Cancelamento", disabled=not confirm, use_container_width=True):
                    _alert("Assinatura cancelada.", "error")
                    st.session_state.show_cancel = False
            with col2:
                if st.button("Manter Assinatura", use_container_width=True, type="primary"):
                    st.session_state.show_cancel = False
                    st.rerun()
    
    return subscription


def render_general_section(settings: Dict[str, Any]) -> Dict[str, Any]:
    general = copy.deepcopy(settings["general"])
    
    st.markdown(render_settings_card("Configurações Gerais", "settings"), unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        language_options = {
            "pt-BR": "Português (Brasil)",
            "en-US": "English (US)",
            "es-ES": "Español"
        }
        language = st.selectbox(
            "Idioma",
            options=list(language_options.keys()),
            index=list(language_options.keys()).index(general.get("language", "pt-BR")),
            format_func=lambda x: language_options[x],
            key="settings_language"
        )
        general["language"] = language
        
        general["notifications"] = st.toggle(
            "Notificações",
            value=general.get("notifications", True),
            help="Receber avisos sobre atualizações",
            key="settings_notifications"
        )
    
    with col2:
        general["cache_enabled"] = st.toggle(
            "Cache Habilitado",
            value=general.get("cache_enabled", True),
            help="Melhora performance armazenando dados",
            key="settings_cache"
        )
        
        general["analytics"] = st.toggle(
            "Permitir Analytics",
            value=general.get("analytics", True),
            help="Dados anônimos para melhorar o app",
            key="settings_analytics"
        )
    
    st.markdown('<div class="section-title">Gerenciar Dados</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        config_json = json.dumps(settings, indent=2, ensure_ascii=False)
        st.download_button(
            "Exportar Config",
            data=config_json,
            file_name=f"safety_ai_config_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        uploaded = st.file_uploader(
            "Importar",
            type="json",
            label_visibility="collapsed",
            key="import_config"
        )
        if uploaded:
            try:
                imported = json.load(uploaded)
                if st.button("Aplicar", use_container_width=True):
                    if save_user_settings(imported):
                        st.session_state.user_settings = load_user_settings()
                        _alert("Configurações importadas com sucesso!", "success")
                        st.rerun()
            except Exception as e:
                _alert(f"Arquivo inválido: {e}", "error")

    with col3:
        if st.button("Limpar Cache", use_container_width=True):
            st.cache_data.clear()
            _alert("Cache limpo com sucesso!", "success")
    
    return general


def render_admin_section(settings: Dict[str, Any]) -> Dict[str, Any]:
    admin = copy.deepcopy(settings.get("admin", DEFAULT_SETTINGS["admin"]))

    st.markdown(render_settings_card("Administração", "settings"), unsafe_allow_html=True)

    st.markdown(f'<div class="section-title">{_get_material_icon_html("sync")} Sincronização Automática da Base de Conhecimento</div>', unsafe_allow_html=True)

    current_interval = admin.get("auto_sync_interval_minutes", 30)
    if current_interval not in VALID_SYNC_INTERVALS:
        current_interval = 30

    interval_labels = {
        15: "15 minutos",
        30: "30 minutos",
        60: "60 minutos (1 hora)",
        120: "120 minutos (2 horas)",
    }

    selected_interval = st.selectbox(
        "Intervalo de Auto-Sincronização",
        options=VALID_SYNC_INTERVALS,
        index=VALID_SYNC_INTERVALS.index(current_interval),
        format_func=lambda x: interval_labels[x],
        help="Define com que frequência a base de conhecimento é sincronizada automaticamente com o Google Drive.",
        key="settings_auto_sync_interval",
    )
    admin["auto_sync_interval_minutes"] = selected_interval

    try:
        from safety_ai_app.auto_sync_scheduler import get_scheduler
        scheduler = get_scheduler()
        status = scheduler.get_status()
        next_run = status.get("next_run_time")
        live_interval = status.get("interval_minutes", "—")
        st.markdown(
            f"**Intervalo atual do agendador:** {live_interval} min"
            + (f" · **Próxima execução:** {next_run.strftime('%d/%m/%Y %H:%M:%S')}" if next_run else ""),
        )
    except Exception:
        pass

    return admin


def _apply_admin_settings(admin: Dict[str, Any]) -> None:
    """Push admin settings values into any live runtime objects."""
    try:
        from safety_ai_app.auto_sync_scheduler import get_scheduler
        scheduler = get_scheduler()
        new_interval = int(admin.get("auto_sync_interval_minutes", 30))
        if scheduler.interval_minutes != new_interval:
            scheduler.update_interval(new_interval)
    except Exception as exc:
        logger.error("Erro ao aplicar configurações de administração: %s", exc)


def render_page() -> None:
    inject_glass_styles()

    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        st.markdown(f'''
        <div class="page-header">
            {_get_material_icon_html('settings')}
            <h1>Configurações</h1>
        </div>
        <div class="page-subtitle">Personalize sua experiência no Safety AI</div>
        ''', unsafe_allow_html=True)
    
    if "user_settings" not in st.session_state:
        st.session_state.user_settings = load_user_settings()
    
    if "show_renewal" not in st.session_state:
        st.session_state.show_renewal = False
    if "show_cancel" not in st.session_state:
        st.session_state.show_cancel = False
    
    settings = copy.deepcopy(st.session_state.user_settings)
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Acessibilidade",
        "Tema",
        "Assinatura",
        "Geral",
        "Administração",
    ])

    with tab1:
        settings["accessibility"] = render_accessibility_section(settings)

    with tab2:
        settings["theme"] = render_theme_section(settings)

    with tab3:
        settings["subscription"] = render_subscription_section(settings)

    with tab4:
        settings["general"] = render_general_section(settings)

    with tab5:
        settings["admin"] = render_admin_section(settings)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Salvar Configurações", type="primary", use_container_width=True):
            if save_user_settings(settings):
                st.session_state.user_settings = settings
                _apply_admin_settings(settings.get("admin", {}))
                _alert("Configurações salvas com sucesso!", "success")
                st.rerun()
            else:
                _alert("Erro ao salvar as configurações. Tente novamente.", "error")

    with col2:
        if st.button("Restaurar Padrões", use_container_width=True, key="restore_defaults_btn"):
            if st.session_state.get("confirm_reset"):
                st.session_state.user_settings = copy.deepcopy(DEFAULT_SETTINGS)
                save_user_settings(DEFAULT_SETTINGS)
                _alert("Configurações restauradas para o padrão!", "success")
                st.session_state.confirm_reset = False
                st.rerun()
            else:
                st.session_state.confirm_reset = True
                _alert("Clique novamente para confirmar a restauração.", "warning")

    with col3:
        if st.button("Cancelar", use_container_width=True, key="cancel_changes_btn"):
            st.session_state.user_settings = load_user_settings()
            _alert("Alterações canceladas.", "info")
            st.rerun()
    
    st.markdown(f"""
    <div class="neo-card" style="margin-top: 30px;">
        <div style="display: flex; gap: 40px; flex-wrap: wrap;">
            <div>
                <h4 style="color: #4ADE80; margin: 0 0 12px 0; display: flex; align-items: center; gap: 8px;">
                    {get_icon('info')} Sobre
                </h4>
                <p style="color: var(--text-muted); margin: 6px 0; font-size: 0.9em;">Configurações salvas localmente</p>
                <p style="color: var(--text-muted); margin: 6px 0; font-size: 0.9em;">Backup recomendado periodicamente</p>
            </div>
            <div>
                <h4 style="color: #22C55E; margin: 0 0 12px 0; display: flex; align-items: center; gap: 8px;">
                    {get_icon('chat')} Suporte
                </h4>
                <p style="color: var(--text-muted); margin: 6px 0; font-size: 0.9em;">safety.ai.app@gmail.com</p>
                <p style="color: var(--text-muted); margin: 6px 0; font-size: 0.9em;">(51) 98289-0205</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
