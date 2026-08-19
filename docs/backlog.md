# Backlog do AlentoSoft-IA

## Prioridade ativa

**Fluxo de marketing semanal do Granjimmy.** O objetivo imediato é gerar conteúdo multicanal com fonte autorizada, validação de segurança, revisão linguística, pré-visualização e aprovação humana, sem publicação automática.

## Pendência bloqueada

### Notificação por e-mail do vigia

- **Estado:** aguardando resposta do provedor de e-mail.
- **Último erro:** `TLSV1_UNRECOGNIZED_NAME` ao conectar a `smtp.granjimmy.com.br:465` com SSL implícito.
- **Evidência:** o servidor apresentou certificado `*.f1.ultramail.com.br`, incompatível com os hostnames documentados `mbox.granjimmy.com.br` e `smtp.granjimmy.com.br`.
- **Configuração informada pelo provedor:** usuário `naoresponda=granjimmy.com.br`, SMTP `smtp.granjimmy.com.br`, porta `465`, SSL/TLS e autenticação.
- **Chamado:** aberto junto ao provedor para corrigir o certificado ou informar os hostnames canônicos.
- **Retomar quando:** o provedor fornecer um hostname que corresponda ao certificado, ou corrigir o certificado para incluir os hostnames utilizados.
- **Regra de segurança:** não aceitar exceção permanente e não desativar a validação TLS.

## Próximas frentes

1. Definir o objetivo e o calendário da primeira semana de conteúdo.
2. Gerar as peças com `--preview` usando o roteamento híbrido.
3. Revisar texto, fonte, qualidade linguística e adequação a cada canal.
4. Organizar o conteúdo aprovado numa campanha semanal reutilizável.
5. Repetir o teste SMTP quando o provedor responder.

## Ideias guardadas

- Editor visual de layouts em SVG/HTML, com Inkscape e GIMP como ferramentas de revisão.
- Integração de notificações por WhatsApp Cloud API para destinatário interno.
- Módulo clínico local: áudio, transcrição, resumo, rascunho de evolução e aprovação médica.
- RBAC e autenticação antes de qualquer uso de dados clínicos reais.
- Biblioteca de templates de marca para Instagram, WhatsApp, LinkedIn, blog e anúncios.
