import os
import base64
import mimetypes
import re
import markdown
import logging

logger = logging.getLogger(__name__)


def get_image_base64(project_root: str, image_path: str) -> str:
    try:
        abs_image_path = os.path.join(project_root, image_path)
        if not os.path.exists(abs_image_path):
            return ""
        mime_type, _ = mimetypes.guess_type(abs_image_path)
        if mime_type is None:
            if abs_image_path.lower().endswith(".png"):
                mime_type = "image/png"
            elif abs_image_path.lower().endswith((".jpg", ".jpeg")):
                mime_type = "image/jpeg"
            else:
                mime_type = "image/octet-stream"
        with open(abs_image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return f"data:{mime_type};base64,{encoded_string}"
    except Exception as e:
        logger.critical(f"[ERRO CRÍTICO] Erro ao codificar imagem Base64 '{image_path}': {e}", exc_info=True)
        return ""


def process_markdown_for_external_links(text) -> str:
    if not text:
        return ""
    if isinstance(text, dict):
        text = text.get("content", text.get("answer", str(text)))
    if not isinstance(text, str):
        text = str(text)
    try:
        pattern = r'$$([^$$]+)\]$([^)]+)$()?'

        def replace_link(match):
            link_text = match.group(1)
            link_url = match.group(2)
            attributes_str = match.group(3) or ""
            html_attributes = ""
            if attributes_str == '' or link_url.startswith(("http://", "https://", "/download_library_doc")):
                html_attributes = '  rel="noopener noreferrer"'
            return f'<a href="{link_url}"{html_attributes}>{link_text}</a>'

        processed = re.sub(pattern, replace_link, text)
        final_html = markdown.markdown(processed, extensions=['extra', 'nl2br', 'md_in_html'], output_format='html')
        for tag in ['</div>', '</p>', '<div>', '<p>', '</span>', '<span>', '</br>', '<br>', '<br/>']:
            final_html = final_html.replace(tag, '')
        return final_html.strip()
    except Exception as e:
        logger.error(f"Erro ao processar markdown: {e}", exc_info=True)
        return text.replace('<', '&lt;').replace('>', '&gt;')
