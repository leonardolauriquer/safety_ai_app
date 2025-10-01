import requests
from bs4 import BeautifulSoup
import re
import io
import os
from PyPDF2 import PdfReader
import json  # Adicione esta importação para trabalhar com JSON

# URL da página que lista todas as NRs
MAIN_NRS_LIST_URL = "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/inspecao-do-trabalho/seguranca-e-saude-no-trabalho/ctpp-nrs/normas-regulamentadoras-nrs/"

# DICIONÁRIO DE URLs DIRETAS DE PDFs PARA NRs ESPECÍFICAS
# Decidimos remover entradas aqui porque os URLs diretos se mostraram muito instáveis.
# A prioridade será para arquivos locais e busca dinâmica nas páginas.
KNOWN_DIRECT_PDF_URLS = {}

# Define um caminho local onde o PDF pode ser baixado manualmente e lido
LOCAL_NR_PDF_PATH_TEMPLATE = r"C:\Dev\safety_ai_app\data\nrs\NR-{nr_number}.pdf"

def get_nr_link_from_list(nr_number):
    """
    Navega pela página principal de NRs e encontra o link específico para a NR desejada.
    Retorna o título completo e a URL, que pode ser HTML ou PDF.
    Esta função busca links *diretamente na página principal*.
    """
    print(f"Buscando link para NR-{nr_number} na página de listagem principal: {MAIN_NRS_LIST_URL}")
    try:
        response = requests.get(MAIN_NRS_LIST_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        content_core = soup.find('div', id='content-core')
        if not content_core:
            print("ERRO: Div 'content-core' não encontrada na página de listagem principal.")
            return None, None

        links = content_core.find_all('a')
        
        html_link_found = None
        for link in links:
            link_text = link.get_text(strip=True)
            # Regex mais flexível para capturar o título da NR na lista
            nr_match = re.search(rf'NR-?0?{nr_number}(\b| -|$)', link_text, re.IGNORECASE)
            
            if nr_match:
                nr_full_title = link_text
                nr_url = link.get('href')
                
                if nr_url and not nr_url.startswith('http'):
                    nr_url = requests.compat.urljoin(MAIN_NRS_LIST_URL, nr_url)

                if nr_url:
                    # Se o link na lista principal é um PDF, priorize-o imediatamente
                    # Adicionado um filtro extra para tentar garantir que o PDF é da NR correta
                    if ".pdf" in nr_url.lower() and (f'nr-{nr_number}' in nr_url.lower() or f'nr{nr_number}' in nr_url.lower()):
                        print(f"Link PDF direto para NR-{nr_number} encontrado na lista principal: {nr_url}")
                        return nr_full_title, nr_url
                    elif ".pdf" not in nr_url.lower(): # Armazena o link HTML para usar se nenhum PDF for encontrado
                        html_link_found = (nr_full_title, nr_url)
        
        if html_link_found:
            print(f"Link HTML para NR-{nr_number} encontrado na lista principal: {html_link_found[1]}")
            return html_link_found
        
        print(f"AVISO: Link para NR-{nr_number} não encontrado na página de listagem principal.")
        return None, None

    except requests.exceptions.RequestException as e:
        print(f"ERRO de requisição HTTP ao buscar links de NRs na lista principal: {e}")
        return None, None
    except Exception as e:
        print(f"ERRO inesperado ao processar a lista de NRs principal: {e}")
        return None, None

def extract_text_from_pdf_url(pdf_url, nr_number_for_logging):
    """Função auxiliar para baixar e extrair texto de uma URL de PDF."""
    print(f"Baixando e extraindo texto do PDF: {pdf_url}")
    try:
        response_pdf = requests.get(pdf_url, stream=True) # Use stream=True for potentially large files
        response_pdf.raise_for_status() # Levanta erro para status 4xx/5xx
        
        if 'application/pdf' not in response_pdf.headers.get('Content-Type', '').lower():
            print(f"AVISO: O link {pdf_url} não é um PDF (Content-Type: {response_pdf.headers.get('Content-Type')}).")
            return None, None # Não é um PDF, retorna None
            
        pdf_file = io.BytesIO(response_pdf.content)
        pdf_reader = PdfReader(pdf_file)
        
        text_content = ""
        for page_num in range(len(pdf_reader.pages)):
            try:
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"
            except Exception as e:
                print(f"AVISO: Erro ao extrair texto da página {page_num+1} do PDF {pdf_url}: {e}")
        
        cleaned_text = re.sub(r'\n\s*\n', '\n', text_content).strip()
        cleaned_text = re.sub(r' +', ' ', cleaned_text)
        
        inferred_title = f"NR-{nr_number_for_logging} - Conteúdo do PDF"
        
        return inferred_title, cleaned_text

    except requests.exceptions.RequestException as e:
        print(f"ERRO de requisição HTTP ao baixar PDF {pdf_url}: {e}")
        return None, None
    except Exception as e:
        print(f"ERRO inesperado ao processar PDF {pdf_url}: {e}")
        return None, None

def scrape_html_content(nr_number, nr_full_title, html_url):
    """
    Extrai o conteúdo de uma página HTML de NR, focando no conteúdo principal.
    Note: Esta função pode retornar uma NR incompleta se a página HTML tiver apenas uma introdução.
    """
    print(f"Raspando conteúdo HTML da página {html_url}")
    try:
        response_html = requests.get(html_url)
        response_html.raise_for_status()
        
        soup = BeautifulSoup(response_html.text, 'html.parser')
        
        content_div = soup.find('div', id='parent-fieldname-text')
        
        if not content_div:
            # Tentar outros seletores comuns para o corpo principal do conteúdo
            print(f"AVISO: Div 'parent-fieldname-text' não encontrada para {html_url}. Tentando 'document-body' ou 'main'.")
            content_div = soup.find('div', class_='document-body')
            if not content_div:
                content_div = soup.find('main') # Ou <article>

        if not content_div:
            print(f"AVISO: Não foi possível encontrar a div de conteúdo principal para {html_url}. Extraindo do body como último recurso.")
            content_div = soup.find('body') # Último recurso, pode pegar lixo

        if not content_div:
             print(f"ERRO: Não foi possível encontrar conteúdo algum para {html_url}.")
             return None

        raw_text = content_div.get_text(separator='\n', strip=True)
        cleaned_text = re.sub(r'\n\s*\n', '\n', raw_text).strip()
        cleaned_text = re.sub(r' +', ' ', cleaned_text)

        return cleaned_text

    except requests.exceptions.RequestException as e:
        print(f"ERRO de requisição HTTP ao processar HTML {html_url}: {e}")
        return None
    except Exception as e:
        print(f"ERRO inesperado ao processar HTML {html_url}: {e}")
        return None

def find_pdf_link_on_nr_html_page(html_page_url, nr_number_for_logging):
    """
    Visita uma página HTML de uma NR e tenta encontrar um link para o PDF completo.
    Procura por links que terminam em .pdf e contêm o número da NR no URL ou texto do link.
    """
    print(f"Procurando por link de PDF na página HTML da NR: {html_page_url}")
    try:
        response = requests.get(html_page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.IGNORECASE))

        for link in pdf_links:
            pdf_url = link.get('href')
            if pdf_url:
                # Tratar URLs relativas
                if not pdf_url.startswith('http'):
                    pdf_url = requests.compat.urljoin(html_page_url, pdf_url)
                
                # Critérios de filtragem: URL ou texto do link contém o número da NR
                link_text = link.get_text(strip=True)
                if (f'nr-{nr_number_for_logging}' in pdf_url.lower() or
                    f'nr{nr_number_for_logging}' in pdf_url.lower() or
                    f'nr-{nr_number_for_logging}' in link_text.lower() or
                    f'nr{nr_number_for_logging}' in link_text.lower() or
                    (re.search(r'norma\s+regulamentadora', link_text, re.IGNORECASE) and f'{nr_number_for_logging}' in link_text)): # Heurística extra
                    
                    print(f"Link de PDF para NR-{nr_number_for_logging} encontrado na página HTML: {pdf_url}")
                    return pdf_url
        
        print(f"Nenhum link de PDF relevante encontrado na página {html_page_url} para NR-{nr_number_for_logging}.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"ERRO de requisição HTTP ao procurar PDF na página {html_page_url}: {e}")
        return None
    except Exception as e:
        print(f"ERRO inesperado ao processar página {html_page_url} para link PDF: {e}")
        return None


def scrape_nr(nr_number):
    """
    Realiza o scraping e extração de texto de uma Norma Regulamentadora (NR) específica.
    Prioriza:
    1. Arquivo PDF local (se o usuário o colocou manualmente para maior robustez).
    2. Link PDF direto encontrado na página de listagem principal (MAIN_NRS_LIST_URL).
    3. Link PDF encontrado *dentro* da página HTML específica da NR.
    4. Conteúdo HTML da página específica da NR (como último recurso, pode ser incompleto).
    """
    nr_full_title = f"NR-{nr_number}" # Título padrão
    final_cleaned_text = None

    # TENTATIVA 1: Ler de um arquivo PDF local
    local_pdf_path = LOCAL_NR_PDF_PATH_TEMPLATE.format(nr_number=nr_number)
    if os.path.exists(local_pdf_path):
        print(f"Tentando ler PDF da NR-{nr_number} do caminho local: {local_pdf_path}")
        try:
            with open(local_pdf_path, 'rb') as f:
                pdf_file = io.BytesIO(f.read())
            pdf_reader = PdfReader(pdf_file)
            text_content = ""
            for page_num in range(len(pdf_reader.pages)):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
                except Exception as e:
                    print(f"AVISO: Erro ao extrair texto da página {page_num+1} do PDF local {local_pdf_path}: {e}")
            
            cleaned_text = re.sub(r'\n\s*\n', '\n', text_content).strip()
            cleaned_text = re.sub(r' +', ' ', cleaned_text)
            nr_full_title = f"NR-{nr_number} (Local PDF)"
            print(f"Conteúdo da NR-{nr_number} extraído com sucesso do PDF local.")
            return nr_number, nr_full_title, cleaned_text
        except Exception as e:
            print(f"ERRO ao ler ou processar PDF local {local_pdf_path}: {e}")
            print("Não foi possível extrair do PDF local. Tentando fontes online.")

    # TENTATIVA 2: Buscar o link para a NR na lista principal (pode ser HTML ou PDF direto)
    nr_full_title_from_list, nr_link_from_main_list = get_nr_link_from_list(nr_number)

    if nr_link_from_main_list:
        nr_full_title = nr_full_title_from_list if nr_full_title_from_list else nr_full_title

        if ".pdf" in nr_link_from_main_list.lower(): # Se o link da lista principal já é um PDF
            print(f"Link identificado como PDF direto da lista principal. Baixando e extraindo texto para {nr_link_from_main_list}...")
            extracted_title, extracted_text = extract_text_from_pdf_url(nr_link_from_main_list, nr_number)
            if extracted_text:
                nr_full_title = extracted_title if extracted_title else nr_full_title
                print(f"Conteúdo da NR-{nr_number} extraído com sucesso da URL PDF direta da lista principal.")
                return nr_number, nr_full_title, extracted_text
            else:
                print(f"AVISO: Falha ao extrair PDF do link direto da lista principal ({nr_link_from_main_list}). Tentando outras heurísticas.")
        
        # TENTATIVA 3: Se não era um PDF direto da lista principal (ou a extração falhou),
        # agora tentamos encontrar um link de PDF *dentro* da página HTML específica da NR.
        print(f"Tentando encontrar link de PDF dentro da página HTML da NR-{nr_number}: {nr_link_from_main_list}")
        pdf_link_from_html_page = find_pdf_link_on_nr_html_page(nr_link_from_main_list, nr_number)
        
        if pdf_link_from_html_page:
            print(f"Link PDF encontrado na página HTML da NR-{nr_number}: {pdf_link_from_html_page}. Baixando e extraindo...")
            extracted_title, extracted_text = extract_text_from_pdf_url(pdf_link_from_html_page, nr_number)
            if extracted_text:
                nr_full_title = extracted_title if extracted_title else nr_full_title
                print(f"Conteúdo da NR-{nr_number} extraído com sucesso do PDF encontrado na página HTML.")
                return nr_number, nr_full_title, extracted_text
            else:
                print(f"AVISO: Falha ao extrair conteúdo do PDF em {pdf_link_from_html_page}. Tentando raspar a página HTML diretamente.")
        
        # TENTATIVA FINAL: Se nenhuma das opções acima funcionou para obter o PDF completo,
        # raspar o conteúdo da própria página HTML (pode ser incompleto para chunking detalhado).
        print(f"Extraindo conteúdo da página HTML {nr_link_from_main_list} para NR-{nr_number} (pode ser incompleto para chunking detalhado).")
        final_cleaned_text = scrape_html_content(nr_number, nr_full_title, nr_link_from_main_list)
        if final_cleaned_text:
            return nr_number, nr_full_title, final_cleaned_text
    
    print(f"AVISO: Não foi possível obter o conteúdo completo da NR-{nr_number} de nenhuma fonte online ou local.")
    return nr_number, nr_full_title, None

def process_nr_text_to_chunks(nr_number, nr_title, cleaned_text):
    """
    Divide o texto limpo da NR em chunks baseados na sua estrutura (itens e subitens)
    e associa metadados.
    """
    chunks = []
    lines = cleaned_text.split('\n')

    # Regex refinada para identificar itens:
    # 1. Numeração hierárquica (ex: "1.", "1.1.", "35.1.1.") no início da linha,
    #    OBRIGATORIAMENTE terminando com um ponto (e.g., '1.', '1.1.')
    # 2. Anexos (ex: "ANEXO I", "ANEXO II DA NR-35")
    item_pattern = re.compile(
        r'^\s*'
        r'(?:'
            r'(\d+(?:\.\d+)*\.)' # Grupo 1: Itens numerados (ex: "35.1.", "1.1.") - OBRIGA O PONTO FINAL
            r'|'
            r'(ANEXO\s+[IVXLCDM]+(?:(?:\s+da)?\s+NR-?\d+)?\b)' # Grupo 2: Anexos (ex: "ANEXO I", "ANEXO II da NR-35")
        r')'
        r'(?:\s+|$)(.*)', # Opcional espaço após o identificador, ou fim da linha. Grupo 3: O resto da linha.
        re.IGNORECASE
    )
    
    current_item_id = "Introdução" 
    current_item_title = None 
    current_text_buffer = []

    # Processa o texto antes do primeiro item numerado como parte da introdução
    intro_lines = []
    first_item_line_index = -1
    for i, line in enumerate(lines):
        if item_pattern.match(line.strip()):
            first_item_line_index = i
            break
    
    if first_item_line_index != -1:
        intro_lines = lines[:first_item_line_index]
        remaining_lines = lines[first_item_line_index:]
    else: 
        intro_lines = lines
        remaining_lines = []

    if intro_lines and "".join(intro_lines).strip():
        chunks.append({
            "nr_number": nr_number,
            "nr_title": nr_title,
            "item_id": "Introdução",
            "item_title": None,
            "text_content": "\n".join(intro_lines).strip()
        })
    
    for line in remaining_lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        match = item_pattern.match(line_stripped)
        
        if match:
            item_identifier = None
            if match.group(1): 
                item_identifier = match.group(1).strip()
                if item_identifier.endswith('.'): 
                    item_identifier = item_identifier[:-1]
            elif match.group(2): 
                item_identifier = match.group(2).strip()
            
            content_after_id = match.group(3).strip()

            if item_identifier:
                if current_text_buffer and "\n".join(current_text_buffer).strip():
                    chunks.append({
                        "nr_number": nr_number,
                        "nr_title": nr_title,
                        "item_id": current_item_id,
                        "item_title": current_item_title,
                        "text_content": "\n".join(current_text_buffer).strip()
                    })
                
                current_item_id = item_identifier
                current_text_buffer = [content_after_id] 
            else: 
                current_text_buffer.append(line_stripped)
        else:
            current_text_buffer.append(line_stripped)
    
    if current_text_buffer and "\n".join(current_text_buffer).strip():
        chunks.append({
            "nr_number": nr_number,
            "nr_title": nr_title,
            "item_id": current_item_id,
            "item_title": current_item_title,
            "text_content": "\n".join(current_text_buffer).strip()
        })
    
    return chunks

def save_chunks_to_json(chunks, output_filename="nrs_chunks.json"):
    """
    Salva a lista de chunks em um arquivo JSON.
    """
    try:
        # Verifica se a pasta 'data' e 'nrs' existem, se não, cria
        output_dir = os.path.join("data", "nrs")
        os.makedirs(output_dir, exist_ok=True)
        
        full_path = os.path.join(output_dir, output_filename)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=4)
        print(f"Chunks salvos com sucesso em {full_path}")
    except Exception as e:
        print(f"ERRO ao salvar chunks em JSON: {e}")

