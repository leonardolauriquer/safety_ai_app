import streamlit as st
import logging
import time
from typing import Dict, Any, List

from safety_ai_app.theme_config import THEME, _get_material_icon_html
from safety_ai_app.web_interface.shared_styles import inject_glass_styles
from safety_ai_app.google_drive_integrator import (
    get_service_account_drive_integrator_instance,
    get_file_bytes_for_download,
    get_download_metadata,
)

logger = logging.getLogger(__name__)

MIME_DISPLAY = {
    'application/pdf': 'PDF',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
    'application/msword': 'DOC',
    'text/plain': 'TXT',
    'application/vnd.google-apps.document': 'Docs',
    'application/vnd.google-apps.spreadsheet': 'Sheets',
    'application/vnd.google-apps.presentation': 'Slides',
    'application/vnd.google-apps.folder': 'Pasta',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
    'application/vnd.ms-excel': 'XLS',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PPTX',
    'application/vnd.ms-powerpoint': 'PPT',
    'image/jpeg': 'JPEG',
    'image/png': 'PNG',
    'default': 'Arquivo'
}

CATEGORIES = {
    "Todos": None,
    "PDF": ['application/pdf'],
    "Docs": ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword', 'text/plain', 'application/vnd.google-apps.document'],
    "Planilhas": ['application/vnd.google-apps.spreadsheet', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'],
    "Slides": ['application/vnd.google-apps.presentation', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/vnd.ms-powerpoint'],
}


def format_size(size_bytes) -> str:
    if not size_bytes:
        return ""
    try:
        s = int(size_bytes)
        if s < 1024: return f"{s}B"
        if s < 1024**2: return f"{s/1024:.0f}KB"
        if s < 1024**3: return f"{s/(1024**2):.1f}MB"
        return f"{s/(1024**3):.1f}GB"
    except:
        return ""


def get_files(drive, folder_id: str) -> List[Dict]:
    try:
        files = []
        token = None
        while True:
            r = drive.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                pageSize=1000, pageToken=token,
                fields="nextPageToken, files(id, name, mimeType, size)"
            ).execute()
            files.extend(r.get('files', []))
            token = r.get('nextPageToken')
            if not token: break
        return files
    except Exception as e:
        logger.error(f"Drive error: {e}")
        return []


def download(drive, fid: str, mime: str, exp: str):
    for i in range(3):
        try:
            data = get_file_bytes_for_download(drive, fid, mime, exp)
            if data: return data
            raise Exception("Não disponível")
        except Exception as e:
            if i == 2: raise
            time.sleep(0.5)
    raise Exception("Falha")


def render_page() -> None:
    inject_glass_styles()
    st.markdown("""
    <style>
    .lib-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 4px;
    }
    .lib-header h2 {
        color: #4ADE80;
        font-size: 1.3em;
        font-weight: 600;
        margin: 0;
    }
    .lib-header svg { color: #4ADE80; width: 22px; height: 22px; }
    .lib-path {
        color: #64748B;
        font-size: 0.82em;
        margin-bottom: 14px;
    }
    .lib-stats {
        color: #64748B;
        font-size: 0.78em;
        margin: 10px 0;
    }
    .lib-stats b { color: #4ADE80; }
    .file-row {
        display: flex;
        align-items: center;
        padding: 8px 12px;
        background: rgba(15,23,42,0.4);
        border: 1px solid rgba(74,222,128,0.06);
        border-radius: 8px;
        margin-bottom: 4px;
        transition: all 0.12s;
    }
    .file-row:hover {
        background: rgba(74,222,128,0.05);
        border-color: rgba(74,222,128,0.18);
    }
    .f-icon {
        width: 32px; height: 32px;
        display: flex; align-items: center; justify-content: center;
        background: rgba(74,222,128,0.1);
        border-radius: 6px;
        margin-right: 10px;
        flex-shrink: 0;
    }
    .f-icon svg { width: 16px; height: 16px; color: #4ADE80; }
    .f-icon.fld { background: rgba(34,211,238,0.1); }
    .f-icon.fld svg { color: #22D3EE; }
    .f-name {
        flex: 1;
        color: #E2E8F0;
        font-size: 0.88em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .f-meta {
        color: #64748B;
        font-size: 0.72em;
        margin-left: 10px;
        white-space: nowrap;
    }
    .empty-box {
        text-align: center;
        padding: 28px;
        color: #64748B;
        font-size: 0.9em;
    }
    .empty-box svg { opacity: 0.3; margin-bottom: 8px; }
    .pg-bar {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        margin-top: 14px;
        padding-top: 10px;
        border-top: 1px solid rgba(74,222,128,0.08);
        color: #64748B;
        font-size: 0.8em;
    }
    </style>
    """, unsafe_allow_html=True)
    
    folder_svg = _get_material_icon_html("folder")
    file_svg = _get_material_icon_html("file")
    lib_svg = _get_material_icon_html("library")
    
    drive = st.session_state.get("app_drive_service")
    if not drive:
        st.warning("Google Drive não disponível.")
        return
    
    integrator = get_service_account_drive_integrator_instance()
    if not integrator:
        st.error("Erro ao conectar.")
        return
    
    root_id = integrator._get_library_folder_id()
    if not root_id:
        st.error("Pasta Biblioteca não encontrada.")
        return
    
    if 'lib_path' not in st.session_state:
        st.session_state.lib_path = []
    
    path = st.session_state.lib_path
    current_id = path[-1]['id'] if path else root_id
    path_text = " / ".join(["Biblioteca"] + [p['name'] for p in path])
    title = path[-1]['name'] if path else "Biblioteca"
    
    with st.container():
        st.markdown(f'''
        <div class="page-header">
            {lib_svg}
            <h1>{title}</h1>
        </div>
        <div class="page-subtitle">{path_text}</div>
        ''', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([0.12, 0.22, 0.66])
        with c1:
            if path and st.button("←", help="Voltar", use_container_width=True):
                st.session_state.lib_path = path[:-1]
                st.session_state.pop('lib_pg', None)
                st.rerun()
        with c2:
            cat = st.selectbox("Tipo", list(CATEGORIES.keys()), label_visibility="collapsed")
        with c3:
            search = st.text_input("Buscar", placeholder="Buscar...", label_visibility="collapsed")
        
        with st.spinner(""):
            items = get_files(drive, current_id)
        
        folders = sorted([f for f in items if f['mimeType'] == 'application/vnd.google-apps.folder'], key=lambda x: x['name'].lower())
        files = sorted([f for f in items if f['mimeType'] != 'application/vnd.google-apps.folder'], key=lambda x: x['name'].lower())
        
        if search:
            q = search.lower()
            folders = [f for f in folders if q in f['name'].lower()]
            files = [f for f in files if q in f['name'].lower()]
        
        if cat != "Todos" and CATEGORIES[cat]:
            files = [f for f in files if f['mimeType'] in CATEGORIES[cat]]
        
        all_items = folders + files
        per_page = 18
        total = len(all_items)
        pages = max(1, (total + per_page - 1) // per_page)
        
        if 'lib_pg' not in st.session_state:
            st.session_state.lib_pg = 1
        pg = min(st.session_state.lib_pg, pages)
        
        visible = all_items[(pg-1)*per_page : pg*per_page]
        
        st.markdown(f'<div class="lib-stats"><b>{len(folders)}</b> pastas, <b>{len(files)}</b> arquivos</div>', unsafe_allow_html=True)
        
        if not visible:
            st.markdown(f'<div class="empty-box">{folder_svg}<br>Nenhum item</div>', unsafe_allow_html=True)
        else:
            for item in visible:
                is_fld = item['mimeType'] == 'application/vnd.google-apps.folder'
                ftype = MIME_DISPLAY.get(item['mimeType'], 'Arquivo')
                size = format_size(item.get('size'))
                meta = ftype if is_fld else (f"{ftype} • {size}" if size else ftype)
                icon = folder_svg if is_fld else file_svg
                icls = "fld" if is_fld else ""
                
                cols = st.columns([0.88, 0.12])
                with cols[0]:
                    st.markdown(f'''
                    <div class="file-row">
                        <div class="f-icon {icls}">{icon}</div>
                        <div class="f-name">{item["name"]}</div>
                        <div class="f-meta">{meta}</div>
                    </div>
                    ''', unsafe_allow_html=True)
                
                with cols[1]:
                    if is_fld:
                        if st.button("→", key=f"o_{item['id']}", help="Abrir pasta", use_container_width=True):
                            st.session_state.lib_path.append({'id': item['id'], 'name': item['name']})
                            st.session_state.pop('lib_pg', None)
                            st.rerun()
                    else:
                        fname, exp = get_download_metadata(item['name'], item['mimeType'])
                        if fname:
                            rk = f"r_{item['id']}"
                            if rk in st.session_state and time.time() - st.session_state[rk].get('t', 0) < 300:
                                d = st.session_state[rk]
                                st.download_button("↓", d['b'], d['n'], d['m'], key=f"s_{item['id']}", help="Salvar", use_container_width=True)
                            else:
                                if st.button("↓", key=f"d_{item['id']}", help="Baixar", use_container_width=True):
                                    try:
                                        data = download(drive, item['id'], item['mimeType'], exp)
                                        st.session_state[rk] = {'b': data, 'n': fname, 'm': exp, 't': time.time()}
                                        st.rerun()
                                    except Exception as e:
                                        st.error(str(e))
        
        if pages > 1:
            p1, p2, p3 = st.columns([0.3, 0.4, 0.3])
            with p1:
                if st.button("←", key="pv", disabled=pg==1, use_container_width=True):
                    st.session_state.lib_pg = pg - 1
                    st.rerun()
            with p2:
                st.markdown(f"<div style='text-align:center;color:#64748B;padding:6px'>{pg}/{pages}</div>", unsafe_allow_html=True)
            with p3:
                if st.button("→", key="nx", disabled=pg==pages, use_container_width=True):
                    st.session_state.lib_pg = pg + 1
                    st.rerun()
