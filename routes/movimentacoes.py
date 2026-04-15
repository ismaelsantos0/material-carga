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
                "usuario_logado": mov.usuario_logado or "Sistema"
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
    material.respons
