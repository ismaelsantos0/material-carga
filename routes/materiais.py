from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from pydantic import BaseModel

router = APIRouter(prefix="/materiais", tags=["Materiais"])

# Schema para validação (você pode colocar isso no schemas.py também)
class MaterialCreate(BaseModel):
    id_patrimonio: str
    descricao: str
    valor: str
    tipo: str # "Carga" ou "Ferramental"

@router.post("/")
def cadastrar_material(dados: MaterialCreate, db: Session = Depends(get_db)):
    # Regra de ouro: Verifica se o ID do patrimônio já existe
    existente = db.query(models.Material).filter(models.Material.id_patrimonio == dados.id_patrimonio).first()
    if existente:
        raise HTTPException(status_code=400, detail="Este Número de Patrimônio já está cadastrado.")
    
    novo_material = models.Material(
        id_patrimonio=dados.id_patrimonio,
        descricao=dados.descricao,
        valor=dados.valor,
        tipo=dados.tipo
    )
    db.add(novo_material)
    db.commit()
    return {"msg": "Material cadastrado com sucesso!"}

@router.get("/")
def listar_materiais(db: Session = Depends(get_db)):
    return db.query(models.Material).filter(models.Material.ativo == True).all()
