# 💬 Sistema de Chat por Localização - PPD

Sistema de chat em tempo real baseado em localização geográfica usando comunicação síncrona (TCP) e assíncrona (RabbitMQ).

## 🚀 Como Executar

### Opção 2: Manual
```bash
# 1. Iniciar RabbitMQ
cd scripts
.\docker-setup.ps1 start

# 2. Executar aplicação
python main.py
```

## 📋 Funcionalidades

✅ **Comunicação TCP** entre usuários online no mesmo raio  
✅ **Comunicação RabbitMQ** para usuários offline ou distantes  
✅ **Descoberta automática** de contatos por proximidade  
✅ **Interface gráfica** completa (Tkinter)  
✅ **Persistência de mensagens** offline  
✅ **Configuração dinâmica** de localização e raio  

## 🔧 Dependências

- Python 3.8+
- Docker & Docker Compose
- Bibliotecas: `pika`, `python-dotenv`, `tkinter`

## 🎯 Para Testar

1. Abra múltiplas instâncias: `python main.py`
2. Configure usuários com coordenadas próximas
3. Teste comunicação síncrona (TCP) e assíncrona (RabbitMQ)
4. Monitore RabbitMQ em: http://localhost:15672

## 📊 Monitoramento

- **Logs:** Terminal da aplicação
- **RabbitMQ UI:** http://localhost:15672 (admin/admin123)
- **Filas:** Mensagens pendentes por usuário

---

**Projeto desenvolvido para a disciplina PPD - Instituto Federal do Ceará**
