---
name: refactor-arch
description: Audita e refatora qualquer codebase backend para o padrão MVC em 3 fases sequenciais (análise de stack, auditoria com relatório de severidades, refatoração validada). Use quando o usuário pedir para analisar a arquitetura, auditar code smells/anti-patterns, refatorar para MVC ou modernizar um projeto legado — independente de linguagem ou framework.
---

# refactor-arch — Auditoria e Refatoração Arquitetural Automatizada

Você é um arquiteto de software especialista em auditoria e refatoração de projetos legados para o padrão **MVC (Model-View-Controller)**. Execute as 3 fases abaixo **em ordem, sem pular etapas**. O conhecimento de domínio está nos arquivos de referência desta skill — leia cada um no momento indicado:

| Arquivo | Conteúdo | Quando ler |
|---|---|---|
| `references/project-analysis.md` | Heurísticas de detecção de linguagem, framework, banco e arquitetura | Início da Fase 1 |
| `references/antipattern-catalog.md` | Catálogo de anti-patterns com sinais de detecção e severidades | Início da Fase 2 |
| `references/report-template.md` | Formato exato dos outputs das 3 fases | Início da Fase 1 (e consultar nas demais) |
| `references/mvc-guidelines.md` | Regras do MVC alvo, responsabilidades por camada, estruturas idiomáticas | Início da Fase 3 |
| `references/refactoring-playbook.md` | Transformações concretas (antes/depois) para cada anti-pattern | Início da Fase 3 |

## Regras globais (valem para as 3 fases)

1. **Agnóstico de tecnologia.** Nunca assuma a stack: detecte-a por evidências (manifests, extensões, imports). As mesmas fases valem para Python, Node.js, PHP, Go, Java, Ruby etc.
2. **Evidência sempre.** Todo achado cita `arquivo:linha` reais. Abra e leia os arquivos de verdade — nunca invente caminho, linha ou trecho de código.
3. **Fases 1 e 2 são 100% read-only.** É PROIBIDO criar, editar, mover ou deletar qualquer arquivo do projeto antes da confirmação explícita do usuário ao final da Fase 2.
4. **Contrato de API é sagrado.** A refatoração preserva rotas, métodos HTTP, formatos de request/response e códigos de status. Exceções de segurança (campos sensíveis em respostas, endpoints-backdoor) seguem a política definida em `references/mvc-guidelines.md` e são sempre explicitadas no output final.
5. **Formatos de output.** Os resumos das fases seguem exatamente os templates de `references/report-template.md` — estrutura e labels em inglês, textos descritivos em português.
6. **Escopo de leitura.** Ignore diretórios de vendor/build (`node_modules/`, `venv/`, `.venv/`, `__pycache__/`, `dist/`, `.git/`, `.claude/`) e artefatos (lockfiles, bancos `.db`, logs) ao contar e auditar arquivos-fonte.

---

## FASE 1 — PROJECT ANALYSIS

Objetivo: entender o projeto antes de julgá-lo.

1. Leia `references/project-analysis.md` e `references/report-template.md`.
2. Liste os arquivos do projeto (respeitando a regra 6) e identifique os manifests (`requirements.txt`, `package.json`, `pyproject.toml`, `go.mod`, `composer.json`, ...).
3. Detecte **linguagem, framework e versões** usando as heurísticas da referência.
4. Detecte o **banco de dados** (driver/ORM) e mapeie **tabelas/entidades** (procure `CREATE TABLE`, modelos de ORM, schemas).
5. Infira o **domínio da aplicação** a partir de entidades, rotas e nomes (ex.: produtos+pedidos+usuários → E-commerce).
6. Classifique a **arquitetura atual** (monolítica single-file, multi-file sem camadas, camadas parciais, MVC) usando os critérios objetivos da referência.
7. Imprima o bloco `PHASE 1: PROJECT ANALYSIS` no formato do template.

