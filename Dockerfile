FROM python:3.11-slim

WORKDIR /app

# Dependências primeiro (cache de build)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Produção agendada: roda o agendador (usa SCHEDULE_CRON do ambiente).
# Para uma execução única, sobrescreva o comando: ["python", "orchestrator.py", "--once"]
CMD ["python", "orchestrator.py", "--schedule"]
