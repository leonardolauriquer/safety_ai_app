import logging
import os
import pandas as pd
import streamlit as st
import io
import tempfile
import shutil
from typing import Dict, Any, Optional
import requests

from safety_ai_app.google_drive_integrator import (
    get_service_account_drive_integrator_instance,
    GRAU_DE_RISCO_FILE_ID # Importa o ID direto do arquivo
)

logger = logging.getLogger(__name__)

LOCAL_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
CNAE_RISK_CACHE_FILE = os.path.join(LOCAL_CACHE_DIR, "cnae_risk_cache.parquet")

class CNAERiskDataProcessor:
    _instance: Optional['CNAERiskDataProcessor'] = None
    _data: Optional[pd.DataFrame] = None
    _is_loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CNAERiskDataProcessor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not CNAERiskDataProcessor._is_loaded:
            CNAERiskDataProcessor._data = self._load_excel_data_cached()
            CNAERiskDataProcessor._is_loaded = True

    @staticmethod
    def _save_to_local_cache(df: pd.DataFrame) -> None:
        try:
            os.makedirs(LOCAL_CACHE_DIR, exist_ok=True)
            df.to_parquet(CNAE_RISK_CACHE_FILE, index=False)
            logger.info(f"Cache local de Grau de Risco da CNAE salvo em '{CNAE_RISK_CACHE_FILE}'.")
        except Exception as e:
            logger.warning(f"Não foi possível salvar cache local de CNAE Risk: {e}")

    @staticmethod
    def _load_from_local_cache() -> Optional[pd.DataFrame]:
        try:
            if os.path.exists(CNAE_RISK_CACHE_FILE):
                df = pd.read_parquet(CNAE_RISK_CACHE_FILE)
                logger.info(f"Cache local de Grau de Risco da CNAE carregado de '{CNAE_RISK_CACHE_FILE}' com {len(df)} registros.")
                return df
        except Exception as e:
            logger.warning(f"Não foi possível carregar cache local de CNAE Risk: {e}")
        return None

    @staticmethod
    @st.cache_resource
    def _load_excel_data_cached() -> Optional[pd.DataFrame]:
        logger.info("Iniciando carregamento dos dados de Grau de Risco da CNAE do Google Drive.")
        
        integrator = get_service_account_drive_integrator_instance()
        if not integrator:
            logger.warning("Integrador do Google Drive não disponível. Tentando carregar do cache local.")
            cached_df = CNAERiskDataProcessor._load_from_local_cache()
            if cached_df is not None:
                st.warning("⚠️ Google Drive indisponível. Utilizando dados locais em cache.")
                return cached_df
            logger.error("Nenhum cache local disponível para dados de Grau de Risco da CNAE.")
            st.error("Erro: Serviço do Google Drive não disponível e não há cache local.")
            return None

        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, "grau_de_risco.xlsx")

        try:
            integrator.download_file_from_drive(GRAU_DE_RISCO_FILE_ID, temp_file_path)
            logger.info(f"Arquivo 'grau_de_risco.xlsx' baixado com sucesso para '{temp_file_path}'.")

            df = pd.read_excel(temp_file_path)
            if 'CNAE' in df.columns and 'Grau de Risco' in df.columns:
                if not df.empty:
                    logger.debug(f"Primeiro CNAE do Excel (original): {df['CNAE'].iloc[0]}")

                df['CNAE'] = df['CNAE'].astype(str)
                df['CNAE'] = df['CNAE'].str.replace('.', '', regex=False)
                df['CNAE'] = df['CNAE'].str.replace('-', '', regex=False)
                df['CNAE'] = df['CNAE'].str.replace('/', '', regex=False)
                df['CNAE'] = df['CNAE'].str.strip()

                logger.info(f"Carregados {len(df)} entradas de Grau de Risco da CNAE. Primeiras 5 linhas (APÓS LIMPEZA):\n{df.head().to_string()}")
                logger.debug(f"Amostra de CNAEs limpos no DataFrame: {df['CNAE'].unique()[:10]}")
                logger.debug(f"dtype of CNAE column in DataFrame (APÓS LIMPEZA): {df['CNAE'].dtype}")
                
                if not df.empty:
                    logger.debug(f"Primeiro CNAE do DataFrame (após limpeza): {df['CNAE'].iloc[0]}")

                CNAERiskDataProcessor._save_to_local_cache(df)
                return df
            else:
                logger.error("Colunas 'CNAE' ou 'Grau de Risco' não encontradas no arquivo Excel de Grau de Risco.")
                st.error("Erro: Colunas 'CNAE' ou 'Grau de Risco' não encontradas no arquivo Excel de Grau de Risco. Verifique os cabeçalhos do arquivo.")
                return None

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, OSError) as e:
            logger.warning(f"Google Drive indisponível: {e}. Tentando carregar do cache local.")
            cached_df = CNAERiskDataProcessor._load_from_local_cache()
            if cached_df is not None:
                st.warning("⚠️ Google Drive temporariamente indisponível. Utilizando dados locais em cache.")
                return cached_df
            logger.error("Nenhum cache local disponível após falha de conexão com Google Drive.")
            st.error("Erro: Não foi possível conectar ao Google Drive e não há cache local disponível.")
            return None
        except Exception as e:
            logger.warning(f"Erro ao carregar dados de Grau de Risco da CNAE do Google Drive: {e}. Tentando cache local.")
            cached_df = CNAERiskDataProcessor._load_from_local_cache()
            if cached_df is not None:
                st.warning("⚠️ Erro ao acessar Google Drive. Utilizando dados locais em cache.")
                return cached_df
            logger.error(f"Erro ao carregar dados de Grau de Risco da CNAE: {e}", exc_info=True)
            st.error(f"Erro ao carregar dados de Grau de Risco da CNAE. Detalhes: {e}")
            return None
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Diretório temporário '{temp_dir}' removido.")

    @staticmethod
    @st.cache_data(ttl=3600)
    def _get_risk_level_cached(cnae_code: str) -> Optional[int]:
        if CNAERiskDataProcessor._data is None or CNAERiskDataProcessor._data.empty:
            return None
        
        cleaned_cnae_code = str(cnae_code).replace('.', '').replace('-', '').replace('/', '').strip()
        
        cnae_for_lookup = cleaned_cnae_code
        if len(cleaned_cnae_code) == 7:
            cnae_for_lookup = cleaned_cnae_code[:5]
        elif len(cleaned_cnae_code) != 5:
            return None
        
        if cnae_for_lookup not in CNAERiskDataProcessor._data['CNAE'].values:
            return None

        result = CNAERiskDataProcessor._data[CNAERiskDataProcessor._data['CNAE'] == cnae_for_lookup]
        
        if not result.empty:
            risk_level = result['Grau de Risco'].iloc[0]
            try:
                return int(risk_level)
            except ValueError:
                return None
        return None

    def get_risk_level(self, cnae_code: str) -> Optional[int]:
        if CNAERiskDataProcessor._data is None or CNAERiskDataProcessor._data.empty:
            logger.warning("Dados de Grau de Risco da CNAE não carregados ou vazios.")
            return None
        
        result = CNAERiskDataProcessor._get_risk_level_cached(cnae_code)
        if result is not None:
            logger.debug(f"get_risk_level: Grau de Risco '{result}' encontrado para CNAE '{cnae_code}'.")
        else:
            logger.debug(f"get_risk_level: Nenhum Grau de Risco encontrado para CNAE '{cnae_code}'.")
        return result
