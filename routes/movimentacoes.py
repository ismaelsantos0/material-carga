from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
import io
from reportlab.pdfgen import canvas
from auth import get_usuario_atual

router = APIRouter(prefix="/movimentacoes", tags=["Movimentações"])

@router.post("/cautelar")
def cautelar_material(
    dados: schemas.CautelaCreate, 
    db: Session = Depends(get_db), 
    usuario_atual: dict = Depends(get_usuario_atual)
):
    material = db.query(models.Material).filter(models.Material.id_patrimonio == dados.id_patrimonio).first()
    militar = db.query(models.Militar).filter(models.Militar.id == dados.id_militar).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="Material não encontrado")
    if not militar:
        raise HTTPException(status_code=404, detail="Militar não encontrado")
    if material.situacao == "Em Uso":
        raise HTTPException(status_code=400, detail="Este material já está cautelado!")

    # Registra o log da movimentação
    nova_movimentacao = models.Movimentacao(
        id_patrimonio=dados.id_patrimonio,
        id_militar=dados.id_militar,
        tipo_movimentacao="Cautela"
    )
    db.add(nova_movimentacao)
    
    # Atualiza material
    material.situacao = "Em Uso"
    material.responsavel = f"{militar.posto_graduacao} {militar.nome_de_guerra}"
    
    db.commit()

    # Gera PDF
    try:
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer)
        pdf.drawString(100, 800, "TERMO DE CAUTELA DE MATERIAL")
        pdf.drawString(100, 780, f"Patrimônio: {material.id_patrimonio} - {material.descricao}")
        pdf.drawString(100, 760, f"Recebedor: {militar.posto_graduacao} {militar.nome_de_guerra}")
        pdf.drawString(100, 740, "________________________________________________")
        pdf.drawString(100, 720, "Assinatura do Recebedor")
        pdf.save()
        buffer.seek(0)
        
        headers = {
            "Content-Disposition": f"inline; filename=cautela_{material.id_patrimonio}.pdf",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
        
        return StreamingResponse(
            buffer, 
            media_type="application/pdf",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar PDF: {str(e)}")


@router.post("/devolver")
def devolver_material(
    dados: schemas.DevolucaoCreate, 
    db: Session = Depends(get_db),
    usuario_atual: dict = Depends(get_usuario_atual)
):
    material = db.query(models.Material).filter(models.Material.id_patrimonio == dados.id_patrimonio).first()
    
    if not material or material.situacao == "Disponível":
        raise HTTPException(status_code=400, detail="Material já está disponível no estoque.")

    # Registra o log de devolução
    nova_movimentacao = models.Movimentacao(
        id_patrimonio=dados.id_patrimonio,
        tipo_movimentacao="Devolucao"
    )
    db.add(nova_movimentacao)

    # Devolve material e limpa responsável
    material.situacao = "Disponível"
    material.responsavel = None 
    
    db.commit()
    
    return {"msg": "Material devolvido ao estoque com sucesso!"}

# === NOVA ROTA DE AUDITORIA / HISTÓRICO ===
@router.get("/")
def listar_movimentacoes(db: Session = Depends(get_db)):
    try:
        # Puxa tudo ordenado do mais recente para o mais antigo
        movimentacoes = db.query(models.Movimentacao).order_by(models.Movimentacao.data_hora.desc()).all()
        
        historico = []
        for mov in movimentacoes:
            # 1. Busca a descrição do material
            material = db.query(models.Material).filter(models.Material.id_patrimonio == mov.id_patrimonio).first()
            descricao_mat = material.descricao if material else "Material Desconhecido/Removido"
            
            # 2. Busca o nome do militar (se houver)
            nome_mil = "-"
            if mov.id_militar:
                militar = db.query(models.Militar).filter(models.Militar.id == mov.id_militar).first()
                if militar:
                    nome_mil = f"{militar.posto_graduacao} {militar.nome_de_guerra}"
            
            # 3. Monta o dicionário exato que o frontend pediu
            historico.append({
                "id": mov.id,
                "id_patrimonio": mov.id_patrimonio,
                "tipo": getattr(mov, 'tipo_movimentacao', getattr(mov, 'tipo', '')), # Converte o nome da coluna para "tipo"
                "data_hora": str(mov.data_hora) if mov.data_hora else None,
                "descricao_material": descricao_mat,
                "nome_militar": nome_mil
            })
            
        return historico
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar histórico: {str(e)}")
