import redis
import requests
import json
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - RedisListener - %(levelname)s - %(message)s')

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = 6379
# Canal do Redis que monitora a expiração de chaves
EXPIRY_CHANNEL = '__keyevent@0__:expired' 
# Endpoint do WebSocket Service para notificar sobre a liberação
WS_HOST = os.getenv('WS_HOST', 'localhost')
WS_NOTIFY_URL = f'http://{WS_HOST}:8000/notify_liberacao'

def start_redis_listener():
    r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)
    # Cria um objeto PubSub para escutar o canal
    pubsub = r.pubsub()
    pubsub.subscribe(EXPIRY_CHANNEL)
    
    logging.info("Escutando eventos de expiração do Redis...")

    for message in pubsub.listen():
        if message['type'] == 'message':
            # A chave expirada é o valor da mensagem
            key = message['data'].decode('utf-8')
            
            # Formato da chave é 'sessao:ID:assento:NUM'. Queremos apenas chaves de bloqueio
            if 'sessao:' in key and 'assento:' in key:
                logging.warning(f"🔑 Chave Expirada Detectada: {key}")
                
                try:
                    # Extrai dados da chave (ex: 'sessao:S001:assento:A5')
                    parts = key.split(':')
                    sessao_id = parts[1]
                    assento_num = parts[3]
                    
                    payload = {
                        "sessao": sessao_id,
                        "assento": assento_num,
                        "motivo": "timeout"
                    }
                    
                    # Notifica o Servidor WebSocket para que ele faça o broadcast para todos os clientes
                    response = requests.post(WS_NOTIFY_URL, json=payload)
                    if response.status_code == 200:
                        logging.info(f"Notificação de liberação enviada com sucesso para o WebSocket para o assento {assento_num}.")
                    else:
                        logging.error(f"Falha ao notificar o WebSocket: Status {response.status_code}")
                
                except Exception as e:
                    logging.error(f"Erro ao processar evento de expiração: {e}")

if __name__ == '__main__':
    start_redis_listener()