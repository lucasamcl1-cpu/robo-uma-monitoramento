#!/usr/bin/env python3
"""
Monitora colunas I e J (linhas 2-10) de cada aba da planilha UMA
e envia um resumo por aba via Telegram.
"""
import os
import io
import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SheetsMonitor")

SPREADSHEET_ID = "1K05xzKr5jg0LLqGWm73H8vdVfYFnq-Qs9MxKj8DUUZI"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_GROUP_ID", "-5144739527")

ABAS = [
    {"nome": "UMA Jardim dos Estados", "gid": "1025428530"},
    {"nome": "UMA Monte Castelo",      "gid": "1606234752"},
    {"nome": "UMA Brilhante",          "gid": "173321880"},
    {"nome": "UMA Centro",             "gid": "448467908"},
    {"nome": "UMA Julio de Castilho",  "gid": "1661500249"},
    {"nome": "UMA Chacara Cachoeira",  "gid": "1159353007"},
]

LINHA_INICIO_DIAS = 13
COL_REAL_FAT = 9
COL_DATA = 1


def ler_aba(gid: str) -> tuple[list[tuple[str, str]], str]:
    """
    Retorna:
      - lista de (descrição, valor) para I2:J10
      - último dia preenchido (ex: '04/05/26  seg.')
    """
    url = (
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
        f"/export?format=csv&gid={gid}"
    )
    resp = requests.get(url, timeout=15)
    resp.encoding = "utf-8"
    resp.raise_for_status()

    df = pd.read_csv(io.StringIO(resp.text), header=None)

    # Resumo I2:J10
    resumo = []
    for row in range(1, 10):
        descricao = str(df.iat[row, 8]) if df.shape[0] > row and df.shape[1] > 8 else "N/A"
        valor     = str(df.iat[row, 9]) if df.shape[0] > row and df.shape[1] > 9 else "N/A"
        resumo.append((descricao, valor))

    # Último dia preenchido: última linha com J (Real Fat) não-NaN
    ultimo_dia = "Não encontrado"
    for row in range(len(df) - 1, LINHA_INICIO_DIAS - 1, -1):
        if df.shape[1] <= COL_REAL_FAT:
            break
        val_j = df.iat[row, COL_REAL_FAT]
        val_b = df.iat[row, COL_DATA]
        if pd.notna(val_j) and str(val_j).strip() not in ("", "nan", "Real Fat"):
            dia_semana = str(df.iat[row, 2]).strip()
            ultimo_dia = f"{str(val_b).strip()}  {dia_semana}"
            break

    return resumo, ultimo_dia


def enviar_telegram(mensagem: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
    resp = requests.post(url, json=payload, timeout=15)
    if resp.status_code != 200:
        logger.error(f"Erro Telegram {resp.status_code}: {resp.text}")


def main() -> None:
    data_hora = datetime.now(ZoneInfo("America/Campo_Grande")).strftime("%d/%m/%Y %H:%M")
    logger.info(f"Iniciando monitoramento — {data_hora}")

    for aba in ABAS:
        logger.info(f"Lendo aba: {aba['nome']}...")
        try:
            resumo, ultimo_dia = ler_aba(aba["gid"])
        except Exception as e:
            logger.error(f"Erro ao ler {aba['nome']}: {e}")
            continue

        linhas_resumo = "\n".join(f"  <b>{desc}:</b> {valor}" for desc, valor in resumo)
        mensagem = (
            f"📍 <b>{aba['nome']}</b>\n"
            f"<i>{data_hora}</i>\n\n"
            f"{linhas_resumo}\n\n"
            f"📅 <b>Último dia preenchido:</b> {ultimo_dia}"
        )

        enviar_telegram(mensagem)
        logger.info(f"  ✓ enviado | último dia: {ultimo_dia}")
        time.sleep(1)

    logger.info("Monitoramento concluído.")


if __name__ == "__main__":
    main()
