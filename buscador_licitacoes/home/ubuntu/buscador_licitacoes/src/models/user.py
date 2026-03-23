from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    cliente_id = db.Column(db.Integer, nullable=False)

    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    senha_hash = db.Column(db.String(255), nullable=False)

    tipo_usuario = db.Column(db.String(20), nullable=False, default="comum")
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    primeiro_acesso = db.Column(db.Boolean, default=True, nullable=False)

    # controle de sessão
    session_token = db.Column(db.String(255), nullable=True)
    ultimo_ip = db.Column(db.String(100), nullable=True)
    ultimo_user_agent = db.Column(db.Text, nullable=True)
    sessao_expira_em = db.Column(db.DateTime, nullable=True)

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def __repr__(self):
        return f"<User {self.username}>"

    def to_dict(self):
        return {
            "id": self.id,
            "cliente_id": self.cliente_id,
            "username": self.username,
            "email": self.email,
            "tipo_usuario": self.tipo_usuario,
            "ativo": self.ativo,
            "primeiro_acesso": self.primeiro_acesso,
            "ultimo_ip": self.ultimo_ip,
            "sessao_expira_em": self.sessao_expira_em.isoformat() if self.sessao_expira_em else None
        }