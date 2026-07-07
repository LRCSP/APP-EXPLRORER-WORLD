---
description: Revisa um diff/PR contra as regras do projeto antes de considerá-lo pronto (escopo, copy pública, guardrail jurídico, Definition of Done).
---

Revise o diff atual (ou o PR indicado) contra as três regras do projeto:
- `.claude/rules/product-positioning.md`
- `.claude/rules/public-copy.md`
- `.claude/rules/validation.md`

Passos:

1. Liste os arquivos alterados (`git status` / diff do PR).
2. Se algum arquivo de copy pública foi tocado (`web/template.html`,
   README voltado a usuário), rode o agente `copy-critic` sobre as partes
   alteradas.
3. Rode o agente `risk-auditor` sobre o diff completo para checar escopo
   (produto/preço/público/visual/código funcional/secrets/CI) e o
   guardrail jurídico (sem recomendação de compra/venda de ativo).
4. Confira se a descrição do PR/rodada evita chamar algo de "prompt final"
   antes de aprovação explícita do usuário.
5. Confira se a entrega inclui o bloco `## Definition of Done`.
6. Se houver testes relevantes (`pytest`, `tools/validate_sources.py`),
   confirme que passam.

Reporte os achados (bloqueante vs. aviso) com localização e sugestão. Não
aprove nem faça merge — isso é decisão do usuário.
