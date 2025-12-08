import grpc
from concurrent import futures
import time

# Importações dos arquivos gerados pelo protoc e dos serviços
import cinema_pb2
import cinema_pb2_grpc
from seat_state_service import SeatStateService
from notification_producer import NotificationProducer

class ReservaServicer(cinema_pb2_grpc.ReservaServicer):
    """Implementa o serviço gRPC de Reserva."""
    def __init__(self):
        self.seat_service = SeatStateService()
        self.producer = NotificationProducer()

    def ReservarAssento(self, request: cinema_pb2.ReservaRequest, context) -> cinema_pb2.ReservaResponse:
        sessao = request.assento.sessao_id
        assento_num = request.assento.assento_num
        usuario = request.usuario_id

        print(f"Recebida requisição de reserva: S:{sessao}, A:{assento_num} por {usuario}")

        # 1. Tenta obter o Bloqueio Distribuído (Redis)
        if self.seat_service.bloquear_assento(assento_num, sessao, usuario):
            # O assento está agora BLOQUEADO_TEMP (estado no Redis com timeout)
            print(f"Assento {assento_num} bloqueado temporariamente.")
            return cinema_pb2.ReservaResponse(
                sucesso=True,
                mensagem="Assento bloqueado. Prossiga para o pagamento em 5 minutos.",
                reserva_token=f"TOKEN-{usuario}-{int(time.time())}"
            )
        else:
            # O assento está OCUPADO ou já bloqueado por outro usuário
            return cinema_pb2.ReservaResponse(
                sucesso=False,
                mensagem="Assento já ocupado ou bloqueado por outro usuário.",
                reserva_token=""
            )

    def ConfirmarPagamento(self, request: cinema_pb2.ReservaRequest, context) -> cinema_pb2.ReservaResponse:
        sessao = request.assento.sessao_id
        assento_num = request.assento.assento_num
        usuario = request.usuario_id
        
        # 2. SIMULAÇÃO de Pagamento Bem-sucedido (na vida real, chamaria um Payment Service)
        # ... simulação ...
        
        # 3. Tenta confirmar a Reserva (muda o estado no Redis)
        if self.seat_service.confirmar_reserva(assento_num, sessao, usuario):
            print(f"Pagamento confirmado. Assento {assento_num} reservado permanentemente.")
            
            # 4. Notificação Assíncrona (Kafka)
            reserva_data = {
                "sessao_id": sessao,
                "assento_num": assento_num,
                "usuario_id": usuario,
                "status": "CONFIRMADO",
                "timestamp": time.time()
            }
            self.producer.send_confirmation(reserva_data)
            
            return cinema_pb2.ReservaResponse(
                sucesso=True,
                mensagem="Reserva confirmada e pagamento concluído!",
                reserva_token=f"FINAL-{usuario}-{int(time.time())}"
            )
        else:
            # Falha ao confirmar (o bloqueio pode ter expirado ou foi liberado)
            return cinema_pb2.ReservaResponse(
                sucesso=False,
                mensagem="Falha na confirmação. O bloqueio temporário expirou ou foi perdido.",
                reserva_token=""
            )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    cinema_pb2_grpc.add_ReservaServicer_to_server(ReservaServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Servidor gRPC de Reserva iniciado na porta 50051...")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()