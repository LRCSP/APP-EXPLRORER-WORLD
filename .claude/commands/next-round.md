---
description: Inicia a próxima rodada iterativa de trabalho neste projeto, carregando as regras atuais antes de propor qualquer mudança.
---

Antes de propor qualquer alteração nesta rodada:

1. Releia as três regras do projeto:
   - `.claude/rules/product-positioning.md`
   - `.claude/rules/public-copy.md`
   - `.claude/rules/validation.md`
2. Pergunte ao usuário (se ainda não estiver claro na conversa) qual é o
   objetivo específico desta rodada e o que fica fora de escopo.
3. Trabalhe dentro do escopo permitido em `validation.md`. Se o pedido
   tocar produto, preço, público, visual, código funcional, secrets,
   deploy ou CI, confirme explicitamente com o usuário antes de agir.
4. Trate o resultado desta rodada como uma proposta sujeita a aprovação —
   nunca a chame de "prompt final" ou "versão final".
5. Ao final, entregue um resumo curto (o que mudou, por quê) seguido do
   bloco `## Definition of Done` exigido por `validation.md`.

Se a rodada envolver copy pública, considere usar `/validate-site` antes
de reportar como concluída.
