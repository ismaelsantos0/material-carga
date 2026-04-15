import io
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

# Imports para gerar Tabelas e Imagens Profissionais no PDF
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors

from database import engine, Base, SessionLocal, get_db
from routes import movimentacoes, materiais, militares
import auth
import models

# Cria as tabelas no banco de dados automaticamente
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema Vero - Controle de Material", 
    description="Sistema de gestão de patrimônio, cautelas e auditoria",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(materiais.router)
app.include_router(militares.router)
app.include_router(movimentacoes.router)

@app.on_event("startup")
def criar_admin_padrao():
    db = SessionLocal()
    try:
        admin_existe = db.query(models.Usuario).filter(models.Usuario.nome_usuario == "admin").first()
        if not admin_existe:
            novo_admin = models.Usuario(
                nome_usuario="admin",
                senha_hash=auth.obter_hash_senha("admin123"), 
                regra="Admin"
            )
            db.add(novo_admin)
            db.commit()
    finally:
        db.close()

# === RELATÓRIO 1: DEVEDORES GERAL ===
@app.get("/relatorios/devedores", tags=["Relatórios"])
def listar_devedores(db: Session = Depends(get_db)):
    try:
        movimentacoes_lista = db.query(models.Movimentacao).order_by(models.Movimentacao.data_hora.desc()).all()
        devedores = []
        itens_processados = set()
        
        for mov in movimentacoes_lista:
            if mov.id_patrimonio not in itens_processados:
                itens_processados.add(mov.id_patrimonio)
                tipo_mov = getattr(mov, 'tipo', getattr(mov, 'tipo_movimentacao', ''))
                
                if tipo_mov == 'Cautela':
                    material = db.query(models.Material).filter(models.Material.id_patrimonio == mov.id_patrimonio).first()
                    militar = None
                    if mov.id_militar:
                        militar = db.query(models.Militar).filter(models.Militar.id == mov.id_militar).first()
                    
                    if material and militar:
                        data_segura = str(mov.data_hora) if mov.data_hora else None
                        devedores.append({
                            "id_patrimonio": material.id_patrimonio,
                            "descricao": material.descricao,
                            "responsavel": f"{militar.posto_graduacao} {militar.nome_de_guerra}",
                            "data_cautela": data_segura,
                            "observacao": material.observacao
                        })
        return devedores
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# === RELATÓRIO 2: DEVEDORES POR MILITAR (Mostra tudo, inclusive consumo) ===
@app.get("/relatorios/devedores_por_militar", tags=["Relatórios"])
def relatorio_devedores_militar(db: Session = Depends(get_db)):
    try:
        materiais_em_uso = db.query(models.Material).filter(models.Material.situacao == "Em Uso").all()
        relatorio = {}
        for mat in materiais_em_uso:
            resp = mat.responsavel or "Militar Desconhecido"
            if resp not in relatorio:
                relatorio[resp] = []
            relatorio[resp].append({
                "id_patrimonio": mat.id_patrimonio,
                "descricao": mat.descricao,
                "tipo": mat.tipo,
                "observacao": mat.observacao
            })
        resultado = [{"militar": k, "materiais": v, "total_itens": len(v)} for k, v in relatorio.items()]
        return sorted(resultado, key=lambda x: x["militar"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# === RELATÓRIO 3: INVENTÁRIO POR LOCAL (TELA) ===
@app.get("/relatorios/materiais_por_local", tags=["Relatórios"])
def relatorio_materiais_local(db: Session = Depends(get_db)):
    try:
        materiais_lista = db.query(models.Material).filter(models.Material.ativo == True).all()
        relatorio = {}
        for mat in materiais_lista:
            
            # REGRA: Ignora se for material de consumo
            if mat.tipo and "Consumo" in mat.tipo:
                continue

            local = mat.local
            if mat.tipo == "Ferramental" and (not local or local == "Estoque"):
                local = "Almox"
            elif not local:
                local = "Não Definido"
                
            if local not in relatorio:
                relatorio[local] = []
            relatorio[local].append({
                "id_patrimonio": mat.id_patrimonio,
                "descricao": mat.descricao,
                "situacao": mat.situacao,
                "responsavel": mat.responsavel,
                "tipo": mat.tipo,
                "observacao": mat.observacao
            })
        resultado = [{"local": k, "materiais": v, "total_itens": len(v)} for k, v in relatorio.items()]
        return sorted(resultado, key=lambda x: x["local"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# === ROTA DE EXPORTAÇÃO: PDF DE DEVEDORES (GERAL) ===
@app.get("/relatorios/devedores_por_militar/pdf", tags=["Relatórios"])
def relatorio_devedores_militar_pdf(db: Session = Depends(get_db)):
    try:
        materiais_em_uso = db.query(models.Material).filter(models.Material
