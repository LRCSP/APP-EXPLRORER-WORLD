# Processo de validação (regras de rodada)

## Iterativo por padrão

Trate toda entrega como uma rodada intermediária. Nunca chame um texto,
copy ou spec de **"prompt final"**, "versão final" ou equivalente até o
usuário aprovar explicitamente naquela conversa. Use "rodada N",
"proposta" ou "rascunho para revisão".

## Escopo permitido sem pedido explícito

- Editar copy pública seguindo `public-copy.md` e `product-positioning.md`.
- Rodar testes existentes (`pytest`), `tools/validate_sources.py`,
  validação de estrutura/markdown.
- Criar/ajustar arquivos em `.claude/` (comandos, regras, agentes).

## Fora de escopo sem pedido explícito

- Produto, preço, público-alvo, visual (CSS/layout) ou código funcional
  (`analysis/`, `impact/`, `delivery/`, `orchestrator.py`, etc.).
- Secrets, `.env`, deploy, CI/CD, GitHub Actions, permissões, configuração
  sensível.
- Merge de branches ou push para branch diferente da designada na tarefa.
- Criar subagentes além dos já definidos em `.claude/agents/` — reusar os
  existentes antes de propor um novo.

## Definition of Done (obrigatório em toda alteração)

Toda mudança — de copy, regra, comando ou agente — deve terminar com um
bloco `## Definition of Done` explícito cobrindo:

1. O que foi alterado (arquivos).
2. Regras aplicadas (`product-positioning.md` / `public-copy.md` /
   `validation.md`) e como foram verificadas.
3. O que **não** foi alterado (produto/preço/público/visual/código/secrets/
   CI), quando relevante ao pedido.
4. Pendências ou decisões que ainda dependem do usuário.

Sem esse bloco, a rodada não está completa.
