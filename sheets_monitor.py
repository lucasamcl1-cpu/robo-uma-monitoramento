#!/usr/bin/env python3
"""
Monitora colunas I e J (linhas 2-10) de cada aba da planilha UMA
e envia um resumo por aba via Telegram.
"""
import asyncio
import os
import io
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import aiohttp
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SheetsMonitor")

SPREADSHEET_ID = "1K05xzKr5jg0LLqGWm73H8vdVfYFnq-Qs9MxKj8DUUZI"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

ABAS = [
    {"nome": "UMA Jardim dos Estados", "gid": "1025428530"},
    {"nome": "UMA Monte Castelo",      "gid": "1606234752"},
    {"nome": "UMA Brilhante",          "gid": "173321880"},
    {"nome": "UMA Centro",             "gid": "448467908"},
    {"nome": "UMA Julio de Castilho",  "gid": "1661500249"},
    {"nome": "UMA Chacara Cachoeira",  "gid": "1159353007"},
]


def ler_aba(gid: str) -> list[tuple[str, str]]:
    """Lê I2:J10 de uma aba e retorna lista de (descrição, valor)."""
    url = (
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
        f"/export?format=csv&gid={gid}"
    )
    resp = requests.get(url, timeout=15)
    resp.encoding = "utf-8"
    resp.raise_for_status()

    df = pd.read_csv(io.StringIO(resp.text), header=None)

    resultado = []
    for row in range(1, 10):  # índices 1-9 = linhas 2-10
        descricao = str(df.iat[row, 8]) if df.shape[0] > row and df.shape[1] > 8 else "N/A"
        valor = str(df.iat[row, 9]) if df.shape[0] > row and df.shape[1] > 9 else "N/A"
        resultado.append((descricao, valor))

    return resultado


async def enviar_telegram(mensagem: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.error(f"Erro Telegram {resp.status}: {text}")


async def main() -> None:
    data_hora = datetime.now(ZoneInfo("America/Campo_Grande")).strftime("%d/%m/%Y %H:%M")
    logger.info(f"Iniciando monitoramento — {data_hora}")

    for aba in ABAS:
        logger.info(f"Lendo aba: {aba['nome']}...")
        try:
            dados = ler_aba(aba["gid"])
        except Exception as e:
            logger.error(f"Erro ao ler {aba['nome']}: {e}")
            continue

        linhas = "\n".join(f"  <b>{desc}:</b> {valor}" for desc, valor in dados)
        mensagem = (
            f"📍 <b>{aba['nome']}</b>\n"
            f"<i>{data_hora}</i>\n\n"
            f"{linhas}"
        )

        await enviar_telegram(mensagem)
        logger.info(f"  ✓ enviado")
        await asyncio.sleep(1)  # evita rate limit do Telegram

    logger.info("Monitoramento concluído.")


if __name__ == "__main__":
    asyncio.run(main())
