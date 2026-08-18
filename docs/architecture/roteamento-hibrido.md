# Roteamento híbrido do AlentoSoft-IA

## Objetivo

O roteamento híbrido separa tarefas que podem utilizar serviços cloud das tarefas que devem permanecer na infraestrutura local do hospital. A regra principal é determinada pelo **domínio da tarefa e pela fonte autorizada**, e não apenas pelo modelo escolhido na linha de comando.

> **Regra de segurança:** prontuários, transcrições clínicas, dados identificáveis de pacientes, informações de RH, dados financeiros e credenciais nunca devem ser enviados a um provider cloud neste protótipo.

O objetivo é aproveitar modelos cloud para acelerar a criação de conteúdo institucional de marketing, sem transformar essa conveniência em uma passagem indireta de dados clínicos para terceiros. Todas as peças de marketing continuam sendo rascunhos e exigem aprovação humana antes de qualquer publicação.

## Classificação operacional

| Classe | Exemplos | Provider permitido | Aprovação |
|---|---|---|---|
| Marketing público autorizado | Contexto da marca, serviços institucionais autorizados, tom de voz e canais | OpenRouter ou OpenAI, mediante allowlist da fonte; Ollama também é permitido | Sempre obrigatória |
| Administrativo sem dado sensível | Política fictícia, checklist genérico, documentação interna não identificável | Ollama local por padrão; cloud não é permitido pelo modo híbrido atual | Conforme o domínio |
| Clínico sensível | Áudio de atendimento, transcrição, evolução, prontuário, diagnóstico ou prescrição | Ollama local | Obrigatória e médica quando aplicável |
| RH e financeiro | Dados de colaboradores, folha, contratos, contabilidade e documentos fiscais | Ollama local | Obrigatória |
| Segredos operacionais | Chaves de API, tokens, credenciais e arquivos de configuração | Nunca enviar ao modelo | Não se aplica |

A allowlist padrão do marketing contém apenas `granjimmy_contexto_marca.md` e `granjimmy_contexto_minimo.md`. O arquivo `profissionais-granjimmy` é sensível e permanece fora do repositório público e fora de chamadas cloud.

## Modos disponíveis

| Modo CLI | Comportamento |
|---|---|
| `demo` | Usa a skill determinística para demonstrações sem modelo externo. |
| `ollama` | Usa o endpoint local `/api/chat`; é o caminho padrão para clinical, RH e financeiro. |
| `openai` | Usa a API compatível da OpenAI, mas só aceita o domínio marketing e uma fonte allowlisted. |
| `openrouter` | Usa a API compatível do OpenRouter, mas só aceita o domínio marketing e uma fonte allowlisted. |
| `hybrid` | Usa cloud para marketing allowlisted e Ollama local para os demais domínios. |

O modo `hybrid` é deliberadamente **fail-closed**. Se o domínio não for marketing, o provider retornado é o Ollama. Se o domínio for marketing, mas a fonte não estiver autorizada, a execução cloud é recusada. Uma tentativa explícita de usar `openai` ou `openrouter` em `clinical` também é recusada antes da chamada HTTP.

## Configuração de marketing cloud

Para OpenRouter, é necessário fornecer uma chave de API e o slug de um modelo disponível na conta:

```bash
export OPENROUTER_API_KEY="..."
export OPENROUTER_MODEL="<slug-do-modelo>"
export ALENTO_CLOUD_PROVIDER="openrouter"
```

A execução usa JSON Schema estruturado para manter o contrato da skill. O OpenRouter documenta um endpoint compatível com Chat Completions em `/api/v1/chat/completions` e informa que o OpenAI SDK pode ser apontado para esse endpoint como substituição compatível [1].

Para OpenAI direta, use uma chave de API própria e, opcionalmente, defina o modelo:

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-5-mini"
```

A assinatura do ChatGPT não deve ser confundida com acesso à API: a documentação da OpenAI informa que ChatGPT e a plataforma API possuem sistemas de faturamento separados [2]. Portanto, a existência de uma assinatura de interface não garante que `OPENAI_API_KEY` esteja habilitada ou tenha saldo.

O OpenCode é tratado como uma ferramenta cliente, não como um provider automático do AlentoSoft-IA. A documentação do OpenCode descreve suporte a diversos providers, modelos locais e URLs base customizadas [3]. Para o AlentoSoft-IA utilizar um serviço associado ao OpenCode, seria necessário existir uma API ou endpoint OpenAI-compatible com credencial própria; uma sessão autenticada do aplicativo não deve ser reutilizada como chave do hospital.

## Fluxo de segurança

1. A CLI lê o domínio, o canal e a fonte autorizada.
2. O roteador verifica se o modo escolhido é `hybrid`, `openai` ou `openrouter`.
3. Se houver cloud, o roteador exige domínio `marketing` e nome de fonte presente na allowlist.
4. O provider recebe apenas o texto da fonte autorizada e o objetivo da tarefa.
5. A skill gera JSON Schema com evidência, riscos e revisão humana obrigatória.
6. O validador independente bloqueia itens classificados como `blocked`.
7. Mesmo uma saída válida fica aguardando aprovação antes de qualquer publicação.

A implementação atual controla o caminho do provider, mas não substitui autenticação, RBAC, criptografia, retenção, gestão de consentimento, avaliação de impacto e revisão jurídica. Antes do módulo clínico real, essas camadas precisam ser implementadas e testadas separadamente.

## Referências

[1]: https://openrouter.ai/docs/quickstart — OpenRouter, “Quickstart”.

[2]: https://help.openai.com/en/articles/9039756-managing-billing-settings-on-chatgpt-web-and-platform — OpenAI Help, “Managing Billing Settings on ChatGPT Web and Platform”.

[3]: https://opencode.ai/docs/providers/ — OpenCode, “Providers”.
