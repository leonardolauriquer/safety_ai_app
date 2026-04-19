# Fluxo de Autenticacao

## Visao Geral

O SafetyAI utiliza Google OAuth 2.0 para autenticacao de usuarios, com um fluxo de tres etapas: Login > Sincronizacao > Aplicacao Principal.

---

## 1. Diagrama de Fluxo

```
┌────────────────┐
│  Usuario       │
│  Acessa App    │
└───────┬────────┘
        │
        ▼
┌────────────────┐    Nao
│  logged_in?    │───────────────────┐
└───────┬────────┘                   │
        │ Sim                        ▼
        │                   ┌────────────────┐
        │                   │  Login Page    │
        │                   │  (Google OAuth)│
        │                   └───────┬────────┘
        │                           │ Sucesso
        │                           │
        │◄──────────────────────────┘
        ▼
┌────────────────┐    Nao
│  sync_done?    │───────────────────┐
└───────┬────────┘                   │
        │ Sim                        ▼
        │                   ┌────────────────┐
        │                   │  Sync Page     │
        │                   │  (Google Drive)│
        │                   └───────┬────────┘
        │                           │ Completo
        │                           │
        │◄──────────────────────────┘
        ▼
┌────────────────┐
│  Main App      │
│  (Navegacao)   │
└────────────────┘
```

---

## 2. Estados de Sessao

### 2.1 Variaveis de Session State

| Variavel | Tipo | Descricao |
|----------|------|-----------|
| `logged_in` | `bool` | Usuario autenticado |
| `sync_done` | `bool` | Sincronizacao concluida |
| `user_email` | `str` | Email do usuario |
| `user_name` | `str` | Nome do usuario |
| `user_picture` | `str` | URL da foto do usuario |
| `current_page` | `str` | Pagina atual |

### 2.2 Inicializacao

```python
# web_app.py
def _initialize_session_state():
    defaults = {
        'logged_in': False,
        'sync_done': False,
        'user_email': None,
        'user_name': None,
        'user_picture': None,
        'current_page': 'home',
        'chat_history': [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
```

---

## 3. Pagina de Login

### 3.1 Funcao: `_render_login_page()`

### 3.2 Componentes

1. **Logo SafetyAI**: Com efeito neon glow
2. **Versao**: Badge "v2.0"
3. **Titulo**: "SafetyAI"
4. **Subtitulo**: Descricao do assistente
5. **Features**: Lista de recursos
   - Normas Regulamentadoras (NRs)
   - Consultas CBO, CID, CNAE e CA
   - Dimensionamento CIPA e SESMT
   - Geracao de documentos e Drive
6. **Botao Google**: "Entrar com Google"
7. **Texto de rodape**: Instrucao de login

### 3.3 Estilos Responsivos

```css
/* Desktop */
.login-card {
    max-width: 500px;
    padding: 2rem;
}

/* Tablet */
@media (max-width: 768px) {
    .login-card { max-width: 90%; }
}

/* Mobile altura pequena */
@media (max-height: 650px) {
    .features-list { display: none; }
    .logo { height: 80px; }
}
```

---

## 4. Google OAuth 2.0

### 4.1 Configuracao

```python
# Arquivo de credenciais
CREDENTIALS_FILE = "credentials.json"

# Escopos necessarios
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/drive.readonly',
]
```

### 4.2 Fluxo OAuth

```python
from google_auth_oauthlib.flow import InstalledAppFlow

def authenticate_user():
    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_FILE, 
        scopes=SCOPES
    )
    
    # Abre navegador para autenticacao
    credentials = flow.run_local_server(port=0)
    
    # Salva token para uso futuro
    with open('token_user.pickle', 'wb') as token:
        pickle.dump(credentials, token)
    
    return credentials
```

### 4.3 Verificacao de Token

```python
def get_user_credentials():
    credentials = None
    
    # Verifica token salvo
    if os.path.exists('token_user.pickle'):
        with open('token_user.pickle', 'rb') as token:
            credentials = pickle.load(token)
    
    # Token expirado ou invalido
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            credentials = authenticate_user()
    
    return credentials
```

---

## 5. Pagina de Sincronizacao

### 5.1 Arquivo: `sync_page.py`

### 5.2 Funcao: `render_page()`

### 5.3 Processo de Sincronizacao

