import redis
import time

# Configuração
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
TIMEOUT_SEGUNDOS = 300 # 5 minutos para o bloqueio

class SeatStateService:
    def __init__(self):
        self.r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

    def _get_key(self, assento_id: str, sessao_id: str):
        """Formata a chave no Redis: 'sessao:123:assento:A5'"""
        return f"sessao:{sessao_id}:assento:{assento_id}"

    def bloquear_assento(self, assento_id: str, sessao_id: str, usuario_id: str) -> bool:
        """
        Tenta adquirir um bloqueio distribuído para o assento.
        Usa o comando 'SET NX EX' do Redis: SET if Not eXists, com EXpiration.
        Retorna True se o bloqueio foi adquirido, False caso contrário.
        """
        key = self._get_key(assento_id, sessao_id)
        
        # Valor é o ID do usuário que bloqueou
        # nx=True: apenas se a chave NÃO EXISTE
        # ex=TIMEOUT_SEGUNDOS: expira em N segundos
        bloqueado = self.r.set(key, usuario_id, nx=True, ex=TIMEOUT_SEGUNDOS)
        
        return bool(bloqueado)

    def confirmar_reserva(self, assento_id: str, sessao_id: str, usuario_id: str) -> bool:
        """
        Muda o estado do assento para permanentemente reservado.
        Aqui, o valor no Redis pode ser simplesmente a string "RESERVADO".
        """
        key = self._get_key(assento_id, sessao_id)
        
        # Podemos usar uma transação (Pipeline) para garantir que
        # 1. O bloqueio temporário ainda pertence a este usuário.
        # 2. O estado final "RESERVADO" seja definido, e o timeout removido.
        
        pipeline = self.r.pipeline()
        pipeline.watch(key)
        
        if pipeline.get(key) == usuario_id:
            pipeline.multi()
            # Remove o timeout (persiste o estado) e define o valor como 'RESERVADO'
            pipeline.set(key, "RESERVADO", ex=None) 
            pipeline.execute()
            return True
        else:
            # O assento foi desbloqueado ou pego por outro usuário/sistema
            pipeline.unwatch() 
            return False

    def liberar_bloqueio(self, assento_id: str, sessao_id: str, usuario_id: str) -> None:
        """
        Remove o bloqueio (se ainda pertencer ao usuário).
        """
        key = self._get_key(assento_id, sessao_id)
        
        # Script LUA para garantir a atomicidade (libera APENAS se o valor for o usuario_id)
        # ZELDA: Zero/Delete/Locking/Atomic
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        # Executa o script atômico no Redis
        self.r.eval(lua_script, 1, key, usuario_id)
        print(f"Bloqueio liberado para {assento_id}.")


# Exemplo de uso (não faz parte do gRPC, apenas para teste)
if __name__ == '__main__':
    service = SeatStateService()
    SESSAO = "A1"
    ASSENTO = "5C"
    USUARIO = "user_123"

    # Tentativa de Bloqueio 1
    if service.bloquear_assento(ASSENTO, SESSAO, USUARIO):
        print(f"Assento {ASSENTO} bloqueado temporariamente por {USUARIO}.")
        time.sleep(2) # Simula o tempo de compra
        
        # Confirmação
        if service.confirmar_reserva(ASSENTO, SESSAO, USUARIO):
            print(f"Reserva para {ASSENTO} CONFIRMADA.")
        else:
            print(f"Erro ao confirmar reserva. Bloqueio perdido.")
            service.liberar_bloqueio(ASSENTO, SESSAO, USUARIO) # Em caso de falha de confirmação (opcional)
    else:
        print(f"Assento {ASSENTO} já está ocupado ou bloqueado.")