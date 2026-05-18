#!/usr/bin/env python3
"""
Monitora planilha UMA: envia resumo + análise com 5 ações por salão via Telegram.
"""
import os
import io
import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import anthropic
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SheetsMonitor")

SPREADSHEET_ID = "1K05xzKr5jg0LLqGWm73H8vdVfYFnq-Qs9MxKj8DUUZI"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_GROUP_ID", "-5144739527")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

ABAS = [
    {"nome": "UMA Jardim dos Estados", "gid": "1025428530"},
    {"nome": "UMA Monte Castelo",      "gid": "1606234752"},
    {"nome": "UMA Brilhante",          "gid": "173321880"},
    {"nome": "UMA Centro",             "gid": "448467908"},
    {"nome": "UMA Julio de Castilho",  "gid": "1661500249"},
    {"nome": "UMA Chacara Cachoeira",  "gid": "1159353007"},
]

LINHA_INICIO_DIAS = 13
COL_DATA = 1
COL_DIA_SEMANA = 2
COL_REAL_FAT = 9   # J = Real Fat


def ler_aba(gid: str) -> dict:
    """Lê dados completos da aba e retorna dicionário com resumo e histórico."""
    url = (
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
        f"/export?format=csv&gid={gid}"
    )
    resp = requests.get(url, timeout=15)
    resp.encoding = "utf-8"
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text), header=None)

    # --- Resumo I2:J10 ---
    resumo = []
    for row in range(1, 10):
        desc  = str(df.iat[row, 8]) if df.shape[0] > row and df.shape[1] > 8 else "N/A"
        valor = str(df.iat[row, 9]) if df.shape[0] > row and df.shape[1] > 9 else "N/A"
        resumo.append((desc, valor))

    # --- Metas (linhas 5-10, col B e C) ---
    metas = []
    for row in range(4, 10):
        nome = str(df.iat[row, 1]) if df.shape[1] > 1 else "N/A"
        val  = str(df.iat[row, 2]) if df.shape[1] > 2 else "N/A"
        if str(nome) != "nan":
            metas.append(f"{nome}: {val}")

    # --- Histórico diário preenchido ---
    historico = []
    ultimo_dia = "Não encontrado"
    for row in range(LINHA_INICIO_DIAS, len(df)):
        if df.shape[1] <= COL_REAL_FAT:
            break
        val_j  = df.iat[row, COL_REAL_FAT]
        val_b  = df.iat[row, COL_DATA]
        val_c  = df.iat[row, COL_DIA_SEMANA]
        if pd.notna(val_j) and str(val_j).strip() not in ("", "nan", "Real Fat"):
            historico.append({
                "data":    str(val_b).strip(),
                "dia":     str(val_c).strip(),
                "real_fat": str(val_j).strip(),
            })
            ultimo_dia = f"{str(val_b).strip()}  {str(val_c).strip()}"

    # Pega os últimos 7 dias preenchidos para contexto
    historico_recente = historico[-7:] if len(historico) >= 7 else historico

    return {
        "resumo": resumo,
        "metas": metas,
        "ultimo_dia": ultimo_dia,
        "historico_recente": historico_recente,
    }


def analisar_com_claude(nome: str, dados: dict) -> str:
    """Chama Claude para analisar os dados e gerar 5 ações."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Monta contexto
    resumo_txt = "\n".join(f"  {d}: {v}" for d, v in dados["resumo"])
    metas_txt  = "\n".join(f"  {m}" for m in dados["metas"])
    hist_txt   = "\n".join(
        f"  {h['data']} ({h['dia']}): Real Fat = {h['real_fat']}"
        for h in dados["historico_recente"]
    ) or "  Nenhum dia preenchido ainda."

    prompt = f"""Você é um consultor de gestão especialista em redes de salões de beleza no Brasil.
Analise os dados abaixo do salão **{nome}** e forneça exatamente **5 ações práticas e específicas** para melhorar o desempenho.

## Metas do mês:
{metas_txt}

## Situação atual (totais e projeções):
{resumo_txt}

## Últimos dias preenchidos:
{hist_txt}

## Último dia com lançamento: {dados['ultimo_dia']}

---
Responda APENAS com as 5 ações, numeradas de 1 a 5.
Cada ação deve ser direta, prática e baseada nos dados acima.
Máximo de 2 linhas por ação. Sem introdução ou conclusão."""

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )

    return next(
        (block.text for block in response.content if block.type == "text"),
        "Não foi possível gerar análise."
    )


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
            dados = ler_aba(aba["gid"])
        except Exception as e:
            logger.error(f"Erro ao ler {aba['nome']}: {e}")
            continue

        # Resumo de indicadores
        linhas_resumo = "\n".join(
            f"  <b>{desc}:</b> {valor}" for desc, valor in dados["resumo"]
        )

        # Análise Claude
        logger.info(f"  Analisando com Claude...")
        try:
            acoes = analisar_com_claude(aba["nome"], dados)
        except Exception as e:
            logger.error(f"  Erro na análise: {e}")
            acoes = "Análise indisponível no momento."

        mensagem = (
            f"📍 <b>{aba['nome']}</b>\n"
            f"<i>{data_hora}</i>\n\n"
            f"{linhas_resumo}\n\n"
            f"📅 <b>Último dia preenchido:</b> {dados['ultimo_dia']}\n\n"
            f"🎯 <b>5 Ações:</b>\n{acoes}"
        )

        enviar_telegram(mensagem)
        logger.info(f"  ✓ enviado")
        time.sleep(2)  # evita rate limit

    logger.info("Monitoramento concluído.")


if __name__ == "__main__":
    main()
