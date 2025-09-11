@echo off
rem Define a codificacao UTF-8 para o console, melhorando a compatibilidade com caracteres especiais.
chcp 65001 > nul
setlocal enabledelayedexpansion

rem Define o diretorio do projeto como o diretorio onde o script esta sendo executado.
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo.
echo ===========================================
echo === Enviando Projeto para o GitHub ====
===========================================
echo.

echo ETAPA 0: Verificando a instalacao do Git...
rem Verifica se o comando 'git' esta acessivel no PATH do sistema.
git --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ERRO: Git nao encontrado ou nao acessivel no PATH.
    echo Por favor, verifique se o Git esta instalado corretamente e se seu executavel esta no PATH do sistema.
    pause "Pressione qualquer tecla para sair e resolver o problema de instalacao do Git."
    goto :eof
)
echo Git encontrado e pronto para uso.
echo.

echo ETAPA 1: Inicializando ou verificando o repositorio Git...
rem Verifica se a pasta .git existe, indicando um repositorio ja inicializado.
if not exist ".git" (
    echo Repositorio Git nao encontrado. Inicializando um novo repositorio local...
    git init
    if !errorlevel! neq 0 (
        echo ERRO: Falha ao inicializar o repositorio Git. Codigo de saida: !errorlevel!
        pause "Pressione qualquer tecla para sair e investigar o erro de 'git init'."
        goto :eof
    )
    echo Repositorio Git inicializado com sucesso.
) else (
    echo Repositorio Git ja inicializado.
)
echo.

echo ETAPA 2: Adicionando arquivos ao staging area...
rem O comando 'git add .' adiciona todos os arquivos novos, modificados e deletados ao staging area.
rem Isso prepara as alteracoes para o proximo commit.
git add .
if !errorlevel! neq 0 (
    echo ERRO: Falha ao adicionar arquivos ao staging area. Codigo de saida: !errorlevel!
    echo Isso pode indicar problemas de permissao, arquivos bloqueados ou uma falha interna do Git.
    pause "Pressione qualquer tecla para sair e investigar o erro de 'git add .'."
    goto :eof
)
echo Arquivos adicionados ao staging area.
echo.

echo ETAPA 3: Verificando e fazendo o commit das alteracoes...
rem 'git diff --cached --quiet' verifica se ha alteracoes no staging area prontas para commit.
rem Retorna 0 se nao houver diferencas (nada para commitar) e 1 se houver diferencas.
git diff --cached --quiet
set "changes_staged=!errorlevel!"
echo Debug: git diff --cached --quiet returned !changes_staged!

rem CORREÇÃO CRÍTICA: Se 'changes_staged' for 0, significa que nao ha diferencas no staging area,
rem entao nao ha nada para commitar e o passo de commit deve ser ignorado.
if !changes_staged! equ 0 (
    echo Sub-etapa 3.1: Nenhuma alteracao staged para commitar. Ignorando commit.
    goto :SKIP_COMMIT_SECTION
)

:: --- INICIO DA SECAO DE COMMIT ---
rem Cria arquivos temporarios para armazenar a mensagem de commit e o timestamp.
set "TEMP_COMMIT_MSG_FILE=!TEMP!\git_commit_msg.tmp"
set "TEMP_TIMESTAMP_FILE=!TEMP!\git_timestamp.tmp"

rem Gera um timestamp formatado para a mensagem de commit automatica usando PowerShell.
powershell -Command "(Get-Date -Format 'yyyy-MM-dd HH-mm-ss').ToString()" > "!TEMP_TIMESTAMP_FILE!" 2>nul
set /p "TIMESTAMP_FOR_COMMIT="<"!TEMP_TIMESTAMP_FILE!"
del "!TEMP_TIMESTAMP_FILE!" 2>nul

set "FULL_COMMIT_MESSAGE=Automated commit: !TIMESTAMP_FOR_COMMIT!"

echo !FULL_COMMIT_MESSAGE! > "!TEMP_COMMIT_MSG_FILE!"

echo Sub-etapa 3.1: Tentando commit com a mensagem: "!FULL_COMMIT_MESSAGE!"
git commit -F "!TEMP_COMMIT_MSG_FILE!"
set "commit_result=!errorlevel!"
echo Debug: commit_result after git commit is !commit_result!

