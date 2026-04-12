from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, Base, SessionLocal, get_db
from routes import movimentacoes, materiais, militares
import auth
import models

# Cria as tabelas no banco de dados automaticamente
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Controle de Material Carga", 
    description="Sistema de gestão de patrimônio, cautelas e auditoria",
    version="1.0"
)

# Configuração de CORS - Essencial para o frontend não ser bloqueado
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
    db.close()
# =================================================

# === ROTA DE RELATÓRIO DE DEVEDORES ===
@app.get("/relatorios/devedores", tags=["Relatórios"])
def listar_devedores(db: Session = Depends(get_db)):
    # Puxa todas as movimentações ordenadas da mais recente para a mais antiga
    movimentacoes = db.query(models.Movimentacao).order_by(models.Movimentacao.data_hora.desc()).all()
    
    devedores = []
    itens_processados = set()
    
    for mov in movimentacoes:
        # Pega apenas o registro mais recente de cada material
        if mov.id_patrimonio not in itens_processados:
            itens_processados.add(mov.id_patrimonio)
            
            # Verifica se a última movimentação foi uma Cautela
            # (Trata a variação do nome da coluna caso seja 'tipo' ou 'tipo_movimentacao')
            tipo_mov = getattr(mov, 'tipo', getattr(mov, 'tipo_movimentacao', ''))
            
            if tipo_mov == 'Cautela':
                material = db.query(models.Material).filter(models.Material.id_patrimonio == mov.id_patrimonio).first()
                militar = db.query(models.Militar).filter(models.Militar.id == mov.id_militar).first()
                
                if material and militar:
                    devedores.append({
                        "id_patrimonio": material.id_patrimonio,
                        "descricao": material.descricao,
                        "responsavel": f"{militar.posto_graduacao} {militar.nome_de_guerra}",
                        "data_cautela": mov.data_hora.isoformat() if mov.data_hora else None
                    })
                    
    return devedores
# =================================================

# Rota raiz simples para confirmar status
@app.get("/")
def read_root():
    return {
        "status": "online",
        "mensagem": "API de Controle de Material Operacional rodando perfeitamente",
        "dica": "Acesse /docs na URL para abrir o painel de testes interativo"
    }
