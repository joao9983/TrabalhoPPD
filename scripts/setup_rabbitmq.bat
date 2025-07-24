@echo off
echo ===============================================
echo    CONFIGURAÇÃO DO RABBITMQ PARA WINDOWS
echo ===============================================
echo.

echo Verificando se o RabbitMQ está instalado...
rabbitmq-service.bat status >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ RabbitMQ já está instalado
    goto :start_service
)

echo.
echo RabbitMQ não encontrado. Instruções de instalação:
echo.
echo OPÇÃO 1 - Via Chocolatey (Recomendado):
echo 1. Instale o Chocolatey se não tiver: https://chocolatey.org/install
echo 2. Execute: choco install rabbitmq
echo.
echo OPÇÃO 2 - Download Manual:
echo 1. Baixe o Erlang: https://www.erlang.org/downloads
echo 2. Baixe o RabbitMQ: https://www.rabbitmq.com/install-windows.html
echo 3. Instale o Erlang primeiro, depois o RabbitMQ
echo.
echo OPÇÃO 3 - Docker:
echo docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
echo.
pause
goto :end

:start_service
echo.
echo Iniciando serviço RabbitMQ...
net start RabbitMQ >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ RabbitMQ iniciado com sucesso
) else (
    echo Tentando iniciar RabbitMQ via rabbitmq-service...
    rabbitmq-service.bat start
)

echo.
echo Habilitando plugin de gerenciamento...
rabbitmq-plugins.bat enable rabbitmq_management >nul 2>&1

echo.
echo ✓ Configuração concluída!
echo.
echo Para acessar a interface de gerenciamento:
echo URL: http://localhost:15672
echo Usuário: guest
echo Senha: guest
echo.
echo Para executar o sistema:
echo python main.py
echo.

:end
pause
