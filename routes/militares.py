from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from pydantic import BaseModel

router = APIRouter(prefix="/militares", tags=["Militares"])

class MilitarCreate(BaseModel):
    cpf: str
    posto_graduacao: str
    nome_completo: str
    nome_de_guerra: str
    om_origem: str
    secao: str
    telefone: str

@router.post("/")
def cadastrar_militar(dados: MilitarCreate, db: Session = Depends(get_db)):
    existente = db.query(models.Militar).filter(models.Militar.cpf == dados.cpf).first()
    if existente:
        raise HTTPException(status_code=400, detail="CPF já cadastrado.")
    
    novo_militar = models.Militar(**dados.dict())
    db.add(novo_militar)
    db.commit()
    return {"msg": "Militar cadastrado com sucesso!"}

@router.get("/")
def listar_militares(db: Session = Depends(get_db)):
    return db.query(models.Militar).all()
