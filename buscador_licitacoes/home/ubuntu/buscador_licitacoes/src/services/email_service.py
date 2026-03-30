import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", "").strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "1") == "1"
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "0") == "1"

AREA_CLIENTE_URL = os.getenv(
    "AREA_CLIENTE_URL",
    "https://buscador-licitacoes.onrender.com/licitacoes_encontradas"
).strip()

EMAIL_LOGO_URL = os.getenv(
    "EMAIL_LOGO_URL",
    "https://buscador-licitacoes.onrender.com/static/img/logo1.png"
).strip()

def enviar_email(destinatario: str, assunto: str, html: str, texto: str | None = None):
    if not SMTP_HOST:
        raise RuntimeError("SMTP_HOST não configurado")

    if not SMTP_FROM:
        raise RuntimeError("SMTP_FROM não configurado")

    if not destinatario:
        raise RuntimeError("Destinatário não informado")

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_FROM
    msg["To"] = destinatario
    msg["Subject"] = assunto

    if texto:
        msg.attach(MIMEText(texto, "plain", "utf-8"))

    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.ehlo()

                if SMTP_USER and SMTP_PASS:
                    server.login(SMTP_USER, SMTP_PASS)

                server.sendmail(SMTP_FROM, [destinatario], msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.ehlo()

                if SMTP_USE_TLS:
                    server.starttls()
                    server.ehlo()

                if SMTP_USER and SMTP_PASS:
                    server.login(SMTP_USER, SMTP_PASS)

                server.sendmail(SMTP_FROM, [destinatario], msg.as_string())

    except Exception as e:
        raise RuntimeError(
            f"Erro ao enviar email via SMTP "
            f"(host={SMTP_HOST}, porta={SMTP_PORT}, ssl={SMTP_USE_SSL}, tls={SMTP_USE_TLS}): {e}"
        )


def _render_logo_html():
    if EMAIL_LOGO_URL:
        return f"""
        <img
            src="{EMAIL_LOGO_URL}"
            alt="Buscador de Licitações"
            style="
                height:48px;
                width:auto;
                display:block;
                border-radius:10px;
                background:#ffffff;
                padding:4px;
            "
        >
        """

    return """
    <div style="
        width:44px;
        height:44px;
        border-radius:12px;
        background:linear-gradient(135deg, #2b6cb0, #4f8fe8);
        display:flex;
        align-items:center;
        justify-content:center;
        font-weight:800;
        font-size:18px;
        color:#ffffff;
        box-shadow:0 10px 20px rgba(0,0,0,0.15);
    ">
        BL
    </div>
    """


def _email_base_template(titulo: str, conteudo_html: str):
    logo_html = _render_logo_html()

    return f"""
    <html>
    <body style="
        margin:0;
        padding:0;
        background:#f4f7fb;
        font-family:Arial, Helvetica, sans-serif;
        color:#142033;
    ">
        <div style="width:100%;background:#f4f7fb;padding:32px 12px;">
            <div style="
                max-width:720px;
                margin:0 auto;
                background:#ffffff;
                border:1px solid #d8e2f0;
                border-radius:20px;
                overflow:hidden;
                box-shadow:0 14px 40px rgba(11, 44, 95, 0.10);
            ">
                <div style="
                    background:linear-gradient(135deg, #0b2c5f, #163d7a);
                    padding:24px 28px;
                    color:#ffffff;
                ">
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="width:100%;">
                        <tr>
                            <td style="vertical-align:middle;width:64px;">
                                {logo_html}
                            </td>
                            <td style="vertical-align:middle;padding-left:12px;">
                                <div style="font-size:20px;font-weight:800;line-height:1.1;">
                                    Buscador de Licitações
                                </div>
                                <div style="font-size:13px;color:#dbe8ff;margin-top:4px;">
                                    Encontre oportunidades com mais rapidez
                                </div>
                            </td>
                        </tr>
                    </table>

                    <div style="margin-top:18px;font-size:24px;font-weight:800;line-height:1.2;">
                        {titulo}
                    </div>
                </div>

                <div style="padding:28px;">
                    {conteudo_html}
                </div>

                <div style="
                    padding:18px 28px;
                    border-top:1px solid #e7edf7;
                    background:#f8fbff;
                    font-size:13px;
                    color:#5b6575;
                ">
                    <div style="margin-bottom:6px;">
                        Este e-mail foi enviado automaticamente pelo sistema <b>Buscador de Licitações</b>.
                    </div>
                    <div>
                        Caso tenha dúvidas, acesse sua área do cliente.
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


def montar_email_licitacoes(
    nome_empresa,
    lista_licitacoes,
    total_encontrado=None,
    area_cliente_url=None
):
    if area_cliente_url is None:
        area_cliente_url = AREA_CLIENTE_URL

    itens_html = ""
    itens_texto = []

    for lic in lista_licitacoes:
        data_pub = lic.data_publicacao.strftime("%d/%m/%Y") if lic.data_publicacao else "Não informada"

        if lic.link_fonte:
            link_html = f"""
            <div style="margin-top:14px;">
                <a href="{lic.link_fonte}" target="_blank"
                   style="
                        display:inline-block;
                        padding:10px 16px;
                        background:#eef4ff;
                        color:#0b2c5f !important;
                        text-decoration:none;
                        border-radius:10px;
                        font-weight:700;
                        border:1px solid #d6e6ff;
                        font-size:14px;
                   ">
                    Ver licitação
                </a>
            </div>
            """
            link_texto = f"Link: {lic.link_fonte}\n"
        else:
            link_html = """
            <div style="margin-top:12px;color:#6b7280;font-size:13px;">
                Link da licitação não informado na origem.
            </div>
            """
            link_texto = "Link: não informado\n"

        itens_html += f"""
        <div style="
            margin-bottom:18px;
            padding:18px;
            border:1px solid #d8e2f0;
            border-radius:16px;
            background:#fbfdff;
        ">
            <div style="margin-bottom:10px;font-size:16px;font-weight:700;color:#0b2c5f;line-height:1.5;">
                {lic.objeto or 'Não informado'}
            </div>

            <div style="font-size:14px;color:#142033;line-height:1.7;">
                <div><b>Órgão:</b> {lic.orgao_licitante or 'Não informado'}</div>
                <div><b>UF:</b> {lic.localidade_uf or 'Não informada'}</div>
                <div><b>Município:</b> {lic.localidade_municipio or 'Não informado'}</div>
                <div><b>Modalidade:</b> {lic.modalidade or 'Não informada'}</div>
                <div><b>Data de publicação:</b> {data_pub}</div>
            </div>

            {link_html}
        </div>
        """

        itens_texto.append(
            f"Objeto: {lic.objeto or 'Não informado'}\n"
            f"Órgão: {lic.orgao_licitante or 'Não informado'}\n"
            f"UF: {lic.localidade_uf or 'Não informada'}\n"
            f"Município: {lic.localidade_municipio or 'Não informado'}\n"
            f"Modalidade: {lic.modalidade or 'Não informada'}\n"
            f"Data publicação: {data_pub}\n"
            f"{link_texto}"
        )

    total = total_encontrado if total_encontrado is not None else len(lista_licitacoes)
    exibidos = len(lista_licitacoes)

    conteudo_html = f"""
    <div style="
        background:#f8fbff;
        border:1px solid #d8e2f0;
        border-radius:16px;
        padding:16px 18px;
        margin-bottom:22px;
    ">
        <div style="font-size:14px;color:#5b6575;margin-bottom:6px;">Resumo do monitoramento</div>
        <div style="font-size:16px;color:#142033;line-height:1.8;">
            <div><b>Total de licitações encontradas:</b> {total}</div>
            <div><b>Mostrando neste e-mail:</b> {exibidos}</div>
        </div>
    </div>

    <p style="margin:0 0 14px 0;font-size:15px;line-height:1.7;color:#142033;">
        Olá <b>{nome_empresa}</b>,
    </p>

    <p style="margin:0 0 22px 0;font-size:15px;line-height:1.7;color:#5b6575;">
        Encontramos <b>{total}</b> novas licitações que podem interessar à sua empresa.
        Abaixo estão <b>{exibidos}</b> destaques selecionados.
    </p>

    {itens_html}

    <div style="
        margin-top:26px;
        padding:20px;
        border-radius:16px;
        background:linear-gradient(135deg, #f4f7fb, #eef4ff);
        border:1px solid #d8e2f0;
    ">
        <p style="margin:0 0 14px 0;font-size:15px;line-height:1.7;color:#142033;">
            Para visualizar todas as licitações encontradas, acesse sua área do cliente:
        </p>

        <a href="{area_cliente_url}" target="_blank"
           style="
                display:inline-block;
                padding:12px 18px;
                background:linear-gradient(135deg, #0b2c5f, #163d7a);
                color:#ffffff !important;
                text-decoration:none;
                border-radius:12px;
                font-weight:700;
                font-size:14px;
           ">
            Ver todas as licitações
        </a>
    </div>
    """

    html = _email_base_template("Novas licitações encontradas", conteudo_html)

    texto = (
        f"Novas licitações encontradas\n\n"
        f"Olá {nome_empresa},\n\n"
        f"Encontramos {total} novas licitações que podem interessar à sua empresa.\n"
        f"Mostrando neste email: {exibidos}\n\n"
        + "\n----------------------\n".join(itens_texto)
        + f"\n\nPara ver todas as licitações, acesse sua área do cliente:\n{area_cliente_url}\n"
        + "\nBuscador de Licitações\n"
    )

    return html, texto


def enviar_email_teste(destinatario: str):
    assunto = "Teste de envio de email"

    conteudo_html = f"""
    <p style="margin:0 0 14px 0;font-size:15px;line-height:1.7;color:#142033;">
        Este é um e-mail de teste do seu sistema.
    </p>

    <p style="margin:0 0 22px 0;font-size:15px;line-height:1.7;color:#5b6575;">
        Se você recebeu esta mensagem, o SMTP do <b>Buscador de Licitações</b> está funcionando corretamente.
    </p>

    <div style="
        margin-top:18px;
        padding:20px;
        border-radius:16px;
        background:linear-gradient(135deg, #f4f7fb, #eef4ff);
        border:1px solid #d8e2f0;
    ">
        <a href="{AREA_CLIENTE_URL}" target="_blank"
           style="
                display:inline-block;
                padding:12px 18px;
                background:linear-gradient(135deg, #0b2c5f, #163d7a);
                color:#ffffff !important;
                text-decoration:none;
                border-radius:12px;
                font-weight:700;
                font-size:14px;
           ">
            Ir para a área do cliente
        </a>
    </div>
    """

    html = _email_base_template("Teste de envio de e-mail", conteudo_html)

    texto = (
        "Teste de email\n\n"
        "Se você recebeu esta mensagem, o SMTP do sistema está funcionando.\n\n"
        f"Área do cliente: {AREA_CLIENTE_URL}"
    )

    enviar_email(destinatario, assunto, html, texto)


def enviar_codigo_recuperacao_senha(destinatario: str, nome_usuario: str, codigo: str):
    assunto = "Recuperação de senha - Buscador de Licitações"

    conteudo_html = f"""
    <p style="margin:0 0 14px 0;font-size:15px;line-height:1.7;color:#142033;">
        Olá <b>{nome_usuario}</b>,
    </p>

    <p style="margin:0 0 18px 0;font-size:15px;line-height:1.7;color:#5b6575;">
        Recebemos uma solicitação para redefinir a senha da sua conta.
    </p>

    <p style="margin:0 0 10px 0;font-size:15px;line-height:1.7;color:#142033;">
        Use o código abaixo para continuar:
    </p>

    <div style="
        margin:20px 0;
        padding:22px;
        background:#f8fbff;
        border:1px solid #d8e2f0;
        border-radius:16px;
        text-align:center;
    ">
        <span style="
            font-size:34px;
            font-weight:800;
            letter-spacing:8px;
            color:#0b2c5f;
        ">{codigo}</span>
    </div>

    <div style="
        margin-top:18px;
        padding:16px 18px;
        border-radius:14px;
        background:#eef4ff;
        border:1px solid #d6e6ff;
        color:#142033;
        font-size:14px;
        line-height:1.7;
    ">
        Este código expira em <b>10 minutos</b>.
    </div>

    <p style="margin:20px 0 0 0;color:#5b6575;font-size:14px;line-height:1.7;">
        Se você não solicitou a troca de senha, ignore este e-mail.
    </p>
    """

    html = _email_base_template("Recuperação de senha", conteudo_html)

    texto = (
        f"Recuperação de senha\n\n"
        f"Olá {nome_usuario},\n\n"
        f"Recebemos uma solicitação para redefinir a senha da sua conta.\n"
        f"Use este código para continuar: {codigo}\n\n"
        f"Este código expira em 10 minutos.\n\n"
        f"Se você não solicitou a troca de senha, ignore este e-mail.\n"
    )

    enviar_email(destinatario, assunto, html, texto)