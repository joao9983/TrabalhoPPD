# ===============================================
#    SCRIPT DOCKER PARA SISTEMA DE CHAT
# =========================================function Clean-Docker {
    Write-Host "Limpando containers e volumes..." -ForegroundColor Red
    
    $confirm = Read-Host "Isso ira remover TODOS os dados do RabbitMQ. Continuar? (y/N)"
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        try {
            Set-Location "../docker"
            docker-compose down -v
            docker system prune -f
            Set-Location "../scripts"
            Write-Host "Limpeza concluida!" -ForegroundColor Green
        } catch {
            Write-Host "Erro na limpeza: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "Operacao cancelada." -ForegroundColor Yellow
    }(
    [Parameter(Mandatory=$false)]
    [ValidateSet("start", "stop", "restart", "logs", "status", "clean")]
    [string]$Action = "start"
)

function Show-Usage {
    Write-Host ""
    Write-Host "USO: .\docker-setup.ps1 [AÇÃO]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "AÇÕES:" -ForegroundColor Yellow
    Write-Host "  start    - Inicia RabbitMQ (padrão)"
    Write-Host "  stop     - Para RabbitMQ"
    Write-Host "  restart  - Reinicia RabbitMQ"
    Write-Host "  logs     - Mostra logs do RabbitMQ"
    Write-Host "  status   - Verifica status dos containers"
    Write-Host "  clean    - Remove containers e volumes"
    Write-Host ""
}

function Test-Docker {
    try {
        docker --version | Out-Null
        return $true
    } catch {
        Write-Host "Docker nao encontrado!" -ForegroundColor Red
        Write-Host "Instale Docker Desktop: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
        return $false
    }
}

function Test-DockerCompose {
    try {
        docker-compose --version | Out-Null
        return $true
    } catch {
        try {
            docker compose version | Out-Null
            return $true
        } catch {
            Write-Host "Docker Compose nao encontrado!" -ForegroundColor Red
            return $false
        }
    }
}

function Start-RabbitMQ {
    Write-Host "Iniciando RabbitMQ..." -ForegroundColor Green
    
    try {
        Set-Location "../docker"
        docker-compose up -d rabbitmq
        Set-Location "../scripts"
        
        Write-Host ""
        Write-Host "RabbitMQ iniciado com sucesso!" -ForegroundColor Green
        Write-Host ""
        Write-Host "INFORMACOES DE ACESSO:" -ForegroundColor Cyan
        Write-Host "  RabbitMQ Server: localhost:5672"
        Write-Host "  Management UI:   http://localhost:15672"
        Write-Host "  Usuario:         admin"
        Write-Host "  Senha:           admin123"
        Write-Host ""
        Write-Host "Para executar aplicacao:" -ForegroundColor Yellow
        Write-Host "  python main.py"
        Write-Host ""
        
    } catch {
        Write-Host "Erro ao iniciar RabbitMQ: $_" -ForegroundColor Red
    }
}

function Stop-RabbitMQ {
    Write-Host "Parando RabbitMQ..." -ForegroundColor Yellow
    
    try {
        Set-Location "../docker"
        docker-compose stop rabbitmq
        Set-Location "../scripts"
        Write-Host "RabbitMQ parado!" -ForegroundColor Green
    } catch {
        Write-Host "Erro ao parar RabbitMQ: $_" -ForegroundColor Red
    }
}

function Restart-RabbitMQ {
    Write-Host "Reiniciando RabbitMQ..." -ForegroundColor Blue
    Stop-RabbitMQ
    Start-Sleep -Seconds 2
    Start-RabbitMQ
}

function Show-Logs {
    Write-Host "Logs do RabbitMQ:" -ForegroundColor Cyan
    Set-Location "../docker"
    docker-compose logs -f rabbitmq
    Set-Location "../scripts"
}

function Show-Status {
    Write-Host "Status dos Containers:" -ForegroundColor Cyan
    Write-Host ""
    Set-Location "../docker"
    docker-compose ps
    Set-Location "../scripts"
    Write-Host ""
    
    # Testa conectividade
    Write-Host "Testando conectividade..." -ForegroundColor Yellow
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:15672" -TimeoutSec 5 -UseBasicParsing
        Write-Host "Management UI acessivel" -ForegroundColor Green
    } catch {
        Write-Host "Management UI nao acessivel" -ForegroundColor Red
    }
    
    # Testa porta AMQP
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.Connect("localhost", 5672)
        $tcpClient.Close()
        Write-Host "Porta AMQP (5672) acessivel" -ForegroundColor Green
    } catch {
        Write-Host "Porta AMQP (5672) nao acessivel" -ForegroundColor Red
    }
}

function Clean-Docker {
    Write-Host "Limpando containers e volumes..." -ForegroundColor Red
    
    $confirm = Read-Host "Isso ira remover TODOS os dados do RabbitMQ. Continuar? (y/N)"
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        try {
            docker-compose down -v
            docker system prune -f
            Write-Host "Limpeza concluida!" -ForegroundColor Green
        } catch {
            Write-Host "Erro na limpeza: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "Operacao cancelada." -ForegroundColor Yellow
    }
}

# Função principal
function Main {
    Write-Host ""
    Write-Host "DOCKER SETUP - Sistema de Chat por Localizacao" -ForegroundColor Magenta
    Write-Host "================================================" -ForegroundColor Magenta
    
    if (-not (Test-Docker)) {
        return
    }
    
    if (-not (Test-DockerCompose)) {
        return
    }
    
    switch ($Action) {
        "start"   { Start-RabbitMQ }
        "stop"    { Stop-RabbitMQ }
        "restart" { Restart-RabbitMQ }
        "logs"    { Show-Logs }
        "status"  { Show-Status }
        "clean"   { Clean-Docker }
        default   { Show-Usage }
    }
}

# Executa função principal
Main
