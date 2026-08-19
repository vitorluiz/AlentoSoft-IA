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

Use `--preview` para visualizar o rascunho produzido sem aprovar a tarefa:

```bash
PYTHONPATH=. python3 -m alento_soft_ia.main \
  --provider hybrid \
  --domain marketing \
  --channel instagram \
  --goal "Criar um post educativo sobre acolhimento e orientação às famílias" \
  --source-file examples/marketing/granjimmy_contexto_minimo.md \
  --preview
```

O campo `preview` mostra o resultado da etapa de geração, enquanto o estado permanece `waiting_approval` quando a revisão é necessária. A opção não publica e não substitui a aprovação humana. O campo `output` somente é preenchido após `--approve` neste protótipo. Quando a verificação linguística identificar um padrão conhecido, o rascunho também poderá conter `quality_warnings`; esses avisos orientam a revisão e não alteram `blocked` nem liberam publicação.

## Roteamento híbrido local/cloud

O AlentoSoft-IA pode usar um provider cloud para marketing institucional sem dados sensíveis e manter o Ollama local para clínica, prontuário, RH e financeiro. O modo `hybrid` é fail-closed: somente o domínio `marketing` pode ir para cloud e somente quando a fonte tiver um nome explicitamente autorizado. As fontes públicas de demonstração autorizadas por padrão são `granjimmy_contexto_marca.md` e `granjimmy_contexto_minimo.md`. O arquivo sensível `profissionais-granjimmy` não deve ser usado como fonte cloud nem entrar no repositório público.

Para usar OpenRouter no marketing, configure uma chave de API e um identificador de modelo disponível na sua conta:

```bash
export OPENROUTER_API_KEY="sua-chave-fora-do-repositorio"
export OPENROUTER_MODEL="<slug-do-modelo-disponivel>"
export ALENTO_CLOUD_PROVIDER="openrouter"
PYTHONPATH=. python3 -m alento_soft_ia.main \
  --provider hybrid \
  --domain marketing \
  --channel whatsapp \
  --goal "Criar uma mensagem curta de acolhimento para famílias" \
  --source-file examples/marketing/granjimmy_contexto_minimo.md
```

Para chamar diretamente a API da OpenAI, use `OPENAI_API_KEY` e, opcionalmente, `OPENAI_MODEL`:

```bash
export OPENAI_API_KEY="sua-chave-fora-do-repositorio"
export OPENAI_MODEL="gpt-5-mini"
PYTHONPATH=. python3 -m alento_soft_ia.main \
  --provider openai \
  --domain marketing \
  --channel instagram \
  --goal "Criar um post educativo sobre acolhimento e orientação às famílias" \
  --source-file examples/marketing/granjimmy_contexto_marca.md
```

O modo `hybrid` devolve `OllamaProvider` para `clinical`, `hr`, `finance` e demais domínios não autorizados para cloud. Mesmo que alguém tente usar `--provider openai` ou `--provider openrouter` em `clinical`, a barreira de domínio interrompe a execução antes da chamada externa. O resultado de marketing continua exigindo aprovação humana e nunca publica automaticamente.

Se a API retornar `Provider HTTP 429`, observe o tipo exibido entre parênteses. `insufficient_quota` normalmente indica ausência de saldo, orçamento mensal atingido ou API não habilitada para a organização; `rate_limit_exceeded` indica limite temporário de requisições ou tokens por minuto. No OpenRouter, `metadata.error_type=rate_limit_exceeded` pode vir acompanhado de `provider_code=model_capacity`, indicando que o endpoint upstream está sem capacidade naquele momento, e não necessariamente que a conta ficou sem créditos. O provider preserva o tipo, o provider upstream e os cabeçalhos públicos de limite, mas nunca inclui a chave. Consulte também `GET https://openrouter.ai/api/v1/key` antes de repetir. A OpenAI recomenda exponential backoff para limites temporários [1].

Uma assinatura do ChatGPT não deve ser presumida como uma chave de API da OpenAI; a assinatura ChatGPT e a plataforma API são produtos com faturamento separado. O OpenCode é principalmente uma ferramenta cliente para conectar providers; só poderá ser usado diretamente pelo AlentoSoft-IA se houver um endpoint compatível e uma credencial própria disponível. Não se deve enviar uma chave de assinatura ou credencial de sessão para o repositório.

## Vigia de políticas e Perfil da Empresa

O vigia lê fontes públicas de Meta, LinkedIn, YouTube e Google Business Profile, guarda snapshots em SQLite, gera relatórios Markdown e detecta alterações entre execuções. Ele funciona manualmente por padrão e não publica, edita perfis, responde avaliações ou denuncia conteúdo automaticamente.

