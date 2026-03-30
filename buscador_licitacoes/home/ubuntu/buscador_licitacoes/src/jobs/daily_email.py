from datetime import datetime, timedelta
from src.models import (
    db, Cliente, Usuario, ClientePreferencias,
    Assinatura, AssinaturaStatus, EmailLog, Licitacao
)
from src.services.email_service import enviar_email, montar_email_licitacoes

def _split_csv(s: str):
    return [x.strip() for x in (s or "").split(",") if x.strip()]

def assinatura_permite_envio(ass):
    if not ass:
        return False

    agora = datetime.utcnow()

    # Assinatura paga ativa
    if ass.status == AssinaturaStatus.ACTIVE:
        return True

    # Trial grátis ainda válido
    if ass.trial_ends_at and agora <= ass.trial_ends_at:
        return True

    return False

def run():
    agora = datetime.utcnow().date()
    inicio = agora - timedelta(days=1)

    clientes = Cliente.query.filter_by(ativo=True).all()

    for c in clientes:
        ass = Assinatura.query.filter_by(cliente_id=c.id).first()
        if not assinatura_permite_envio(ass):
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

        licitacoes = q.order_by(Licitacao.data_publicacao.desc(), Licitacao.id.desc()).limit(200).all()

        if keywords:
            filtradas = []
            for l in licitacoes:
                texto_busca = f"{l.objeto or ''} {l.orgao_licitante or ''} {l.numero_processo or ''}".lower()
                if any(k in texto_busca for k in keywords):
                    filtradas.append(l)
            licitacoes = filtradas

        if not licitacoes:
            continue

        usuarios = Usuario.query.filter_by(cliente_id=c.id, ativo=True).all()
        assunto = f"Licitações novas (últimas 24h) - {c.nome_empresa}"
        html, texto = montar_email_licitacoes(
            nome_empresa=c.nome_empresa,
            lista_licitacoes=licitacoes[:5],
            total_encontrado=len(licitacoes)
        )

        for u in usuarios:
            if not u.email:
                continue

            try:
                enviar_email(u.email, assunto, html, texto)
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