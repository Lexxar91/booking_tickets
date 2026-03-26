from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from src.core.security import decode_token

# OAuth2PasswordBearer указывает FastAPI где искать токен —
# в заголовке Authorization: Bearer <token>
# tokenUrl — только для Swagger UI чтобы знал куда отправлять логин
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8002/api/v1/auth/login")


async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """
    Dependency — извлекает user_id из JWT токена.

    Booking Service проверяет подпись токена сам — используя тот же SECRET_KEY
    что и Auth Service. 

    Raises:
        HTTPException 401: Если токен невалидный, протухший или неверного типа.
    """
    try:
        payload = decode_token(token)
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или протухший токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный тип токена",
            headers={"WWW-Authenticate": "Bearer"},
    )

    return int(payload.sub)
