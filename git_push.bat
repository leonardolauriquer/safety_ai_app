@echo off
setlocal enabledelayedexpansion

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo.
echo ===========================================
echo === Enviando Projeto para o GitHub ====
echo ===========================================
echo.

echo ETAPA 1: Inicializando o repositorio Git...
if not exist ".git" (
    echo Inicializando o repositorio Git local...
    git init
    if !errorlevel! neq 0 (
        echo ERRO: Falha ao inicializar o repositorio Git.
        goto :eof
    )
    echo Repositorio Git inicializado.
) else (
    echo Repositorio Git ja inicializado.
)
echo.

echo ETAPA 2: Adicionando arquivos ao staging area...
git add .
if !errorlevel! neq 0 (
    echo ERRO: Falha ao adicionar arquivos.
    goto :eof
)
echo Arquivos adicionados.
echo.

echo ETAPA 3: Verificando e fazendo o commit das alteracoes...
git diff --cached --quiet
set "changes_staged=!errorlevel!"
echo Debug: git diff --cached --quiet returned !changes_staged!

if !changes_staged! neq 0 (
    set "TEMP_COMMIT_MSG_FILE=!TEMP!\git_commit_msg.tmp"
    set "TEMP_TIMESTAMP_FILE=!TEMP!\git_timestamp.tmp"
    
    :: Gera o timestamp via PowerShell e salva em um arquivo temporario.
    powershell -Command "(Get-Date -Format 'yyyy-MM-dd HH-mm-ss').ToString()" > "!TEMP_TIMESTAMP_FILE!" 2>nul
    
    :: Le o timestamp do arquivo temporario para uma variavel.
    set /p "TIMESTAMP_FOR_COMMIT="<"!TEMP_TIMESTAMP_FILE!"
    
    :: Monta a mensagem de commit completa.
    set "FULL_COMMIT_MESSAGE=Automated commit: !TIMESTAMP_FOR_COMMIT!"

    echo !FULL_COMMIT_MESSAGE! > "!TEMP_COMMIT_MSG_FILE!"
    
    echo Sub-etapa 3.1: Tentando commit lendo mensagem do arquivo: "!TEMP_COMMIT_MSG_FILE!"
    git commit -F "!TEMP_COMMIT_MSG_FILE!"
    set "commit_result=!errorlevel!"

    if !commit_result! neq 0 (
        echo ERRO: Falha ao fazer o commit. (Exit code: !commit_result!)
        del "!TEMP_COMMIT_MSG_FILE!" 2>nul
        del "!TEMP_TIMESTAMP_FILE!" 2>nul
        goto :eof
    )
    echo Sub-etapa 3.2: Alteracoes commitadas.
    del "!TEMP_COMMIT_MSG_FILE!" 2>nul
    del "!TEMP_TIMESTAMP_FILE!" 2>nul
) else (
    echo Sub-etapa 3.1: Nenhum commit novo a ser feito.
)
echo.

echo ETAPA 4: Configurando o repositorio remoto...
git remote get-url origin >nul 2>&1
if !errorlevel! neq 0 (
    echo Adicionando 'origin' remoto...
    git remote add origin https://github.com/leonardolauriquer/safety_ai_app.git
    if !errorlevel! neq 0 (
        echo ERRO: Falha ao adicionar o remoto 'origin'.
        goto :eof
    )
) else (
    echo 'origin' remoto ja existe. Verificando URL...
    for /f "delims=" %%i in ('git remote get-url origin') do set "current_origin_url=%%i"
    if /i "!current_origin_url!" neq "https://github.com/leonardolauriquer/safety_ai_app.git" (
        echo A URL remota 'origin' e diferente. Atualizando...
        git remote set-url origin https://github.com/leonardolauriquer/safety_ai_app.git
        if !errorlevel! neq 0 (
            echo ERRO: Falha ao atualizar a URL remota 'origin'.
            goto :eof
        )
    ) else (
        echo URL remota 'origin' ja correta.
    )
)
echo Repositorio remoto configurado.
echo.

echo ETAPA 5: Sincronizando com o repositorio remoto (git pull)...
git pull origin main
set "pull_result=!errorlevel!"
if !pull_result! neq 0 (
    echo.
    echo ATENCAO: Ocorreu um erro ou conflito durante o 'git pull'. (Exit code: !pull_result!)
    echo Resolva manualmente (edite, 'git add .', 'git commit').
    echo Apos resolver, execute este script novamente.
    echo.
    goto :eof
)
echo Repositorio local atualizado.
echo.

echo ETAPA 6: Enviando alteracoes para a branch 'main' no GitHub...
git push -u origin main --force
set "push_result=!errorlevel!"
if !push_result! neq 0 (
    echo ERRO: Falha ao enviar para o GitHub. Verifique credenciais ou permissoes. (Exit code: !push_result!)
    goto :eof
)
echo.
echo ===============================================
echo === Projeto enviado com sucesso para o GitHub! ===
===============================================
echo.

pause
endlocal