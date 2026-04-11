from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from routes import movimentacoes, materiais, militares
import auth
import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Controle de Material Carga")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conecta a nova rota de login
app.include_router(auth.router)

# Rotas do sistema
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

@app.get("/")
def read_root():
    return {"status": "online", "mensagem": "API Rodando com Login e Admin configurados!"}
