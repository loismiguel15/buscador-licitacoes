from datetime import datetime, timedelta
from src.models import (
    db, Cliente, Usuario, ClientePreferencias,
    Assinatura, AssinaturaStatus, EmailLog, Licitacao
)
from src.services.email_service import enviar_email

def _split_csv(s: str):
    return [x.strip() for x in (s or "").split(",") if x.strip()]

def _render_html(cliente: Cliente, licitacoes: list):
    itens = []
    for l in licitacoes:
        titulo = (l.objeto or "").strip()
        orgao = (l.orgao_licitante or "").strip()
        uf = (l.localidade_uf or "").strip()
        modalidade = (l.modalidade or "").strip()
        link = (l.link_fonte or "").strip()

        itens.append(
            f"<li>"
            f"<b>{titulo}</b><br>"
            f"{orgao} — {modalidade} — {uf}<br>"
            f"<a href='{link}'>Abrir no PNCP</a>"
            f"</li><br>"
        )

    return f"""
    <div style="font-family: Arial, sans-serif;">
      <h2>Resumo diário - {cliente.nome_empresa}</h2>
      <p>Encontramos <b>{len(licitacoes)}</b> licitações novas nas últimas 24h, conforme suas preferências.</p>
      <hr>
      <ul>
        {''.join(itens)}
      </ul>
      <hr>
      <p style="font-size: 12px; color: #777;">
        Você recebeu este e-mail porque sua conta está com assinatura ativa.
      </p>
    </div>
    """

def run():
    agora = datetime.utcnow()
    inicio = agora - timedelta(hours=24)

    clientes = Cliente.query.filter_by(ativo=True).all()

    for c in clientes:
        ass = Assinatura.query.filter_by(cliente_id=c.id).first()
        if not ass or ass.status != AssinaturaStatus.ACTIVE:
            continue

        pref = ClientePreferencias.query.filter_by(cliente_id=c.id, ativo=True).first()
        if not pref:
            continue

        keywords = [k.lower() for k in _split_csv(pref.keywords)]
        ufs = [u.upper() for u in _split_csv(pref.uf)]
        modalidades = _split_csv(pref.modalidade)

        q = Licitacao.query.filter(Licitacao.data_publicacao >= inicio)

        if ufs:
            q = q.filter(Licitacao.localidade_uf.in_(ufs))
        if modalidades:
            q = q.filter(Licitacao.modalidade.in_(modalidades))

        licitacoes = q.order_by(Licitacao.data_publicacao.desc().nullslast(), Licitacao.id.desc()).limit(200).all()

        # filtro por keywords (em objeto + orgao + numero_processo)
        if keywords:
            filtradas = []
            for l in licitacoes:
                texto = f"{l.objeto or ''} {l.orgao_licitante or ''} {l.numero_processo or ''}".lower()
                if any(k in texto for k in keywords):
                    filtradas.append(l)
            licitacoes = filtradas

        if not licitacoes:
            continue

        usuarios = Usuario.query.filter_by(cliente_id=c.id, ativo=True).all()
        assunto = f"Licitações novas (últimas 24h) - {c.nome_empresa}"
        html = _render_html(c, licitacoes)

        for u in usuarios:
            if not u.email:
                continue

            try:
                enviar_email(u.email, assunto, html)
                log = EmailLog(
                    cliente_id=c.id,
                    destinatario=u.email,
                    assunto=assunto,
                    qtd_resultados=len(licitacoes),
                    status="ok",
                    erro=None
                )
            except Exception as e:
                log = EmailLog(
                    cliente_id=c.id,
                    destinatario=u.email,
                    assunto=assunto,
                    qtd_resultados=len(licitacoes),
                    status="erro",
                    erro=str(e)
                )

            db.session.add(log)

        db.session.commit()