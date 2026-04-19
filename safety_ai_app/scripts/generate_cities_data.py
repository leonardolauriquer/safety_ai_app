import requests
import json
import os
import time
from typing import List, Dict, Any

# URL base da API de Localidades do IBGE
IBGE_API_BASE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"

def fetch_states() -> List[Dict[str, Any]]:
    """
    Busca a lista de todos os estados brasileiros na API do IBGE.
    """
    url = f"{IBGE_API_BASE_URL}/estados"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Levanta um erro para status codes 4xx/5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar estados do IBGE: {e}")
        return []

def fetch_municipalities_by_state(state_id: int) -> List[str]:
    """
    Busca a lista de municípios para um dado estado na API do IBGE.
    """
    url = f"{IBGE_API_BASE_URL}/estados/{state_id}/municipios"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        municipalities_data = response.json()
        return sorted([m['nome'] for m in municipalities_data])
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar municípios para o estado ID {state_id} do IBGE: {e}")
        return []

def generate_brazilian_cities_json():
    """
    Gera um arquivo JSON com municípios brasileiros (cidades) agrupados por sigla de estado.
    """
    print("Iniciando a busca de dados de municípios (cidades) do IBGE...")
    states = fetch_states()
    
    if not states:
        print("Não foi possível obter a lista de estados. Abortando.")
        return

    brazilian_cities_by_state = {}
    total_states = len(states)

    for i, state in enumerate(states):
        state_abbr = state['sigla']
        state_id = state['id'] # Usar o ID do estado para buscar municípios
        state_name = state['nome']
        print(f"[{i+1}/{total_states}] Buscando municípios para {state_name} ({state_abbr})...")
        municipalities = fetch_municipalities_by_state(state_id)
        brazilian_cities_by_state[state_abbr] = municipalities
        time.sleep(0.1) # Pequeno delay para não sobrecarregar a API do IBGE

    # Define o caminho para salvar o arquivo JSON
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data") # Caminho correto para a pasta 'data'
    os.makedirs(data_dir, exist_ok=True) # Cria a pasta 'data' se não existir
    file_path = os.path.join(data_dir, "brazilian_cities.json") # Nome do arquivo para cidades

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(brazilian_cities_by_state, f, ensure_ascii=False, indent=4)

    print(f"\nArquivo '{file_path}' gerado com sucesso com {len(brazilian_cities_by_state)} estados e seus municípios (cidades).")

if __name__ == "__main__":
    generate_brazilian_cities_json()
