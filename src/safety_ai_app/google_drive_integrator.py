import os
import pickle
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.oauth2 import service_account # Importação adicional para conta de serviço
import streamlit as st

# =====================================================================================
# Variáveis de Configuração
# =====================================================================================

# Onde o arquivo credentials.json (do GCP) está localizado para autenticação do USUÁRIO.
CLIENT_SECRETS_FILE = os.path.join(Path(__file__).resolve().parents[2], 'credentials.json')

# Onde as credenciais do usuário (token.pickle) serão armazenadas.
TOKEN_FILE = os.path.join(Path(__file__).resolve().parents[2], 'token.pickle')

# Onde o arquivo JSON da conta de serviço está localizado para autenticação do APLICATIVO.
SERVICE_ACCOUNT_KEY_FILE = os.path.join(Path(__file__).resolve().parents[2], 'service_account_key.json')

# Scopes necessários para acessar o Google Drive.
# drive.readonly: Permite visualizar arquivos e metadados.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly'] 

# ID da pasta do "Nosso Drive" (Conhecimento Base do Aplicativo)
# Obtido do seu Google Drive pessoal e compartilhado com a conta de serviço.
OUR_DRIVE_FOLDER_ID = "1CyjzomEqd2-acm9EkEAAbS2NxXNCIzKY"

# =====================================================================================
# Funções de Autenticação
# =====================================================================================

def get_google_drive_service_user():
    """
    Autentica o usuário com o Google Drive e retorna um objeto de serviço do Drive API.
    Gerencia o fluxo OAuth2 e armazena/recarrega tokens.
    """
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(TOKEN_FILE, 'wb') as token_file_refreshed:
                    pickle.dump(creds, token_file_refreshed)
            except Exception as e:
                st.warning(f"⚠️ Erro ao renovar o token do usuário: {e}. Será necessária uma nova autenticação.")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                st.rerun()
                return None
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            flow.redirect_uri = 'http://localhost:8501'
            auth_url, _ = flow.authorization_url(prompt='consent')

            st.write("---")
            st.warning("⚠️ **Autenticação de Usuário do Google Drive Necessária**")
            st.markdown(f"Olá, Leo! Por favor, clique no link abaixo para autorizar o SafetyAI a acessar **seu** Google Drive:")
            st.markdown(f"[Autorizar Meu Google Drive]({auth_url})")
            st.write("Após a autorização, você será redirecionado de volta para esta página.")
            st.write("---")

            query_params = st.query_params
            if 'code' in query_params:
                authorization_code = query_params['code'] 
                
                try:
                    flow.fetch_token(code=authorization_code)
                    creds = flow.credentials
                    
                    with open(TOKEN_FILE, 'wb') as token_file_new:
                        pickle.dump(creds, token_file_new)

                    st.query_params.clear() 
                    st.success("✅ Autenticação de usuário bem-sucedida! Carregando Google Drive...")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao autenticar usuário: {e}. Por favor, tente novamente.")
                    if os.path.exists(TOKEN_FILE):
                        os.remove(TOKEN_FILE)
                    st.stop()
            else:
                st.stop()
    
    if creds:
        service = build('drive', 'v3', credentials=creds)
        return service
    else:
        return None


def get_service_account_drive_service():
    """
    Autentica com o Google Drive usando uma Conta de Serviço e retorna um objeto de serviço.
    Ideal para acesso programático ao "Nosso Drive" (conhecimento base do aplicativo).
    """
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_KEY_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        return service
    except FileNotFoundError:
        st.error(f"❌ Erro: Arquivo da chave da conta de serviço não encontrado em: {SERVICE_ACCOUNT_KEY_FILE}")
        st.info("Por favor, siga os passos para criar uma conta de serviço e baixar o arquivo JSON.")
        return None
    except Exception as e:
        st.error(f"❌ Erro ao autenticar com a conta de serviço: {e}")
        st.info("Verifique se o arquivo da chave está correto e se a API do Google Drive está ativada no GCP.")
        return None

# =====================================================================================
# Exemplo de Uso
# =====================================================================================

if __name__ == '__main__':
    st.set_page_config(layout="wide")
    st.title("Teste de Integração Google Drive - SafetyAI")

    st.header("1. Acesso ao Nosso Drive (Conhecimento Base do Aplicativo)")
    st.write("Tentando obter o serviço do Google Drive via Conta de Serviço...")
    app_drive_service = get_service_account_drive_service()

    if app_drive_service:
        st.success("✅ Serviço do Google Drive do aplicativo obtido com sucesso!")
        st.write("Listando alguns arquivos do **Nosso Drive** (pasta compartilhada com a conta de serviço):")
        
        try:
            # Lista até 10 arquivos da pasta específica do "Nosso Drive"
            results = app_drive_service.files().list(
                pageSize=10, 
                q=f"'{OUR_DRIVE_FOLDER_ID}' in parents and trashed=false", # Filtra por pasta
                fields="nextPageToken, files(id, name, mimeType)").execute()
            items = results.get('files', [])

            if not items:
                st.info(f'Nenhum arquivo encontrado na pasta do Nosso Drive (ID: {OUR_DRIVE_FOLDER_ID}). Adicione alguns documentos lá!')
            else:
                for item in items:
                    st.write(f"- {item['name']} ({item['mimeType']}, ID: {item['id']})")
        except Exception as e:
            st.error(f"❌ Erro ao listar arquivos do Nosso Drive: {e}")

    st.markdown("---") # Separador visual

    st.header("2. Acesso ao Google Drive do Usuário")
    st.write("Tentando obter o serviço do Google Drive do usuário...")
    user_drive_service = get_google_drive_service_user()

    if user_drive_service:
        st.success("✅ Serviço do Google Drive do usuário obtido com sucesso!")
        st.write("Listando alguns arquivos do **Seu Drive Pessoal**:")
        
        try:
            # Lista até 10 arquivos do Google Drive do usuário (root)
            results = user_drive_service.files().list(
                pageSize=10, 
                fields="nextPageToken, files(id, name, mimeType)").execute()
            items = results.get('files', [])

            if not items:
                st.info('Nenhum arquivo encontrado no Drive Pessoal do usuário.')
            else:
                for item in items:
                    st.write(f"- {item['name']} ({item['mimeType']}, ID: {item['id']})")
        except Exception as e:
            st.error(f"❌ Erro ao listar arquivos do Drive Pessoal do usuário: {e}")
