import io
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response 
from sqlalchemy.orm import Session

# Imports para gerar Tabelas e Imagens Profissionais no PDF
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors, utils 

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

# === CRIAÇÃO AUTOMÁTICA DOS USUÁRIOS NO BANCO ===
@app.on_event("startup")
def criar_usuarios_padrao():
    db = SessionLocal()
    try:
        usuarios_iniciais = [
            ("admin", "admin123", "Admin"),
            ("henrique", "henrique123", "Operador"),
            ("williames", "williames123", "Operador"),
            ("chefe", "chefe123", "Operador")
        ]

        for nome, senha, regra in usuarios_iniciais:
            usuario_existe = db.query(models.Usuario).filter(models.Usuario.nome_usuario == nome).first()
            
            if not usuario_existe:
                novo_usuario = models.Usuario(
                    nome_usuario=nome,
                    senha_hash=auth.obter_hash_senha(senha), 
                    regra=regra
                )
                db.add(novo_usuario)
                print(f"Usuário '{nome}' inserido com sucesso!")
        
        db.commit()
    finally:
        db.close()

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

@app.get("/relatorios/materiais_por_local", tags=["Relatórios"])
def relatorio_materiais_local(db: Session = Depends(get_db)):
    try:
        materiais_lista = db.query(models.Material).filter(models.Material.ativo == True).all()
        relatorio = {}
        for mat in materiais_lista:
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

