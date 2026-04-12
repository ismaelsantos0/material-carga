from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
import io
from reportlab.pdfgen import canvas
from auth import get_usuario_atual # Protege as rotas para exigir o login

router = APIRouter(prefix="/movimentacoes", tags=["Movimentações"])

@router.post("/cautelar")
def cautelar_material(
    dados: schemas.CautelaCreate, 
    db: Session = Depends(get_db), 
    usuario_atual: dict = Depends(get_usuario_atual)
):
    material = db.query(models.Material).filter(models.Material.id_patrimonio == dados.id_patrimonio).first()
    militar = db.query(models.Militar).filter(models.Militar.id == dados.id_militar).first()
    
    # Validações de segurança
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    if not militar:
        raise HTTPException(status_code=404, detail="Militar não encontrado")
    if material.situacao == "Em Uso":
        raise HTTPException(status_code=400, detail="Este material já está cautelado!")

    # 1. Registra a movimentação no histórico
    nova_movimentacao = models.Movimentacao(
        id_patrimonio=dados.id_patrimonio,
        id_militar=dados.id_militar,
        tipo_movimentacao="Cautela"
    )
    db.add(nova_movimentacao)
    
    # 2. Atualiza o status do material e carimba o responsável
    material.situacao = "Em Uso"
    material.responsavel = f"{militar.posto_graduacao} {militar.nome_de_guerra}"
    
    db.commit()

    # 3. Geração do PDF em memória
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(100, 800, "TERMO DE CAUTELA DE MATERIAL")
    pdf.drawString(100, 780, f"Patrimônio: {material.id_patrimonio} - {material.descricao}")
    pdf.drawString(100, 760, f"Recebedor: {militar.posto_graduacao} {militar.nome_de_guerra}")
    pdf.drawString(100, 740, "________________________________________________")
    pdf.drawString(100, 720, "Assinatura do Recebedor")
    pdf.save()
    buffer.seek(0)
    
    # Retorna o arquivo PDF direto para o navegador
    return StreamingResponse(
        buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=cautela_{material.id_patrimonio}.pdf"}
    )

@router.post("/devolver")
def devolver_material(
    dados: schemas.DevolucaoCreate, 
    db: Session = Depends(get_db),
    usuario_atual: dict = Depends(get_usuario_atual)
):
    material = db.query(models.Material).filter(models.Material.id_patrimonio == dados.id_patrimonio).first()
    
    # Validações
    if not material or material.situacao == "Disponível":
        raise HTTPException(status_code=400, detail="Material já está disponível no estoque.")

    # 1. Registra a devolução no histórico
    nova_movimentacao = models.Movimentacao(
        id_patrimonio=dados.id_patrimonio,
        tipo_movimentacao="Devolucao"
    )
    db.add(nova_movimentacao)

    # 2. Devolve o material para o estoque e limpa o responsável
    material.situacao = "Disponível"
    material.responsavel = None 
    
    db.commit()
    
    return {"msg": "Material devolvido ao estoque com sucesso!"}
