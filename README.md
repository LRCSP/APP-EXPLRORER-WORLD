# Monitor de Inteligência Geopolítica Operacional

Produto B2B que monitora sinais de **energia, petróleo, cyber, fertilizantes,
alimentos, insumos essenciais e exportações** e — o diferencial — traduz cada
sinal em **impacto operacional** para empresários (custo, cadeia de suprimentos,
exposição cyber e ação recomendada). O mesmo briefing é entregue em **3 canais**:
Telegram, DOCX e Google Sheets.

> Alvo desta versão: **produção com execução agendada** (APScheduler).
> Status atual: **Fase 0 — esqueleto** (sem lógica de pipeline ainda).

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

> O pipeline ainda não roda (Fase 0). Quando estiver pronto (Fase 5):

```bash
python orchestrator.py           # execução manual / dry-run
```

O agendamento em produção usa `SCHEDULE_CRON` (formato cron do APScheduler).

## Roadmap (protocolo de fases)

- [x] **Fase 0** — Decisões e esqueleto (estrutura, requirements, `.env.example`, `sources.yaml`)
- [ ] **Fase 1** — Ingestão + validação das fontes
- [ ] **Fase 2** — Análise/classificação (API Anthropic, JSON estrito)
- [ ] **Fase 3** — Motor de impacto operacional + objeto Briefing
- [ ] **Fase 4** — Entrega: Telegram, DOCX, Sheets
- [ ] **Fase 5** — Orquestração, agendamento e teste end-to-end
