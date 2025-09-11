@echo off
setlocal enabledelayedexpansion

:: Define o diretorio do projeto como o diretorio onde o script esta localizado.
:: %~dp0 expande para o drive e caminho do script atual.
:: `cd /d` garante a mudanca de diretorio mesmo entre diferentes drives.
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo.
echo ===========================================
echo === Enviando Projeto para o GitHub ====
echo ===========================================
echo.

echo ETAPA 1: Inicializando o repositorio Git...
:: Verifica se o diretorio .git existe, indicando um repositorio ja inicializado.
if not exist ".git" (
    echo Inicializando o repositorio Git local...
    git init
    :: Verifica o errorlevel para garantir que o comando anterior foi bem-sucedido.
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
:: Adiciona todas as alteracoes no diretorio atual ao staging area.
git add .
if !errorlevel! neq 0 (
    echo ERRO: Falha ao adicionar arquivos.
    goto :eof
)
echo Arquivos adicionados.
echo.

echo ETAPA 3: Verificando e fazendo o commit das alteracoes...
:: `git diff --cached --quiet` verifica se ha alteracoes no staging area.
:: Retorna errorlevel 0 se nao houver alteracoes, 1 se houver.
git diff --cached --quiet
set "changes_staged=!errorlevel!"
echo Debug: git diff --cached --quiet returned !changes_staged!

if !changes_staged! neq 0 (
    :: Define um caminho para um arquivo temporario para a mensagem de commit.
    :: !TEMP! e uma variavel de ambiente do Windows para o diretorio temporario.
    set "TEMP_COMMIT_MSG_FILE=!TEMP!\git_commit_msg.tmp"
    
    :: Obtem o timestamp do PowerShell de forma simples e armazena em uma variavel Batch.
    :: `for /f` captura a saida do comando.
    :: `usebackq` permite usar crases para o comando.
    :: `delims=` garante que a linha inteira seja capturada, sem divisao.
    for /f "usebackq delims=" %%i in (`powershell -Command "(Get-Date -Format 'yyyy-MM-dd HH-mm-ss').ToString()"`) do set "TIMESTAMP_FOR_COMMIT=%%i"
    
    :: Monta a mensagem de commit completa usando a variavel de timestamp.
    set "FULL_COMMIT_MESSAGE=Automated commit: !TIMESTAMP_FOR_COMMIT!"

    :: Escreve a mensagem no arquivo temporario usando redirecionamento do CMD.
    :: Este e um metodo robusto para gravar strings em arquivos no Batch.
    echo !FULL_COMMIT_MESSAGE! > "!TEMP_COMMIT_MSG_FILE!"
    
    echo Sub-etapa 3.1: Tentando commit lendo mensagem do arquivo: "!TEMP_COMMIT_MSG_FILE!"
    :: Realiza o commit lendo a mensagem do arquivo temporario.
    git commit -F "!TEMP_COMMIT_MSG_FILE!"
    set "commit_result=!errorlevel!"

    if !commit_result! neq 0 (
        echo ERRO: Falha ao fazer o commit. (Exit code: !commit_result!)
        :: Tenta deletar o arquivo temporario. `2>nul` suprime erros se o arquivo nao existir.
        del "!TEMP_COMMIT_MSG_FILE!" 2>nul
        goto :eof
    )
    echo Sub-etapa 3.2: Alteracoes commitadas.
    del "!TEMP_COMMIT_MSG_FILE!" 2>nul
) else (
    echo Sub-etapa 3.1: Nenhum commit novo a ser feito.
)
echo.

echo ETAPA 4: Configurando o repositorio remoto...
:: Verifica se o remoto 'origin' ja existe.
:: `>nul 2>&1` redireciona a saida padrao e de erro para o "nada", evitando que o comando exiba mensagens.
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
    :: Captura a URL atual do remoto 'origin'.
    for /f "delims=" %%i in ('git remote get-url origin') do set "current_origin_url=%%i"
    :: Compara a URL atual com a URL desejada.
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
:: Realiza um `git pull` para buscar e mesclar as alteracoes do repositorio remoto.
:: Isso e crucial para evitar conflitos e garantir que seu repositorio local esteja atualizado antes de um push.
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
:: Envia as alteracoes para a branch 'main' no GitHub.
:: `-u origin main` configura a branch local para rastrear a branch remota.
:: `--force` sobrescreve o historico remoto. Use com cautela, especialmente em projetos colaborativos,
:: pois pode apagar alteracoes de outras pessoas. Para projetos pessoais, pode ser aceitavel.
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
:: `endlocal` reverte as alteracoes de ambiente feitas por `setlocal`.
endlocal