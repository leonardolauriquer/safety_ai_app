import streamlit as st
import logging
import feedparser
from datetime import datetime
from typing import List, Dict, Any, Optional
import pytz
import requests
import re
from safety_ai_app.web_interface.shared_styles import inject_glass_styles, glass_marker
from safety_ai_app.theme_config import _get_material_icon_html

logger = logging.getLogger(__name__)

RSS_FEED_URLS: List[str] = [
    "https://protecao.com.br/feed/",
    "https://revistacipa.com.br/category/noticias/feed/",
    "https://onsafety.com.br/blog/feed/",
    "https://segurancadotrabalhonwn.com/feed/",
]

NEWS_PER_PAGE = 20

CATEGORY_KEYWORDS_MAP: Dict[str, List[str]] = {
    "Acidentes": ["acidente", "incidente", "fatalidade", "morte", "lesão", "ocorrência"],
    "Combate ao Incêndio": ["combate a incêndio", "incêndio", "bombeiro", "brigada de incêndio", "extintor", "hidrante", "prevenção de incêndios", "segurança contra incêndio", "plano de emergência"],
    "Dicas": ["dica", "orientação", "guia", "melhores práticas"],
    "EPI": ["epi", "equipamento de proteção individual", "proteção"],
    "Eventos": ["evento", "congresso", "feira", "seminário", "webinar", "encontro"],
    "Fiscalização": ["fiscalização", "auditoria", "inspeção", "multa", "autuação"],
    "Legislação": ["legislação", "lei", "decreto", "portaria", "resolução", "jurídico"],
    "NBRs": ["nbr", "norma brasileira", "abnt"],
    "Normas Regulamentadoras": ["norma regulamentadora", "nr", "nrs", "legislação", "portaria"],
    "Saúde Mental": ["saúde mental", "psicossocial", "estresse", "burnout", "depressão", "ansiedade"],
    "Saúde Ocupacional": ["saúde ocupacional", "saúde do trabalhador", "pcmso", "aso", "ergonomia", "doença ocupacional"],
    "Treinamento": ["treinamento", "capacitação", "curso", "formação"],
}
CATEGORIES = sorted(list(CATEGORY_KEYWORDS_MAP.keys()))

