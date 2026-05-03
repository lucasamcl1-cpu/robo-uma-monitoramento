#!/usr/bin/env python3
"""
Monitora células H2 e I2 de uma planilha Google Sheets pública
e envia os valores via Telegram.
"""
import asyncio
import os
import io
import logging

import pandas as pd
import requests
import aiohttp
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SheetsMonitor")

SPREADSHEET_ID = "1oyzFxUfsuqpLV2QR88hFCVqFfBEyEGefg1BXjp78spA"
SHEET_GID = "1025428530"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
    f"/export?format=csv&gid={SHEET_GID}"
)


def ler_celulas() -> tuple[str, str]:
    """Baixa a planilha e retorna os valores de H2 e I2."""
    resp = requests.get(CSV_URL, timeout=15)
    resp.raise_for_status()

    df = pd.read_csv(io.StringIO(resp.text), header=None)

    # Linha 2 = índice 1, coluna H = índice 7, coluna I = índice 8
    h2 = str(df.iat[1, 7]) if df.shape[0] > 1 and df.shape[1] > 7 else "N/A"
    i2 = str(df.iat[1, 8]) if df.shape[0] > 1 and df.shape[1] > 8 else "N/A"

    return h2, i2


async def enviar_telegram(mensagem: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.error(f"Erro Telegram {resp.status}: {text}")
            else:
                logger.info("Mensagem enviada com sucesso.")


async def main() -> None:
    logger.info("Lendo planilha...")
    h2, i2 = ler_celulas()
    logger.info(f"H2={h2}  I2={i2}")

    mensagem = (
        "📊 <b>UMA — Monitoramento Diário</b>\n\n"
        f"<b>H2:</b> {h2}\n"
        f"<b>I2:</b> {i2}"
    )
    await enviar_telegram(mensagem)


if __name__ == "__main__":
    asyncio.run(main())
