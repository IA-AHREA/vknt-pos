FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Node.js hace falta para las herramientas de Prisma (generate / migrate),
# el cliente Python generado en sí no lo necesita en runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY prisma ./prisma
RUN python -m prisma generate --schema=prisma/schema.prisma

COPY . .

CMD ["sh", "-c", "python -m prisma migrate deploy --schema=prisma/schema.prisma && python -m bot.main"]