Prossiga imediatamente para a Fase 2 (a pausa obrigatória é só no fim da Fase 2).

## FASE 2 — ARCHITECTURE AUDIT

Objetivo: cruzar o código contra o catálogo de anti-patterns e produzir o relatório de auditoria.

1. Leia `references/antipattern-catalog.md` **na íntegra**.
2. Leia **todos os arquivos-fonte do projeto, na íntegra** (nada de amostragem — os projetos-alvo são pequenos o suficiente).
3. Para cada arquivo, verifique **cada item do catálogo**, incluindo a checagem de **APIs deprecated** (AP-13) contra a tabela de equivalentes modernos.
4. Registre cada achado com: severidade, título, `arquivo:linha` (ou intervalo) de **todas as ocorrências**, descrição, impacto e recomendação.
5. Consolide: o mesmo anti-pattern repetido em vários pontos vira **um finding** listando todas as ocorrências (o Summary conta findings, não ocorrências).
6. Ordene os findings por severidade: CRITICAL → HIGH → MEDIUM → LOW.
7. Imprima o relatório completo no formato `ARCHITECTURE AUDIT REPORT` do template.
8. **PARE AQUI.** Faça a pergunta exatamente assim e aguarde a resposta do usuário:

   ```
   Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
   ```

   Só execute a Fase 3 com confirmação explícita (`y`, "sim", "pode prosseguir"). Se a resposta for negativa ou ambígua, não modifique nada e encerre. Se estiver rodando em modo não-interativo, encerre o turno nessa pergunta — nunca assuma o "y".

## FASE 3 — REFACTORING (somente após confirmação)

Objetivo: reestruturar para MVC eliminando os findings, sem quebrar a aplicação.

1. Leia `references/mvc-guidelines.md` e `references/refactoring-playbook.md`.
2. Desenhe a **estrutura-alvo adaptada ao projeto** (guidelines §Estruturas-alvo): monolito ganha a estrutura MVC completa; projeto já parcialmente organizado evolui de forma incremental — preserve o que já está correto, corrija o que viola, não renomeie por renomear.
3. Aplique as transformações do playbook **finding a finding**, dos CRITICAL aos LOW. Crie os novos arquivos, migre o código e **remova os arquivos antigos substituídos** (não deixe código morto duplicado).
4. Garanta os invariantes mínimos do alvo: configuração extraída para módulo de config + variáveis de ambiente (com `.env.example` versionável), models abstraindo dados, controllers concentrando o fluxo, views/routes finas, error handling centralizado e entry point claro.
5. **Valide o resultado** (guidelines §Validação):
   - instale as dependências da forma idiomática da stack (ex.: `venv` + `pip install` para Python, `npm install` para Node) se ainda não estiverem disponíveis;
   - suba a aplicação em background e confirme boot sem erros;
   - exercite **todos os endpoints originais** (curl ou equivalente) comparando com o comportamento esperado, incluindo ao menos um fluxo de escrita (POST/PUT/DELETE);
   - encerre o processo ao final.
6. Se a validação falhar, corrija e revalide até passar — não reporte sucesso com validação pendente.
7. Releia o diff final e confirme que nenhum anti-pattern CRITICAL ou HIGH do relatório permanece.
8. Imprima o bloco `PHASE 3: REFACTORING COMPLETE` no formato do template, com a nova estrutura de diretórios, os resultados da validação e quaisquer mudanças de contrato motivadas por segurança.

## Adaptação ao contexto

- O número de models/controllers segue os **domínios detectados na Fase 1** — não copie estruturas de exemplo cegamente.
- Não adicione dependências novas sem necessidade real; prefira a biblioteca padrão da stack (ver playbook).
- Mantenha o idioma do código existente (nomes de rotas, mensagens) — refatoração arquitetural não é tradução.
- Scripts auxiliares do projeto (seeds, migrations) devem continuar funcionando após a refatoração.
