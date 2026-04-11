from pydantic import BaseModel
from typing import Optional

class Login(BaseModel):
    nome_usuario: str
    senha: str

class CautelaCreate(BaseModel):
    id_patrimonio: str
    id_militar: int

class DevolucaoCreate(BaseModel):
    id_patrimonio: str
