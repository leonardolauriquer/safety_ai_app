import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class AdzunaJobIntegrator:
    """
    Integração com a API da Adzuna para buscar vagas de emprego.
    """
    BASE_URL = "https://api.adzuna.com/v1/api/jobs"
    COUNTRY = "br" # Brasil

    def __init__(self, require_credentials: bool = True):
        """
        Inicializa o integrador com as credenciais da Adzuna.
        As credenciais são carregadas das variáveis de ambiente.
        
        Args:
            require_credentials: Se True, lança exceção se credenciais ausentes.
        """
        self.app_id = os.getenv("ADZUNA_APP_ID")
        self.api_key = os.getenv("ADZUNA_API_KEY")
        self._credentials_configured = bool(self.app_id and self.api_key)

        if not self._credentials_configured:
            logger.warning("ADZUNA_APP_ID ou ADZUNA_API_KEY não configurados. Funcionalidade de busca de vagas desativada.")
            if require_credentials:
                raise ValueError("Credenciais da Adzuna API não configuradas.")
    
    @property
    def is_configured(self) -> bool:
        """Retorna True se as credenciais estão configuradas."""
        return self._credentials_configured

    def _build_query_params(self,
                      what: str, # Este 'what' será usado como 'what_phrase'
                      where: Optional[str] = None,
                      max_days_old: int = 30,
                      results_per_page: int = 20,
                      salary_min: Optional[int] = None,
                      salary_max: Optional[int] = None,
                      is_full_time: Optional[bool] = None,
                      is_part_time: Optional[bool] = None,
                      is_contract: Optional[bool] = None,
                      is_permanent: Optional[bool] = None
                      ) -> Dict[str, Any]:
        """
        Constrói os parâmetros da query string para a API da Adzuna.
        """
        query_params = {
            "app_id": self.app_id,
            "app_key": self.api_key,
            "what_phrase": what, # <--- ALTERADO PARA what_phrase para busca exata da frase
            "sort_by": "date",
            "sort_direction": "down",
            "max_days_old": max_days_old,
            "results_per_page": results_per_page,
            "content-type": "application/json"
        }
        if where:
            query_params["where"] = where
        
        # Adiciona filtros de salário se fornecidos
        if salary_min is not None:
            query_params["salary_min"] = salary_min
        if salary_max is not None:
            query_params["salary_max"] = salary_max
        
        # Adiciona filtros de tipo de contrato se True
        if is_full_time:
            query_params["full_time"] = "1"
        if is_part_time:
            query_params["part_time"] = "1"
        if is_contract:
            query_params["contract"] = "1"
        if is_permanent:
            query_params["permanent"] = "1"
            
        # Garante que nenhum parâmetro com valor None ou string vazia seja passado
        cleaned_query_params = {k: v for k, v in query_params.items() if v is not None and v != ""}
        
        return cleaned_query_params

    def search_jobs(self,
                    what: str,
                    where: Optional[str] = None,
                    max_days_old: int = 30,
                    page: int = 1,
                    results_per_page: int = 20,
                    salary_min: Optional[int] = None,
                    salary_max: Optional[int] = None,
                    is_full_time: Optional[bool] = None,
                    is_part_time: Optional[bool] = None,
                    is_contract: Optional[bool] = None,
                    is_permanent: Optional[bool] = None
                    ) -> List[Dict[str, Any]]:
        """
        Realiza uma busca de vagas na API da Adzuna.
        """
        query_params_dict = self._build_query_params(
            what, where, max_days_old, results_per_page,
            salary_min, salary_max, is_full_time, is_part_time, is_contract, is_permanent
        )
        
        # Constrói a URL base do endpoint, com 'page' APENAS NO PATH
        base_endpoint_url = f"{self.BASE_URL}/{self.COUNTRY}/search/{page}"
        
        # Codifica os parâmetros da query manualmente e anexa à URL base
        encoded_query_string = urlencode(query_params_dict)
        full_url = f"{base_endpoint_url}?{encoded_query_string}"

        try:
            logger.info(f"Requisição Adzuna URL COMPLETA (Python - httpx - Corrigido what_phrase): {full_url}")

            headers = {
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
            }
            
            with httpx.Client() as client:
                response = client.get(full_url, headers=headers, timeout=30.0)
                
                logger.info(f"Status Code da resposta: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    jobs = data.get("results", [])
                    logger.info(f"Encontradas {len(jobs)} vagas para what='{what}', where='{where}'.")
                    return jobs
                else:
                    logger.error(f"Erro HTTP {response.status_code}. Resposta: {response.text[:500]}\nURL: {full_url}")
                    return []
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP ao buscar vagas na Adzuna: {e}. Resposta: {e.response.text[:500] if e.response else 'N/A'}\nURL: {full_url}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Erro de requisição (conexão/timeout) ao buscar vagas na Adzuna: {e}\nURL: {full_url}")
            return []
        except Exception as e:
            logger.error(f"Erro inesperado ao processar resposta da Adzuna: {e}\nURL: {full_url}")
            return []
