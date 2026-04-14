from pydantic import BaseModel
from typing import Optional, List

class MaterialCreate(BaseModel):
    id_patrimonio: str
    descricao: str
    valor: str
    tipo: str
    local: Optional[str] = "Estoque"
    observacao: Optional[str] = None

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

# === NOVOS SCHEMAS PARA LOTE E SELEÇÃO MÚLTIPLA ===

class MaterialLoteCreate(BaseModel):
    prefixo_id: str
    descricao: str
    valor: str
    tipo: str
    local: Optional[str] = "Almox"
    observacao: Optional[str] = None
    quantidade: int

class CautelaMultiplaCreate(BaseModel):
    ids_patrimonio: List[str]
    id_militar: int

class DevolucaoMultiplaCreate(BaseModel):
    ids_patrimonio: List[str]
