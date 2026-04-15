from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas

router = APIRouter(prefix="/movimentacoes", tags=["Movimentações"])

# === HISTÓRICO / AUDITORIA ===
@router.get("/")
def historico_movimentacoes(db: Session = Depends(get_db)):
    try:
        movimentacoes = db.query(models.Movimentacao).order_by(models.Movimentacao.data_hora.desc()).all()
        resultado = []
        
        for mov in movimentacoes:
            material = db.query(models.Material).filter(models.Material.id_patrimonio == mov.id_patrimonio).first()
            militar = None
            if mov.id_militar:
                militar = db.query(models.Militar).filter(models.Militar.id == mov.id_militar).first()

            resultado.append({
                "id": mov.id,
                "data_hora": mov.data_hora,
                "tipo": mov.tipo_movimentacao,
                "id_patrimonio": mov.id_patrimonio,
                "material_desc": material.descricao if material else "Material Excluído",
                "militar_nome": f"{militar.posto_graduacao} {militar.nome_de_guerra}" if militar else "Almoxarifado",
                "usuario_logado": mov.usuario_logado or "Sistema" # Envia o nome do operador para a tela
            })
            
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar auditoria: {str(e)}")

# === CAUTELA UNITÁRIA ===
@router.post("/cautela")
def cautelar_material(dados: schemas.CautelaCreate, db: Session = Depends(get_db)):
    material = db.query(models.Material).filter(models.Material.id_patrimonio == dados.id_patrimonio).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado.")
    if material.situacao == "Em Uso":
        raise HTTPException(status_code=400, detail="Material já está em uso.")
    
    militar = db.query(models.Militar).filter(models.Militar.id == dados.id_militar).first()
    if not militar:
        raise HTTPException(status_code=404, detail="Militar não encontrado.")

    material.situacao = "Em Uso"
    material.responsavel = f"{militar.posto_graduacao} {militar.nome_de_guerra}" # <-- CORRIGIDO AQUI!
    
    nova_mov = models.Movimentacao(
        id_patrimonio=material.id_patrimonio,
        id_militar=militar.id,
        tipo_movimentacao="Cautela",
        usuario_logado=dados.usuario_logado # Salva o operador
    )
    db.add(nova_mov)
    db.commit()
    return {"msg": "Material cautelado com sucesso!"}

# === DEVOLUÇÃO UNITÁRIA ===
@router.post("/devolucao")
def devolver_material(dados: schemas.DevolucaoCreate, db: Session = Depends(get_db)):
    material = db.query(models.Material).filter(models.Material.id_patrimonio == dados.id_patrimonio).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado.")
    if material.situacao == "Disponível":
        raise HTTPException(status_code=400, detail="Material já está disponível.")

    material.situacao = "Disponível"
    material.responsavel = None

    nova_mov = models.Movimentacao(
        id_patrimonio=material.id_patrimonio,
        id_militar=None,
        tipo_movimentacao="Devolucao",
        usuario_logado=dados.usuario_logado # Salva o operador
    )
    db.add(nova_mov)
    db.commit()
    return {"msg": "Material devolvido com sucesso!"}

# === CAUTELA MÚLTIPLA ===
@router.post("/cautela_multipla")
def cautela_multipla(dados: schemas.CautelaMultiplaCreate, db: Session = Depends(get_db)):
    try:
        militar = db.query(models.Militar).filter(models.Militar.id == dados.id_militar).first()
        if not militar:
            raise HTTPException(status_code=404, detail="Militar não encontrado.")

        sucessos = 0
        for id_pat in dados.ids_patrimonio:
            material = db.query(models.Material).filter(models.Material.id_patrimonio == id_pat).first()
            if not material or material.situacao == "Em Uso":
                continue 

            material.situacao = "Em Uso"
            material.responsavel = f"{militar.posto_graduacao} {militar.nome_de_guerra}"

            nova_mov = models.Movimentacao(
                id_patrimonio=material.id_patrimonio,
                id_militar=militar.id,
                tipo_movimentacao="Cautela",
                usuario_logado=dados.usuario_logado # Salva o operador
            )
            db.add(nova_mov)
            sucessos += 1
        
        db.commit()
        return {"msg": f"{sucessos} itens cautelados com sucesso para {militar.nome_de_guerra}."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# === DEVOLUÇÃO MÚLTIPLA ===
@router.post("/devolucao_multipla")
def devolucao_multipla(dados: schemas.DevolucaoMultiplaCreate, db: Session = Depends(get_db)):
    try:
        sucessos = 0
        for id_pat in dados.ids_patrimonio:
            material = db.query(models.Material).filter(models.Material.id_patrimonio == id_pat).first()
            if not material or material.situacao == "Disponível":
                continue

            material.situacao = "Disponível"
            material.responsavel = None

            nova_mov = models.Movimentacao(
                id_patrimonio=material.id_patrimonio,
                id_militar=None,
                tipo_movimentacao="Devolucao",
                usuario_logado=dados.usuario_logado # Salva o operador
            )
            db.add(nova_mov)
            sucessos += 1
            
        db.commit()
        return {"msg": f"{sucessos} itens devolvidos com sucesso ao Almoxarifado!"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
