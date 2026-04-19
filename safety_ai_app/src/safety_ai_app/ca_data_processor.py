import ftplib
import pandas as pd
import os
import logging
from datetime import datetime, timedelta
import streamlit as st
import zipfile
import socket

logger = logging.getLogger(__name__)

FTP_TIMEOUT_SECONDS = 30

# --- CONSTANTES ATUALIZADAS ---
FTP_HOST = "ftp.mtps.gov.br"
FTP_PATH = "portal/fiscalizacao/seguranca-e-saude-no-trabalho/caepi/"
FTP_FILENAME = "tgg_export_caepi.zip"
EXTRACTED_FILENAME = "tgg_export_caepi.txt"

LOCAL_DATA_DIR = os.path.join("data")
LOCAL_CA_FILE = os.path.join(LOCAL_DATA_DIR, "ca_data.parquet")
LAST_UPDATE_FILE = os.path.join(LOCAL_DATA_DIR, "ca_last_update.txt")

class CADataProcessor:
    def __init__(self):
        os.makedirs(LOCAL_DATA_DIR, exist_ok=True)

    def _download_ca_file(self, local_zip_path: str) -> bool:
        """
        Baixa o arquivo CA (agora um ZIP) do servidor FTP usando ftplib.
        Tenta usar o caminho sem a barra inicial, como o pacote Go parece fazer.
        """
        full_ftp_file_path_no_leading_slash = f"{FTP_PATH}{FTP_FILENAME}"
        
        logger.info(f"Iniciando download do arquivo CA do FTP: {FTP_HOST}/{full_ftp_file_path_no_leading_slash}")
        try:
            with ftplib.FTP(FTP_HOST, timeout=FTP_TIMEOUT_SECONDS) as ftp:
                ftp.login()
                with open(local_zip_path, 'wb') as fp:
                    ftp.retrbinary(f'RETR {full_ftp_file_path_no_leading_slash}', fp.write)
            logger.info(f"Download do arquivo CA ZIP concluído para: {local_zip_path}")
            return True
        except (socket.timeout, ftplib.error_temp, OSError) as e:
            logger.warning(f"FTP do Ministério do Trabalho temporariamente indisponível: {e}. Será utilizado o arquivo local se disponível.")
            return False
        except ftplib.all_errors as e:
            logger.warning(f"Erro de conexão FTP: {e}. Será utilizado o arquivo local se disponível.")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado durante o download do arquivo CA: {e}", exc_info=True)
            return False

    def _parse_ca_txt_to_df(self, txt_path: str) -> pd.DataFrame:
        """
        Faz o parsing do arquivo TXT de CA para um DataFrame do Pandas.
        """
        logger.info(f"Iniciando parsing do arquivo CA: {txt_path}")
        try:
            df = None
            # CORREÇÃO AQUI: Prioriza UTF-8, depois cp1252, latin1/iso-8859-1
            encodings_to_try = ['utf-8', 'cp1252', 'latin1', 'iso-8859-1'] 
            for encoding in encodings_to_try:
                try:
                    df = pd.read_csv(txt_path, sep='|', encoding=encoding, low_memory=False)
                    logger.debug(f"DEBUG: Arquivo CA lido com sucesso usando encoding: {encoding}")
                    break # Sai do loop se a leitura for bem-sucedida
                except UnicodeDecodeError:
                    logger.debug(f"DEBUG: Falha ao ler arquivo CA com encoding: {encoding}. Tentando o próximo.")
                    continue
                except Exception as e:
                    logger.error(f"Erro inesperado ao tentar ler com encoding {encoding}: {e}", exc_info=True)
                    continue
            
            if df is None:
                raise Exception("Não foi possível ler o arquivo TXT com nenhuma das codificações tentadas.")

            # Limpa e padroniza os nomes das colunas
            df.columns = [col.strip().upper() for col in df.columns]
            
            # Mapeamento de colunas para nomes mais amigáveis e consistentes
            column_mapping = {
                'NR REGISTRO CA': 'ca_numero',
                'EQUIPAMENTO': 'equipamento_tipo',
                'DESCRICAO': 'descricao_detalhada',
                'DESCRICAO EQUIPAMENTO': 'descricao_detalhada',
                'FABRICANTE': 'fabricante_nome',
                'SITUACAO': 'situacao_ca',
                'VALIDADE': 'validade_ca',
                'DATA DE VALIDADE': 'validade_ca',
                'REFERENCIA': 'referencia_fabricante',
                'PROCESSO': 'processo_numero',
                'DATA_REGISTRO': 'data_registro_ca',
                'UF': 'fabricante_uf',
                'CNPJ': 'fabricante_cnpj',
                'RAZAO_SOCIAL': 'fabricante_razao_social',
                'NATUREZA': 'natureza_equipamento',
                'APROVACAO': 'aprovacao_ca',
                'MARCA CA': 'marca_ca',
                'COR': 'cor_equipamento',
                'APROVADO PARA LAUDO': 'aprovado_laudo',
                'RESTRICAO LAUDO': 'restricao_laudo',
                'OBSERVACAO ANALISE LAUDO': 'observacao_laudo',
                'CNPJ LABORATORIO': 'cnpj_laboratorio',
                'RAZAO SOCIAL LABORATORIO': 'razao_social_laboratorio',
                'NR LAUDO': 'nr_laudo',
                'NORMA': 'norma_referencia',
            }
            
            # Filtra o mapeamento para incluir apenas colunas que realmente existem no DataFrame
            actual_column_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
            df.rename(columns=actual_column_mapping, inplace=True)

            logger.debug(f"DEBUG: Colunas após renomear em _parse_ca_txt_to_df: {df.columns.tolist()}")
            if 'ca_numero' not in df.columns:
                logger.error("ERRO: A coluna 'ca_numero' está faltando após o parsing e renomeação em _parse_ca_txt_to_df!")
                raise ValueError("Crítico: A coluna 'ca_numero' não foi encontrada após o parsing e renomeação.")

            # Converte colunas para os tipos de dados corretos
            if 'ca_numero' in df.columns:
                df['ca_numero'] = df['ca_numero'].astype(str).str.strip()
            if 'validade_ca' in df.columns:
                df['validade_ca'] = pd.to_datetime(df['validade_ca'], errors='coerce', format='%d/%m/%Y')
            if 'data_registro_ca' in df.columns:
                df['data_registro_ca'] = pd.to_datetime(df['data_registro_ca'], errors='coerce', format='%d/%m/%Y')
            
            # DEBUG: Loga as primeiras linhas para verificar a codificação
            logger.debug(f"DEBUG: Primeiras 5 linhas do DataFrame após parsing e renomeação:\n{df.head().to_string()}")

            logger.info(f"Parsing do arquivo CA concluído. {len(df)} registros carregados.")
            return df
        except Exception as e:
            logger.error(f"Erro ao fazer parse do arquivo CA: {e}", exc_info=True)
            raise

    def _should_update_data(self) -> bool:
        """
        Verifica se os dados de CA precisam ser atualizados.
        """
        if not os.path.exists(LOCAL_CA_FILE):
            logger.info("Arquivo CA local (parquet) não encontrado. Necessário baixar nova versão.")
            return True
        
        if os.path.exists(LAST_UPDATE_FILE):
            with open(LAST_UPDATE_FILE, 'r') as f:
                last_update_str = f.read().strip()
            try:
                last_update_date = datetime.strptime(last_update_str, "%Y-%m-%d").date()
                if datetime.now().date() > last_update_date:
                    logger.info("Dados CA desatualizados (data). Necessário baixar nova versão.")
                    return True
            except ValueError:
                logger.warning("Formato de data inválido em ca_last_update.txt. Forçando atualização.")
                return True
        else:
            logger.info("Arquivo ca_last_update.txt não encontrado. Forçando atualização.")
            return True
        
        return False

    def _update_ca_data(self) -> bool:
        """
        Coordena o processo de download do ZIP, descompactação, parsing e salvamento dos dados.
        """
        local_zip_path = os.path.join(LOCAL_DATA_DIR, FTP_FILENAME)
        local_txt_path = os.path.join(LOCAL_DATA_DIR, EXTRACTED_FILENAME)

        try:
            if self._download_ca_file(local_zip_path):
                logger.info(f"Arquivo CA ZIP baixado com sucesso para: {local_zip_path}")
                
                logger.info(f"Descompactando {local_zip_path} para {LOCAL_DATA_DIR}...")
                with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
                    zip_ref.extract(EXTRACTED_FILENAME, LOCAL_DATA_DIR)
                logger.info("Arquivo CA TXT descompactado com sucesso.")

                df = self._parse_ca_txt_to_df(local_txt_path)
                df.to_parquet(LOCAL_CA_FILE, index=False)
                logger.info(f"Dados CA salvos em {LOCAL_CA_FILE}")
                
                with open(LAST_UPDATE_FILE, 'w') as f:
                    f.write(datetime.now().strftime("%Y-%m-%d"))
                
                return True
            else:
                logger.error("Falha no download do arquivo CA ZIP.")
                return False
        except Exception as e:
            logger.error(f"Falha ao atualizar dados CA: {e}", exc_info=True)
            return False
        finally:
            if os.path.exists(local_zip_path):
                os.remove(local_zip_path)
                logger.info(f"Arquivo ZIP temporário removido: {local_zip_path}")
            if os.path.exists(local_txt_path):
                os.remove(local_txt_path)
                logger.info(f"Arquivo TXT temporário removido: {local_txt_path}")

    @st.cache_resource(ttl=timedelta(hours=24))
    def _get_cached_ca_data(_self) -> pd.DataFrame: # Mantido _self para compatibilidade com st.cache_resource
        """
        Obtém os dados de CA, usando cache do Streamlit e lógica de atualização.
        """
        if _self._should_update_data():
            logger.info("Atualizando dados CA...")
            with st.spinner("Atualizando base de dados de CA... Isso pode levar alguns segundos."):
                if _self._update_ca_data():
                    logger.info("Dados CA atualizados com sucesso.")
                    df = pd.read_parquet(LOCAL_CA_FILE)
                    logger.debug(f"DEBUG: Após _update_ca_data e pd.read_parquet: df.empty={df.empty}, 'ca_numero' in df.columns={'ca_numero' in df.columns}, df.columns={df.columns.tolist()}")
                    _self._log_ca_data_details(df)
                    return df
                else:
                    logger.warning("Falha ao atualizar dados CA. Tentando carregar versão local antiga.")
                    if os.path.exists(LOCAL_CA_FILE):
                        st.warning("⚠️ FTP do Ministério do Trabalho temporariamente indisponível. Utilizando dados locais em cache.")
                        df = pd.read_parquet(LOCAL_CA_FILE)
                        logger.debug(f"DEBUG: Após falha na atualização, carregando parquet antigo: df.empty={df.empty}, 'ca_numero' in df.columns={'ca_numero' in df.columns}, df.columns={df.columns.tolist()}")
                        _self._log_ca_data_details(df)
                        return df
                    else:
                        st.error("Não foi possível carregar ou atualizar os dados de CA. Nenhuma versão local disponível.")
                        return pd.DataFrame()
        elif os.path.exists(LOCAL_CA_FILE):
            logger.info(f"Carregando dados CA de {LOCAL_CA_FILE}")
            df = pd.read_parquet(LOCAL_CA_FILE)
            logger.debug(f"DEBUG: Após carregar do parquet existente: df.empty={df.empty}, 'ca_numero' in df.columns={'ca_numero' in df.columns}, df.columns={df.columns.tolist()}")
            _self._log_ca_data_details(df)
            return df
        else:
            st.error("Não foi possível carregar os dados de CA. Nenhuma versão local disponível.")
            return pd.DataFrame()

    def _log_ca_data_details(self, df: pd.DataFrame):
        """Logs detailed information about the ca_numero column for debugging."""
        logger.debug(f"DEBUG: In _log_ca_data_details - df.empty={df.empty}, 'ca_numero' in df.columns={'ca_numero' in df.columns}")
        if not df.empty and 'ca_numero' in df.columns:
            logger.debug(f"DEBUG: Total de registros no DataFrame: {len(df)}")
            logger.debug(f"DEBUG: Tipo da coluna 'ca_numero': {df['ca_numero'].dtype}")
            logger.debug(f"DEBUG: Amostra da coluna 'ca_numero' (primeiros 5):\n{df['ca_numero'].head().to_string()}")
            
            null_count = df['ca_numero'].isnull().sum()
            empty_string_count = (df['ca_numero'] == '').sum()
            logger.debug(f"DEBUG: Contagem de valores nulos em 'ca_numero': {null_count}")
            logger.debug(f"DEBUG: Contagem de strings vazias em 'ca_numero': {empty_string_count}")

            target_ca_numbers = ['9722', '15649', '34082']
            for target_ca in target_ca_numbers:
                cleaned_ca_numbers = df['ca_numero'].astype(str).str.strip()
                
                if target_ca in cleaned_ca_numbers.tolist():
                    logger.debug(f"DEBUG: CA '{target_ca}' ENCONTRADO na coluna 'ca_numero' (correspondência exata após limpeza).")
                else:
                    logger.debug(f"DEBUG: CA '{target_ca}' NÃO ENCONTRADO na coluna 'ca_numero' (correspondência exata após limpeza).")
                    if cleaned_ca_numbers.str.contains(target_ca, case=False, na=False).any():
                        logger.debug(f"DEBUG: CA '{target_ca}' ENCONTRADO na coluna 'ca_numero' (contém após limpeza).")
                    else:
                        logger.debug(f"DEBUG: CA '{target_ca}' NÃO ENCONTRADO de forma alguma na coluna 'ca_numero'.")
        else:
            logger.debug("DEBUG: DataFrame vazio ou coluna 'ca_numero' não encontrada para log de detalhes (condição inicial falhou).")


    def get_ca_data(self) -> pd.DataFrame:
        """
        Método público para obter os dados de CA.
        """
        return self._get_cached_ca_data()

    def search_ca(self, search_term: str) -> pd.DataFrame:
        """
        Realiza uma busca nos dados de CA.
        """
        df = self.get_ca_data()
        if df.empty:
            logger.info("DataFrame de CA vazio, retornando sem resultados.")
            return pd.DataFrame()

        search_term_processed = search_term.strip().lower()
        logger.debug(f"DEBUG: Termo de busca original: '{search_term}'")
        logger.debug(f"DEBUG: Termo de busca processado (strip().lower()): '{search_term_processed}'")
        
        mask = pd.Series([False] * len(df), index=df.index)

        searchable_cols = [
            'ca_numero', 'equipamento_tipo', 'descricao_detalhada',
            'fabricante_nome', 'referencia_fabricante', 'aprovacao_ca',
            'situacao_ca', 'marca_ca', 'cor_equipamento' # Adicionando mais colunas para busca
        ]
        
        # 1. Tentar correspondência exata para 'ca_numero'
        if 'ca_numero' in df.columns:
            ca_numbers_cleaned = df['ca_numero'].astype(str).str.strip().fillna('')
            exact_match_mask = (ca_numbers_cleaned == search_term_processed)
            
            if exact_match_mask.any():
                logger.debug(f"DEBUG: Correspondência EXATA encontrada na coluna 'ca_numero' para '{search_term_processed}'.")
                mask = mask | exact_match_mask
            else:
                logger.debug(f"DEBUG: Nenhuma correspondência EXATA encontrada na coluna 'ca_numero' para '{search_term_processed}'.")

        # 2. Tentar correspondência 'contains' para todas as colunas (incluindo ca_numero para busca parcial)
        for col in searchable_cols:
            if col in df.columns:
                col_data = df[col].astype(str).str.strip().fillna('')
                col_contains_mask = col_data.str.contains(search_term_processed, case=False, na=False)
                
                if col_contains_mask.any():
                    logger.debug(f"DEBUG: Coluna '{col}' - Correspondências 'CONTAINS' encontradas: {col_contains_mask.sum()}")
                
                mask = mask | col_contains_mask

        if not mask.any():
            logger.info(f"Nenhum CA encontrado para o termo '{search_term}'.")
            logger.debug(f"DEBUG: Máscara final resultou em 0 correspondências.")
            return pd.DataFrame()

        results = df[mask]
        logger.debug(f"DEBUG: Total de correspondências encontradas: {len(results)}")
        logger.debug(f"DEBUG: Amostra dos resultados (primeiros 5 CAs): {results['ca_numero'].head().tolist()}")
        return results