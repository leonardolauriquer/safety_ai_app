@echo off
setlocal

:: Define o diretório do projeto (assumindo que o .bat está na raiz do projeto)
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo.
echo ===========================================
echo === Enviando Projeto para o GitHub ====
echo ===========================================
echo.

:: 1. Inicializa o repositório Git se ainda não foi inicializado
:: Verifica se o diretório .git existe
if not exist ".git" (
    echo.
    echo Inicializando o repositório Git local...
    git init
    if %errorlevel% neq 0 (
        echo ERRO: Falha ao inicializar o repositório Git.
        goto :eof
    )
    echo Repositório Git inicializado.
    echo.
) else (
    echo.
    echo Repositório Git jß inicializado.
    echo.
)

:: 2. Adiciona todos os arquivos ao staging area
echo Adicionando todos os arquivos ao staging area...
git add .
if %errorlevel% neq 0 (
    echo ERRO: Falha ao adicionar arquivos.
    goto :eof
)
echo Arquivos adicionados.
echo.

:: 3. Faz o commit das alterações
echo Fazendo o commit das alteraþ§es...
git diff-index --quiet HEAD
if %errorlevel% neq 0 (
    :: Existem mudanþas a serem commitadas
    git commit -m "Initial commit of Safety AI App - Web Interface"
    if %errorlevel% neq 0 (
        echo ERRO: Falha ao fazer o commit.
        goto :eof
    )
    echo Alteraþ§es commitadas.
) else (
    :: Nenhuma mudanþa para commitar
    echo Nenhum commit novo a ser feito.
)
echo.

:: 4. Adiciona o repositório remoto (se nþo existir) ou atualiza
echo Configurando o reposit¾rio remoto...
:: Verifica se o 'origin' jß existe
git remote get-url origin >nul 2>&1
if %errorlevel% neq 0 (
    echo Adicionando 'origin' remoto...
    git remote add origin https://github.com/leonardolauriquer/safety_ai_app.git
    if %errorlevel% neq 0 (
        echo ERRO: Falha ao adicionar o remoto 'origin'.
        goto :eof
    )
) else (
    echo 'origin' remoto jß existe. Verificando URL...
    for /f "delims=" %%i in ('git remote get-url origin') do set "current_origin_url=%%i"
    if /i "%current_origin_url%" neq "https://github.com/leonardolauriquer/safety_ai_app.git" (
        echo A URL remota 'origin' ß diferente. Atualizando...
        git remote set-url origin https://github.com/leonardolauriquer/safety_ai_app.git
        if %errorlevel% neq 0 (
            echo ERRO: Falha ao atualizar a URL remota 'origin'.
            goto :eof
        )
    ) else (
        echo URL remota 'origin' jß correta.
    )
)
echo Reposit¾rio remoto configurado.
echo.

:: 5. Faz o push das alteraþ§es para a branch 'main'
echo Enviando alteraþ§es para a branch 'main' no GitHub...
git push -u origin main
if %errorlevel% neq 0 (
    echo ERRO: Falha ao enviar para o GitHub. Por favor, verifique suas credenciais ou permiss§es.
    echo Pode ser necessßrio gerar um Personal Access Token no GitHub se vocø estiver usando autenticaþ§o de dois fatores.
    goto :eof
)
echo.
echo ===============================================
echo === Projeto enviado com sucesso para o GitHub! ===
echo ===============================================
echo.

pause
endlocal