from kafka import KafkaConsumer
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def consume_reservas():
    # Configuração: Assumindo Kafka rodando em localhost:9092 (conforme o docker-compose.yml)
    consumer = KafkaConsumer(
        'reservas_confirmadas',
        bootstrap_servers=['localhost:9092'],
        auto_offset_reset='earliest', # Começa lendo desde o início do tópico
        enable_auto_commit=True,
        group_id='notificacao-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    logging.info("Consumidor Kafka iniciado. Aguardando reservas confirmadas...")

    for message in consumer:
        reserva_data = message.value
        logging.info(f"✅ Nova Mensagem de Confirmação Recebida!")
        logging.info(f"   Sessão: {reserva_data['sessao_id']}, Assento: {reserva_data['assento_num']}")
        logging.info(f"   Usuário: {reserva_data['usuario_id']}, Status: {reserva_data['status']}")

if __name__ == '__main__':
    consume_reservas()