from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
import models

SECRET_KEY = "sua_chave_secreta_super_segura_aqui"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Função para checar a senha na hora do login
def verificar_senha(senha_plana, senha_hash):
    return pwd_context.verify(senha_plana, senha_hash)

# NOVA FUNÇÃO: Para gerar o hash na hora de criar o usuário
def obter_hash_senha(senha):
    return pwd_context.hash(senha)

def criar_token_jwt(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=8)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_usuario_atual(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: str = payload.get("sub")
        if usuario_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
        return {"id": usuario_id, "nome_usuario": payload.get("nome")}
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

# ROTAS DE AUTENTICAÇÃO
router = APIRouter(tags=["Autenticação"])

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Busca o usuário no banco
    usuario = db.query(models.Usuario).filter(models.Usuario.nome_usuario == form_data.username).first()
    
    # Se não achar o usuário ou a senha estiver errada
    if not usuario or not verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Se deu certo, gera o token JWT
    token_jwt = criar_token_jwt({"sub": str(usuario.id), "nome": usuario.nome_usuario})
    return {"access_token": token_jwt, "token_type": "bearer"}