```python
def sync_documents():
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 1. Conectar ao Google Drive
    status_text.text("Conectando ao Google Drive...")
    drive = GoogleDriveIntegrator()
    progress_bar.progress(10)
    
    # 2. Listar documentos na pasta
    status_text.text("Listando documentos...")
    files = drive.list_files_in_folder(KNOWLEDGE_BASE_FOLDER_ID)
    progress_bar.progress(30)
    
    # 3. Baixar novos/modificados
    status_text.text("Baixando documentos...")
    for i, file in enumerate(files):
        # Download e processamento
        progress_bar.progress(30 + (i / len(files)) * 50)
    
    # 4. Processar para ChromaDB
    status_text.text("Processando documentos...")
    process_documents_to_chromadb()
    progress_bar.progress(100)
    
    # 5. Marcar como concluido
    st.session_state['sync_done'] = True
```

### 5.4 Skip de Sincronizacao

O usuario pode pular a sincronizacao se:
- Ja possui dados no ChromaDB
- Quer apenas usar consultas (sem chat RAG)

---

## 6. Service Account (Acesso Automatizado)

### 6.1 Uso

A Service Account e usada para:
- Acessar pastas compartilhadas no Drive
- Baixar arquivos de referencia (CBO, CID, etc.)
- Sincronizacao automatica

### 6.2 Configuracao

```python
from google.oauth2 import service_account

def get_service_account_credentials():
    credentials = service_account.Credentials.from_service_account_file(
        'service_account.json',
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    return credentials
```

### 6.3 Diferenca de User vs Service Account

| Aspecto | User OAuth | Service Account |
|---------|------------|-----------------|
| Autenticacao | Interativa (navegador) | Automatica (JSON) |
| Acesso | Arquivos do usuario | Pastas compartilhadas |
| Token | Expira, precisa refresh | Nao expira |
| Uso | Login do usuario | Backend automatizado |

---

## 7. Logout

### 7.1 Funcao de Logout

```python
def logout():
    # Limpar session state
    st.session_state['logged_in'] = False
    st.session_state['sync_done'] = False
    st.session_state['user_email'] = None
    st.session_state['user_name'] = None
    st.session_state['user_picture'] = None
    st.session_state['chat_history'] = []
    
    # Remover token
    if os.path.exists('token_user.pickle'):
        os.remove('token_user.pickle')
    
    # Recarregar pagina
    st.rerun()
```

---

## 8. Seguranca

### 8.1 Boas Praticas

1. **Nao commitar credenciais**: `credentials.json` e `service_account.json` no `.gitignore`
2. **Tokens temporarios**: OAuth tokens expiram e sao renovados
3. **Escopos minimos**: Solicitar apenas permissoes necessarias
4. **HTTPS**: Todas as comunicacoes via HTTPS

### 8.2 Arquivos Sensiveis

| Arquivo | Conteudo | Gitignore |
|---------|----------|-----------|
| `credentials.json` | OAuth Client ID/Secret | Sim |
| `service_account.json` | Chave da Service Account | Sim |
| `token_user.pickle` | Token do usuario | Sim |
| `.env` | Variaveis de ambiente | Sim |

---

## 9. Tratamento de Erros

### 9.1 Erros Comuns

| Erro | Causa | Solucao |
|------|-------|---------|
| `invalid_grant` | Token expirado | Re-autenticar |
| `access_denied` | Permissao negada | Verificar escopos |
| `invalid_client` | Client ID invalido | Verificar credentials.json |
| `quota_exceeded` | Limite de API | Aguardar ou aumentar quota |

### 9.2 Tratamento

```python
try:
    credentials = get_user_credentials()
except google.auth.exceptions.RefreshError:
    st.error("Sessao expirada. Por favor, faca login novamente.")
    logout()
except Exception as e:
    st.error(f"Erro de autenticacao: {e}")
    logger.error(f"Auth error: {e}", exc_info=True)
```

---

## 10. URL Parameters

### 10.1 Parametros Suportados

| Parametro | Valor | Efeito |
|-----------|-------|--------|
| `sync_done` | `true` | Pula sincronizacao |
| `page` | Nome da pagina | Vai direto para pagina |

### 10.2 Exemplo

```
https://safetyai.streamlit.app/?sync_done=true&page=chat
```