@st.cache_data(ttl=3600)
def fetch_and_parse_feed(url: str) -> Optional[feedparser.FeedParserDict]:
    """
    Busca e analisa um feed RSS de uma URL específica.

    Args:
        url: A URL do feed RSS.

    Returns:
        Um objeto FeedParserDict contendo os dados do feed, ou None em caso de erro.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo:
            logger.warning(f"Erro ao analisar feed RSS de {url}: {feed.bozo_exception}")
            return None
        return feed
    except requests.exceptions.RequestException as e:
        logger.warning(f"Erro ao acessar feed RSS de {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar ou analisar feed RSS de {url}: {e}", exc_info=True)
        return None

@st.cache_data(ttl=3600)
def get_all_news_items() -> List[Dict[str, Any]]:
    """
    Busca e agrega notícias de todos os feeds RSS configurados.

    Returns:
        Uma lista de dicionários, onde cada dicionário representa uma notícia
        com 'title', 'link', 'published_date' e 'source'.
    """
    all_news: List[Dict[str, Any]] = []
    for url in RSS_FEED_URLS:
        feed = fetch_and_parse_feed(url)
        if feed and feed.entries:
            for entry in feed.entries:
                try:
                    published_date = None
                    if entry.get('published_parsed'):
                        published_date = datetime(*entry.published_parsed[:6], tzinfo=pytz.utc)
                    elif entry.get('published'):
                        try:
                            published_date = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=pytz.utc)
                        except ValueError:
                            try:
                                published_date = datetime.fromisoformat(entry.published)
                            except ValueError:
                                logger.warning(f"Não foi possível analisar a data '{entry.published}' do feed {url}.")
                                published_date = None
                    
                    if published_date and published_date.tzinfo is None:
                        published_date = pytz.utc.localize(published_date)

                    summary = entry.get('summary') or entry.get('description')
                    if summary:
                        summary = re.sub(r'<[^>]+>', '', summary)
                        if len(summary) > 200:
                            summary = summary[:197] + "..."
                    
                    all_news.append({
                        "title": entry.get('title', 'Título não disponível'),
                        "link": entry.get('link', '#'),
                        "published_date": published_date,
                        "source": feed.feed.get('title', url),
                        "summary": summary
                    })
                except Exception as e:
                    logger.error(f"Erro ao processar entrada do feed {url}: {e}", exc_info=True)
    
    all_news.sort(key=lambda x: x['published_date'] if x['published_date'] else datetime.min.replace(tzinfo=pytz.utc), reverse=True)
    return all_news

def render_page() -> None:
    """
    Renderiza a página do Feed de Notícias.
    """
    inject_glass_styles()
    
    with st.container():
        st.markdown(glass_marker(), unsafe_allow_html=True)
        
        # Compact header with icon
        icon_html = _get_material_icon_html("news")
        st.markdown(f'''
            <div class="page-header">
                {icon_html}
                <h1>Feed de Notícias</h1>
            </div>
            <p class="page-subtitle">Mantenha-se atualizado com as últimas notícias sobre Saúde e Segurança do Trabalho.</p>
        ''', unsafe_allow_html=True)

        if 'num_news_to_display' not in st.session_state:
            st.session_state.num_news_to_display = NEWS_PER_PAGE
        if 'selected_categories' not in st.session_state:
            st.session_state.selected_categories = []
        if 'search_query' not in st.session_state:
            st.session_state.search_query = ""

        with st.expander("Filtros e Busca", expanded=False):
            selected_categories = st.multiselect(
                "Filtrar por Categoria:",
                options=CATEGORIES,
                default=st.session_state.selected_categories,
                key="category_filter"
            )
            if selected_categories != st.session_state.selected_categories:
                st.session_state.selected_categories = selected_categories
                st.session_state.num_news_to_display = NEWS_PER_PAGE
                st.rerun()

            search_query = st.text_input(
                "Buscar por palavra-chave:",
                value=st.session_state.search_query,
                key="search_input"
            )
            if search_query != st.session_state.search_query:
                st.session_state.search_query = search_query
                st.session_state.num_news_to_display = NEWS_PER_PAGE
                st.rerun()
            
            if st.button("Limpar Filtros", key="clear_filters_button", use_container_width=True):
                st.session_state.selected_categories = []
                st.session_state.search_query = ""
                st.session_state.num_news_to_display = NEWS_PER_PAGE
                st.rerun()

        with st.spinner("Buscando e filtrando as últimas notícias..."):
            all_news_items = get_all_news_items()

        if not all_news_items:
            st.markdown('<div class="info-hint">Nenhuma notícia encontrada ou feeds RSS não configurados/acessíveis. Por favor, verifique sua conexão com a internet e os URLs dos feeds RSS.</div>', unsafe_allow_html=True)
            logger.info("Nenhuma notícia para exibir no Feed de Notícias.")
            return

        filtered_news_items = []
        for news in all_news_items:
            match_category = True
            if st.session_state.selected_categories:
                match_category = False
                for category in st.session_state.selected_categories:
                    for keyword in CATEGORY_KEYWORDS_MAP[category]:
                        if keyword.lower() in news['title'].lower() or \
                           (news['summary'] and keyword.lower() in news['summary'].lower()):
                            match_category = True
                            break
                    if match_category:
                        break
            
            match_search = True
            if st.session_state.search_query:
                search_term = st.session_state.search_query.lower()
                if not (search_term in news['title'].lower() or \
                        (news['summary'] and search_term in news['summary'].lower())):
                    match_search = False
            
            if match_category and match_search:
                filtered_news_items.append(news)

        if not filtered_news_items:
            st.markdown('<div class="info-hint">Nenhuma notícia encontrada com os filtros e busca aplicados. Tente ajustar suas opções.</div>', unsafe_allow_html=True)
            return

        # Stats Line
        st.markdown(f'<div class="stats-line">Mostrando <b>{min(st.session_state.num_news_to_display, len(filtered_news_items))}</b> de <b>{len(filtered_news_items)}</b> notícias encontradas.</div>', unsafe_allow_html=True)

        news_for_display = filtered_news_items[: st.session_state.num_news_to_display]

        for news in news_for_display:
            pub_date = news['published_date'].strftime('%d/%m/%Y %H:%M') if news['published_date'] else 'Data desconhecida'
            summary_text = news['summary'] if news['summary'] else 'Clique para ler mais...'
            
            st.markdown(f'''
                <div class="result-card">
                    <div class="result-title">
                        <a href="{news['link']}" target="_blank" style="text-decoration: none; color: inherit;">{news['title']}</a>
                    </div>
                    <div class="result-meta">
                        {pub_date} • Fonte: {news['source']}
                    </div>
                    <div class="result-detail">
                        {summary_text}
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        
        if st.session_state.num_news_to_display < len(filtered_news_items):
            if st.button("Carregar mais notícias", key="load_more_news_button", use_container_width=True):
                st.session_state.num_news_to_display += NEWS_PER_PAGE
                st.rerun()
        elif len(filtered_news_items) > 0:
            st.markdown('<div class="info-hint">Todas as notícias filtradas foram carregadas.</div>', unsafe_allow_html=True)

        logger.info(f"Página Feed de Notícias renderizada with {len(news_for_display)} notícias. Total de notícias filtradas: {len(filtered_news_items)}.")
