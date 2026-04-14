from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
import models, schemas

router = APIRouter(prefix="/materiais", tags=["Materiais"])

@router.post("/")
def cadastrar_material(dados: schemas.MaterialCreate, db: Session = Depends(get_db)):
    try:
        # Verifica se o material já existe pelo ID do Patrimônio
        if db.query(models.Material).filter(models.Material.id_patrimonio == dados.id_patrimonio).first():
            raise HTTPException(status_code=400, detail="Este Patrimônio já está cadastrado.")
        
        novo_material = models.Material(**dados.dict())
        db.add(novo_material)
        db.commit()
        return {"msg": "Material cadastrado com sucesso!"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao cadastrar: {str(e)}")

# === ROTA: CADASTRAR MATERIAL EM LOTE (CONSUMO) ===
@router.post("/lote")
def cadastrar_material_lote(dados: schemas.MaterialLoteCreate, db: Session = Depends(get_db)):
    try:
        materiais_criados = []
        for i in range(1, dados.quantidade + 1):
            # Formata o ID com zeros à esquerda: ENX-001, ENX-002, etc.
            id_gerado = f"{dados.prefixo_id}-{i:03d}"
            
            # Verifica se já existe para não dar conflito
            if db.query(models.Material).filter(models.Material.id_patrimonio == id_gerado).first():
                continue

            novo_material = models.Material(
                id_patrimonio=id_gerado,
                descricao=dados.descricao,
                valor=dados.valor,
                tipo=dados.tipo,
                local=dados.local,
                observacao=dados.observacao
            )
            db.add(novo_material)
            materiais_criados.append(id_gerado)
        
        db.commit()
        return {"msg": f"{len(materiais_criados)} itens gerados e cadastrados com sucesso!", "ids": materiais_criados}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao cadastrar lote: {str(e)}")

@router.get("/")
def listar_materiais(local: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        query = db.query(models.Material).filter(models.Material.ativo == True)
        if local:
            query = query.filter(models.Material.local.ilike(f"%{local}%"))
        return query.all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno no Banco de Dados: {str(e)}")

@router.put("/{id_patrimonio}")
def editar_material(id_patrimonio: str, dados: schemas.MaterialCreate, db: Session = Depends(get_db)):
    try:
        # Busca o material estritamente pelo ID
        material = db.query(models.Material).filter(models.Material.id_patrimonio == id_patrimonio).first()
        if not material:
            raise HTTPException(status_code=404, detail="Material não encontrado")

        material.descricao = dados.descricao
        material.valor = dados.valor
        material.tipo = dados.tipo
        material.local = dados.local
        material.observacao = dados.observacao
        
        db.commit()
        return {"msg": "Material atualizado com sucesso!"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao editar: {str(e)}")
