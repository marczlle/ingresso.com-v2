# Sistema Distribuído de Reserva de Ingressos

Aplicação de compra de ingressos que combina gRPC, Redis, Kafka e um front em tempo real via WebSocket/FastAPI. O objetivo é simular o fluxo completo de seleção de assentos para uma sessão de cinema, garantindo bloqueio distribuído, confirmação de pagamento e notificação visual instantânea entre vários clientes.

## Arquitetura resumida

- **`booking_service_server.py`**: servidor gRPC com os métodos `ReservarAssento` e `ConfirmarPagamento`.
- **`seat_state_service.py`**: acesso ao Redis para aplicar bloqueios temporários e confirmar reservas.
- **`websocket_server.py`**: expõe o front (HTML/CSS/JS) e o WebSocket que conversa com o backend gRPC, publica atualizações para todos e envia snapshot inicial.
- **`redis_listener.py`**: observa expiração de locks no Redis e avisa o WebSocket para liberar o assento.
- **`notification_producer.py` / `notification_consumer.py`**: publicam e consomem confirmações no Kafka (workflow assíncrono).
- **`email_service.py`**: envia e-mails de confirmação via SMTP após pagamento fictício.

## Requisitos

- Python 3.11+
- Redis (porta 6379) com notificações de expiração habilitadas (`notify-keyspace-events Ex`)
- Kafka + Zookeeper (pode usar `docker-compose.yml`)
- Opcional: MailHog ou SMTP válido para teste de e-mail

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. cinema.proto
```

## Variáveis de ambiente principais

| Variável | Descrição | Default |
| --- | --- | --- |
| `SMTP_HOST` / `SMTP_PORT` | Endereço do servidor SMTP | `localhost` / `1025` |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | Credenciais do SMTP | vazio |
| `SMTP_USE_TLS` | Usa STARTTLS? (`true/false`) | `false` |
| `SMTP_FROM` | Remetente padrão do e-mail | `cinema@example.com` |
| `WS_NOTIFY_URL` | Endpoint do WebSocket para liberar assentos (usado pelo redis listener) | `http://localhost:8000/notify_liberacao` |

Exemplo para Gmail (necessário app password e porta liberada):

```bash
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="seu_email@gmail.com"
export SMTP_PASSWORD="senha_de_app"
export SMTP_USE_TLS="true"
export SMTP_FROM="seu_email@gmail.com"
```

## Execução

1. **Infra**: `docker compose up -d` (Kafka/Zookeeper/Redis se desejar)
2. **Listener**: `python redis_listener.py`
3. **Serviço de reserva**: `python booking_service_server.py`
4. **WebSocket/Frontend**: `uvicorn websocket_server:app --reload`
5. (Opcional) **Consumidor Kafka**: `python notification_consumer.py`

Abra `http://localhost:8000` para ver o mapa de assentos estilo cinema. Ao selecionar uma poltrona, o servidor gRPC tenta o bloqueio distribuído; outros clientes veem a cadeira cinza imediatamente. Ao confirmar o pagamento fictício, informe nome, CPF e e-mail – os assentos passam para “Ocupado”, um registro é salvo em `reservas_confirmadas.json` e o e-mail de confirmação é disparado.

## Teste rápido via gRPC

O script `tests/client.py` executa um fluxo concorrente simples:

```bash
python tests/client.py
```

## Estrutura

```
booking_service_server.py   # gRPC service
seat_state_service.py       # Redis helpers (lock / confirm / list)
websocket_server.py         # Frontend + WebSocket API
redis_listener.py           # Observa timeouts no Redis
notification_producer.py    # Kafka producer
notification_consumer.py    # Kafka consumer
email_service.py            # SMTP wrapper
cinema.proto                # contrato gRPC
requirements.txt            # dependências
```

## Observações

- O front-end usa WebSocket para tudo; não há framework extra, então qualquer alteração visual pode ser feita direto no HTML embedded.
- As mensagens Kafka são um bônus para mostrar integração; a lógica principal funciona sem elas.
- Para ambiente de produção, configure SSL/TLS reais e um serviço de fila de e-mails robusto.