if __name__ == "__main__":
    nr_to_scrape = 35 # Exemplo: NR-35 - Trabalho em Altura

    nr_num, nr_full_title, cleaned_text = scrape_nr(nr_to_scrape)

    if cleaned_text:
        print(f"\n--- Conteúdo BRUTO da {nr_num} - {nr_full_title} (para validação) ---\n")
        print(cleaned_text[:1500]) 
        print("\n...\n")
        print(cleaned_text[-500:]) 
        print(f"\nTotal de caracteres extraídos (bruto): {len(cleaned_text)}")

        print("\n--- Processando chunks... ---\n")
        nr_chunks = process_nr_text_to_chunks(nr_num, nr_full_title, cleaned_text)

        print(f"Total de chunks gerados: {len(nr_chunks)}\n")
        if nr_chunks:
            for i, chunk in enumerate(nr_chunks[:10]): 
                print(f"CHUNK {i+1}:")
                print(f"  NR: {chunk['nr_number']}")
                print(f"  Título NR: {chunk['nr_title']}")
                print(f"  ID Item: {chunk['item_id']}")
                print(f"  Título Item: {chunk['item_title']}")
                print(f"  Conteúdo: {chunk['text_content'][:300]}...")
                print("-" * 30)
            
            if len(nr_chunks) > 10:
                print(f"\n... e {len(nr_chunks) - 10} chunks a mais.")
            
            # --- NOVA LINHA AQUI: SALVANDO OS CHUNKS ---
            save_chunks_to_json(nr_chunks, f"nr_{nr_num}_chunks.json")

        else:
            print("Nenhum chunk foi gerado. Verifique o conteúdo extraído e o padrão da regex.")

    else:
        print(f"\nNão foi possível extrair o conteúdo da NR-{nr_to_scrape} de nenhuma fonte online ou local.")
