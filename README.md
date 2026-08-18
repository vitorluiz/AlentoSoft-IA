# AlentoSoft-IA — protótipo inicial

Este repositório contém um núcleo pequeno de orquestração para um agente local do AlentoSoft-IA. Ele não é ainda um sistema clínico e não deve receber dados reais de pacientes. O objetivo é validar primeiro o processo: criar tarefa, planear etapas, produzir um resultado estruturado, validar, bloquear domínios sensíveis até haver aprovação e registar auditoria.

## O que já funciona

O protótipo possui um plano explícito com as etapas de compreensão, recolha, geração, validação e aprovação. Tem políticas por domínio, auditoria SQLite, uma skill determinística não clínica, workspace isolado e um adaptador opcional para endpoints compatíveis com OpenAI. Tarefas clínicas, RH e financeiras ficam pendentes de aprovação humana; nenhuma ferramenta externa ou escrita no prontuário está implementada.

## Executar a demonstração

A partir da pasta do projeto:

```bash
cd /home/ubuntu/alento-soft-ia
PYTHONPATH=. python3 -m alento_soft_ia.main --goal "Criar checklist de admissão administrativa" --domain general
```

Para demonstrar o bloqueio de aprovação clínica:

```bash
PYTHONPATH=. python3 -m alento_soft_ia.main --goal "Preparar rascunho de evolução" --domain clinical
```

Para simular a aprovação humana:

```bash
PYTHONPATH=. python3 -m alento_soft_ia.main --goal "Preparar rascunho de evolução" --domain clinical --approve
```

A auditoria de cada demonstração é gravada em `workspaces/demo/audit.sqlite3`.

## Testes

```bash
cd /home/ubuntu/alento-soft-ia
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

## Ligação ao Ollama

O adaptador nativo usa o endpoint local `/api/chat` para controlar `think=false`, JSON Schema, `temperature=0` e `keep_alive`. Para executar uma tarefa administrativa com o Qwen3.5:

```bash
cd /home/ubuntu/alento-soft-ia
export MODEL_NAME="qwen3.5:4b-q4_K_M"
PYTHONPATH=. python3 -m alento_soft_ia.main \
  --provider ollama \
  --goal "Criar checklist de admissão administrativa" \
  --domain general
```

O modo thinking fica desativado por padrão nas tarefas simples. Use `OLLAMA_THINK=true` somente para planeamento mais complexo e nunca como padrão em todas as chamadas. `OLLAMA_KEEP_ALIVE=10m` evita recarregar o modelo a cada tarefa durante os testes.

Para testar uma skill fundamentada, forneça a política fictícia como fonte autorizada:

```bash
PYTHONPATH=. python3 -m alento_soft_ia.main \\
  --provider ollama \\
  --goal "Criar checklist de admissão de colaborador usando somente a política" \\
  --domain general \\
  --source-file examples/politicas/politica_admissao_colaborador_ficticia.md
```

A skill deve citar a seção e a evidência de cada item. Informações ausentes devem aparecer em `missing_information` e não podem ser convertidas em requisitos inventados. Se um item vier com `status: blocked`, a tarefa fica bloqueada e não pode ser concluída apenas com `--approve`; a aprovação humana só libera um rascunho que não contenha bloqueios.

Para confirmar que o Ollama está disponível:

```bash
curl http://localhost:11434/api/tags
```

## Skill de marketing do Granjimmy

A skill de marketing usa uma fonte autorizada da marca e mantém cada peça em revisão humana. Para testar localmente:

```bash
PYTHONPATH=. python3 -m alento_soft_ia.main \\
  --provider ollama \\
  --domain marketing \\
  --channel instagram \\
  --goal "Criar uma semana de conteúdo para Instagram" \\
  --source-file examples/marketing/granjimmy_contexto_marca.md
```

A saída contém canal, formato, título, texto, chamada para ação, fonte, evidência, riscos e `human_review_required`. A publicação automática em qualquer canal está bloqueada no MVP. Para uma máquina sem GPU, execute um canal por vez. Os limites padrão do Ollama são `OLLAMA_NUM_CTX=8192` e `OLLAMA_NUM_PREDICT=600`; podem ser reduzidos para acelerar o teste.

## Documentação técnica

A arquitetura de controlo, validação, aprovação, bloqueio, políticas, workspace, memória e auditoria está documentada em [`docs/architecture/controles-e-fluxo-do-agente.md`](docs/architecture/controles-e-fluxo-do-agente.md).

## Próximos módulos

A sequência segura é acrescentar um executor de ferramentas em sandbox, armazenamento de documentos com RBAC, RAG por domínio, roteamento entre modelos, validação JSON estrita, observabilidade e depois áudio/transcrição. O módulo de áudio deve entrar somente depois de o núcleo, as permissões e a auditoria estarem validados.

## Limites

Não usar este protótipo para prescrição, evolução clínica real, RH real, contabilidade real ou qualquer decisão irreversível. Não ligar o protótipo ao prontuário oficial antes de existir autenticação, controlo de acesso, criptografia, retenção, backups, revisão clínica e avaliação de segurança.
