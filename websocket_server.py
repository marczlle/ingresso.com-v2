from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
import json
import grpc
import time
import asyncio
import logging

HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Reserva Distribuída de Cinema</title>
    <style>
        body { font-family: Arial, sans-serif; display: flex; flex-direction: column; align-items: center; }
        #screen { width: 300px; height: 10px; background: #333; margin-bottom: 20px; border-radius: 5px; }
        #seats-container { display: grid; grid-template-columns: repeat(5, 50px); gap: 10px; }
        .seat { width: 50px; height: 50px; background-color: green; border: 1px solid #1e7e34; border-radius: 5px; cursor: pointer; display: flex; justify-content: center; align-items: center; font-weight: bold; }
        .seat.blocked { background-color: #ffc107; cursor: not-allowed; border-color: #da9b0c; }
        .seat.reserved { background-color: red; cursor: not-allowed; border-color: #c82333; }
        .seat.unavailable { background-color: gray; cursor: not-allowed; border-color: #6c757d; }
        #status-box { margin-top: 20px; padding: 10px; border: 1px solid #ccc; width: 300px; }
    </style>
</head>
<body>
    <h1>Sala de Cinema Distribuída</h1>
    <div id="screen"></div>
    <p>Sessão: S001 | Usuário ID: <span id="user-display">Gerando...</span></p>

    <div id="seats-container">
        </div>

    <div id="status-box">Status: Conectando...</div>

    <script>
        const WS_URL = 'ws://localhost:8000/ws/reserva';
        const SEAT_CONTAINER = document.getElementById('seats-container');
        const STATUS_BOX = document.getElementById('status-box');
        const USER_ID = "USER_" + Math.floor(Math.random() * 1000); // ID único para o cliente
        document.getElementById('user-display').innerText = USER_ID;
        
        const SEAT_MAP = ["A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5"];
        const SESSION_ID = "S001";
        let socket = null;

        // 1. Inicializa os Assentos no DOM
        SEAT_MAP.forEach(id => {
            const seat = document.createElement('div');
            seat.className = 'seat';
            seat.id = id;
            seat.innerText = id;
            seat.addEventListener('click', () => handleSeatClick(id));
            SEAT_CONTAINER.appendChild(seat);
        });

        // 2. Conexão WebSocket
        function connectWebSocket() {
            socket = new WebSocket(WS_URL);

            socket.onopen = () => {
                STATUS_BOX.innerText = "Status: Conectado. Clique para bloquear.";
            };

            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleBroadcast(data);
            };

            socket.onclose = () => {
                STATUS_BOX.innerText = "Status: Desconectado. Tentando reconectar...";
                setTimeout(connectWebSocket, 3000); 
            };
            
            socket.onerror = (error) => {
                console.error("WebSocket Error:", error);
                STATUS_BOX.innerText = "Status: Erro de Conexão.";
            };
        }
        
        // 3. Ação do Usuário ao Clicar
        function handleSeatClick(seatId) {
            const seatElement = document.getElementById(seatId);
            if (seatElement.classList.contains('blocked') || seatElement.classList.contains('reserved')) {
                STATUS_BOX.innerText = `Assento ${seatId} já está indisponível.`;
                return;
            }

            // Envia a requisição de bloqueio via WebSocket
            socket.send(JSON.stringify({
                acao: "bloquear",
                sessao: SESSION_ID,
                assento: seatId,
                usuario_id: USER_ID
            }));

            // Muda o estado imediatamente para dar feedback, mas o broadcast confirmará
            seatElement.classList.add('unavailable'); 
            STATUS_BOX.innerText = `Tentando bloquear ${seatId}...`;
        }

        // 4. Receber e Tratar Broadcasts (Comunicação em Tempo Real)
        function handleBroadcast(data) {
            const seatElement = document.getElementById(data.assento);
            if (!seatElement) return;

            // Limpa classes anteriores
            seatElement.classList.remove('blocked', 'reserved', 'unavailable');

            if (data.evento === 'assento_bloqueado') {
                // Outro cliente bloqueou (deve ficar cinza para todos)
                seatElement.classList.add('blocked');
                STATUS_BOX.innerText = data.usuario_bloqueador === USER_ID 
                    ? `Bloqueio de ${data.assento} BEM-SUCEDIDO (Você).`
                    : `Assento ${data.assento} BLOQUEADO por ${data.usuario_bloqueador}.`;
            
            } else if (data.evento === 'assento_liberado') {
                // Assento liberado (TIMEOUT ou CANCELAMENTO)
                seatElement.classList.add('available'); // Volta a ser verde (disponível)
                seatElement.style.backgroundColor = 'green';
                STATUS_BOX.innerText = `Assento ${data.assento} LIBERADO (${data.motivo}).`;
                
            } else if (data.evento === 'assento_reservado') {
                // Assento reservado permanentemente
                seatElement.classList.add('reserved');
                STATUS_BOX.innerText = `Assento ${data.assento} RESERVADO PERMANENTEMENTE.`;
            }
            
            // Re-habilita ou desabilita o clique
            seatElement.disabled = seatElement.classList.contains('reserved') || seatElement.classList.contains('blocked');
        }

        // Inicia a aplicação
        connectWebSocket();
    </script>
</body>
</html>
"""

# Configuração
logging.basicConfig(level=logging.INFO, format='%(asctime)s - WebSocket - %(levelname)s - %(message)s')
app = FastAPI()

# Mantenha um registro de todos os clientes conectados
active_connections: list[WebSocket] = []

# --- Conexão gRPC com o Backend (Seu Booking Service) ---
# Importe os stubs gRPC (garanta que cinema_pb2 foi gerado)
import cinema_pb2
import cinema_pb2_grpc
GRPC_HOST_PORT = 'localhost:50051'
channel = grpc.insecure_channel(GRPC_HOST_PORT)
grpc_stub = cinema_pb2_grpc.ReservaStub(channel)


# --- Funções de Broadcast ---

async def broadcast(message: dict):
    """Envia uma mensagem para todos os clientes WebSocket conectados."""
    msg_json = json.dumps(message)
    # Cria uma lista de tarefas para enviar a mensagem a todos os clientes
    send_tasks = [conn.send_text(msg_json) for conn in active_connections]
    # Espera que todas as mensagens sejam enviadas
    await asyncio.gather(*send_tasks)
    logging.info(f"Broadcast enviado para {len(active_connections)} clientes: {message['evento']}")


# --- Endpoint REST para o Redis Listener ---

@app.post("/notify_liberacao")
async def notify_liberacao(request: Request):
    """Recebe notificação do Redis Listener quando um bloqueio expira (timeout)."""
    data = await request.json()
    assento_num = data.get("assento")
    
    # Faz o broadcast para o frontend (assento volta a ser verde)
    await broadcast({
        "evento": "assento_liberado",
        "assento": assento_num,
        "motivo": "timeout"
    })
    return {"message": "Notification received and broadcasted"}


# --- Endpoint WebSocket (A Comunicação em Tempo Real) ---

@app.websocket("/ws/reserva")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logging.info(f"Novo cliente conectado. Total: {len(active_connections)}")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            acao = message.get("acao")
            
            sessao = message['sessao']
            assento_num = message['assento']
            usuario = message['usuario_id']
            
            assento_id = cinema_pb2.AssentoID(sessao_id=sessao, assento_num=assento_num)
            request_grpc = cinema_pb2.ReservaRequest(assento=assento_id, usuario_id=usuario)

            # --- AÇÃO: BLOQUEAR ASSENTO (Usuário Clicou) ---
            if acao == "bloquear":
                try:
                    # Chama o gRPC para tentar bloquear (adquirir o lock no Redis)
                    response = grpc_stub.ReservarAssento(request_grpc)
                    
                    if response.sucesso:
                        # Bloqueio SUCESSO: Faz o broadcast para todos os clientes
                        await broadcast({
                            "evento": "assento_bloqueado",
                            "assento": assento_num,
                            "usuario_bloqueador": usuario
                        })
                        # Retorna a confirmação apenas para o cliente que solicitou
                        await websocket.send_text(json.dumps({"status": "ok", "mensagem": "Bloqueio temporário realizado."}))
                    else:
                        # Bloqueio FALHA: Retorna a falha apenas para o cliente que solicitou
                        await websocket.send_text(json.dumps({"status": "erro", "mensagem": response.mensagem}))
                        
                except grpc.RpcError as e:
                    logging.error(f"Erro gRPC ao bloquear: {e}")
                    await websocket.send_text(json.dumps({"status": "erro", "mensagem": "Erro interno no servidor de reserva."}))
            
            # --- Adicione mais ações aqui (e.g., confirmar pagamento, cancelar) ---
            
    except Exception as e:
        logging.warning(f"Conexão fechada inesperadamente: {e}")
    finally:
        active_connections.remove(websocket)
        logging.info(f"Cliente desconectado. Total: {len(active_connections)}")


# --- Endpoint HTML para o Frontend Simples ---

@app.get("/", response_class=HTMLResponse)
async def get():
    # Este é o HTML/JS que será servido (passo 4)
    return HTML_CONTENT