from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth import get_usuario_atual
from services.pdf_generator import gerar_cautela_pdf
from datetime import datetime
from fastapi.responses import FileResponse

router = APIRouter(prefix="/movimentacoes", tags=["Movimentações"])

@router.post("/cautelar")
def efetuar_cautela(dados: schemas.CautelaCreate, db: Session = Depends(get_db), usuario_atual: dict = Depends(get_usuario_atual)):
    # 1. Verifica se o item existe e está disponível pelo ID
    material = db.query(models.Material).filter(models.Material.id_patrimonio == dados.id_patrimonio).first()
    if not material or material.ativo == False:
        raise HTTPException(status_code=404, detail="Material não encontrado ou baixado.")
    
    militar = db.query(models.Militar).filter(models.Militar.id == dados.id_militar).first()
    
    # 2. Registra a movimentação
    nova_mov = models.Movimentacao(
        id_patrimonio=material.id_patrimonio,
        id_militar=militar.id,
        situacao="Em Uso"
    )
    db.add(nova_mov)
    
    # 3. A TESTEMUNHA OCULAR: Grava o Log de Auditoria
    log = models.LogAuditoria(
        id_usuario=usuario_atual["id"],
        acao=f"Cautelou para {militar.posto_graduacao} {militar.nome_de_guerra}",
        id_patrimonio=material.id_patrimonio
    )
    db.add(log)
    db.commit()

    # 4. Gera e retorna o PDF
    pdf_path = gerar_cautela_pdf(material.id_patrimonio, material.descricao, militar.nome_de_guerra, militar.posto_graduacao)
    return FileResponse(pdf_path, media_type='application/pdf', filename=f"Cautela_{material.id_patrimonio}.pdf")

@router.post("/devolver")
def devolver_material(dados: schemas.DevolucaoCreate, db: Session = Depends(get_db), usuario_atual: dict = Depends(get_usuario_atual)):
    # Lógica de devolução seguindo o ID
    movimentacao_aberta = db.query(models.Movimentacao).filter(
        models.Movimentacao.id_patrimonio == dados.id_patrimonio,
        models.Movimentacao.situacao == "Em Uso",
        models.Movimentacao.data_devolucao == None
    ).first()

    if not movimentacao_aberta:
        raise HTTPException(status_code=400, detail="Este material não consta como cautelado.")

    movimentacao_aberta.situacao = "Disponível"
    movimentacao_aberta.data_devolucao = datetime.utcnow()

    log = models.LogAuditoria(
        id_usuario=usuario_atual["id"],
        acao="Descautelou / Devolveu para Estoque",
        id_patrimonio=dados.id_patrimonio
    )
    db.add(log)
    db.commit()
    return {"msg": "Material devolvido com sucesso."}