Para executar uma verificação manual:

```bash
PYTHONPATH=. python3 -m alento_soft_ia.policy_watch
```

Também existe um wrapper para execução manual ou pelo agendador do computador:

```bash
./scripts/policy_watch_weekly.sh
```

Para executar semanalmente às 08:00 de segunda-feira no Linux, abra `crontab -e` e adicione uma linha como esta:

```cron
0 8 * * 1 POLICY_WATCH_ENV_FILE=/home/ubuntu/.config/alento-policy-watch.env /home/ubuntu/AlentoSoft-IA/scripts/policy_watch_weekly.sh --send-email --send-whatsapp >> /home/ubuntu/AlentoSoft-IA/workspaces/policy-watch/cron.log 2>&1
```

O caminho deve ser ajustado ao diretório real do projeto. A execução manual continua disponível a qualquer momento; o cron não substitui a revisão do relatório. Para notificações, prefira guardar as variáveis num ficheiro fora do repositório, por exemplo `/home/ubuntu/.config/alento-policy-watch.env`, com permissões `chmod 600`, e executar o wrapper com `POLICY_WATCH_ENV_FILE=/home/ubuntu/.config/alento-policy-watch.env`.

A execução grava o histórico em `workspaces/policy-watch/policy_watch.sqlite3`, relatórios datados em `workspaces/policy-watch/reports/` e o relatório mais recente em `workspaces/policy-watch/reports/latest.md`. É possível indicar outros caminhos com `--db` e `--report-dir`. O timeout padrão é de 30 segundos por fonte e pode ser alterado com `--timeout 10`; as fontes são coletadas em paralelo e páginas lentas viram erros registados, sem travar o restante da coleta. Se houver erros, o relatório é marcado como parcial e não afirma que não houve alterações nas fontes que falharam.

O envio de e-mail é opcional e usa SMTP configurado por variáveis de ambiente, sem guardar credenciais no repositório:

```bash
export POLICY_WATCH_SMTP_HOST="smtp.exemplo.com"
export POLICY_WATCH_SMTP_PORT="587"
export POLICY_WATCH_SMTP_USER="usuario"
export POLICY_WATCH_SMTP_PASSWORD="senha-fora-do-repositorio"
export POLICY_WATCH_EMAIL_FROM="vigia@exemplo.com"
export POLICY_WATCH_EMAIL_TO="responsavel@exemplo.com"
PYTHONPATH=. python3 -m alento_soft_ia.policy_watch --send-email
```

O WhatsApp usa a WhatsApp Cloud API oficial e exige um token, um phone number ID, um destinatário interno e um template aprovado pela Meta. A integração não deve ser usada para enviar mensagens automáticas a pacientes ou famílias neste MVP:

```bash
export POLICY_WATCH_WHATSAPP_ACCESS_TOKEN="token-fora-do-repositorio"
export POLICY_WATCH_WHATSAPP_PHONE_NUMBER_ID="id-do-numero"
export POLICY_WATCH_WHATSAPP_TO="5511XXXXXXXXX"
export POLICY_WATCH_WHATSAPP_TEMPLATE_NAME="policy_watch_weekly"
export POLICY_WATCH_WHATSAPP_TEMPLATE_LANGUAGE="pt_BR"
PYTHONPATH=. python3 -m alento_soft_ia.policy_watch --send-whatsapp
```

Fora da janela de atendimento do WhatsApp, a Meta exige templates aprovados; por isso, o envio semanal deve usar um template de utilidade previamente aprovado e destinado somente ao responsável interno. Tokens e IDs devem permanecer no ambiente local ou num gestor de segredos.

## Documentação técnica

A arquitetura de controlo, validação, aprovação, bloqueio, políticas, workspace, memória e auditoria está documentada em [`docs/architecture/controles-e-fluxo-do-agente.md`](docs/architecture/controles-e-fluxo-do-agente.md).

## Próximos módulos

A sequência segura é acrescentar um executor de ferramentas em sandbox, armazenamento de documentos com RBAC, RAG por domínio, roteamento entre modelos, validação JSON estrita, observabilidade e depois áudio/transcrição. O módulo de áudio deve entrar somente depois de o núcleo, as permissões e a auditoria estarem validados.

## Limites

Não usar este protótipo para prescrição, evolução clínica real, RH real, contabilidade real ou qualquer decisão irreversível. Não ligar o protótipo ao prontuário oficial antes de existir autenticação, controlo de acesso, criptografia, retenção, backups, revisão clínica e avaliação de segurança.
