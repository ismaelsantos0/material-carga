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
            raise HTTPException(status_code=400, detail="Este Patrimônio já está cadastrado.")
        
        # Cria o novo material
        novo_material = models.Material(**dados.dict())
        db.add(novo_material)
        db.commit()
        return {"msg": "Material cadastrado com sucesso!"}
    
    except HTTPException:
        raise # Repassa o erro 400 normal se for patrimônio duplicado
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao cadastrar: {str(e)}")


@router.get("/")
def listar_materiais(local: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        query = db.query(models.Material).filter(models.Material.ativo == True)
        if local:
            query = query.filter(models.Material.local.ilike(f"%{local}%"))
        return query.all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno no Banco de Dados: {str(e)}")


# === NOVA ROTA: EDITAR MATERIAL ===
@router.put("/{id_patrimonio}")
def editar_material(id_patrimonio: str, dados: schemas.MaterialCreate, db: Session = Depends(get_db)):
    try:
        # Busca o material estritamente pelo ID
        material = db.query(models.Material).filter(models.Material.id_patrimonio == id_patrimonio).first()
        if not material:
            raise HTTPException(status_code=404, detail="Material não encontrado")

        # Atualiza os dados permitidos
        material.descricao = dados.descricao
        material.valor = dados.valor
        material.tipo = dados.tipo
        material.local = dados.local
        material.observacao = dados.observacao
        
        db.commit()
        return {"msg": "Material atualizado com sucesso!"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao editar: {str(e)}")
