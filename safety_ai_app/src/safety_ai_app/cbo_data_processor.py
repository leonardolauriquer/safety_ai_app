import pandas as pd
import logging
import os
import tempfile
import shutil
import streamlit as st
from typing import Dict, Any, List, Optional, Tuple

from safety_ai_app.google_drive_integrator import (
    get_service_account_drive_integrator_instance,
    CBO2025_FILE_ID # Importa o ID direto do arquivo
)

logger = logging.getLogger(__name__)

class CBODatabase:
    _instance: Optional['CBODatabase'] = None
    _data: Optional[pd.DataFrame] = None
    _cargos_dict: Optional[Dict[str, Any]] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CBODatabase, cls).__new__(cls)
            cls._instance._load_cbo_data()
        return cls._instance

    def __init__(self):
        pass

    @staticmethod
    @st.cache_data(ttl=3600)
    def _load_cbo_data_cached() -> Tuple[pd.DataFrame, Dict[str, Any]]:
        logger.info("Iniciando carregamento dos dados da CBO do Google Drive.")
        
        integrator = get_service_account_drive_integrator_instance()
        if not integrator:
            logger.error("Não foi possível obter o integrador do Google Drive.")
            return pd.DataFrame(), {}

        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, "CBO2025.xlsx")

        try:
            integrator.download_file_from_drive(CBO2025_FILE_ID, temp_file_path)
            logger.info(f"Arquivo CBO2025.xlsx baixado com sucesso para '{temp_file_path}'.")

            data = pd.read_excel(temp_file_path)
            logger.info(f"Dados da CBO carregados com sucesso de '{temp_file_path}'.")
            
            cargos_dict = CBODatabase._process_cbo_data_static(data)
            return data, cargos_dict

        except Exception as e:
            logger.error(f"Erro ao carregar ou processar CBO: {e}", exc_info=True)
            return pd.DataFrame(), {}
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Diretório temporário '{temp_dir}' removido.")

    @staticmethod
    def _process_cbo_data_static(data: pd.DataFrame) -> Dict[str, Any]:
        if data is None or data.empty:
            return {}

        logger.info("Processando dados da CBO para estrutura hierárquica.")
        cargos_dict: Dict[str, Any] = {}

        required_cols = ['COD_OCUPACAO', 'CARGO', 'SGL_GRANDE_AREA', 'NOME_GRANDE_AREA', 'COD_ATIVIDADE', 'NOME_ATIVIDADE']
        if not all(col in data.columns for col in required_cols):
            logger.error(f"Colunas obrigatórias não encontradas no arquivo CBO. Esperadas: {required_cols}. Encontradas: {data.columns.tolist()}")
            return {}

        for _, row in data.iterrows():
            cod_ocupacao = str(row['COD_OCUPACAO']).strip()
            cargo_nome = str(row['CARGO']).strip()
            nome_grande_area = str(row['NOME_GRANDE_AREA']).strip()
            cod_atividade = str(row['COD_ATIVIDADE']).strip()
            nome_atividade = str(row['NOME_ATIVIDADE']).strip()

            if cod_ocupacao not in cargos_dict:
                cargos_dict[cod_ocupacao] = {
                    "CARGO": cargo_nome,
                    "AREAS_DE_ATUACAO": {}
                }

            if nome_grande_area not in cargos_dict[cod_ocupacao]["AREAS_DE_ATUACAO"]:
                cargos_dict[cod_ocupacao]["AREAS_DE_ATUACAO"][nome_grande_area] = []

            cargos_dict[cod_ocupacao]["AREAS_DE_ATUACAO"][nome_grande_area].append({
                "COD_ATIVIDADE": cod_atividade,
                "NOME_ATIVIDADE": nome_atividade
            })
        logger.info("Dados da CBO processados com sucesso.")
        return cargos_dict

    def _load_cbo_data(self) -> None:
        data, cargos_dict = CBODatabase._load_cbo_data_cached()
        self._data = data
        self._cargos_dict = cargos_dict

    def get_all_cargos(self) -> List[Dict[str, str]]:
        if self._cargos_dict is None:
            return []
        sorted_cargos = sorted([{"COD_OCUPACAO": k, "CARGO": v["CARGO"]} for k, v in self._cargos_dict.items()], key=lambda x: x["CARGO"])
        return sorted_cargos

    def get_areas_by_cargo_code(self, cod_ocupacao: str) -> List[str]:
        if self._cargos_dict and cod_ocupacao in self._cargos_dict:
            return sorted(list(self._cargos_dict[cod_ocupacao]["AREAS_DE_ATUACAO"].keys()))
        return []

    def get_activities_by_cargo_and_area(self, cod_ocupacao: str, area_nome: str) -> List[Dict[str, str]]:
        if self._cargos_dict and cod_ocupacao in self._cargos_dict:
            areas = self._cargos_dict[cod_ocupacao]["AREAS_DE_ATUACAO"]
            if area_nome in areas:
                return sorted(areas[area_nome], key=lambda x: x["NOME_ATIVIDADE"])
        return []

    def get_cargo_name_by_code(self, cod_ocupacao: str) -> Optional[str]:
        if self._cargos_dict and cod_ocupacao in self._cargos_dict:
            return self._cargos_dict[cod_ocupacao]["CARGO"]
        return None
