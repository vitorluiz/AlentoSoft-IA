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

O adaptador aceita endpoints compatíveis com OpenAI. Para usar o Ollama localmente:

```bash
export MODEL_BASE_URL="http://localhost:11434/v1"
export MODEL_API_KEY="ollama"
export MODEL_NAME="qwen3.5:4b-q4_K_M"
```

A primeira integração deve usar JSON estruturado, `temperature=0` e `think=false` para tarefas simples. O modo thinking deve ser reservado para planeamento mais complexo, não ativado em todas as chamadas.

## Próximos módulos

A sequência segura é acrescentar um executor de ferramentas em sandbox, armazenamento de documentos com RBAC, RAG por domínio, roteamento entre modelos, validação JSON estrita, observabilidade e depois áudio/transcrição. O módulo de áudio deve entrar somente depois de o núcleo, as permissões e a auditoria estarem validados.

## Limites

Não usar este protótipo para prescrição, evolução clínica real, RH real, contabilidade real ou qualquer decisão irreversível. Não ligar o protótipo ao prontuário oficial antes de existir autenticação, controlo de acesso, criptografia, retenção, backups, revisão clínica e avaliação de segurança.
