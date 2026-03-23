from flask import Blueprint, request, jsonify
from datetime import date, timedelta

from src.models import db, EmailLog
from src.services.pncp_client import fetch_contratacoes_publicacao
from src.services.monitoramento_service import processar_monitoramento
from src.services.email_service import enviar_email

pncp_debug_bp = Blueprint("pncp_debug", __name__)


@pncp_debug_bp.route("/raw", methods=["GET"])
def raw_pncp():
    try:
        dias = int(request.args.get("dias", 3))
        limite = int(request.args.get("limite", 10))
        codigo_modalidade = int(request.args.get("modalidade", 6))

        limite = max(1, min(limite, 100))

        hoje = date.today()
        ini = (hoje - timedelta(days=dias)).strftime("%Y%m%d")
        fim = hoje.strftime("%Y%m%d")

        data = fetch_contratacoes_publicacao(
            data_inicial=ini,
            data_final=fim,
            codigo_modalidade=codigo_modalidade,
            pagina=1,
            tamanho=limite,
        )

        itens = data.get("data", []) or []

        return jsonify({
            "periodo": {
                "dataInicial": ini,
                "dataFinal": fim,
            },
            "total_recebidos": len(itens),
            "primeiro_item": itens[0] if itens else None
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pncp_debug_bp.route("/monitorar", methods=["GET"])
def debug_monitoramento():
    try:
        resultado = processar_monitoramento()

        return jsonify({
            "message": "Monitoramento executado",
            "resultado": resultado
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": str(e)
        }), 500


@pncp_debug_bp.route("/email-logs", methods=["GET"])
def email_logs():
    try:
        logs = EmailLog.query.order_by(EmailLog.id.desc()).limit(20).all()

        return jsonify([
            {
                "id": log.id,
                "cliente_id": log.cliente_id,
                "destinatario": log.destinatario,
                "assunto": log.assunto,
                "enviado_em": log.enviado_em.isoformat() if log.enviado_em else None,
                "qtd_resultados": log.qtd_resultados,
                "status": log.status,
                "erro": log.erro,
            }
            for log in logs
        ]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pncp_debug_bp.route("/email-teste", methods=["GET"])
def email_teste():
    try:
        destinatario = request.args.get("email", "lois.miguelluma@gmail.com").strip()

        html = """
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Email de teste</h2>
            <p>Seu sistema está enviando emails corretamente.</p>
        </body>
        </html>
        """

        texto = "Email de teste\n\nSeu sistema está enviando emails corretamente."

        enviar_email(
            destinatario,
            "Teste do Buscador de Licitações",
            html,
            texto
        )

        return jsonify({
            "message": "Email enviado com sucesso",
            "destinatario": destinatario
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500