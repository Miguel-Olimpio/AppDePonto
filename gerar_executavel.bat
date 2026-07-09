@echo off
setlocal
cd /d "%~dp0"
echo Instalando dependencias...
python -m pip install -r requirements.txt
echo.
echo Limpando build anterior...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo.
echo Gerando executavel...
pyinstaller --clean --noconfirm ControlePontoTarefas.spec
if not exist "dist\ControlePontoTarefas\data" mkdir "dist\ControlePontoTarefas\data"
if not exist "dist\ControlePontoTarefas\pdfs" mkdir "dist\ControlePontoTarefas\pdfs"
if not exist "dist\ControlePontoTarefas\backups" mkdir "dist\ControlePontoTarefas\backups"
if not exist "dist\ControlePontoTarefas\icon" mkdir "dist\ControlePontoTarefas\icon"
if not exist "dist\ControlePontoTarefas\data\wwebjs_auth" mkdir "dist\ControlePontoTarefas\data\wwebjs_auth"
if exist "icon\icon.ico" copy /Y "icon\icon.ico" "dist\ControlePontoTarefas\icon\icon.ico" >nul
echo.
echo Finalizado.
echo O executavel fica em dist\ControlePontoTarefas\ControlePontoTarefas.exe.
echo O icone usado no executavel e na janela e icon\icon.ico.
endlocal
pause
