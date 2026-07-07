# Copy pública — regras literais

Aplica-se a qualquer texto que um usuário final possa ler: `web/template.html`
(PT e EN), meta tags/SEO, mensagens de Telegram, DOCX, README voltado a
usuário. Não se aplica a comentários de código, nomes de variáveis ou docs
internas de engenharia.

## Regras

1. **Literal, sem jargão desnecessário.** Prefira linguagem simples e
   direta (ex.: "custo, caixa e consumo") a termos técnicos ou de mercado
   financeiro que o público-alvo (MEI/PME) não usaria no dia a dia.
2. **"Comércio exterior", nunca "comex".** Vale para PT e para qualquer
   variação (títulos, `data-i`, alt text, meta description).
3. **Preço e trial exatamente como em `.claude/rules/product-positioning.md`.**
   Não arredondar, não trocar "7 dias grátis" por "trial gratuito" etc. sem
   decisão explícita.
4. **Sem promessa de recomendação de compra/venda de ativos** — nem mesmo
   implícita ("essa é a hora de comprar X").
5. **PT/EN em paridade.** Se um bloco de copy muda em PT, o bloco
   equivalente em EN (mesma chave `data-i` em `web/template.html`) muda
   junto, e vice-versa.
6. **Consistência de tom.** Direto, analítico, sem sensacionalismo — mesmo
   tom já usado em `impact/engine.py` (`acao_recomendada`, `impacto_custo`).

## O que isso NÃO autoriza

Estas são regras de redação, não permissão para mudar preço, público,
produto ou visual. Mudança de conteúdo (o que é dito) segue estas regras;
mudança de decisão (o que é verdade) exige aprovação explícita do usuário.
