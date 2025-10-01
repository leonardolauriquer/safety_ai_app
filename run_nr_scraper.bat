@echo off
REM Navega para o diretório raiz do projeto
cd C:\Dev\safety_ai_app\

REM Ativa o ambiente virtual
REM Certifique-se de que o caminho para o activate.bat está correto para o seu .venv
call .venv\Scripts\activate.bat

REM Executa o script Python nr_scraper.py que está na pasta 'scripts'
python scripts\nr_scraper.py

REM Desativa o ambiente virtual (opcional, mas boa prática)
call deactivate

echo.
echo Script nr_scraper.py executado.
pause