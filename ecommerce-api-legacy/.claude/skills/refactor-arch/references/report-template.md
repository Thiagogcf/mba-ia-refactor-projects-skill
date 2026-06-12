# Templates de Output (Fases 1, 2 e 3)

Reproduza os formatos abaixo **exatamente** (mesmos labels, mesma ordem). Labels e estrutura em inglês; textos descritivos em português. As linhas de `=` têm 32 caracteres.

## Fase 1 — Resumo da análise

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem + versão se detectável>
Framework:     <framework + versão>
Dependencies:  <dependências secundárias relevantes>
Domain:        <domínio em uma linha (recursos principais)>
Architecture:  <classificação + descrição curta da organização atual>
Source files:  <N> files analyzed
DB tables:     <tabelas/entidades detectadas>
================================
```

Campos sem evidência: use `n/a` + observação curta. Não invente.

## Fase 2 — Relatório de auditoria

````
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome do diretório do projeto>
Stack:   <linguagem + framework>
Files:   <N> analyzed | ~<L> lines of code

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

## Findings

### [<SEVERITY>] <Título do finding> (<AP-xx>)
File: <arquivo>:<linha ou intervalo>[, <arquivo>:<linhas> ...]
Description: <o que foi encontrado, com evidência concreta (trecho/valor) em português>
Impact: <consequência prática>
Recommendation: <correção objetiva, citando a transformação do playbook quando aplicável>

[... um bloco por finding ...]

================================
Total: <n> findings
================================
````

**Regras do relatório:**

1. Ordene por severidade: todos os CRITICAL, depois HIGH, MEDIUM, LOW. Dentro da mesma severidade, ordene do impacto maior para o menor.
2. `File:` lista **todas as ocorrências** do finding (`arquivo:linha`); use intervalos (`models.py:43-52`) para blocos.
3. Os números do `## Summary` contam **findings** (já consolidados), e devem bater com os blocos listados e com o `Total:`.
4. `~<L> lines of code` = soma aproximada de linhas dos arquivos-fonte analisados.
5. Cada finding referencia o item do catálogo (`AP-xx`) para rastreabilidade.
6. Após imprimir o relatório, faça a pergunta de confirmação **fora** do bloco do relatório:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

## Fase 3 — Resumo da refatoração

````
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<árvore de diretórios/arquivos resultante (formato `tree`), anotando o entry point>

## Findings Resolved
<n>/<total> findings resolvidos (liste IDs e, para qualquer não resolvido, o motivo)

## Security Contract Changes
<mudanças de contrato motivadas por segurança (ex.: endpoint X agora exige header Y; campo `senha` removido das respostas) — ou "None">

## Validation
  ✓ Application boots without errors            (<comando usado>)
  ✓ All original endpoints respond correctly    (<N> endpoints exercitados)
  ✓ Write flow verified                         (<exemplo: POST /recurso → 201>)
  ✓ Zero CRITICAL/HIGH anti-patterns remaining
================================
````

**Regras do resumo final:**

1. Só marque `✓` no que foi de fato executado e observado nesta sessão; falhas aparecem como `✗` com explicação e o resumo só sai depois de re-validar.
2. Liste os endpoints exercitados e o status HTTP obtido de cada um (pode ser em lista compacta abaixo do bloco).
3. Se algum finding LOW/MEDIUM ficou pendente de propósito (ex.: fora de escopo), declare em `Findings Resolved` — transparência acima de score.
