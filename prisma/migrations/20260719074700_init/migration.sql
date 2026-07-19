-- CreateEnum
CREATE TYPE "TipoMovimiento" AS ENUM ('PAGO', 'CORRECCION');

-- CreateTable
CREATE TABLE "Sistema" (
    "id" SERIAL NOT NULL,
    "nombre" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Sistema_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Outpost" (
    "id_num" INTEGER NOT NULL,
    "discord_id" TEXT NOT NULL,
    "nombre_pos" TEXT NOT NULL,
    "sistema_id" INTEGER NOT NULL,
    "pagado_hasta_mes" INTEGER NOT NULL DEFAULT 0,
    "anio_vencimiento" INTEGER NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Outpost_pkey" PRIMARY KEY ("id_num")
);

-- CreateTable
CREATE TABLE "Pago" (
    "id" SERIAL NOT NULL,
    "outpost_id" INTEGER NOT NULL,
    "tipo" "TipoMovimiento" NOT NULL DEFAULT 'PAGO',
    "meses" INTEGER NOT NULL,
    "monto" DOUBLE PRECISION,
    "moneda" TEXT DEFAULT 'ISK',
    "registrado_por_id" TEXT NOT NULL,
    "mes_resultante" INTEGER NOT NULL,
    "anio_resultante" INTEGER NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Pago_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Sistema_nombre_key" ON "Sistema"("nombre");

-- CreateIndex
CREATE INDEX "Outpost_discord_id_idx" ON "Outpost"("discord_id");

-- CreateIndex
CREATE INDEX "Pago_outpost_id_idx" ON "Pago"("outpost_id");

-- AddForeignKey
ALTER TABLE "Outpost" ADD CONSTRAINT "Outpost_sistema_id_fkey" FOREIGN KEY ("sistema_id") REFERENCES "Sistema"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Pago" ADD CONSTRAINT "Pago_outpost_id_fkey" FOREIGN KEY ("outpost_id") REFERENCES "Outpost"("id_num") ON DELETE CASCADE ON UPDATE CASCADE;
