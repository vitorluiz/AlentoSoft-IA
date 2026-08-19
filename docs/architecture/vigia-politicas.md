# Vigia de políticas e operação do Granjimmy

## Objetivo

O vigia acompanha fontes públicas de Meta, LinkedIn, YouTube e Google Business Profile. Ele guarda versões datadas, identifica alterações e prepara um relatório para revisão humana. O componente não publica conteúdo, não edita perfis, não responde avaliações e não denuncia material automaticamente.

## Fontes monitorizadas

| Identificador | Plataforma | Categoria | Prioridade |
|---|---|---|---|
| `meta_business_help` | Meta | Central de ajuda empresarial | Importante |
| `meta_ads_guide_update` | Meta | Guia de anúncios | Importante |
| `meta_ad_standards` | Meta | Padrões de publicidade | Crítica |
| `linkedin_help` | LinkedIn | Ajuda geral | Importante |
| `linkedin_policy_updates` | LinkedIn | User Agreement e Privacy Policy | Crítica |
| `youtube_policy` | YouTube | Políticas de criadores | Importante |
| `youtube_monetization` | YouTube | Monetização | Crítica |
| `google_business_help` | Google Business Profile | Central de ajuda | Importante |
| `google_business_policies` | Google Business Profile | Políticas e diretrizes | Crítica |
| `google_business_representation` | Google Business Profile | Representação da empresa | Crítica |
| `google_business_edit_profile` | Google Business Profile | Operação e informações editáveis | Crítica |
| `google_business_reviews` | Google Business Profile | Avaliações e denúncias | Crítica |

A URL do YouTube é mantida em forma canônica, sem parâmetros de sessão ou visita. O mesmo princípio deve ser aplicado a qualquer nova fonte adicionada ao vigia.

## Dados guardados

O SQLite contém o cadastro das fontes, cada snapshot coletado, hash SHA-256 do conteúdo normalizado e alterações detectadas. O conteúdo normalizado remove scripts, estilos, SVGs, espaços redundantes e navegação irrelevante quando possível. O relatório Markdown contém a execução, as fontes inicializadas, alterações, severidade, resumo, diff limitado e erros de coleta.

A estrutura foi escolhida para permitir auditoria sem depender do estado atual da página. O hash serve para detectar mudanças; o diff serve para permitir a revisão humana. O vigia não interpreta a mudança como uma decisão jurídica ou como autorização para publicar.

## Severidade

| Severidade | Uso |
|---|---|
| `critical` | Alterações em saúde, privacidade, dados pessoais, direitos autorais, monetização, restrições, avaliações, endereço, telefone, horário, categoria ou descrição do negócio. |
| `important` | Alterações de operação, ajuda, formatos, requisitos de anúncios ou recursos de plataforma. |
| `informative` | Mudanças textuais sem indicador prioritário; ainda ficam no histórico. |

A severidade é uma triagem inicial, não uma conclusão jurídica. Toda mudança deve ser lida por uma pessoa responsável antes de ser incorporada às regras da skill de marketing.

## Execução

A verificação manual é feita por:

```bash
PYTHONPATH=. python3 -m alento_soft_ia.policy_watch
```

O mesmo comando pode ser executado semanalmente pelo agendador do computador do hospital. O sistema não exige login para ler as fontes públicas, mas alguns conteúdos podem variar por idioma, sessão ou renderização dinâmica; falhas são registadas como erros de coleta.

## Notificações

O e-mail usa SMTP e recebe o relatório Markdown completo. O WhatsApp usa a WhatsApp Cloud API oficial e deve enviar somente um resumo curto para um número interno, utilizando template aprovado quando a janela de atendimento não estiver aberta. O destinatário deve ser o responsável pelo marketing/IT, nunca uma lista de pacientes ou famílias.

A notificação é opcional e executada somente quando o operador passa explicitamente `--send-email` ou `--send-whatsapp`. Credenciais são lidas de variáveis de ambiente e não entram no SQLite, no Markdown, nos testes ou no repositório.

## Limites de segurança

O vigia é somente leitura. Ele não deve usar credenciais do Google Business Profile, Meta Business Suite, LinkedIn ou YouTube para modificar contas. Não deve recolher avaliações ou mensagens privadas como fonte para o LLM. Não deve incluir nomes de pacientes, prontuários, diagnósticos, transcrições, telefones pessoais ou dados clínicos nos relatórios.

Uma alteração pode gerar uma tarefa de revisão para a skill de marketing, mas a tarefa continuará submetida às políticas do domínio, à validação de conteúdo e à aprovação humana. Uma mudança de plataforma nunca autoriza automaticamente promessa de cura, diagnóstico, prescrição, exposição de caso ou publicação.

## Fontes oficiais consultadas

1. [Meta Business Help Center](https://www.facebook.com/business/help/)
2. [Meta Advertising Standards](https://transparency.meta.com/policies/ad-standards/)
3. [LinkedIn — Updates to User Agreement and Privacy Policy](https://www.linkedin.com/help/linkedin/answer/a1341216/updates-to-user-agreement-and-privacy-policy)
4. [YouTube — Channel monetization policies](https://support.google.com/youtube/answer/1311392?hl=pt-BR)
5. [Google Business Profile — All policies and guidelines](https://support.google.com/business/answer/7667250?hl=pt-BR)
6. [Google Business Profile — Guidelines for representing your business](https://support.google.com/business/answer/3038177?hl=pt-BR)
7. [Google Business Profile — Edit your Business Profile](https://support.google.com/business/answer/3039617?hl=pt-BR)
8. [Google Business Profile — Report inappropriate reviews](https://support.google.com/business/answer/4596773?hl=pt-BR)
9. [Meta — WhatsApp Cloud API Get Started](https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started)
10. [Meta — WhatsApp Service messages](https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages)
11. [Meta — WhatsApp Template fundamentals](https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/overview)