@app.get("/relatorios/devedores_por_militar/pdf", tags=["Relatórios"])
def relatorio_devedores_militar_pdf(db: Session = Depends(get_db)):
    try:
        materiais_em_uso = db.query(models.Material).filter(models.Material.situacao == "Em Uso").all()
        relatorio = {}
        
        for mat in materiais_em_uso:
            resp = mat.responsavel or "Militar Desconhecido"
            if resp not in relatorio:
                relatorio[resp] = []
            relatorio[resp].append({
                "id": mat.id_patrimonio,
                "desc": mat.descricao,
                "obs": mat.observacao or ""
            })
            
        relatorio_ordenado = sorted(relatorio.items())
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("<b>Relatório de Materiais Cautelados por Militar</b>", styles['Heading1']))
        elements.append(Spacer(1, 12))

        for militar, itens in relatorio_ordenado:
            elements.append(Paragraph(f"<b>Responsável: {militar} ({len(itens)} itens pendentes)</b>", styles['Heading3']))
            
            data = [['Patrimônio', 'Descrição', 'Observação']]
            for item in itens:
                data.append([item["id"], Paragraph(item["desc"], styles['Normal']), Paragraph(item["obs"], styles['Normal'])])
            
            t = Table(data, colWidths=[80, 280, 170])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2d3748")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 10),
                ('TOPPADDING', (0,0), (-1,0), 10),
                ('BACKGROUND', (0,1), (-1,-1), colors.white),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf2f7")])
            ]))
            elements.append(t)
            elements.append(Spacer(1, 20))

        doc.build(elements)
        buffer.seek(0)
        
        headers = {"Content-Disposition": "inline; filename=relatorio_devedores.pdf"}
        return Response(content=buffer.getvalue(), media_type="application/pdf", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")

@app.get("/relatorios/materiais_por_local/pdf", tags=["Relatórios"])
def relatorio_materiais_local_pdf(db: Session = Depends(get_db)):
    try:
        materiais_lista = db.query(models.Material).filter(models.Material.ativo == True).all()
        relatorio = {}
        
        for mat in materiais_lista:
            if mat.tipo and "Consumo" in mat.tipo:
                continue

            local = mat.local
            if mat.tipo == "Ferramental" and (not local or local == "Estoque"):
                local = "Almox"
            elif not local:
                local = "Não Definido"
                
            if local not in relatorio:
                relatorio[local] = []
            
            status_texto = f"[{mat.situacao}]"
            if mat.situacao == "Em Uso" and mat.responsavel:
                status_texto += f"\n c/ {mat.responsavel}"
                
            relatorio[local].append({
                "id": mat.id_patrimonio,
                "desc": mat.descricao,
                "status": status_texto,
                "obs": mat.observacao or ""
            })
            
        relatorio_ordenado = sorted(relatorio.items())
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("<b>Relatório de Inventário por Local</b>", styles['Heading1']))
        elements.append(Spacer(1, 12))

        for local_nome, itens in relatorio_ordenado:
            elements.append(Paragraph(f"<b>Local: {local_nome} ({len(itens)} itens)</b>", styles['Heading3']))
            
            data = [['Patrimônio', 'Descrição', 'Status / Responsável', 'Observação (Sala exata)']]
            
            for item in itens:
                data.append([item["id"], Paragraph(item["desc"], styles['Normal']), Paragraph(item["status"], styles['Normal']), Paragraph(item["obs"], styles['Normal'])])
            
            t = Table(data, colWidths=[80, 380, 140, 180])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2d3748")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 10),
                ('TOPPADDING', (0,0), (-1,0), 10),
                ('BACKGROUND', (0,1), (-1,-1), colors.white),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf2f7")])
            ]))
            elements.append(t)
            elements.append(Spacer(1, 25))

        doc.build(elements)
        buffer.seek(0)
        
        headers = {"Content-Disposition": "inline; filename=inventario_local.pdf"}
        return Response(content=buffer.getvalue(), media_type="application/pdf", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")

@app.get("/relatorios/termo_cautela/{id_militar}/pdf", tags=["Relatórios"])
def gerar_termo_cautela_pdf(id_militar: int, db: Session = Depends(get_db)):
    try:
        militar = db.query(models.Militar).filter(models.Militar.id == id_militar).first()
        if not militar:
            raise HTTPException(status_code=404, detail="Militar não encontrado")

        nome_responsavel = f"{militar.posto_graduacao} {militar.nome_de_guerra}"
        materiais = db.query(models.Material).filter(
            models.Material.situacao == "Em Uso",
            models.Material.responsavel == nome_responsavel
        ).all()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(name='CenterTitle', parent=styles['Heading2'], alignment=TA_CENTER, fontName='Helvetica-Bold')

        logo_path = "capa_acolhida.png" 
        if os.path.exists(logo_path):
            img_reader = utils.ImageReader(logo_path)
            orig_w, orig_h = img_reader.getSize()

            target_width = 120
            aspect = orig_h / float(orig_w)
            target_height = target_width * aspect

            img = Image(logo_path, width=target_width, height=target_height)
            img.hAlign = 'CENTER' 
            
            elements.append(img)
            elements.append(Spacer(1, 1)) 

        elements.append(Paragraph("DEPÓSITO DO ALMOXARIFADO DA OPERAÇÃO ACOLHIDA", title_style))
        elements.append(Spacer(1, 5))
        elements.append(Paragraph("TERMO DE CAUTELA E RESPONSABILIDADE", title_style))
        elements.append(Spacer(1, 25))

        data = [['Material / Patrimônio', 'Data da Apanha', 'Operador (Sistema)', 'Militar Responsável']]

        for mat in materiais:
            mov = db.query(models.Movimentacao).filter(
                models.Movimentacao.id_patrimonio == mat.id_patrimonio,
                models.Movimentacao.tipo_movimentacao == "Cautela",
                models.Movimentacao.id_militar == militar.id
            ).order_by(models.Movimentacao.data_hora.desc()).first()

            data_apanha = mov.data_hora.strftime("%d/%m/%Y %H:%M") if mov and mov.data_hora else "N/D"
            operador = mov.usuario_logado if mov and mov.usuario_logado else "Sistema"

            desc_formatada = f"<b>{mat.id_patrimonio}</b><br/>{mat.descricao}"
            resp_formatado = f"{nome_responsavel}<br/>Tel: {militar.telefone}"

            data.append([
                Paragraph(desc_formatada, styles['Normal']),
                Paragraph(data_apanha, styles['Normal']),
                Paragraph(operador, styles['Normal']),
                Paragraph(resp_formatado, styles['Normal'])
            ])

        t = Table(data, colWidths=[180, 100, 110, 140])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")), 
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('TOPPADDING', (0,0), (-1,0), 10),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf2f7")])
        ]))

        elements.append(t)
        elements.append(Spacer(1, 60)) 

        assinatura_style = ParagraphStyle(name='Assinatura', parent=styles['Normal'], alignment=TA_CENTER)
        
        elements.append(Paragraph("__________________________________________________________", assinatura_style))
        elements.append(Spacer(1, 5))
        elements.append(Paragraph(f"<b>{militar.posto_graduacao} {militar.nome_completo}</b>", assinatura_style))
        elements.append(Paragraph(f"CPF: {militar.cpf}", assinatura_style))

        doc.build(elements)
        buffer.seek(0)

        headers = {"Content-Disposition": f'inline; filename="termo_cautela_{militar.nome_de_guerra}.pdf"'}
        return Response(content=buffer.getvalue(), media_type="application/pdf", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")

@app.get("/")
def read_root():
    return {"status": "online"}
