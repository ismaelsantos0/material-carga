from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import uuid # <-- Ferramenta do Python para gerar IDs únicos
from database import get_db
import models, schemas

router = APIRouter(prefix="/materiais", tags=["Materiais"])

@router.post("/")
def cadastrar_material(dados: schemas.MaterialCreate, db: Session = Depends(get_db)):
    try:
        # === TRAVA DE AUTOMAÇÃO 1: ID Automático e Local Nulo ===
        if dados.tipo == "Ferramental de Consumo":
            dados.local = None
            # Gera um código único (ex: CONS-4F8A2C)
            dados.id_patrimonio = f"CONS-{uuid.uuid4().hex[:6].upper()}"
        
        # Se NÃO for consumo, o ID é obrigatório (Carga normal)
        elif not dados.id_patrimonio:
            raise HTTPException(status_code=400, detail="O ID do Patrimônio é obrigatório para materiais de Carga.")

        if db.query(models.Material).filter(models.Material.id_patrimonio == dados.id_patrimonio).first():
            raise HTTPException(status_code=400, detail="Este Patrimônio já está cadastrado.")
        
        novo_material = models.Material(
            id_patrimonio=dados.id_patrimonio,
            descricao=dados.descricao,
            valor=dados.valor,
            tipo=dados.tipo,
            local=dados.local,
            observacao=dados.observacao
        )
        db.add(novo_material)
        db.commit()
        return {"msg": "Material cadastrado com sucesso!"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao cadastrar: {str(e)}")

@router.post("/lote")
def cadastrar_material_lote(dados: schemas.MaterialLoteCreate, db: Session = Depends(get_db)):
    try:
        # === TRAVA DE AUTOMAÇÃO 2: Lote 100% autônomo ===
        if dados.tipo == "Ferramental de Consumo":
            dados.local = None

        materiais_criados = []
        for _ in range(dados.quantidade):
            # O sistema gera IDs até completar a quantidade pedida
            id_gerado = f"CONS-{uuid.uuid4().hex[:6].upper()}"
            
            # Garantia dupla para evitar raríssimas colisões do UUID
            while db.query(models.Material).filter(models.Material.id_patrimonio == id_gerado).first():
                id_gerado = f"CONS-{uuid.uuid4().hex[:6].upper()}"

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
        return {"msg": f"{len(materiais_criados)} itens gerados com sucesso!", "ids": materiais_criados}
        
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
        if dados.tipo == "Ferramental de Consumo":
            dados.local = None

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
