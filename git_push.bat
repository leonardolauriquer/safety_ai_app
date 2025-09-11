@echo off
cls
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
        exit /b 1
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
    exit /b 1
)
echo Arquivos adicionados.
echo.

echo ETAPA 3: Verificando e fazendo o commit das alteracoes...
git diff --cached --quiet
set "changes_staged=!errorlevel!"
echo Debug: git diff --cached --quiet returned !changes_staged!

if !changes_staged! neq 0 (
    set "TEMP_COMMIT_MSG_FILE=!TEMP!\git_commit_msg.tmp"
    
    :: ESTE TIMESTAMP É APENAS PARA DEBUG. REMOVEMOS A GERACAO DINAMICA TEMPORARIAMENTE.
    set "TIMESTAMP_FOR_COMMIT=2025-09-11 19-00-00 (DEBUG)"
    
    set "FULL_COMMIT_MESSAGE=Automated commit: !TIMESTAMP_FOR_COMMIT!"

    echo !FULL_COMMIT_MESSAGE! > "!TEMP_COMMIT_MSG_FILE!"
    
    echo Sub-etapa 3.1: Tentando commit lendo mensagem do arquivo: "!TEMP_COMMIT_MSG_FILE!"
    git commit -F "!TEMP_COMMIT_MSG_FILE!"
    set "commit_result=!errorlevel!"
    echo Debug: commit_result after git commit is !commit_result!
    pause  :: PAUSE 1: APÓS EXIBIR O RESULTADO DO COMMIT

    if !commit_result! neq 0 (
        echo ERRO: Falha ao fazer o commit. (Exit code: !commit_result!)
        del "!TEMP_COMMIT_MSG_FILE!" 2>nul
        exit /b 1
    )
    echo Sub-etapa 3.2: Alteracoes commitadas.
    del "!TEMP_COMMIT_MSG_FILE!" 2>nul
    pause  :: PAUSE 2: APÓS O SUCESSO DO COMMIT E LIMPEZA DE ARQUIVOS TEMP
) else (
    echo Sub-etapa 3.1: Nenhum commit novo a ser feito.
    pause :: PAUSE 2.1: SE NENHUM COMMIT FOI NECESSÁRIO
)
echo Debug: FINALIZOU ETAPA 3. PROSSEGUINDO...
pause :: PAUSE 3: APÓS O FIM DO BLOCO DA LÓGICA DE COMMIT
echo.

echo ETAPA 4: Configurando o repositorio remoto...
git remote get-url origin >nul 2>&1
if !errorlevel! neq 0 (
    echo Adicionando 'origin' remoto...
    git remote add origin https://github.com/leonardolauriquer/safety_ai_app.git
    if !errorlevel! neq 0 (
        echo ERRO: Falha ao adicionar o remoto 'origin'.
        exit /b 1
    )
) else (
    echo 'origin' remoto ja existe. Verificando URL...
    for /f "delims=" %%i in ('git remote get-url origin') do set "current_origin_url=%%i"
    if /i "!current_origin_url!" neq "https://github.com/leonardolauriquer/safety_ai_app.git" (
        echo A URL remota 'origin' e diferente. Atualizando...
        git remote set-url origin https://github.com/leonardolauriquer/safety_ai_app.git
        if !errorlevel! neq 0 (
            echo ERRO: Falha ao atualizar a URL remota 'origin'.
            exit /b 1
        )
    ) else (
        echo URL remota 'origin' ja correta.
    )
)
echo Repositorio remoto configurado.
echo.

echo ETAPA 5: Sincronizando com o repositorio remoto (git pull)...
git pull origin main
if !errorlevel! neq 0 (
    echo.
    echo ATENCAO: Ocorreu um erro ou conflito durante o 'git pull'. (Exit code: !errorlevel!)
    echo Resolva manualmente (edite, 'git add .', 'git commit').
    echo Apos resolver, execute este script novamente.
    echo.
    exit /b 1
)
echo Repositorio local atualizado.
echo.

echo ETAPA 6: Enviando alteracoes para a branch 'main' no GitHub...
git push -u origin main --force
if !errorlevel! neq 0 (
    echo ERRO: Falha ao enviar para o GitHub. Verifique credenciais ou permissoes. (Exit code: !errorlevel!)
    exit /b 1
)
echo.
echo ===============================================
echo === Projeto enviado com sucesso para o GitHub! ===
===============================================
echo.

pause
endlocal
exit /b 0