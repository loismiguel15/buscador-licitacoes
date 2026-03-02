from flask_sqlalchemy import SQLAlchemy
from enum import Enum as PyEnum
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash # Import hashing functions

db = SQLAlchemy()

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nome_empresa = db.Column(db.String(255), nullable=False)
    cnpj = db.Column(db.String(18), unique=True)
    email_contato = db.Column(db.String(255), nullable=False)
    telefone_contato = db.Column(db.String(20))
    data_cadastro = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)
    usuarios = db.relationship('Usuario', backref='cliente', lazy=True, cascade="all, delete-orphan")

class TipoUsuario(PyEnum):
    MASTER = 'master'
    COMUM = 'comum'

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    nome_completo = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False) # Store hash, not plain text
    tipo = db.Column(db.Enum(TipoUsuario), nullable=False, default=TipoUsuario.COMUM)
    data_criacao = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    ultimo_login = db.Column(db.TIMESTAMP)
    ativo = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        """Create hashed password."""
        # Increased iterations for better security
        self.senha_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.senha_hash, password)

class Licitacao(db.Model):
    __tablename__ = 'licitacoes'
    id = db.Column(db.Integer, primary_key=True)
    numero_processo = db.Column(db.String(100), index=True)
    identificador_unico_pncp = db.Column(db.String(100), unique=True, nullable=True)
    orgao_licitante = db.Column(db.String(500), nullable=False, index=True)
    modalidade = db.Column(db.String(100), nullable=False, index=True)
    objeto = db.Column(db.Text, nullable=False)
    data_publicacao = db.Column(db.Date, index=True)
    data_abertura_propostas = db.Column(db.DateTime, index=True)
    localidade_uf = db.Column(db.String(2), index=True)
    localidade_municipio = db.Column(db.String(255), index=True)
    fonte_dados = db.Column(db.String(255), nullable=False)
    link_fonte = db.Column(db.String(2048))
    texto_integral_aviso = db.Column(db.Text) # Use Text for potentially long content
    valor_estimado = db.Column(db.Numeric(15, 2))
    situacao = db.Column(db.String(50), default='Aberta', index=True)
    data_coleta = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    data_ultima_atualizacao = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add full-text index configuration if needed, depends on DB engine/version
    # __table_args__ = {
    #     'mysql_engine': 'InnoDB',
    #     'mysql_charset': 'utf8mb4',
    #     'mysql_collate': 'utf8mb4_general_ci',
    #     'indexes': [db.Index('ix_licitacoes_objeto_fulltext', 'objeto', mysql_prefix='FULLTEXT')]
    # }

