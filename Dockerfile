FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Prisma descarga su propio Node.js portable para "generate"/"migrate";
# ese binario necesita libatomic1 en el sistema para poder correr, y no
# viene incluida en las imágenes "slim" de Debian.
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs ca-certificates libatomic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY prisma ./prisma
RUN python -m prisma generate --schema=prisma/schema.prisma

COPY . .

CMD ["sh", "-c", "python -m prisma migrate deploy --schema=prisma/schema.prisma && python -m bot.main"]
