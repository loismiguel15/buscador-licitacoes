from flask_sqlalchemy import SQLAlchemy
from enum import Enum as PyEnum
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ==============================
# CLIENTE
# ==============================

class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nome_empresa = db.Column(db.String(255), nullable=False)
    cnpj = db.Column(db.String(18), unique=True)
    email_contato = db.Column(db.String(255), nullable=False)
    telefone_contato = db.Column(db.String(20))

    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    usuarios = db.relationship(
        "Usuario",
        backref="cliente",
        lazy=True,
        cascade="all, delete-orphan",
    )

    preferencias = db.relationship(
        "ClientePreferencias",
        backref="cliente",
        uselist=False,
        cascade="all, delete-orphan",
    )

    assinatura = db.relationship(
        "Assinatura",
        backref="cliente",
        uselist=False,
        cascade="all, delete-orphan",
    )

    licitacoes_cliente = db.relationship(
        "LicitacaoCliente",
        backref="cliente",
        lazy=True,
        cascade="all, delete-orphan",
    )

    historicos_busca = db.relationship(
        "HistoricoBusca",
        backref="cliente",
        lazy=True,
        cascade="all, delete-orphan",
    )


# ==============================
# USUÁRIO
# ==============================

class TipoUsuario(PyEnum):
    MASTER = "master"
    COMUM = "comum"


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)

    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    nome_completo = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)

    senha_hash = db.Column(db.String(255), nullable=False)

    tipo = db.Column(
        db.Enum(TipoUsuario, native_enum=False),
        nullable=False,
        default=TipoUsuario.COMUM,
    )

    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ultimo_login = db.Column(db.DateTime, nullable=True)
    ultimo_ip = db.Column(db.String(100), nullable=True)
    ultimo_user_agent = db.Column(db.String(255), nullable=True)
    sessao_expira_em = db.Column(db.DateTime, nullable=True)
    session_token = db.Column(db.String(64), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    reset_code = db.Column(db.String(10), nullable=True)
    reset_code_expires_at = db.Column(db.DateTime, nullable=True)
    reset_code_used = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password: str):
        self.senha_hash = generate_password_hash(
            password, method="pbkdf2:sha256", salt_length=16
        )

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.senha_hash, password)


# ==============================
# PREFERÊNCIAS
# ==============================

class ClientePreferencias(db.Model):
    __tablename__ = "clientes_preferencias"

    id = db.Column(db.Integer, primary_key=True)

    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    keywords = db.Column(db.Text, nullable=False, default="")
    ufs = db.Column(db.Text, nullable=False, default="")
    modalidades = db.Column(db.Text, nullable=False, default="")

    ativo = db.Column(db.Boolean, default=True, nullable=False)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# ==============================
# ASSINATURA
# ==============================

class AssinaturaStatus(PyEnum):
    INACTIVE = "inactive"
    PENDING = "pending"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    PAUSED = "paused"


class Assinatura(db.Model):
    __tablename__ = "assinaturas"

    id = db.Column(db.Integer, primary_key=True)

    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    status = db.Column(
        db.Enum(AssinaturaStatus, native_enum=False),
        nullable=False,
        default=AssinaturaStatus.INACTIVE,
    )

    provider = db.Column(db.String(30), nullable=True)
    provider_ref = db.Column(db.String(120), nullable=True, index=True)
    provider_status = db.Column(db.String(50), nullable=True)

    trial_ends_at = db.Column(db.DateTime, nullable=True)

    started_at = db.Column(db.DateTime, nullable=True)
    canceled_at = db.Column(db.DateTime, nullable=True)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# ==============================
# EMAIL LOG
# ==============================

class EmailLog(db.Model):
    __tablename__ = "emails_log"

    id = db.Column(db.Integer, primary_key=True)

    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    destinatario = db.Column(db.String(255), nullable=False, index=True)
    assunto = db.Column(db.String(255), nullable=False, default="")

    enviado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    qtd_resultados = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(20), default="ok", nullable=False)
    erro = db.Column(db.Text, nullable=True)


# ==============================
# LICITAÇÃO
# ==============================

