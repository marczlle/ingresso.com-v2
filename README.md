cinema.proto = grpc; 
(define as mensagens e os serviços que serão usados por todos os componentes.)

compilando o arquivo para gerar os stubs:
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. cinema.proto