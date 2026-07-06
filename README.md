# Monitor de Inteligência Geopolítica Operacional

Produto B2B que monitora sinais de **energia, petróleo, cyber, fertilizantes,
alimentos, insumos essenciais e exportações** e — o diferencial — traduz cada
sinal em **impacto operacional** para empresários (custo, cadeia de suprimentos,
exposição cyber e ação recomendada). O mesmo briefing é entregue em **3 canais**:
Telegram, DOCX e Google Sheets.

> Alvo desta versão: **produção com execução agendada** (APScheduler).
> Status: **pipeline completo e rodável** (`python orchestrator.py --dry-run`).

## Arquitetura

```
ingest/        Fase 1 — busca e normaliza eventos das fontes (RSS)
analysis/      Fase 2 — classifica setor/geografia/severidade/relevância (API Anthropic)
impact/        Fase 3 — gera o bloco de impacto operacional + objeto Briefing
delivery/      Fase 4 — adaptadores Telegram / DOCX / Sheets (1 fonte de verdade)
config/        configuração (sources.yaml) e loaders
orchestrator.py  Fase 5 — pipeline end-to-end, logging e agendamento
```

Princípios: **modular e auditável**, configuração **fora do código**
(YAML + `.env`), **sem hardcode de chaves**.

Schema comum de evento (Fase 1):
`{titulo, fonte, url, data, setor, texto_bruto}`

## Pré-requisitos

- Python 3.10+
- Chave da **API Anthropic**
- **Bot do Telegram** (token) e um chat/canal de destino (chat_id)
- **Service account do Google** com acesso à planilha de destino (Sheets API)

## Setup

```bash
# 1. Ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Dependências
pip install -r requirements.txt

# 3. Configuração
cp .env.example .env             # preencha suas chaves no .env (NÃO comite)
```

### Credenciais

Todos os segredos ficam em `.env` (ignorado pelo git). O `.env.example` lista
cada variável esperada:

| Variável | Para quê |
|---|---|
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | Análise (Fase 2) e impacto (Fase 3) |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Entrega no Telegram (Fase 4) |
| `GOOGLE_SA_JSON_PATH` / `GOOGLE_SHEETS_ID` / `GOOGLE_SHEETS_WORKSHEET` | Entrega no Sheets (Fase 4) |
| `SCHEDULE_CRON` / `TIMEZONE` | Agendamento (Fase 5) |
| `TOP_N_EVENTS` / `LOG_LEVEL` | Comportamento do pipeline |

O JSON da service account do Google deve ficar **fora do repositório** (ex.:
`./secrets/`, já no `.gitignore`) e ser referenciado por `GOOGLE_SA_JSON_PATH`.

## Fontes

As fontes ficam em `config/sources.yaml`, agrupadas por setor. São feeds
**candidatos** — a Fase 1 valida cada um e reporta quais respondem e quais
falham. Para desativar uma fonte sem removê-la, use `enabled: false`.

## Execução

```bash
python orchestrator.py --dry-run    # roda TUDO sem enviar; gera arquivos em out/
python orchestrator.py --once       # roda e entrega nos canais configurados (.env)
python orchestrator.py --schedule   # agenda execuções (APScheduler / SCHEDULE_CRON)
```

O `--dry-run` funciona **sem nenhuma credencial**: gera `out/briefing.docx`,
`out/briefing.csv` (preview do Sheets) e `out/telegram_preview.txt`.

Validar as fontes a qualquer momento:

```bash
python -m tools.validate_sources
```

### Modo DEMO x Modo REAL

Sem nenhuma chave de IA, a classificação e o impacto rodam em **modo DEMO**
(heurística por palavras-chave + textos templated) — útil para ver o pipeline
funcionando. Com uma chave presente, o sistema usa a IA de verdade, gerando
classificação e impacto operacional específicos por evento. A troca é
automática: nenhum código muda.

O "cérebro" é isolado e aceita **dois provedores** (escolha no `.env` via
`LLM_PROVIDER`):
- **Gemini** (`GEMINI_API_KEY`) — tem **faixa gratuita**, opção mais barata.
- **Anthropic** (`ANTHROPIC_API_KEY`) — alternativa.

## Como ligar de verdade (3 chaves)

Tudo vai no arquivo `.env` (copie de `.env.example`). Nada de chave no código.

1. **Chave da IA** (cérebro: análise + impacto) — escolha uma:
   - **Gemini (mais barato, faixa gratuita):** https://aistudio.google.com/apikey
     → cole em `GEMINI_API_KEY` (começa com `AIza...`).
   - **Anthropic (alternativa):** https://console.anthropic.com → API Keys
     → cole em `ANTHROPIC_API_KEY`.

2. **Telegram** (entrega no celular)
   - No Telegram, fale com o **@BotFather**, mande `/newbot`, siga os passos.
     Ele te dá o **token** → `TELEGRAM_BOT_TOKEN`.
   - Adicione o bot ao seu grupo/canal e descubra o **chat_id** (ex.: mande
     uma mensagem e acesse `https://api.telegram.org/bot<TOKEN>/getUpdates`).
     Coloque em `TELEGRAM_CHAT_ID`.

3. **Google Sheets** (planilha)
   - No Google Cloud Console, crie uma **service account**, ative a **Google
     Sheets API**, gere uma chave **JSON** e salve em `./secrets/`.
   - Aponte `GOOGLE_SA_JSON_PATH` para esse arquivo.
   - Crie uma planilha, **compartilhe** com o e-mail da service account e
     copie o ID da URL para `GOOGLE_SHEETS_ID`.

Depois é só `python orchestrator.py --once`.

## Produção (agendado)

- Local/servidor: `python orchestrator.py --schedule` (lê `SCHEDULE_CRON`).
- Docker: `docker build -t geo-monitor . && docker run --env-file .env geo-monitor`.

## Roadmap (protocolo de fases) — todas concluídas ✅

- [x] **Fase 0** — Decisões e esqueleto
- [x] **Fase 1** — Ingestão + validação das fontes (14/14 feeds validados)
- [x] **Fase 2** — Análise/classificação (API Anthropic, JSON estrito + fallback DEMO)
- [x] **Fase 3** — Motor de impacto operacional + objeto Briefing
- [x] **Fase 4** — Entrega: Telegram, DOCX, Sheets (3 adaptadores, 1 fonte de verdade)
- [x] **Fase 5** — Orquestração, agendamento e teste end-to-end
