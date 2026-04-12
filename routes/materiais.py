from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
import models, schemas

router = APIRouter(prefix="/materiais", tags=["Materiais"])

@router.post("/")
def cadastrar_material(dados: schemas.MaterialCreate, db: Session = Depends(get_db)):
    try:
        # Verifica se o material já existe pelo ID do Património
        if db.query(models.Material).filter(models.Material.id_patrimonio == dados.id_patrimonio).first():
            raise HTTPException(status_code=400, detail="Este Património já está cadastrado.")
        
        # Cria o novo material desempacotando os dados do schema
        novo_material = models.Material(**dados.dict())
        db.add(novo_material)
        db.commit()
        return {"msg": "Material cadastrado com sucesso!"}
    
    except HTTPException:
        raise # Repassa o erro 400 normal se for patrimônio duplicado
    except Exception as e:
        # Se quebrar por coluna faltando ou outro erro do banco
        raise HTTPException(status_code=500, detail=f"Erro interno ao cadastrar: {str(e)}")


@router.get("/")
def listar_materiais(local: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        # Puxa apenas os materiais ativos
        query = db.query(models.Material).filter(models.Material.ativo == True)
        
        # Filtro opcional: Se o frontend mandar um local, a API filtra
        if local:
            query = query.filter(models.Material.local.ilike(f"%{local}%"))
            
        return query.all()
        
    except Exception as e:
        # Escudo ativado: Pega o erro real do SQLAlchemy e cospe na tela (ex: no such column)
        raise HTTPException(status_code=500, detail=f"Erro interno no Banco de Dados: {str(e)}")