class Licitacao(db.Model):
    __tablename__ = "licitacoes"

    id = db.Column(db.Integer, primary_key=True)

    numero_processo = db.Column(db.String(255), nullable=True, index=True)
    identificador_unico_pncp = db.Column(
        db.String(255), nullable=True, unique=True, index=True
    )

    orgao_licitante = db.Column(db.String(255), nullable=True, index=True)
    modalidade = db.Column(db.String(120), nullable=True, index=True)

    objeto = db.Column(db.Text, nullable=True)

    data_publicacao = db.Column(db.DateTime, nullable=True, index=True)
    data_abertura_propostas = db.Column(db.DateTime, nullable=True)

    # NOVO: data final para envio de alertas 48h/24h
    data_encerramento_proposta = db.Column(db.DateTime, nullable=True, index=True)

    localidade_uf = db.Column(db.String(2), nullable=True, index=True)
    localidade_municipio = db.Column(db.String(255), nullable=True)

    fonte_dados = db.Column(db.String(50), nullable=True, index=True)
    link_fonte = db.Column(db.Text, nullable=True)

    # NOVO: edital
    link_edital = db.Column(db.Text, nullable=True)
    caminho_edital = db.Column(db.Text, nullable=True)

    texto_integral_aviso = db.Column(db.Text, nullable=True)

    valor_estimado = db.Column(db.Numeric(15, 2), nullable=True)

    situacao = db.Column(db.String(120), nullable=True)

    data_coleta = db.Column(db.DateTime, nullable=True)
    data_ultima_atualizacao = db.Column(db.DateTime, nullable=True)

    clientes_relacionados = db.relationship(
        "LicitacaoCliente",
        backref="licitacao",
        lazy=True,
        cascade="all, delete-orphan",
    )


# ==============================
# RELAÇÃO CLIENTE x LICITAÇÃO
# ==============================

class LicitacaoCliente(db.Model):
    __tablename__ = "licitacoes_cliente"

    id = db.Column(db.Integer, primary_key=True)

    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    licitacao_id = db.Column(
        db.Integer,
        db.ForeignKey("licitacoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    termo_encontrado = db.Column(db.String(255), nullable=True, index=True)

    email_enviado = db.Column(db.Boolean, default=False, nullable=False)
    enviado_em = db.Column(db.DateTime, nullable=True)

    # NOVO: alertas de prazo
    alerta_48h_enviado = db.Column(db.Boolean, default=False, nullable=False)
    alerta_24h_enviado = db.Column(db.Boolean, default=False, nullable=False)
    alerta_48h_enviado_em = db.Column(db.DateTime, nullable=True)
    alerta_24h_enviado_em = db.Column(db.DateTime, nullable=True)

    data_encontro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    observacoes = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint(
            "cliente_id",
            "licitacao_id",
            "termo_encontrado",
            name="uq_cliente_licitacao_termo",
        ),
    )


# ==============================
# HISTÓRICO DE BUSCAS
# ==============================

class HistoricoBusca(db.Model):
    __tablename__ = "historico_buscas"

    id = db.Column(db.Integer, primary_key=True)

    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    keywords = db.Column(db.Text, nullable=True)
    ufs = db.Column(db.String(255), nullable=True)
    modalidades = db.Column(db.String(255), nullable=True)

    data_inicial = db.Column(db.String(8), nullable=True)
    data_final = db.Column(db.String(8), nullable=True)

    pagina_inicial = db.Column(db.Integer, default=1, nullable=False)
    total_paginas_consultadas = db.Column(db.Integer, default=0, nullable=False)
    total_itens_recebidos = db.Column(db.Integer, default=0, nullable=False)
    total_licitacoes_novas = db.Column(db.Integer, default=0, nullable=False)

    executado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default="ok", nullable=False)
    erro = db.Column(db.Text, nullable=True)


# ==============================
# CONTROLE DE EXECUÇÃO DO MONITORAMENTO
# ==============================

class MonitoramentoExecucao(db.Model):
    __tablename__ = "monitoramento_execucao"

    id = db.Column(db.Integer, primary_key=True)

    ultima_execucao = db.Column(db.DateTime, nullable=True)

    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# ==============================
# PAGAMENTO
# ==============================

class Pagamento(db.Model):
    __tablename__ = "pagamentos"

    id = db.Column(db.Integer, primary_key=True)

    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    charge_id = db.Column(db.String(50), unique=True, nullable=False)
    payment_url = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="pendente")
    valor = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)