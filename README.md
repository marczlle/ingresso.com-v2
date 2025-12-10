cinema.proto = grpc; 
(define as mensagens e os serviços que serão usados por todos os componentes.)

compilando o arquivo para gerar os stubs:
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. cinema.proto

rodando um unico cliente:
docker compose up -d
python booking_service_server.py (roda o servidor)
python notification_consumer.py (consumidor)
python client.py (cliente)

rodando pra escolha de assento no front:
docker compose up -d
python booking_service_server.py (roda o servidor)
python notification_consumer.py (consumidor)
python redis_listener.py
python -m uvicorn websocket_server:app --reload --port 8000