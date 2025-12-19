from kafka import KafkaProducer
import json
import logging
import os
import time

logging.basicConfig(level=logging.INFO)

class NotificationProducer:
    def __init__(self):
        # Pega a configuração do ambiente ou usa localhost (fallback)
        self.bootstrap_servers = [os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')]
        self.TOPIC = 'reservas_confirmadas'
        self.producer = None
        
        self._connect()

    def _connect(self):
        """Tenta conectar ao Kafka com retries até conseguir."""
        while True:
            try:
                logging.info(f"Producer tentando conectar ao Kafka em: {self.bootstrap_servers}...")
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
                logging.info("Producer conectado ao Kafka com sucesso!")
                break
            except Exception as e:
                logging.warning(f"Kafka ainda não está pronto ({e}). Tentando novamente em 5 segundos...")
                time.sleep(5)

    def send_confirmation(self, reserva_data: dict):
        """Envia uma mensagem de confirmação para o tópico Kafka."""
        if not self.producer:
            logging.error("Produtor Kafka não inicializado.")
            return

        try:
            future = self.producer.send(self.TOPIC, value=reserva_data)
            # Opcional: esperar um pouco para garantir entrega, mas sem bloquear muito
            # future.get(timeout=10) 
            logging.info(f"Mensagem enviada para Kafka: {reserva_data}")
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem para Kafka: {e}")
            # Opcional: Tentar reconectar se o erro for de conexão
            # self._connect()