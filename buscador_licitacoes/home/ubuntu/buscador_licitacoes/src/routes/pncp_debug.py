from flask import Blueprint, request, jsonify
from datetime import date, timedelta
import traceback

from src.models import db, EmailLog
from src.services.pncp_client import fetch_contratacoes_publicacao
from src.services.monitoramento_service import processar_monitoramento
from src.services.email_service import enviar_email

pncp_debug_bp = Blueprint("pncp_debug", __name__)


# =========================================
# 🔍 TESTE BRUTO PNCP (LEVE)
# =========================================
@pncp_debug_bp.route("/raw", methods=["GET"])
def raw_pncp():
    try:
        dias = int(request.args.get("dias", 1))
        limite = int(request.args.get("limite", 5))
        codigo_modalidade = int(request.args.get("modalidade", 6))

        limite = max(1, min(limite, 20))

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
            "amostra": itens[:3]
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# =========================================
# ⚡ MONITORAMENTO MANUAL (CONTROLADO)
# =========================================
@pncp_debug_bp.route("/monitorar", methods=["GET"])
def debug_monitoramento():
    try:
        force = request.args.get("force", "0")
        modo = request.args.get("modo", "leve").strip().lower()

        if force != "1":
            return jsonify({
                "error": "Use ?force=1 para executar monitoramento"
            }), 400

        resultado = processar_monitoramento(
            modo_leve=(modo != "completo")
        )

        return jsonify({
            "message": "Monitoramento executado",
            "resultado": resultado
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# =========================================
# 📧 LOGS DE EMAIL (LIMITADO)
# =========================================
@pncp_debug_bp.route("/email-logs", methods=["GET"])
def email_logs():
    try:
        limite = int(request.args.get("limite", 10))
        limite = max(1, min(limite, 50))

        logs = EmailLog.query.order_by(EmailLog.id.desc()).limit(limite).all()

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
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# =========================================
# ✉️ TESTE DE EMAIL
# =========================================
@pncp_debug_bp.route("/email-teste", methods=["GET"])
def email_teste():
    try:
        destinatario = request.args.get(
            "email",
            "lois.miguelluma@gmail.com"
        ).strip()

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
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
