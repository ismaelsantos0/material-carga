from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nome_usuario = Column(String, unique=True, index=True)
    senha_hash = Column(String)
    regra = Column(String, default="Admin")

class Material(Base):
    __tablename__ = "materiais"
    id_patrimonio = Column(String, primary_key=True, index=True)
    descricao = Column(String)
    valor = Column(String)
    tipo = Column(String) # "Carga" ou "Ferramental"
    ativo = Column(Boolean, default=True)
    local = Column(String, default="Estoque")
    situacao = Column(String, default="Disponível") # "Disponível" ou "Em Uso"
    responsavel = Column(String, nullable=True) # Nome do militar com o material

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

class Movimentacao(Base):
    __tablename__ = "movimentacoes"
    id = Column(Integer, primary_key=True, index=True)
    id_patrimonio = Column(String, ForeignKey("materiais.id_patrimonio"))
    id_militar = Column(Integer, ForeignKey("militares.id"), nullable=True)
    tipo_movimentacao = Column(String) # "Cautela" ou "Devolucao"
    data_hora = Column(DateTime, default=datetime.utcnow)
