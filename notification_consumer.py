from kafka import KafkaConsumer
import json
import logging
import os  # <--- FALTAVA ISSO
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def consume_reservas():
    # PEGAR DO DOCKER ou usar localhost se rodar fora
    kafka_server = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    
    logging.info(f"Tentando conectar ao Kafka em: {kafka_server}")

    # Loop de retry simples para esperar o Kafka subir
    while True:
        try:
            consumer = KafkaConsumer(
                'reservas_confirmadas',
                bootstrap_servers=[kafka_server], # <--- AQUI ESTAVA O ERRO (estava 'localhost')
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='notificacao-group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            break # Conectou com sucesso
        except Exception as e:
            logging.warning(f"Kafka indisponível ({e}). Tentando novamente em 5s...")
            time.sleep(5)
    
    logging.info("Consumidor Kafka iniciado. Aguardando reservas confirmadas...")

    for message in consumer:
        reserva_data = message.value
        logging.info(f"✅ Nova Mensagem de Confirmação Recebida!")
        logging.info(f"   Sessão: {reserva_data.get('sessao_id')}, Assento: {reserva_data.get('assento_num')}")
        logging.info(f"   Usuário: {reserva_data.get('usuario_id')}, Status: {reserva_data.get('status')}")

if __name__ == '__main__':
    consume_reservas()