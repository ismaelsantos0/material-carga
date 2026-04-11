from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes import movimentacoes, materiais, militares

# Cria as tabelas no banco de dados automaticamente
# (Muito útil agora no início ou quando conectar o PostgreSQL no Railway)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Controle de Material Carga", 
    description="Sistema de gestão de patrimônio, cautelas e auditoria",
    version="1.0"
)

# Configuração de CORS - Essencial para o frontend não ser bloqueado
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # No futuro, substitua o "*" pela URL exata gerada pelo Lovable
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conectando todas as rotas (Os módulos do seu sistema)
app.include_router(materiais.router)
app.include_router(militares.router)
app.include_router(movimentacoes.router)

# Rota raiz simples para você confirmar que o servidor ligou no Railway
@app.get("/")
def read_root():
    return {
        "status": "online",
        "mensagem": "API de Controle de Material Operacional rodando perfeitamente",
        "dica": "Acesse /docs na URL para abrir o painel de testes interativo"
    }
