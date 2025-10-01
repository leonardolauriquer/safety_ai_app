@echo off
rem Define a codificacao UTF-8 para o console, melhorando a compatibilidade com caracteres especiais
rem e garantindo que mensagens de erro ou logs com caracteres acentuados sejam exibidos corretamente.
chcp 65001 > nul
setlocal enabledelayedexpansion

rem Define o diretorio do projeto como o diretorio onde o script esta sendo executado.
rem Isso garante que todos os comandos Git sejam executados no contexto correto do repositorio.
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo.
echo ===========================================
echo === Enviando Projeto para o GitHub ====
===========================================
echo.

echo ETAPA 0: Verificando a instalacao do Git...
rem Verifica se o comando 'git' esta acessivel no PATH do sistema.
rem 'git --version' e um comando leve que verifica a presenca do Git.
rem '2>&1' redireciona stderr para stdout, e '>nul' descarta toda a saida.
git --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ERRO: Git nao encontrado ou nao acessivel no PATH.
    echo Por favor, verifique se o Git esta instalado corretamente e se seu executavel esta no PATH do sistema.
    echo Voce pode adicionar o Git ao PATH do sistema nas configuracoes de Variaveis de Ambiente.
    pause "Pressione qualquer tecla para sair e resolver o problema de instalacao do Git."
    goto :eof
)
echo Git encontrado e pronto para uso.
echo.

echo ETAPA 1: Inicializando ou verificando o repositorio Git...
rem Verifica se a pasta .git existe, indicando um repositorio ja inicializado.
rem 'git init' e idempotente; se ja for um repositorio, ele apenas re-inicializa sem perder dados.
if not exist ".git" (
    echo Repositorio Git nao encontrado. Inicializando um novo repositorio local...
    git init
    if !errorlevel! neq 0 (
        echo ERRO: Falha ao inicializar o repositorio Git. Codigo de saida: !errorlevel!
        echo Verifique permissoes de diretorio ou se ha algum problema com a instalacao do Git.
        pause "Pressione qualquer tecla para sair e investigar o erro de 'git init'."
        goto :eof
    )
    echo Repositorio Git inicializado com sucesso.
) else (
    echo Repositorio Git ja inicializado.
)
echo.

echo ETAPA 2: Adicionando arquivos ao staging area...
echo Debug: Definindo TEMP_ADD_OUTPUT.
set "TEMP_ADD_OUTPUT=!TEMP!\git_add_output.tmp"
echo Debug: Executando git add.
git add --all -- ":!service_account_key.json" ":!run.bat" >"!TEMP_ADD_OUTPUT!" 2>&1
echo Debug: git add finalizado. Errorlevel e !errorlevel!.
set "add_result=!errorlevel!"

if !add_result! neq 0 (
    echo Debug: git add retornou errorlevel diferente de zero: !add_result!.
    echo Debug: Conteudo de TEMP_ADD_OUTPUT:
    type "!TEMP_ADD_OUTPUT!"
)

echo Debug: Verificando a existencia de TEMP_ADD_OUTPUT.
if exist "!TEMP_ADD_OUTPUT!" (
    echo Debug: TEMP_ADD_OUTPUT existe. Tentando findstr.
    findstr /i /c:"The following paths are ignored by one of your .gitignore files:" "!TEMP_ADD_OUTPUT!" >nul 2>&1
    echo Debug: findstr completado. Errorlevel e !errorlevel!.
    if !errorlevel! equ 0 (
        echo Aviso: Alguns arquivos foram ignorados conforme .gitignore ou exclusao explicita. Nao e um erro fatal.
        echo Debug: Forcando add_result para 0.
        set "add_result=0"
    ) else (
        echo Debug: findstr nao encontrou o aviso de "ignored files".
    )
) else (
    echo Debug: TEMP_ADD_OUTPUT nao existe apos git add. Pulando verificacao findstr.
)
echo Debug: Final add_result antes da verificacao de erro e !add_result!.

if !add_result! neq 0 (
    echo ERRO: Falha ao adicionar arquivos ao staging area. Codigo de saida: !add_result!
    echo Isso pode indicar problemas de permissao, arquivos bloqueados ou uma falha interna do Git.
    echo Verifique o output do comando 'git add' para mais detalhes.
    pause "Pressione qualquer tecla para sair e investigar o erro de 'git add'."
    if exist "!TEMP_ADD_OUTPUT!" del "!TEMP_ADD_OUTPUT!" 2>nul
    goto :eof
)
echo Arquivos adicionados ao staging area (excluindo service_account_key.json e run.bat).
if exist "!TEMP_ADD_OUTPUT!" del "!TEMP_ADD_OUTPUT!" 2>nul
echo.

echo ETAPA 3: Verificando e fazendo o commit das alteracoes...
rem 'git diff --cached --quiet' verifica se ha alteracoes no staging area prontas para commit.
rem Retorna 0 se nao houver diferencas (nada para commitar) e 1 se houver diferencas.
git diff --cached --quiet
set "changes_staged=!errorlevel!"
echo Debug: git diff --cached --quiet retornou !changes_staged!

rem CORRECAO CRITICA: Se 'changes_staged' for 0, significa que nao ha diferencas no staging area,
rem entao nao ha nada para commitar e o passo de commit deve ser ignorado para evitar commits vazios.
if !changes_staged! equ 0 (
    echo Sub-etapa 3.1: Nenhuma alteracao staged para commitar. Ignorando commit.
    goto :SKIP_COMMIT_SECTION
)

