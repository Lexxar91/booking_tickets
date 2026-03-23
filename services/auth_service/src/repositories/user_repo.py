import email

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
 
from src.models.user import User
from src.schemas.user import UserRegister
from src.core.security import hash_password


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, user_data: UserRegister) -> User:
        """Создаём пользователя. Пароль хэшируем здесь — в БД попадает только хэш."""
        new_user = User(
            email = user_data.email,
            hashed_password = hash_password(user_data.password)
        )
        self.session.add(new_user)
        await self.session.flush()
        await self.session.refresh(new_user)
        return new_user
    
    async def get_user_by_id(self, user_id: int) -> User | None:
        """Ищем пользователя по ID — используется при проверке refresh токена."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> User | None:
        """Ищем пользователя по email — используется при логине."""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
