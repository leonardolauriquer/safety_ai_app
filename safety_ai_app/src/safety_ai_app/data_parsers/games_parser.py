import logging
import os
import tempfile
import shutil
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

CROSSWORD_REQUIRED_COLUMNS = ['Dificuldade', 'Dica', 'Resposta', 'Caracteres da resposta']
SHOW_DO_MILHAO_REQUIRED_COLUMNS = [
    'Pergunta', 'Alternativa A', 'Alternativa B',
    'Alternativa C', 'Alternativa D', 'Resposta Correta', 'Dificuldade'
]


def parse_crossword_rows(df: pd.DataFrame) -> Optional[List[Dict]]:
    if not all(col in df.columns for col in CROSSWORD_REQUIRED_COLUMNS):
        logger.error(
            f"DataFrame sem colunas esperadas para palavras cruzadas: "
            f"{CROSSWORD_REQUIRED_COLUMNS}. Encontradas: {df.columns.tolist()}"
        )
        return None
    rows = df[CROSSWORD_REQUIRED_COLUMNS].to_dict(orient='records')
    for row in rows:
        row['Resposta'] = str(row['Resposta']).strip().upper()
        row['Dica'] = str(row['Dica']).strip()
        row['Dificuldade'] = str(row['Dificuldade']).strip().upper()
    logger.info(f"Palavras cruzadas parseadas: {len(rows)} entradas.")
    return rows


def parse_show_do_milhao_rows(df: pd.DataFrame) -> Optional[List[Dict]]:
    if not all(col in df.columns for col in SHOW_DO_MILHAO_REQUIRED_COLUMNS):
        logger.error(
            f"DataFrame sem colunas esperadas para Show do Milhão: "
            f"{SHOW_DO_MILHAO_REQUIRED_COLUMNS}. Encontradas: {df.columns.tolist()}"
        )
        return None
    rows = df[SHOW_DO_MILHAO_REQUIRED_COLUMNS].to_dict(orient='records')
    for row in rows:
        for key, value in row.items():
            if isinstance(value, str):
                row[key] = value.strip()
    logger.info(f"Show do Milhão parseado: {len(rows)} entradas.")
    return rows


def download_and_parse_crossword(downloader: Any, file_id: str, file_name: str) -> Optional[List[Dict[str, Any]]]:
    """Download the crossword Excel from Drive using *downloader* and parse it."""
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file_name)
    try:
        downloader.download_to_path(file_id, temp_path)
        if not os.path.exists(temp_path):
            logger.error(f"Arquivo de palavras cruzadas '{file_name}' não foi baixado.")
            return None
        df = pd.read_excel(temp_path)
        return parse_crossword_rows(df)
    except Exception as e:
        logger.error(f"Erro ao baixar/parsear palavras cruzadas '{file_name}': {e}", exc_info=True)
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def download_and_parse_show_do_milhao(downloader: Any, file_id: str, file_name: str) -> Optional[List[Dict[str, Any]]]:
    """Download the Show do Milhão Excel from Drive using *downloader* and parse it."""
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file_name)
    try:
        downloader.download_to_path(file_id, temp_path)
        if not os.path.exists(temp_path):
            logger.error(f"Arquivo Show do Milhão '{file_name}' não foi baixado.")
            return None
        df = pd.read_excel(temp_path)
        return parse_show_do_milhao_rows(df)
    except Exception as e:
        logger.error(f"Erro ao baixar/parsear Show do Milhão '{file_name}': {e}", exc_info=True)
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