:: --- INICIO DA SECAO DE COMMIT ---
rem Cria arquivos temporarios para armazenar a mensagem de commit e o timestamp.
set "TEMP_COMMIT_MSG_FILE=!TEMP!\git_commit_msg.tmp"
set "TEMP_TIMESTAMP_FILE=!TEMP!\git_timestamp.tmp"

rem Gera um timestamp formatado para a mensagem de commit automatica usando PowerShell.
rem O PowerShell e usado para garantir um formato de data/hora consistente e robusto.
powershell -Command "(Get-Date -Format 'yyyy-MM-dd HH-mm-ss').ToString()" > "!TEMP_TIMESTAMP_FILE!" 2>nul
set /p "TIMESTAMP_FOR_COMMIT="<"!TEMP_TIMESTAMP_FILE!"
del "!TEMP_TIMESTAMP_FILE!" 2>nul

set "FULL_COMMIT_MESSAGE=Automated commit: !TIMESTAMP_FOR_COMMIT!"

echo !FULL_COMMIT_MESSAGE! > "!TEMP_COMMIT_MSG_FILE!"

echo Sub-etapa 3.1: Tentando commit com a mensagem: "!FULL_COMMIT_MESSAGE!"
rem 'git commit -F <file>' le a mensagem de commit de um arquivo.
git commit -F "!TEMP_COMMIT_MSG_FILE!"
set "commit_result=!errorlevel!"
echo Debug: commit_result apos git commit e !commit_result!

if !commit_result! neq 0 (
    echo ERRO: Falha ao fazer o commit. Codigo de saida: !commit_result!
    echo Verifique se ha conflitos ou se o Git encontrou algum problema durante o commit.
    echo Isso pode ocorrer se o repositorio estiver em um estado de merge pendente ou se houver ganchos (hooks) Git falhando.
    pause "Pressione qualquer tecla para sair e investigar o erro de 'git commit'."
    del "!TEMP_COMMIT_MSG_FILE!" 2>nul
    goto :eof
)

echo Sub-etapa 3.2: Alteracoes commitadas com sucesso.
del "!TEMP_COMMIT_MSG_FILE!" 2>nul
:: --- FIM DA SECAO DE COMMIT ---

:SKIP_COMMIT_SECTION
echo Debug: FINALIZOU ETAPA 3. PROSSEGUINDO...
echo.

echo ETAPA 4: Configurando o repositorio remoto 'origin'...
rem 'origin' e o nome padrao para o repositorio remoto principal.
rem Verifica se o remoto 'origin' ja existe usando 'git remote get-url'.
git remote get-url origin >nul 2>&1
if !errorlevel! neq 0 (
    echo 'origin' remoto nao encontrado. Adicionando...
    git remote add origin https://github.com/leonardolauriquer/safety_ai_app.git
    if !errorlevel! neq 0 (
        echo ERRO: Falha ao adicionar o remoto 'origin'. Codigo de saida: !errorlevel!
        echo Verifique a URL do repositorio ou sua conexao de rede.
        pause "Pressione qualquer tecla para sair e investigar o erro de 'git remote add'."
    goto :eof
    )
) else (
    echo 'origin' remoto ja existe. Verificando URL...
    rem Captura a URL atual do remoto 'origin'.
    for /f "delims=" %%i in ('git remote get-url origin') do set "current_origin_url=%%i"
    rem Compara a URL atual com a URL esperada, ignorando case-sensitivity para maior robustez.
    if /i "!current_origin_url!" neq "https://github.com/leonardolauriquer/safety_ai_app.git" (
        echo A URL remota 'origin' e diferente da esperada. Atualizando para a URL correta...
        git remote set-url origin https://github.com/leonardolauriquer/safety_ai_app.git
        if !errorlevel! neq 0 (
            echo ERRO: Falha ao atualizar a URL remota 'origin'. Codigo de saida: !errorlevel!
            echo Pode haver um problema de permissao ou a URL fornecida nao e valida.
            pause "Pressione qualquer tecla para sair e investigar o erro de 'git remote set-url'."
            goto :eof
        )
    ) else (
        echo URL remota 'origin' ja esta correta.
    )
)
echo Repositorio remoto 'origin' configurado.
echo.

echo ETAPA 5: Enviando alteracoes para a branch 'main' no GitHub...
rem REMOVIDO: git pull - apenas enviamos, nunca baixamos
rem O '-u' (ou '--set-upstream') configura o branch remoto para o branch local,
rem facilitando futuros 'git pull' e 'git push' sem especificar 'origin main'.
rem Isso e uma boa pratica para a primeira vez que voce faz push de um branch.
git push -u origin main
if !errorlevel! neq 0 (
    echo ERRO: Falha ao enviar para o GitHub. Verifique credenciais, permissoes ou conflitos. Codigo de saida: !errorlevel!
    echo Causa comum: Alteracoes no remoto que conflitam com as locais.
    echo Se necessario, use 'git push --force-with-lease origin main' manualmente (COM CUIDADO).
    echo Verifique tambem se suas credenciais Git (token de acesso pessoal ou SSH key) estao configuradas corretamente.
    pause "Pressione qualquer tecla para sair e investigar o erro de 'git push'."
    goto :eof
)
echo.
cls
rem Limpa a tela antes da mensagem final para uma experiencia mais limpa e focada.
echo ===============================================
echo === Projeto enviado com sucesso para o GitHub! ===
===============================================
echo.

pause
endlocal
goto :eof