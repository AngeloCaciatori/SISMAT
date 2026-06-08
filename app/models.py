"""Modelos do banco SQLite (SQLAlchemy ORM).

Tabelas:
    Operador             — quem faz LOGIN no sistema (5 contas iniciais)
    Militar              — efetivo (172 militares que recebem cautelas)
    Medidas              — medidas corporais por militar (1:1)
    Material             — itens em carga (catálogo do almoxarifado)
    Cautela              — cabeçalho da cautela (1 por documento gerado)
    ItemCautelado        — itens de uma cautela (n por cautela)
    RacaoOperacional     — lotes de ração com validade
    ModeloDocumento      — templates HTML editáveis (FIDU, etc.)
    SolicitacaoReset     — pedidos de redefinição de senha registrados
"""

from datetime import datetime, date
import bcrypt
from flask_login import UserMixin
from .extensions import db


# ===================================================================
#  OPERADOR — usuários do sistema (login)
# ===================================================================

NIVEL_ADMIN = 1
NIVEL_OPERADOR = 2


class Operador(db.Model, UserMixin):
    __tablename__ = "operador"

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(200), nullable=False)
    nivel_seguranca = db.Column(db.Integer, default=NIVEL_OPERADOR, nullable=False)
    secao = db.Column(db.String(100), default="Reserva de Material")
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    senha_temporaria = db.Column(db.Boolean, default=False, nullable=False)
    ultimo_acesso = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Vínculo opcional com um militar do efetivo
    militar_id = db.Column(db.Integer, db.ForeignKey("militar.id"), nullable=True)
    militar = db.relationship("Militar", foreign_keys=[militar_id])

    # Assinatura digital — base64 da imagem PNG capturada no canvas mobile
    assinatura_base64 = db.Column(db.Text, nullable=True)
    assinatura_cadastrada_em = db.Column(db.DateTime, nullable=True)

    # ----- senha -----
    def definir_senha(self, senha_clara: str) -> None:
        """Hashea a senha com bcrypt e armazena."""
        self.senha_hash = bcrypt.hashpw(
            senha_clara.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def verificar_senha(self, senha_clara: str) -> bool:
        if not self.senha_hash:
            return False
        return bcrypt.checkpw(
            senha_clara.encode("utf-8"), self.senha_hash.encode("utf-8")
        )

    # ----- helpers -----
    @property
    def is_admin(self) -> bool:
        return self.nivel_seguranca == NIVEL_ADMIN

    def __repr__(self) -> str:
        return f"<Operador {self.login} nivel={self.nivel_seguranca}>"


# ===================================================================
#  MILITAR — efetivo (recebe cautelas)
# ===================================================================

class Militar(db.Model):
    __tablename__ = "militar"

    id = db.Column(db.Integer, primary_key=True)
    excluido = db.Column(db.Boolean, default=False, nullable=False, index=True)
    excluido_em = db.Column(db.DateTime, nullable=True)
    graduacao = db.Column(db.String(50), nullable=True)
    nome_guerra = db.Column(db.String(50), nullable=True, index=True)
    nome_completo = db.Column(db.String(200), nullable=True)
    cpf = db.Column(db.String(20), unique=True, nullable=False, index=True)
    ri = db.Column(db.String(50), nullable=True)
    antiguidade = db.Column(db.Float, nullable=True, index=True)
    numero = db.Column(db.String(50), nullable=True)
    foto_path = db.Column(db.String(300), nullable=True)
    telefone1 = db.Column(db.String(30), nullable=True)
    telefone2 = db.Column(db.String(30), nullable=True)
    om = db.Column(db.String(100), default="Bia C AD/5", nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relações
    medidas = db.relationship(
        "Medidas", uselist=False, back_populates="militar", cascade="all, delete-orphan"
    )
    cautelas = db.relationship("Cautela", back_populates="militar")

    def __repr__(self) -> str:
        return f"<Militar {self.graduacao} {self.nome_guerra}>"


# ===================================================================
#  MEDIDAS — corporais por militar (1:1)
# ===================================================================

class Medidas(db.Model):
    __tablename__ = "medidas"

    id = db.Column(db.Integer, primary_key=True)
    militar_id = db.Column(
        db.Integer, db.ForeignKey("militar.id"), unique=True, nullable=False
    )
    ombro = db.Column(db.String(20), nullable=True)
    cintura = db.Column(db.String(20), nullable=True)
    quadril = db.Column(db.String(20), nullable=True)
    cabeca = db.Column(db.String(20), nullable=True)
    pe = db.Column(db.String(20), nullable=True)
    braco = db.Column(db.String(20), nullable=True)
    atualizado_em = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    militar = db.relationship("Militar", back_populates="medidas")


# ===================================================================
#  MATERIAL — itens em carga (catálogo)
# ===================================================================

TIPOS_MATERIAL = ("EQUIPAMENTO", "FARDAMENTO", "MATERIAL", "OUTROS")
ESTADOS_CONSERVACAO = ("Novo", "Bom", "2ª Classe", "Em manutenção")
DEPENDENCIAS = ("", "RESERVA 1", "RESERVA 2")


class Material(db.Model):
    __tablename__ = "material"

    id = db.Column(db.Integer, primary_key=True)
    nomenclatura = db.Column(db.String(200), nullable=False, index=True)
    ficha_siscofis = db.Column(db.Text, nullable=True)  # texto livre — pode ter múltiplos lotes
    conta_contabil = db.Column(db.String(50), nullable=True)
    tipo = db.Column(db.String(30), nullable=False, default="EQUIPAMENTO")
    dependencia = db.Column(db.String(20), nullable=True)  # "RESERVA 1" / "RESERVA 2" / NULL
    prateleira = db.Column(db.String(20), nullable=True, index=True)
    qnt_siscofis = db.Column(db.Integer, default=0, nullable=False)  # quantidade total
    valor_unitario = db.Column(db.Numeric(10, 2), nullable=True)
    estado_conservacao = db.Column(db.String(30), default="Bom")
    obs = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relação reversa
    itens_cautelados = db.relationship("ItemCautelado", back_populates="material")

    @property
    def quantidade_cautelada(self) -> int:
        """Soma das quantidades em cautelas ativas (não devolvidas)."""
        return sum(
            i.quantidade
            for i in self.itens_cautelados
            if i.cautela and not i.cautela.devolvida
        )

    @property
    def disponivel(self) -> int:
        return max(0, (self.qnt_siscofis or 0) - self.quantidade_cautelada)

    def __repr__(self) -> str:
        return f"<Material {self.nomenclatura}>"


# ===================================================================
#  CAUTELA + ItemCautelado
# ===================================================================

OM_INTERNA = "interna"
OM_EXTERNA = "externa"


class Cautela(db.Model):
    __tablename__ = "cautela"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)  # ex.: "0143/2026"

    # Quem recebe (militar do efetivo OU externo)
    militar_id = db.Column(db.Integer, db.ForeignKey("militar.id"), nullable=True)
    om_tipo = db.Column(db.String(20), default=OM_INTERNA, nullable=False)
    om_externa_nome = db.Column(db.String(200), nullable=True)
    # Para cautela externa, guardamos os dados manuais do recebedor:
    recebedor_grad = db.Column(db.String(50), nullable=True)
    recebedor_nome_guerra = db.Column(db.String(50), nullable=True)
    recebedor_nome_completo = db.Column(db.String(200), nullable=True)
    recebedor_cpf = db.Column(db.String(20), nullable=True)

    # Quem cautelou
    operador_id = db.Column(db.Integer, db.ForeignKey("operador.id"), nullable=False)

    finalidade = db.Column(db.Text, nullable=True)
    data_cautela = db.Column(db.Date, default=date.today, nullable=False)
    devolucao_prevista = db.Column(db.Date, nullable=True)

    devolvida = db.Column(db.Boolean, default=False, nullable=False, index=True)
    devolvida_em = db.Column(db.Date, nullable=True)
    obs_geral = db.Column(db.Text, nullable=True)
    criada_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    militar = db.relationship("Militar", back_populates="cautelas")
    operador = db.relationship("Operador", foreign_keys=[operador_id])
    itens = db.relationship(
        "ItemCautelado", back_populates="cautela", cascade="all, delete-orphan"
    )

    @property
    def atrasada(self) -> bool:
        if self.devolvida or not self.devolucao_prevista:
            return False
        return self.devolucao_prevista < date.today()

    def __repr__(self) -> str:
        return f"<Cautela {self.numero}>"


class ItemCautelado(db.Model):
    __tablename__ = "item_cautelado"

    id = db.Column(db.Integer, primary_key=True)
    cautela_id = db.Column(
        db.Integer, db.ForeignKey("cautela.id"), nullable=False, index=True
    )
    material_id = db.Column(
        db.Integer, db.ForeignKey("material.id"), nullable=False, index=True
    )
    quantidade = db.Column(db.Integer, default=1, nullable=False)
    obs = db.Column(db.String(200), nullable=True)  # ex.: "2ª classe", "novo"

    cautela = db.relationship("Cautela", back_populates="itens")
    material = db.relationship("Material", back_populates="itens_cautelados")


# ===================================================================
#  RAÇÃO OPERACIONAL
# ===================================================================

class RacaoOperacional(db.Model):
    __tablename__ = "racao_operacional"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(100), nullable=False)  # "R-1", "R-2 (Almoço/Jantar)", etc.
    quantidade = db.Column(db.Integer, default=0, nullable=False)
    validade = db.Column(db.Date, nullable=True, index=True)
    obs = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def dias_para_vencer(self) -> int:
        if not self.validade:
            return 99999
        return (self.validade - date.today()).days

    @property
    def status(self) -> str:
        d = self.dias_para_vencer
        if d < 0:
            return "vencida"
        if d <= 30:
            return "vencendo"
        return "vigente"


