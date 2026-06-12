# Guidelines de Arquitetura — MVC Alvo (Fase 3)

## Camadas e responsabilidades

| Camada | Responsabilidade | O que é PROIBIDO aqui |
|---|---|---|
| **Models** | Acesso a dados (queries/ORM), regras de domínio da entidade (validações de estado, cálculos), serialização canônica (`to_dict`/`toJSON` **sem campos sensíveis**) | Conhecer HTTP (request/response/status), registrar rotas |
| **Views/Routes** | Mapear URL+método → controller; extrair parâmetros brutos do request; devolver a resposta produzida pelo controller | Query/SQL, regra de negócio, validação além de parse básico |
| **Controllers** | Orquestrar o fluxo do caso de uso: validar entrada, chamar models/services, decidir status HTTP, montar a resposta | SQL direto, criação de schema, lógica de domínio complexa (delegar ao model/service) |
| **Config** | Centralizar TODA configuração lendo de variáveis de ambiente com defaults seguros | Importar qualquer outra camada |
| **Middlewares** | Preocupações transversais: error handler, autenticação/autorização, logging de request | Regra de negócio |
| **Services** (opcional) | Integrações externas (email, pagamento, fila) e casos de uso multi-entidade | Conhecer HTTP |
| **Entry point** | Composition root: criar app, carregar config, inicializar banco, registrar rotas e middlewares, iniciar servidor | Definir handlers inline, regra de negócio |

**Regra de dependência (direção única):** `entry point → routes → controllers → models/services → config`. Nenhuma camada importa algo de uma camada acima dela. Models nunca importam controllers; controllers nunca importam routes.

## Estruturas-alvo idiomáticas

Adapte os domínios ao projeto (1 model + 1 controller por entidade/recurso detectado na Fase 1). Não crie arquivos vazios "por simetria".

**Python/Flask:**
```
src/  (ou raiz do projeto, mantendo a convenção existente)
├── app.py                    # composition root (create_app + run)
├── config/settings.py        # os.environ.get(...) com defaults seguros
├── models/<entidade>_model.py
├── controllers/<entidade>_controller.py
├── views/routes.py           # Blueprints: rota → controller (1 linha por rota)
├── middlewares/error_handler.py
└── database.py               # conexão/sessão gerenciada (sem global solto)
```

**Node.js/Express:**
```
src/
├── app.js                    # composition root
├── config/index.js           # process.env com defaults seguros
├── models/<entidade>Model.js
├── controllers/<entidade>Controller.js
├── routes/index.js           # Router: rota → controller
├── middlewares/errorHandler.js
└── database.js               # acesso ao banco promisificado
```

Mapa de termos: Blueprint (Flask) ≈ Router (Express); decorator de rota ≈ `router.get(...)`; `@app.errorhandler` ≈ middleware de erro `(err, req, res, next)`.

## Modo de aplicação: completo vs. incremental

- **Projeto monolítico/sem camadas:** aplique a estrutura-alvo completa. Migre o código por domínio (entidade a entidade), removendo os arquivos antigos ao final de cada migração.
- **Projeto com camadas parciais:** NÃO reescreva do zero nem renomeie diretórios que já seguem convenção válida (`routes/` pode permanecer `routes/`; criar `controllers/` para onde a lógica das rotas vai). Corrija as violações: afinar rotas, mover regra duplicada para o model, extrair config, centralizar erros. Preserve nomes de arquivos/módulos que já estão certos para minimizar o diff.
- Em ambos os casos, scripts auxiliares (seed, migrations) são atualizados para os novos imports e **testados**.

## Invariantes obrigatórios do resultado

1. Config sem hardcoded: segredos e flags via variáveis de ambiente (`config/`), com `.env.example` versionado documentando cada variável (NUNCA commitar `.env` com valores reais).
2. Models abstraem 100% do acesso a dados — nenhuma query fora deles.
3. Controllers concentram o fluxo; routes têm ~1 linha por rota.
4. Error handling centralizado num único lugar; handlers não repetem try/catch genérico.
5. Entry point único e claro; a aplicação sobe com o mesmo comando de antes (ou o novo comando é documentado no resumo final).
6. Comportamento preservado: mesmas rotas, mesmos formatos de resposta, mesma porta, mesma inicialização de banco/seed.

## Política para endpoints e campos inseguros (exceções ao contrato)

O contrato externo só muda quando ele **é** a vulnerabilidade — e toda mudança aparece na seção `Security Contract Changes` do output final:

- **Campos sensíveis em respostas** (senha/hash/token interno): remover do payload. Clientes legítimos não dependem deles.
- **Endpoints administrativos/destrutivos sem auth** (reset de banco, relatórios financeiros): manter o endpoint respondendo, mas protegido por credencial de ambiente (ex.: header `X-Admin-Token` comparado a `ADMIN_TOKEN` do env; sem a variável definida, responder 403). Não invente um sistema de autenticação completo — proteção mínima honesta.
- **Backdoors irrecuperáveis** (endpoint que executa SQL arbitrário do cliente): a recomendação no relatório é REMOÇÃO. Como remover quebra contrato, aplique a proteção por credencial de ambiente e registre a recomendação de remoção — só remova de fato se o usuário aprovar explicitamente.
- **Logs com dados sensíveis** (cartão, chaves): redigir/remover sem cerimônia — log não é contrato.

## Validação (obrigatória antes de declarar sucesso)

1. **Dependências:** se o ambiente não tiver as dependências, instale do jeito idiomático e isolado (`python -m venv venv && venv/bin/pip install -r requirements.txt`; `npm install`). Nunca instale pacotes Python no interpretador global do sistema.
2. **Boot:** suba a aplicação em background redirecionando o log para arquivo; confirme no log que o servidor está ouvindo e sem stack traces.
3. **Endpoints:** exercite todos os endpoints originais com `curl` (ou cliente da stack), conferindo status e shape da resposta. Inclua: ao menos 1 leitura por recurso, 1 fluxo de escrita completo (criar → ler de volta) e 1 caso de erro esperado (404/400) para provar o error handler.
4. **Scripts auxiliares:** rode o seed (se existir) contra um banco limpo e suba de novo.
5. **Encerramento:** mate o processo do servidor ao final e limpe artefatos temporários de teste (bancos de teste, logs), preservando o estado esperado pelo usuário.
6. Falhou? Corrija e repita o ciclo completo. O bloco `PHASE 3: REFACTORING COMPLETE` só é impresso com validação 100% verde.
