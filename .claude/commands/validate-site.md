---
description: Valida a copy e a estrutura de web/template.html contra as regras do projeto (comércio exterior x comex, preço/trial, paridade PT/EN, guardrail jurídico).
---

Valide `web/template.html` (e outra copy pública tocada na rodada) contra:
- `.claude/rules/public-copy.md`
- `.claude/rules/product-positioning.md`

Passos:

1. Busque por "comex" (case-insensitive) em `web/template.html` e em
   qualquer outro arquivo de copy pública alterado. Deve haver zero
   ocorrências fora de comentários que já explicam a proibição.
2. Confira os valores de preço/trial no arquivo contra
   `product-positioning.md` (R$ 29,90/mês, R$ 19,90 beta fundador, 7 dias
   grátis) — em PT e EN.
3. Compare os blocos PT e EN (objeto `t` / chaves `data-i` em
   `web/template.html`): todo texto alterado em um idioma deve ter
   equivalente atualizado no outro.
4. Releia trechos de copy alterados procurando por qualquer sugestão de
   compra/venda de ativo específico, mesmo implícita.
5. Se houver suíte de testes ou script relevante (`tests/test_export_web.py`,
   `tools/validate_sources.py`), rode-os e reporte o resultado.
6. Se disponível, use o agente `copy-critic` para uma segunda leitura da
   copy antes de reportar.

Reporte os achados como uma lista (achado → localização → sugestão de
correção). Não aplique correções automaticamente a menos que pedido —
proponha e espere aprovação. Termine com o bloco `## Definition of Done`
exigido por `.claude/rules/validation.md`.
