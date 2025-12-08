from kafka import KafkaProducer
import json
import logging

logging.basicConfig(level=logging.INFO)

class NotificationProducer:
    def __init__(self):
        # Configuração do Kafka (assume que está rodando em localhost:9092)
        self.producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.TOPIC = 'reservas_confirmadas'

    def send_confirmation(self, reserva_data: dict):
        """Envia uma mensagem de confirmação para o tópico Kafka."""
        try:
            future = self.producer.send(self.TOPIC, value=reserva_data)
            future.get(timeout=10) # Aguarda até 10s pela confirmação de envio
            logging.info(f"Mensagem enviada com sucesso para Kafka: {reserva_data}")
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem para Kafka: {e}")

# Exemplo de como seria chamado:
# producer = NotificationProducer()
# producer.send_confirmation({
#     "sessao": "A1",
#     "assento": "5C",
#     "usuario": "user_123",
#     "timestamp": time.time()
# })