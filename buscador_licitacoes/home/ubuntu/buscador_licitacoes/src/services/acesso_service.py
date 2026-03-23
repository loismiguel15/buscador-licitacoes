from datetime import datetime
from src.models import Cliente, AssinaturaStatus

def cliente_tem_acesso(cliente_id):
    cliente = Cliente.query.get(cliente_id)

    if not cliente:
        return False

    assinatura = cliente.assinatura
    if not assinatura:
        return False

    # Assinatura paga
    if assinatura.status == AssinaturaStatus.ACTIVE:
        return True

    # Trial ativo
    if (
        assinatura.provider_status == "trial"
        and assinatura.trial_ends_at
        and datetime.utcnow() <= assinatura.trial_ends_at
    ):
        return True

    return False