from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nome_usuario = Column(String, unique=True, index=True) # Ismael, Henrique, etc.
    senha_hash = Column(String)
    regra = Column(String, default="Operador") # Admin ou Operador

class Militar(Base):
    __tablename__ = "militares"
    id = Column(Integer, primary_key=True, index=True)
    cpf = Column(String, unique=True, index=True)
    posto_graduacao = Column(String)
    nome_completo = Column(String)
    nome_de_guerra = Column(String)
    om_origem = Column(String)
    secao = Column(String)
    telefone = Column(String)

class Material(Base):
    __tablename__ = "materiais"
    # REGRA DE OURO: Busca e controle estritos pelo ID do Patrimônio
    id_patrimonio = Column(String, primary_key=True, index=True)
    descricao = Column(String)
    valor = Column(String)
    tipo = Column(String) # Carga ou Ferramental
    ativo = Column(Boolean, default=True) # Soft delete

class Movimentacao(Base):
    __tablename__ = "movimentacoes"
    id = Column(Integer, primary_key=True, index=True)
    id_patrimonio = Column(String, ForeignKey("materiais.id_patrimonio"))
    id_militar = Column(Integer, ForeignKey("militares.id"), nullable=True)
    situacao = Column(String) # Disponível, Em Uso, Manutenção
    data_saida = Column(DateTime, default=datetime.utcnow)
    data_devolucao = Column(DateTime, nullable=True)

class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"
    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"))
    acao = Column(String)
    id_patrimonio = Column(String)
    data_hora = Column(DateTime, default=datetime.utcnow)
