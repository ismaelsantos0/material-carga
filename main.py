from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, Base, SessionLocal, get_db
from routes import movimentacoes, materiais, militares
import auth
import models

# Cria as tabelas no banco de dados automaticamente (apenas as tabelas novas, não atualiza colunas)
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

# Conectando todas as rotas (Os módulos do seu sistema)
app.include_router(auth.router)
app.include_router(materiais.router)
app.include_router(militares.router)
app.include_router(movimentacoes.router)

# === A MÁGICA DE CRIAR O ADMIN AUTOMATICAMENTE ===
@app.on_event("startup")
def criar_admin_padrao():
    db = SessionLocal()
    try:
        # Verifica se o admin já existe
        admin_existe = db.query(models.Usuario).filter(models.Usuario.nome_usuario == "admin").first()
        
        if not admin_existe:
            novo_admin = models.Usuario(
                nome_usuario="admin",
                senha_hash=auth.obter_hash_senha("admin123"), # Criptografa a senha "admin123"
                regra="Admin"
            )
            db.add(novo_admin)
            db.commit()
            print("Usuário 'admin' criado com sucesso!")
    finally:
        db.close() # Garante que a conexão feche certinho
# =================================================

# === RELATÓRIO 1: DEVEDORES GERAL (Histórico) ===
@app.get("/relatorios/devedores", tags=["Relatórios"])
def listar_devedores(db: Session = Depends(get_db)):
    try:
        movimentacoes = db.query(models.Movimentacao).order_by(models.Movimentacao.data_hora.desc()).all()
        
        devedores = []
        itens_processados = set()
        
        for mov in movimentacoes:
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
                            "data_cautela": data_segura
                        })
                        
        return devedores

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno no Python: {str(e)}")

# === RELATÓRIO 2: DEVEDORES POR MILITAR (Agrupado) ===
@app.get("/relatorios/devedores_por_militar", tags=["Relatórios"])
def relatorio_devedores_militar(db: Session = Depends(get_db)):
    try:
        # Puxa apenas os materiais que estão 'Em Uso'
        materiais_em_uso = db.query(models.Material).filter(models.Material.situacao == "Em Uso").all()
        
        relatorio = {}
        for mat in materiais_em_uso:
            resp = mat.responsavel or "Militar Desconhecido"
            
            if resp not in relatorio:
                relatorio[resp] = []
                
            relatorio[resp].append({
                "id_patrimonio": mat.id_patrimonio,
                "descricao": mat.descricao,
                "tipo": mat.tipo
            })
            
        # Converte o dicionário numa lista amigável para o frontend
        resultado = [{"militar": k, "materiais": v, "total_itens": len(v)} for k, v in relatorio.items()]
        
        # Ordena alfabeticamente pelo nome do militar
        return sorted(resultado, key=lambda x: x["militar"])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# === RELATÓRIO 3: INVENTÁRIO POR LOCAL (Agrupado) ===
@app.get("/relatorios/materiais_por_local", tags=["Relatórios"])
def relatorio_materiais_local(db: Session = Depends(get_db)):
    try:
        # Puxa todos os materiais ativos
        materiais = db.query(models.Material).filter(models.Material.ativo == True).all()
        
        relatorio = {}
        for mat in materiais:
            local = mat.local
            
            # Regra: Se for ferramental e o local estiver vazio ou for "Estoque", assume "Almox"
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
                "tipo": mat.tipo
            })
            
        # Converte o dicionário numa lista amigável para o frontend
        resultado = [{"local": k, "materiais": v, "total_itens": len(v)} for k, v in relatorio.items()]
        
        # Ordena alfabeticamente pelo nome do local
        return sorted(resultado, key=lambda x: x["local"])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
# =================================================

# Rota raiz simples para confirmar status
@app.get("/")
def read_root():
    return {
        "status": "online",
        "mensagem": "API de Controle de Material Operacional rodando perfeitamente",
        "dica": "Acesse /docs na URL para abrir o painel de testes interativo"
    }
