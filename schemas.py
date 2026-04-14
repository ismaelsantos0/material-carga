from pydantic import BaseModel
from typing import Optional

class MaterialCreate(BaseModel):
    id_patrimonio: str
    descricao: str
    valor: str
    tipo: str
    local: Optional[str] = "Estoque"
    observacao: Optional[str] = None # <-- Permite o Lovable enviar a observação

class MilitarCreate(BaseModel):
    cpf: str
    posto_graduacao: str
    nome_completo: str
    nome_de_guerra: str
    om_origem: str
    secao: str
    telefone: str

class CautelaCreate(BaseModel):
    id_patrimonio: str
    id_militar: int

class DevolucaoCreate(BaseModel):
    id_patrimonio: str
    
