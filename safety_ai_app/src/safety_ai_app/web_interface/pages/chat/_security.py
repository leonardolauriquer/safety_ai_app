"""
Módulo de Segurança e Sanitização — SafetyAI Chat
Responsabilidade: Validar entradas, sanitizar HTML e processar Markdown seguro.
"""

import re
import html
import logging
import markdown

logger = logging.getLogger(__name__)

ALLOWED_TAGS = frozenset({
    'p', 'br', 'strong', 'em', 'b', 'i', 'u', 'code', 'pre', 'blockquote', 
    'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'table', 
    'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'span', 'div', 'sup', 'sub', 'del', 's'
})

ALLOWED_ATTRS = frozenset({'href', 'target', 'rel', 'class', 'id', 'colspan', 'rowspan'})
DANGEROUS_URL_SCHEMES = ('javascript', 'vbscript', 'data', 'file', 'blob')

def _decode_html_entities(text: str) -> str:
    decoded = html.unescape(text)
    decoded = re.sub(r'%([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), decoded)
    decoded = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), decoded)
    decoded = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), decoded)
    return decoded

def _is_dangerous_url(url: str) -> bool:
    decoded = _decode_html_entities(url)
    normalized = re.sub(r'\s+', '', decoded.lower())
    for scheme in DANGEROUS_URL_SCHEMES:
        if normalized.startswith(f'{scheme}:'):
            return True
        if re.match(rf'^{re.escape(scheme)}\s*:', normalized):
            return True
    return False

def _sanitize_tag(match: re.Match) -> str:
    full_tag = match.group(0)
    tag_name = match.group(1).lower() if match.group(1) else match.group(2).lower()
    
    if tag_name not in ALLOWED_TAGS:
        return ''
    
    is_closing = full_tag.startswith('</')
    is_self_closing = full_tag.rstrip().endswith('/>')
    
    if is_closing:
        return f'</{tag_name}>'
    
    safe_attrs = []
    attr_pattern = re.compile(r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|(\S+))', re.IGNORECASE)
    for attr_match in attr_pattern.finditer(full_tag):
        attr_name = attr_match.group(1).lower()
        attr_value = attr_match.group(2) or attr_match.group(3) or attr_match.group(4) or ''
        
        if attr_name.startswith('on'): # Bloqueia event handlers (XSS)
            continue
        
        if attr_name in ('href', 'src', 'action', 'formaction'):
            if _is_dangerous_url(attr_value):
                continue
        
        if attr_name in ALLOWED_ATTRS:
            escaped_value = attr_value.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
            safe_attrs.append(f'{attr_name}="{escaped_value}"')
    
    attrs_str = ' '.join(safe_attrs)
    if attrs_str:
        return f'<{tag_name} {attrs_str}{"/" if is_self_closing else ""}>'
    return f'<{tag_name}{"/" if is_self_closing else ""}>'

def sanitize_html(html_text: str) -> str:
    """Remove tags perigosas e atributos maliciosos do HTML."""
    html_text = re.sub(r'<!--.*?-->', '', html_text, flags=re.DOTALL)
    html_text = re.sub(r'<\s*/?\s*(\w+)[^>]*/?>', _sanitize_tag, html_text)
    html_text = re.sub(r'\{\{[^}]*\}\}|\[\[[^\]]*\]\]', '', html_text) # Proteção contra template injection
    return html_text

def get_safe_markdown(text: str) -> str:
    """Converte Markdown para HTML seguro, com sanitização robusta."""
    if not text:
        return ""
    if isinstance(text, dict):
        text = text.get("content", text.get("answer", str(text)))
    if not isinstance(text, str):
        text = str(text)
    
    try:
        # Conversão inicial
        html_output = markdown.markdown(text, extensions=['extra', 'nl2br'], output_format='html')
        # Sanitização rigorosa
        html_output = sanitize_html(html_output)
        # Força links externos a abrirem em nova aba
        html_output = re.sub(r'<a href="([^"]*)"([^>]*)>', r'<a href="\1" target="_blank" rel="noopener noreferrer"\2>', html_output)
        return html_output
    except Exception as e:
        logger.error(f"Erro ao processar Markdown: {e}")
        # Fallback para texto simples escapado
        return text.replace('<', '&lt;').replace('>', '&gt;')
