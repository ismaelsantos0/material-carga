from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = "sua_chave_secreta_super_segura_aqui"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def verificar_senha(senha_plana, senha_hash):
    return pwd_context.verify(senha_plana, senha_hash)

def criar_token_jwt(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=8) # Token dura 8 horas
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_usuario_atual(token: str = Depends(oauth2_scheme)):
    # Aqui o sistema descobre se quem está logado é o Admin, o Cb Henrique, etc.
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: str = payload.get("sub")
        if usuario_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
        return {"id": usuario_id, "nome_usuario": payload.get("nome")}
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
