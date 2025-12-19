# Usa uma imagem Python leve
FROM python:3.9-slim

# Define diretório de trabalho
WORKDIR /app

# Instala dependências do sistema necessárias para compilar algumas libs (opcional, mas bom ter)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia os requisitos e instala
COPY requirements.txt .
# Atualiza o pip para garantir compatibilidade
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código fonte para dentro do container
COPY . .

# --- A MÁGICA ACONTECE AQUI ---
# Gera os arquivos pb2 e pb2_grpc usando as bibliotecas EXATAS que acabaram de ser instaladas.
# Isso garante que a versão do gerador (gencode) bata com a runtime.
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. cinema.proto
# ------------------------------

# Comando padrão (será sobrescrito pelo docker-compose)
CMD ["python", "-m", "uvicorn", "websocket_server:app", "--host", "0.0.0.0", "--port", "8000"]