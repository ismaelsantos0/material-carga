from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes import movimentacoes
# import routes.materiais, routes.militares (você criaria esses de forma similar)

# Cria as tabelas no banco de dados automaticamente
Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Controle de Material Carga")

# Permite que o Lovable (Frontend) comunique com a API sem bloqueios de segurança do navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # No futuro, coloque aqui a URL gerada pelo Lovable
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conecta as rotas
app.include_router(movimentacoes.router)

@app.get("/")
def read_root():
    return {"status": "API de Controle de Material Operacional"}
