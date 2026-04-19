import logging
import requests
from typing import List, Dict, Any, Optional

from safety_ai_app.cnae_risk_data_processor import CNAERiskDataProcessor

logger = logging.getLogger(__name__)

CNAE_BASE_URL = "https://servicodados.ibge.gov.br/api/v2/cnae/"

class CNAEDataProcessor:
    _instance: Optional['CNAEDataProcessor'] = None
    _risk_processor: Optional[CNAERiskDataProcessor] = None

    def __new__(cls):
        if cls._instance is None: # CORREÇÃO AQUI: === substituído por is
            cls._instance = super(CNAEDataProcessor, cls).__new__(cls)
            cls._instance._risk_processor = CNAERiskDataProcessor()
        return cls._instance

    def _make_api_request(self, endpoint: str, ids: Optional[str] = None) -> List[Dict[str, Any]]:
        url = f"{CNAE_BASE_URL}{endpoint}"
        if ids:
            url = f"{url}/{ids}"

        try:
            logger.info(f"Fazendo requisição à API CNAE: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict):
                data = [data]
            
            for item in data:
                cnae_id = item.get('id')
                if cnae_id and (endpoint == "classes" or endpoint == "subclasses"):
                    risk_level = self._risk_processor.get_risk_level(cnae_id)
                    if risk_level is not None:
                        item['grau_de_risco'] = risk_level
                        logger.debug(f"Grau de Risco {risk_level} adicionado para CNAE {cnae_id}.")
            
            return data
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"Erro HTTP ao acessar a API CNAE {url}: {http_err} - Resposta: {response.text}", exc_info=True)
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Erro de conexão ao acessar a API CNAE {url}: {conn_err}", exc_info=True)
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout ao acessar a API CNAE {url}: {timeout_err}", exc_info=True)
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Erro geral na requisição à API CNAE {url}: {req_err}", exc_info=True)
        except Exception as e:
            logger.error(f"Erro inesperado ao processar a resposta da API CNAE {url}: {e}", exc_info=True)
        return []

    def get_sections(self, ids: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._make_api_request("secoes", ids)

    def get_divisions(self, ids: Optional[str] = None, section_ids: Optional[str] = None) -> List[Dict[str, Any]]:
        if section_ids:
            return self._make_api_request(f"secoes/{section_ids}/divisoes")
        return self._make_api_request("divisoes", ids)

    def get_groups(self, ids: Optional[str] = None, division_ids: Optional[str] = None, section_ids: Optional[str] = None) -> List[Dict[str, Any]]:
        if division_ids:
            return self._make_api_request(f"divisoes/{division_ids}/grupos")
        if section_ids:
            return self._make_api_request(f"secoes/{section_ids}/grupos")
        return self._make_api_request("grupos", ids)

    def get_classes(self, ids: Optional[str] = None, group_ids: Optional[str] = None, division_ids: Optional[str] = None, section_ids: Optional[str] = None) -> List[Dict[str, Any]]:
        if group_ids:
            return self._make_api_request(f"grupos/{group_ids}/classes")
        if division_ids:
            return self._make_api_request(f"divisoes/{division_ids}/classes")
        if section_ids:
            return self._make_api_request(f"secoes/{section_ids}/classes")
        return self._make_api_request("classes", ids)

    def get_subclasses(self, ids: Optional[str] = None, class_ids: Optional[str] = None, group_ids: Optional[str] = None, division_ids: Optional[str] = None, section_ids: Optional[str] = None) -> List[Dict[str, Any]]:
        if class_ids:
            return self._make_api_request(f"classes/{class_ids}/subclasses")
        if group_ids:
            return self._make_api_request(f"grupos/{group_ids}/subclasses")
        if division_ids:
            return self._make_api_request(f"divisoes/{division_ids}/subclasses")
        if section_ids:
            return self._make_api_request(f"secoes/{section_ids}/subclasses")
        return self._make_api_request("subclasses", ids)

    def search_cnae_by_id(self, cnae_id: str, level: str) -> List[Dict[str, Any]]:
        if not cnae_id:
            return []
        
        valid_levels = ["secoes", "divisoes", "grupos", "classes", "subclasses"]
        if level not in valid_levels:
            logger.warning(f"Nível de busca '{level}' inválido. Retornando lista vazia.")
            return []
            
        return self._make_api_request(level, cnae_id)

    def search_cnae_by_description(self, query: str) -> List[Dict[str, Any]]:
        logger.warning("A busca por descrição da CNAE não é diretamente suportada pela API do IBGE de forma eficiente. Considere implementar um cache local ou buscar por ID.")
        return []