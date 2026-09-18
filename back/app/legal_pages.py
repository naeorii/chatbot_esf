from html import escape


UNIT_NAME = "ESF São Carlos/Urlândia"
UNIT_PHONE = "(55) 3174-1588"
LAST_UPDATED = "18 de setembro de 2026"


def privacy_policy_html() -> str:
    return page(
        "Política de Privacidade",
        """
        <p>Esta política explica como o assistente de WhatsApp da ESF São Carlos/Urlândia
        trata os dados enviados durante o atendimento.</p>

        <h2>Dados utilizados</h2>
        <p>O serviço pode tratar o número e o identificador do WhatsApp, o conteúdo da
        conversa e, quando o usuário solicita um agendamento, nome do paciente, documento
        de identificação, serviço, data e horário escolhidos. O documento é armazenado de
        forma mascarada, mantendo apenas os últimos caracteres necessários à conferência.</p>

        <h2>Finalidades</h2>
        <p>Os dados são usados exclusivamente para responder dúvidas sobre a unidade,
        conduzir e administrar agendamentos, evitar reservas duplicadas e manter a
        continuidade da conversa.</p>

        <h2>Compartilhamento e armazenamento</h2>
        <p>O serviço usa a Plataforma do WhatsApp Business da Meta e a infraestrutura
        contratada para hospedar o sistema. A unidade não vende dados pessoais. O acesso
        ao painel de agendamentos é restrito à equipe autorizada.</p>

        <h2>Direitos do titular</h2>
        <p>O usuário pode solicitar informação, correção ou exclusão de seus dados. Para
        proteger o paciente, pedidos relacionados a agendamentos podem exigir confirmação
        de identidade pela equipe da unidade.</p>

        <h2>Contato</h2>
        <p>Para dúvidas ou solicitações sobre dados pessoais, entre em contato com a
        unidade pelo telefone <strong>(55) 3174-1588</strong>.</p>
        """,
    )


def data_deletion_html() -> str:
    return page(
        "Exclusão de dados",
        """
        <p>Para solicitar a exclusão de dados associados ao atendimento pelo WhatsApp,
        entre em contato com a ESF São Carlos/Urlândia pelo telefone
        <strong>(55) 3174-1588</strong>.</p>

        <h2>Como solicitar</h2>
        <ol>
          <li>Informe que deseja excluir os dados do atendimento do chatbot.</li>
          <li>Forneça apenas os dados mínimos solicitados pela equipe para confirmar a identidade.</li>
          <li>A equipe localizará o registro e informará a conclusão ou eventual obrigação de retenção.</li>
        </ol>

        <p>Dados que precisem ser mantidos por obrigação legal, regulatória ou para a
        segurança da assistência poderão ser preservados pelo prazo aplicável. Os demais
        dados serão excluídos após a validação do pedido.</p>
        """,
    )


def terms_html() -> str:
    return page(
        "Termos de Uso",
        """
        <p>O assistente da ESF São Carlos/Urlândia oferece informações gerais sobre a
        unidade e auxilia no agendamento dos serviços disponibilizados no menu.</p>

        <h2>Limites do atendimento</h2>
        <p>O chatbot não realiza diagnóstico, não substitui avaliação de profissional de
        saúde e não deve ser usado para emergências. Em situação de urgência ou emergência,
        ligue para o SAMU pelo número <strong>192</strong>.</p>

        <h2>Agendamentos</h2>
        <p>O usuário deve fornecer informações corretas e revisar os dados antes de
        confirmar. A unidade poderá entrar em contato ou ajustar o atendimento quando
        necessário por razões assistenciais ou operacionais.</p>

        <h2>Uso adequado</h2>
        <p>Não envie informações de terceiros sem autorização e não utilize o serviço para
        conteúdo ilegal, abusivo ou que comprometa a disponibilidade do sistema.</p>

        <h2>Contato</h2>
        <p>Dúvidas podem ser encaminhadas à unidade pelo telefone
        <strong>(55) 3174-1588</strong>.</p>
        """,
    )


def page(title: str, content: str) -> str:
    safe_title = escape(title)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title} | {UNIT_NAME}</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, system-ui, sans-serif; color: #173a34; background: #f4f8f6; }}
    body {{ margin: 0; }}
    main {{ max-width: 760px; margin: 0 auto; padding: 48px 24px 72px; }}
    article {{ background: #fff; border: 1px solid #dce9e4; border-radius: 18px; padding: 36px; box-shadow: 0 16px 45px rgba(20, 64, 55, .08); }}
    h1 {{ margin-top: 0; color: #0b6b57; font-size: clamp(2rem, 5vw, 3rem); }}
    h2 {{ margin-top: 2rem; font-size: 1.2rem; }}
    p, li {{ line-height: 1.7; }}
    footer {{ margin-top: 2rem; color: #5d716c; font-size: .9rem; }}
    a {{ color: #0b6b57; }}
  </style>
</head>
<body>
  <main>
    <article>
      <p><strong>{UNIT_NAME}</strong></p>
      <h1>{safe_title}</h1>
      {content}
      <footer>Última atualização: {LAST_UPDATED} · Contato: {UNIT_PHONE}</footer>
    </article>
  </main>
</body>
</html>"""
