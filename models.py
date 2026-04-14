from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nome_usuario = Column(String, unique=True, index=True)
    senha_hash = Column(String)
    regra = Column(String, default="Usuario")

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
    ativo = Column(Boolean, default=True)

class Material(Base):
    __tablename__ = "materiais"
    
    id_patrimonio = Column(String, primary_key=True, index=True)
    descricao = Column(String)
    valor = Column(String)
    tipo = Column(String)
    local = Column(String, default="Estoque")
    situacao = Column(String, default="Disponível")
    responsavel = Column(String, nullable=True)
    ativo = Column(Boolean, default=True)
    observacao = Column(String, nullable=True) # <-- O novo campo está aqui

class Movimentacao(Base):
    __tablename__ = "movimentacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    id_patrimonio = Column(String)
    id_militar = Column(Integer, nullable=True) # Fica nulo na devolução
    tipo_movimentacao = Column(String)
    data_hora = Column(DateTime, server_default=func.now()) # Salva a hora exata sozinho
