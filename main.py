import io
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from sqlalchemy.orm import Session

from database import engine, Base, SessionLocal, get_db
from routes import movimentacoes, materiais, militares
import auth
import models

# Cria as tabelas no banco de dados automaticamente (apenas as tabelas novas)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema Carga e Ferramental", 
    description="Sistema de gestão de patrimônio, cautelas e auditoria",
    version="1.0"
)

# Configuração de CORS - Essencial para o frontend (Lovable) não ser bloqueado
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conectando todas as rotas
app.include_router(auth.router)
app.include_router(materiais.router)
app.include_router(militares.router)
app.include_router(movimentacoes.router)

# === A MÁGICA DE CRIAR O ADMIN AUTOMATICAMENTE ===
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
            print("Usuário 'admin' criado com sucesso!")
    finally:
        db.close()
# =================================================

# === RELATÓRIO 1: DEVEDORES GERAL (Histórico) ===
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
        raise HTTPException(status_code=500, detail=f"Erro interno no Python: {str(e)}")

# === RELATÓRIO 2: DEVEDORES POR MILITAR (Agrupado) ===
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
                "observacao": mat.observacao # <-- Inserido aqui!
            })
            
        resultado = [{"militar": k, "materiais": v, "total_itens": len(v)} for k, v in relatorio.items()]
        return sorted(resultado, key=lambda x: x["militar"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# === RELATÓRIO 3: INVENTÁRIO POR LOCAL (Agrupado) ===
@app.get("/relatorios/materiais_por_local", tags=["Relatórios"])
def relatorio_materiais_local(db: Session = Depends(get_db)):
    try:
        materiais_lista = db.query(models.Material).filter(models.Material.ativo == True).all()
        relatorio = {}
        
        for mat in materiais_lista:
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
                "observacao": mat.observacao # <-- Inserido aqui!
            })
            
        resultado = [{"local": k, "materiais": v, "total_itens": len(v)} for k, v in relatorio.items()]
        return sorted(resultado, key=lambda x: x["local"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# === ROTA DE EXPORTAÇÃO: PDF DE DEVEDORES ===
@app.get("/relatorios/devedores_por_militar/pdf", tags=["Relatórios"])
def relatorio_devedores_militar_pdf(db: Session = Depends(get_db)):
    try:
        materiais_em_uso = db.query(models.Material).filter(models.Material.situacao == "Em Uso").all()
        relatorio = {}
        
        for mat in materiais_em_uso:
            resp = mat.responsavel or "Militar Desconhecido"
            if resp not in relatorio:
                relatorio[resp] = []
            
            # Adiciona a observação no PDF se ela existir
            obs_texto = f" (Obs: {mat.observacao})" if mat.observacao else ""
            relatorio[resp].append(f"{mat.id_patrimonio} - {mat.descricao}{obs_texto}")
            
        relatorio_ordenado = sorted(relatorio.items())

        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        pdf.setTitle("Relatório de Devedores")

        y = 800 
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, y, "Relatório de Materiais Cautelados por Militar")
        y -= 40

        for militar, itens in relatorio_ordenado:
            if y < 100: 
                pdf.showPage()
                y = 800

            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(50, y, f"Responsável: {militar} ({len(itens)} itens pendentes)")
            y -= 20

            pdf.setFont("Helvetica", 10)
            for item in itens:
                if y < 50:
                    pdf.showPage()
                    y = 800
                    pdf.setFont("Helvetica", 10)
                pdf.drawString(70, y, f"• {item}")
                y -= 15
            y -= 15

        pdf.save()
        buffer.seek(0)

        headers = {
            "Content-Disposition": "inline; filename=relatorio_devedores.pdf",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }

        return StreamingResponse(
            buffer, 
            media_type="application/pdf", 
            headers=headers
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")

# === ROTA DE EXPORTAÇÃO: PDF DE INVENTÁRIO POR LOCAL ===
@app.get("/relatorios/materiais_por_local/pdf", tags=["Relatórios"])
def relatorio_materiais_local_pdf(db: Session = Depends(get_db)):
    try:
        materiais_lista = db.query(models.Material).filter(models.Material.ativo == True).all()
        relatorio = {}
        
        for mat in materiais_lista:
            local = mat.local
            if mat.tipo == "Ferramental" and (not local or local == "Estoque"):
                local = "Almox"
            elif not local:
                local = "Não Definido"
                
            if local not in relatorio:
                relatorio[local] = []
            
            status_texto = f"[{mat.situacao}]"
            if mat.situacao == "Em Uso" and mat.responsavel:
                status_texto += f" c/ {mat.responsavel}"
            
            # Adiciona a observação no PDF se ela existir
            obs_texto = f" - Obs: {mat.observacao}" if mat.observacao else ""
                
            relatorio[local].append(f"{mat.id_patrimonio} - {mat.descricao} {status_texto}{obs_texto}")
            
        relatorio_ordenado = sorted(relatorio.items())

        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        pdf.setTitle("Inventário por Local")

        y = 800 
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, y, "Relatório de Inventário por Local")
        y -= 40

        for local_nome, itens in relatorio_ordenado:
            if y < 100: 
                pdf.showPage()
                y = 800

            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(50, y, f"Local: {local_nome} ({len(itens)} itens)")
            y -= 20

            pdf.setFont("Helvetica", 10)
            for item in itens:
                if y < 50:
                    pdf.showPage()
                    y = 800
                    pdf.setFont("Helvetica", 10)
                pdf.drawString(70, y, f"• {item}")
                y -= 15
            y -= 15

        pdf.save()
        buffer.seek(0)

        headers = {
            "Content-Disposition": "inline; filename=inventario_local.pdf",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }

        return StreamingResponse(
            buffer, 
            media_type="application/pdf", 
            headers=headers
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")
# =================================================

@app.get("/")
def read_root():
    return {"status": "online"}
