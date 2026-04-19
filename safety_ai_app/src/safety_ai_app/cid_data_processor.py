import logging
import os
import requests
import json
import time
import tempfile
import shutil
import streamlit as st
from typing import Dict, List, Any, Optional, Tuple
import re
import pandas as pd
import unicodedata

from safety_ai_app.google_drive_integrator import (
    get_service_account_drive_integrator_instance,
    CID10_FILE_ID # Importa o ID direto do arquivo
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0

ICD_API_AUTH_URL = "https://icdaccessmanagement.who.int/connect/token"
ICD_API_SCOPE = "icdapi_access"

ICD_11_API_RELEASE_ID = "2025-01"
ICD_11_API_LINEARIZATION_NAME = "mms"
ICD_11_API_SEARCH_ENDPOINT = f"https://id.who.int/icd/release/11/{ICD_11_API_RELEASE_ID}/{ICD_11_API_LINEARIZATION_NAME}/search"

CID10_LOCAL_FILE_NAME = "CID10.xlsx"

CID10_CODE_PATTERN = re.compile(r"^[A-Z]\d{2}(\.\d{1,2})?$")

ICD_API_CLIENT_ID = os.getenv("ICD_API_CLIENT_ID")
ICD_API_CLIENT_SECRET = os.getenv("ICD_API_CLIENT_SECRET")

class CIDDatabase:
    _instance: Optional['CIDDatabase'] = None
    _access_token: Optional[str] = None
    _token_expiry_time: Optional[float] = None
    _cid10_local_data: List[Dict[str, str]] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CIDDatabase, cls).__new__(cls)
            cls._instance._cid10_local_data = CIDDatabase._load_cid10_data_cached()
        return cls._instance

    @staticmethod
    @st.cache_data(ttl=3600)
    def _load_cid10_data_cached() -> List[Dict[str, str]]:
        logger.info("Iniciando carregamento dos dados do CID-10 do Google Drive.")
        
        integrator = get_service_account_drive_integrator_instance()
        if not integrator:
            logger.error("Integrador do Google Drive não disponível. Não é possível carregar dados do CID-10 do Drive.")
            return []

        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, CID10_LOCAL_FILE_NAME)

        try:
            integrator.download_file_from_drive(CID10_FILE_ID, temp_file_path)
            logger.info(f"Arquivo '{CID10_LOCAL_FILE_NAME}' baixado com sucesso para '{temp_file_path}'.")
            return CIDDatabase._process_cid10_excel_file_static(temp_file_path)

        except Exception as e:
            logger.error(f"Erro geral ao carregar dados do CID-10 do Google Drive: {e}", exc_info=True)
            return []
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Diretório temporário '{temp_dir}' removido.")

    @staticmethod
    def _process_cid10_excel_file_static(file_path: str) -> List[Dict[str, str]]:
        if not os.path.exists(file_path):
            logger.warning(f"Arquivo Excel do CID-10 não encontrado em '{file_path}'. Não é possível processar.")
            return []

        try:
            df = pd.read_excel(file_path)
            temp_cid10_data = []

            if 'CAT' in df.columns and 'CAT_DESCRICAO' in df.columns:
                for _, row in df[['CAT', 'CAT_DESCRICAO']].drop_duplicates().iterrows():
                    code = str(row['CAT']).strip()
                    description = str(row['CAT_DESCRICAO']).strip()
                    if code and description:
                        temp_cid10_data.append({
                            "COD_CID": code,
                            "DESCRICAO_CID": description
                        })
            else:
                logger.warning("Colunas 'CAT' ou 'CAT_DESCRICAO' não encontradas no arquivo CID10.xlsx. Categorias principais não serão carregadas.")

            if 'SUB_CAT' in df.columns and 'SUB_CAT_DESCRICAO' in df.columns:
                for _, row in df[['SUB_CAT', 'SUB_CAT_DESCRICAO']].drop_duplicates().iterrows():
                    code = str(row['SUB_CAT']).strip()
                    description = str(row['SUB_CAT_DESCRICAO']).strip()
                    if code and description:
                        temp_cid10_data.append({
                            "COD_CID": code,
                            "DESCRICAO_CID": description
                        })
            else:
                logger.warning("Colunas 'SUB_CAT' ou 'SUB_CAT_DESCRICAO' não encontradas no arquivo CID10.xlsx. Subcategorias não serão carregadas.")

            unique_cids = {cid["COD_CID"]: cid for cid in temp_cid10_data}
            result = sorted(list(unique_cids.values()), key=lambda x: x["COD_CID"])

            logger.info(f"Carregados {len(result)} entradas de CID-10 do arquivo do Drive.")
            return result

        except Exception as e:
            logger.error(f"Erro ao processar arquivo Excel do CID-10 de '{file_path}': {e}", exc_info=True)
            return []

    def _get_access_token(self) -> Optional[str]:
        if self._access_token and self._token_expiry_time and self._token_expiry_time > time.time():
            logger.info("Token de acesso do ICD API ainda válido.")
            return self._access_token

        if not ICD_API_CLIENT_ID or not ICD_API_CLIENT_SECRET:
            logger.error("ICD_API_CLIENT_ID ou ICD_API_CLIENT_SECRET não configurados no .env. Verifique o arquivo .env.")
            return None

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'client_credentials',
            'client_id': ICD_API_CLIENT_ID,
            'client_secret': ICD_API_CLIENT_SECRET,
            'scope': ICD_API_SCOPE
        }

        backoff = INITIAL_BACKOFF_SECONDS
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Obtendo novo token de acesso do ICD API... (tentativa {attempt + 1}/{MAX_RETRIES})")
                response = requests.post(ICD_API_AUTH_URL, headers=headers, data=data, timeout=10)
                response.raise_for_status()
                
                token_info = response.json()
                self._access_token = token_info.get('access_token')
                expires_in = token_info.get('expires_in', 3600)
                self._token_expiry_time = time.time() + expires_in - 60
                logger.info("Token de acesso do ICD API obtido com sucesso.")
                return self._access_token

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"API ICD-11 indisponível (tentativa {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Aguardando {backoff:.1f}s antes de tentar novamente...")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.warning("API ICD-11 não disponível após todas as tentativas. Será usado fallback local CID-10.")
                    self._access_token = None
                    self._token_expiry_time = None
                    return None
            except requests.exceptions.RequestException as e:
                logger.error(f"Erro ao obter token de acesso do ICD API: {e}", exc_info=True)
                self._access_token = None
                self._token_expiry_time = None
                return None
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar resposta JSON do token do ICD API: {e}", exc_info=True)
                self._access_token = None
                self._token_expiry_time = None
                return None
            except Exception as e:
                logger.error(f"Erro inesperado ao obter token do ICD API: {e}", exc_info=True)
                self._access_token = None
                self._token_expiry_time = None
                return None
        return None

    @staticmethod
    def _search_cid11_text_with_retry(query: str, token: str) -> Tuple[List[Dict[str, str]], bool]:
        if not query or not token:
            return [], False

        headers = {
            'Authorization': f"Bearer {token}",
            'Accept': 'application/json',
            'Accept-Language': "pt",
            'API-Version': "v2",
        }
        
        params_query = {
            'q': query,
            'flatResults': True,
            'medicalCodingMode': True
        }

        backoff = INITIAL_BACKOFF_SECONDS
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Buscando '{query}' na API do ICD-11 (tentativa {attempt + 1}/{MAX_RETRIES})...")
                response = requests.get(ICD_11_API_SEARCH_ENDPOINT, headers=headers, params=params_query, timeout=10) 
                response.raise_for_status()
                
                search_results = response.json()
                
                found_cids = []
                for destination in search_results.get('destinationEntities', []):
                    code = destination.get('theCode')
                    title_obj = destination.get('title')
                    title = None
                    if isinstance(title_obj, dict) and '@value' in title_obj:
                        title = title_obj['@value']
                    elif isinstance(title_obj, str):
                        title = title_obj
                    
                    if code and title:
                        found_cids.append({
                            "COD_CID": code,
                            "DESCRICAO_CID": title
                        })
                logger.info(f"Encontrados {len(found_cids)} CIDs na API do ICD-11 para a query '{query}'.")
                return found_cids, True

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"API ICD-11 indisponível durante busca (tentativa {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Aguardando {backoff:.1f}s antes de tentar novamente...")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.warning("API ICD-11 não disponível após todas as tentativas.")
                    return [], False
            except requests.exceptions.RequestException as e:
                logger.error(f"Erro ao buscar CIDs na API do ICD-11 para '{query}': {e}", exc_info=True)
                return [], False
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar resposta JSON da API do ICD-11 para '{query}': {e}", exc_info=True)
                return [], False
            except Exception as e:
                logger.error(f"Erro inesperado ao buscar CIDs na API do ICD-11 para '{query}': {e}", exc_info=True)
                return [], False
        return [], False

    def search_cid11_text(self, query: str, fallback_to_local: bool = True) -> Tuple[List[Dict[str, str]], str]:
        if not query:
            return [], ""

        token = self._get_access_token()
        if not token:
            logger.warning("Não foi possível obter token de acesso para a API do ICD-11. Utilizando dados locais CID-10.")
            if fallback_to_local and self._cid10_local_data:
                local_results = self.search_cid10_local(query)
                return local_results, "⚠️ API ICD-11 indisponível. Exibindo resultados do banco de dados local CID-10."
            return [], "⚠️ API ICD-11 indisponível e não há dados locais disponíveis."

        results, api_available = CIDDatabase._search_cid11_text_with_retry(query, token)
        
        if api_available:
            return results, ""
        
        if fallback_to_local and self._cid10_local_data:
            logger.warning("API ICD-11 offline. Utilizando fallback para dados locais CID-10.")
            local_results = self.search_cid10_local(query)
            return local_results, "⚠️ API ICD-11 temporariamente indisponível. Exibindo resultados do banco de dados local CID-10."
        
        return [], "⚠️ API ICD-11 indisponível e não há dados locais disponíveis."

    @staticmethod
    @st.cache_data(ttl=3600)
    def _search_cid10_local_cached(query: str, data_hash: int) -> List[Dict[str, str]]:
        if not query:
            return []
        
        instance = CIDDatabase._instance
        if not instance or not instance._cid10_local_data:
            return []

        normalized_query = CIDDatabase._normalize_text_static(query)
        results = []

        for cid_entry in instance._cid10_local_data:
            normalized_code = CIDDatabase._normalize_text_static(cid_entry["COD_CID"])
            normalized_description = CIDDatabase._normalize_text_static(cid_entry["DESCRICAO_CID"])

            if normalized_query in normalized_code or normalized_query in normalized_description:
                results.append(cid_entry)
        
        logger.info(f"Encontrados {len(results)} CIDs no banco de dados local para a query '{query}'.")
        return results

    def search_cid10_local(self, query: str) -> List[Dict[str, str]]:
        if not query:
            return []
        
        if not self._cid10_local_data:
            logger.warning("Dados locais do CID-10 não carregados. Não é possível realizar a busca.")
            return []

        data_hash = hash(tuple(sorted([(d["COD_CID"], d["DESCRICAO_CID"]) for d in self._cid10_local_data[:10]])))
        return CIDDatabase._search_cid10_local_cached(query, data_hash)

    @staticmethod
    def _normalize_text_static(text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = text.lower()
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
        return text

    def _normalize_text(self, text: str) -> str:
        return CIDDatabase._normalize_text_static(text)