# ===================================================================
#  MODELO DE DOCUMENTO (templates editáveis)
# ===================================================================

class ModeloDocumento(db.Model):
    __tablename__ = "modelo_documento"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    conteudo_html = db.Column(db.Text, nullable=False)
    padrao = db.Column(db.Boolean, default=False, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


# ===================================================================
#  LOG DE AUDITORIA — registro de ações dos operadores
# ===================================================================

class LogAuditoria(db.Model):
    __tablename__ = "log_auditoria"

    id = db.Column(db.Integer, primary_key=True)
    operador_id = db.Column(db.Integer, db.ForeignKey("operador.id"), nullable=True)
    acao = db.Column(db.String(60), nullable=False, index=True)
    descricao = db.Column(db.Text, nullable=False)
    referencia_id = db.Column(db.Integer, nullable=True)  # ID do objeto afetado
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    operador = db.relationship("Operador", foreign_keys=[operador_id])

    @property
    def operador_label(self) -> str:
        """Retorna 'Grad NomeGuerra' se operador tem militar vinculado, senão login."""
        if not self.operador:
            return "Sistema"
        op = self.operador
        if op.militar:
            grad = op.militar.graduacao or ""
            nome = op.militar.nome_guerra or ""
            label = f"{grad} {nome}".strip()
            if label:
                return label
        return op.login


# ===================================================================
#  SOLICITAÇÃO DE RESET DE SENHA (registrada para o admin atender)
# ===================================================================

class SolicitacaoReset(db.Model):
    __tablename__ = "solicitacao_reset"

    id = db.Column(db.Integer, primary_key=True)
    cpf = db.Column(db.String(20), nullable=False, index=True)
    nome = db.Column(db.String(200), nullable=True)
    motivo = db.Column(db.Text, nullable=True)
    atendida = db.Column(db.Boolean, default=False, nullable=False, index=True)
    atendida_em = db.Column(db.DateTime, nullable=True)
    atendida_por_id = db.Column(db.Integer, db.ForeignKey("operador.id"), nullable=True)
    solicitada_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# ===================================================================
#  TOKEN DE ASSINATURA — one-time token para autorizar assinatura
# ===================================================================

class TokenAssinatura(db.Model):
    __tablename__ = "token_assinatura"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False, index=True)
    tipo = db.Column(db.String(40), nullable=False)
    # tipos: "cadastro_operador" | "cautela_recebimento" | "cautela_devolucao" | "documento_recebedor"
    operador_id = db.Column(db.Integer, db.ForeignKey("operador.id"), nullable=True)
    cautela_id = db.Column(db.Integer, db.ForeignKey("cautela.id"), nullable=True)
    documento_id = db.Column(db.Integer, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    expira_em = db.Column(db.DateTime, nullable=False)
    usado = db.Column(db.Boolean, default=False)
    usado_em = db.Column(db.DateTime, nullable=True)
    ip_origem = db.Column(db.String(45), nullable=True)
    ip_uso = db.Column(db.String(45), nullable=True)

    operador = db.relationship("Operador", foreign_keys=[operador_id])
    cautela = db.relationship("Cautela", foreign_keys=[cautela_id])


# ===================================================================
#  ASSINATURA APLICADA — registro de cada assinatura coletada
# ===================================================================

class AssinaturaAplicada(db.Model):
    __tablename__ = "assinatura_aplicada"

    id = db.Column(db.Integer, primary_key=True)
    tipo_documento = db.Column(db.String(40), nullable=False)
    # tipos: "cautela_recebimento" | "cautela_devolucao" | "documento"
    cautela_id = db.Column(db.Integer, db.ForeignKey("cautela.id"), nullable=True)
    documento_id = db.Column(db.Integer, nullable=True)
    papel = db.Column(db.String(20), nullable=False)  # "operador" | "recebedor"
    operador_id = db.Column(db.Integer, db.ForeignKey("operador.id"), nullable=True)
    militar_id = db.Column(db.Integer, db.ForeignKey("militar.id"), nullable=True)
    recebedor_externo_nome = db.Column(db.String(200), nullable=True)
    recebedor_externo_cpf = db.Column(db.String(20), nullable=True)
    imagem_base64 = db.Column(db.Text, nullable=False)
    assinado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_origem = db.Column(db.String(45), nullable=False)
    token_id = db.Column(db.Integer, db.ForeignKey("token_assinatura.id"), nullable=True)

    operador_rel = db.relationship("Operador", foreign_keys=[operador_id])
    militar_rel = db.relationship("Militar", foreign_keys=[militar_id])
    cautela_rel = db.relationship("Cautela", foreign_keys=[cautela_id])
    token_rel = db.relationship("TokenAssinatura", foreign_keys=[token_id])
