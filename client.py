import grpc
import cinema_pb2
import cinema_pb2_grpc
import time

# Configuração do gRPC Server
HOST_PORT = 'localhost:50051'

# Dados para o Teste
TEST_SESSAO = "S001"
TEST_ASSENTO = "A5"
TEST_USUARIO_1 = "Marcelo_1"
TEST_USUARIO_2 = "Concorrente_2"

def run_test(usuario_id, assento_id, sessao_id):
    # Cria a conexão gRPC
    with grpc.insecure_channel(HOST_PORT) as channel:
        stub = cinema_pb2_grpc.ReservaStub(channel)
        
        assento = cinema_pb2.AssentoID(sessao_id=sessao_id, assento_num=assento_id)
        request = cinema_pb2.ReservaRequest(assento=assento, usuario_id=usuario_id)

        print(f"\n--- {usuario_id} tentando RESERVAR Assento {assento_id} ---")
        
        # 1. Tenta Reservar o Assento (Bloqueio Distribuído no Redis)
        try:
            response = stub.ReservarAssento(request)
            print(f"RESPOSTA RESERVA: Sucesso={response.sucesso}, Mensagem: {response.mensagem}")

            if response.sucesso:
                # 2. Se a reserva (bloqueio) foi bem-sucedida, prossegue para o Pagamento
                print(f"TOKEN DE RESERVA: {response.reserva_token}. Simulação de pagamento...")
                time.sleep(2) # Simula o tempo que o usuário leva para pagar
                
                # 3. Confirma o Pagamento (muda o estado no Redis e envia mensagem Kafka)
                confirm_response = stub.ConfirmarPagamento(request)
                print(f"RESPOSTA PAGAMENTO: Sucesso={confirm_response.sucesso}, Mensagem: {confirm_response.mensagem}")
                return confirm_response.sucesso
                
        except grpc.RpcError as e:
            print(f"ERRO RPC: Ocorreu um erro na comunicação: {e}")
            return False

def test_concorrencia():
    print("=== Teste de Fluxo Completo: Usuário 1 (Sucesso) ===")
    
    # 1. Usuário 1 faz a reserva e confirma o pagamento (Deve ter sucesso)
    sucesso_user_1 = run_test(TEST_USUARIO_1, TEST_ASSENTO, TEST_SESSAO)
    
    if sucesso_user_1:
        print("\n=== Teste de Concorrência: Usuário 2 (Deve Falhar) ===")
        
        # 2. Usuário 2 tenta reservar o MESMO assento (Deve falhar no Bloqueio)
        run_test(TEST_USUARIO_2, TEST_ASSENTO, TEST_SESSAO)

if __name__ == '__main__':
    test_concorrencia()