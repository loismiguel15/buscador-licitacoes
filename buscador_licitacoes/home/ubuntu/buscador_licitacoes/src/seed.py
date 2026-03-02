from datetime import date, datetime
from src.main import app
from src.models import db, Licitacao

with app.app_context():
    cols = [c.name for c in Licitacao.__table__.columns]
    print("Colunas em Licitacao:", cols)

    exemplos = [
        Licitacao(
            numero_processo="001/2026",
            identificador_unico_pncp="TESTE-001",
            orgao_licitante="Prefeitura de Exemplo",
            modalidade="Pregão",
            objeto="Aquisição de materiais de informática",
            data_publicacao=date.today(),
            data_abertura_propostas=None,
            localidade_uf="SP",
            localidade_municipio="Osasco",
            fonte_dados="TESTE",
            link_fonte="https://exemplo.com/edital1",
            texto_integral_aviso="Aviso de licitação (teste).",
            valor_estimado=15000.00,
            situacao="Aberta",
            data_coleta=datetime.now(),
            data_ultima_atualizacao=datetime.now(),
        ),
        Licitacao(
            numero_processo="002/2026",
            identificador_unico_pncp="TESTE-002",
            orgao_licitante="Secretaria de Saúde",
            modalidade="Concorrência",
            objeto="Contratação de serviços de limpeza",
            data_publicacao=date.today(),
            data_abertura_propostas=None,
            localidade_uf="SP",
            localidade_municipio="São Paulo",
            fonte_dados="TESTE",
            link_fonte="https://exemplo.com/edital2",
            texto_integral_aviso="Aviso de licitação (teste).",
            valor_estimado=98000.00,
            situacao="Aberta",
            data_coleta=datetime.now(),
            data_ultima_atualizacao=datetime.now(),
        ),
        Licitacao(
            numero_processo="003/2026",
            identificador_unico_pncp="TESTE-003",
            orgao_licitante="Universidade X",
            modalidade="Dispensa",
            objeto="Manutenção de ar-condicionado e climatização",
            data_publicacao=date.today(),
            data_abertura_propostas=None,
            localidade_uf="MG",
            localidade_municipio="Itajubá",
            fonte_dados="TESTE",
            link_fonte="https://exemplo.com/edital3",
            texto_integral_aviso="Aviso de licitação (teste).",
            valor_estimado=32000.00,
            situacao="Aberta",
            data_coleta=datetime.now(),
            data_ultima_atualizacao=datetime.now(),
        ),
    ]

    # (opcional) limpar antes:
    # db.session.query(Licitacao).delete()

    db.session.add_all(exemplos)
    db.session.commit()
    print("OK: licitações de teste inseridas!")