if !commit_result! neq 0 (
    echo ERRO: Falha ao fazer o commit. Codigo de saida: !commit_result!
    echo Verifique se ha conflitos ou se o Git encontrou algum problema durante o commit.
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
rem Verifica se o remoto 'origin' ja existe.
git remote get-url origin >nul 2>&1
if !errorlevel! neq 0 (
    echo 'origin' remoto nao encontrado. Adicionando...
    git remote add origin https://github.com/leonardolauriquer/safety_ai_app.git
    if !errorlevel! neq 0 (
        echo ERRO: Falha ao adicionar o remoto 'origin'. Codigo de saida: !errorlevel!
        pause "Pressione qualquer tecla para sair e investigar o erro de 'git remote add'."
        goto :eof
    )
) else (
    echo 'origin' remoto ja existe. Verificando URL...
    rem Captura a URL atual do remoto 'origin'.
    for /f "delims=" %%i in ('git remote get-url origin') do set "current_origin_url=%%i"
    rem Compara a URL atual com a URL esperada, ignorando case-sensitivity.
    if /i "!current_origin_url!" neq "https://github.com/leonardolauriquer/safety_ai_app.git" (
        echo A URL remota 'origin' e diferente da esperada. Atualizando...
        git remote set-url origin https://github.com/leonardolauriquer/safety_ai_app.git
        if !errorlevel! neq 0 (
            echo ERRO: Falha ao atualizar a URL remota 'origin'. Codigo de saida: !errorlevel!
            pause "Pressione qualquer tecla para sair e investigar o erro de 'git remote set-url'."
            goto :eof
        )
    ) else (
        echo URL remota 'origin' ja esta correta.
    )
)
echo Repositorio remoto 'origin' configurado.
echo.

echo ETAPA 5: Sincronizando com o repositorio remoto (git pull)...
set "TEMP_PULL_OUTPUT=!TEMP!\git_pull_output.tmp"
rem Redireciona a saida do 'git pull' para um arquivo temporario para analise.
git pull origin main >"!TEMP_PULL_OUTPUT!" 2>&1
set "pull_result=!errorlevel!"

echo Debug: pull_result after git pull is !pull_result!
echo Debug: Conteudo completo do pull_output:
type "!TEMP_PULL_OUTPUT!"

rem Verifica se o repositorio ja estava atualizado, procurando pela string "Already up to date." na saida.
findstr /i /c:"Already up to date." "!TEMP_PULL_OUTPUT!" >nul 2>&1
if !errorlevel! equ 0 (
    echo Repositorio local ja estava atualizado. Prosseguindo.
    del "!TEMP_PULL_OUTPUT!" 2>nul
    goto :PULL_SUCCESS_SECTION
)

if !pull_result! neq 0 (
    echo.
    echo ATENCAO: Ocorreu um erro ou conflito durante o 'git pull'. Codigo de saida: !pull_result!
    echo Possiveis causas: Conflitos de merge, problemas de rede, ou configuracoes do Git.
    echo Por favor, resolva manualmente quaisquer conflitos (edite os arquivos, 'git add .', 'git commit').
    echo Apos resolver, execute este script novamente.
    echo.
    pause "Pressione qualquer tecla para sair e resolver o problema de 'git pull'."
    del "!TEMP_PULL_OUTPUT!" 2>nul
    goto :eof
)

:PULL_SUCCESS_SECTION
echo Repositorio local sincronizado com sucesso.
echo.
del "!TEMP_PULL_OUTPUT!" 2>nul


echo ETAPA 6: Enviando alteracoes para a branch 'main' no GitHub...
rem O '-u' (ou '--set-upstream') configura o branch remoto para o branch local,
rem facilitando futuros 'git pull' e 'git push' sem especificar 'origin main'.
git push -u origin main
if !errorlevel! neq 0 (
    echo ERRO: Falha ao enviar para o GitHub. Verifique credenciais, permissoes ou conflitos. Codigo de saida: !errorlevel!
    echo Causa comum: Alteracoes no remoto que nao foram puxadas (git pull) antes do push.
    pause "Pressione qualquer tecla para sair e investigar o erro de 'git push'."
    goto :eof
)
echo.
cls :: Limpa a tela antes da mensagem final para uma experiencia mais limpa e focada.
echo ===============================================
echo === Projeto enviado com sucesso para o GitHub! ===
===============================================
echo.

pause
endlocal
goto :eof