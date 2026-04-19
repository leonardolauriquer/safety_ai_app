"""Processador de dados de multas NR 28.

Lê uma planilha Excel do Google Drive e calcula penalidades com base
no número de funcionários, tipo de infração e reincidência.
"""
import os
import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from safety_ai_app.google_drive_integrator import GoogleDriveIntegrator

logger = logging.getLogger(__name__)


def format_currency_br(value: float) -> str:
    """Formata um float para o padrão monetário brasileiro (ex: 1.234,56)."""
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class FinesDataProcessor:
    """Processa dados de multas e infrações da NR 28 a partir de um arquivo Excel do Google Drive."""

    def __init__(
        self,
        google_drive_integrator: GoogleDriveIntegrator,
        drive_file_path: str,
        local_temp_dir: str,
    ) -> None:
        self.google_drive_integrator = google_drive_integrator
        self.drive_file_path = drive_file_path
        self.local_temp_dir = local_temp_dir
        self.excel_path = os.path.join(local_temp_dir, os.path.basename(drive_file_path))

        self.df_gradacao_sst: Optional[pd.DataFrame] = None
        self.df_gradacao_med: Optional[pd.DataFrame] = None
        self.df_itens: Optional[pd.DataFrame] = None

        self._load_and_process_data()

    def _load_and_process_data(self) -> None:
        """Baixa o arquivo Excel do Google Drive e carrega os dados das abas."""
        if not self.google_drive_integrator.download_file_by_path(
            self.drive_file_path, self.excel_path
        ):
            raise Exception(
                f"Não foi possível baixar o arquivo '{self.drive_file_path}' do Google Drive."
            )
        logger.info(f"Arquivo '{self.drive_file_path}' baixado com sucesso.")

        try:
            with pd.ExcelFile(self.excel_path) as xls:
                self.df_gradacao_sst = pd.read_excel(xls, sheet_name="MULTAS_EM_REAIS_SEG", header=0)
                self.df_gradacao_med = pd.read_excel(xls, sheet_name="MULTAS_EM_REAIS_MED", header=0)
                self.df_itens = pd.read_excel(xls, sheet_name="Itens", header=0)

            self._clean_data()

        except ValueError as e:
            try:
                xls_temp = pd.ExcelFile(self.excel_path)
                available_sheets = xls_temp.sheet_names
                xls_temp.close()
                msg = (
                    f"Erro ao carregar aba do Excel: {e}. "
                    f"Abas disponíveis: {', '.join(available_sheets)}."
                )
            except Exception as inner_e:
                msg = (
                    f"Erro ao carregar aba do Excel: {e}. "
                    f"Não foi possível listar as abas: {inner_e}"
                )
            logger.error(msg, exc_info=True)
            raise Exception(msg)

        except Exception as e:
            msg = f"Erro ao carregar ou processar dados do Excel do Drive: {e}"
            logger.error(msg, exc_info=True)
            raise Exception(msg)

        finally:
            if os.path.exists(self.excel_path):
                try:
                    os.remove(self.excel_path)
                    logger.info(f"Arquivo temporário '{self.excel_path}' removido.")
                except OSError as e:
                    logger.error(f"Erro ao remover arquivo temporário '{self.excel_path}': {e}", exc_info=True)

    def _clean_data(self) -> None:
        """Realiza a limpeza e padronização dos DataFrames carregados."""
        _range_map = {
            "01-10": "01 à 10", "11-25": "11 à 25", "26-50": "26 à 50",
            "51-100": "51 à 100", "101-250": "101 à 250",
            "251-500": "251 à 500", "501-1000": "501 à 1000",
            "Mais de 1000": "Mais de 1000",
        }

        for attr, sheet_label in [
            ("df_gradacao_sst", "MULTAS_EM_REAIS_SEG"),
            ("df_gradacao_med", "MULTAS_EM_REAIS_MED"),
        ]:
            df = getattr(self, attr)
            if df is None:
                continue
            df = df.copy()
            df.columns = ["infracao", "num_empregados", "minimo", "maximo", "reincidencia"]
            for col in ["minimo", "maximo", "reincidencia"]:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(".", "", regex=False)
                    .str.replace(",", ".", regex=False)
                )
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["num_empregados"] = df["num_empregados"].astype(str).replace(_range_map).str.strip()
            df["infracao"] = pd.to_numeric(df["infracao"], errors="coerce")
            setattr(self, attr, df)
            logger.info(f"DataFrame '{sheet_label}' limpo e processado.")

        if self.df_itens is not None:
            df = self.df_itens.copy()
            df.columns = ["nr", "anexo", "item_subitem", "codigo", "infracao", "tipo"]
            df = df.dropna(how="all")
            df["nr"] = pd.to_numeric(df["nr"], errors="coerce")
            df["anexo"] = df["anexo"].fillna("").astype(str)
            df["item_subitem"] = df["item_subitem"].astype(str)
            df["codigo"] = df["codigo"].astype(str)
            df["infracao"] = pd.to_numeric(df["infracao"], errors="coerce")
            df["tipo"] = df["tipo"].astype(str)
            self.df_itens = df
            logger.info("DataFrame 'Itens' limpo e processado.")

    def get_fines_data(self) -> Dict[str, Optional[pd.DataFrame]]:
        """Retorna os DataFrames processados."""
        return {
            "gradacao_sst": self.df_gradacao_sst,
            "gradacao_med": self.df_gradacao_med,
            "itens": self.df_itens,
        }

    def calculate_total_fine(
        self,
        employee_range_str: str,
        has_recidivism: bool,
        selected_item_codes: List[str],
    ) -> Tuple[float, float, float, List[Dict[str, Any]]]:
        """Calcula a multa total com base nos parâmetros fornecidos.

        Returns:
            Tupla (total_base, total_seg, total_med, detalhes_por_item).
        """
        total_base = 0.0
        total_seg = 0.0
        total_med = 0.0
        details: List[Dict[str, Any]] = []

        if self.df_itens is None or self.df_gradacao_sst is None or self.df_gradacao_med is None:
            logger.error("DataFrames de itens ou gradação de multas não carregados.")
            return 0.0, 0.0, 0.0, []

        for item_code in selected_item_codes:
            item_info = self.df_itens[self.df_itens["codigo"] == item_code]
            if item_info.empty:
                logger.warning(f"Item de infração '{item_code}' não encontrado.")
                continue

            item_infracao_level = pd.to_numeric(item_info["infracao"].iloc[0], errors="coerce")
            if pd.isna(item_infracao_level):
                logger.warning(f"Nível de infração inválido para o item '{item_code}'. Pulando.")
                continue

            item_tipo = item_info["tipo"].iloc[0]
            item_description = f"NR {item_info['nr'].iloc[0]} - {item_info['item_subitem'].iloc[0]}"

            if item_tipo == "SEG":
                gradacao_df = self.df_gradacao_sst
            elif item_tipo == "MED":
                gradacao_df = self.df_gradacao_med
            else:
                logger.warning(f"Tipo de infração desconhecido '{item_tipo}' para '{item_code}'. Pulando.")
                continue

            fine_data = gradacao_df[
                (pd.to_numeric(gradacao_df["infracao"], errors="coerce") == item_infracao_level)
                & (gradacao_df["num_empregados"] == employee_range_str)
            ]

            if fine_data.empty:
                logger.warning(
                    f"Dados de multa não encontrados para Infração {item_infracao_level}, "
                    f"Faixa '{employee_range_str}', Tipo '{item_tipo}'."
                )
                continue

            if has_recidivism:
                current_fine = fine_data["reincidencia"].iloc[0]
                fine_type = "Reincidência"
            else:
                current_fine = fine_data["maximo"].iloc[0]
                fine_type = "Base (Máximo)"

            total_base += current_fine
            if item_tipo == "SEG":
                total_seg += current_fine
            else:
                total_med += current_fine

            details.append({
                "item_codigo": item_code,
                "item_descricao": item_description,
                "tipo_infracao": item_tipo,
                "nivel_infracao": item_infracao_level,
                "faixa_empregados": employee_range_str,
                "valor_multa": current_fine,
                "base_calculo": fine_type,
            })

        return total_base, total_seg, total_med, details
