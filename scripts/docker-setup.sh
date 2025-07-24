#!/bin/bash

# ===============================================
#    SCRIPT DOCKER PARA SISTEMA DE CHAT
# ===============================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

function show_usage() {
    echo ""
    echo -e "${CYAN}USO: ./docker-setup.sh [AÇÃO]${NC}"
    echo ""
    echo -e "${YELLOW}AÇÕES:${NC}"
    echo "  start    - Inicia RabbitMQ (padrão)"
    echo "  stop     - Para RabbitMQ"
    echo "  restart  - Reinicia RabbitMQ"
    echo "  logs     - Mostra logs do RabbitMQ"
    echo "  status   - Verifica status dos containers"
    echo "  clean    - Remove containers e volumes"
    echo ""
}

function check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker não encontrado!${NC}"
        echo -e "${YELLOW}Instale Docker: https://docs.docker.com/get-docker/${NC}"
        exit 1
    fi
}

function check_docker_compose() {
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}❌ Docker Compose não encontrado!${NC}"
        exit 1
    fi
}

function start_rabbitmq() {
    echo -e "${GREEN}🚀 Iniciando RabbitMQ...${NC}"
    
    docker-compose up -d rabbitmq
    
    echo ""
    echo -e "${GREEN}✅ RabbitMQ iniciado com sucesso!${NC}"
    echo ""
    echo -e "${CYAN}📊 INFORMAÇÕES DE ACESSO:${NC}"
    echo "  RabbitMQ Server: localhost:5672"
    echo "  Management UI:   http://localhost:15672"
    echo "  Usuário:         admin"
    echo "  Senha:           admin123"
    echo ""
    echo -e "${YELLOW}🎮 Para executar aplicação:${NC}"
    echo "  python main.py"
    echo ""
}

function stop_rabbitmq() {
    echo -e "${YELLOW}🛑 Parando RabbitMQ...${NC}"
    docker-compose stop rabbitmq
    echo -e "${GREEN}✅ RabbitMQ parado!${NC}"
}

function restart_rabbitmq() {
    echo -e "${BLUE}🔄 Reiniciando RabbitMQ...${NC}"
    stop_rabbitmq
    sleep 2
    start_rabbitmq
}

function show_logs() {
    echo -e "${CYAN}📋 Logs do RabbitMQ:${NC}"
    docker-compose logs -f rabbitmq
}

function show_status() {
    echo -e "${CYAN}📊 Status dos Containers:${NC}"
    echo ""
    docker-compose ps
    echo ""
    
    echo -e "${YELLOW}🔍 Testando conectividade...${NC}"
    
    # Testa Management UI
    if curl -s http://localhost:15672 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Management UI acessível${NC}"
    else
        echo -e "${RED}❌ Management UI não acessível${NC}"
    fi
    
    # Testa porta AMQP
    if nc -z localhost 5672 2>/dev/null; then
        echo -e "${GREEN}✅ Porta AMQP (5672) acessível${NC}"
    else
        echo -e "${RED}❌ Porta AMQP (5672) não acessível${NC}"
    fi
}

function clean_docker() {
    echo -e "${RED}🧹 Limpando containers e volumes...${NC}"
    echo -e "${YELLOW}Isso irá remover TODOS os dados do RabbitMQ.${NC}"
    
    read -p "Continuar? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v
        docker system prune -f
        echo -e "${GREEN}✅ Limpeza concluída!${NC}"
    else
        echo -e "${YELLOW}Operação cancelada.${NC}"
    fi
}

function main() {
    echo ""
    echo -e "${MAGENTA}🐳 DOCKER SETUP - Sistema de Chat por Localização${NC}"
    echo -e "${MAGENTA}=================================================${NC}"
    
    check_docker
    check_docker_compose
    
    case "${1:-start}" in
        start)
            start_rabbitmq
            ;;
        stop)
            stop_rabbitmq
            ;;
        restart)
            restart_rabbitmq
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        clean)
            clean_docker
            ;;
        *)
            show_usage
            ;;
    esac
}

# Executa função principal
main "$@"
