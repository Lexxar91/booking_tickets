"""
Unit-тесты для RefreshTokenRepository.

Проверяем:
- создание refresh-токена
- поиск активного токена
- отзыв токена
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from src.repositories.refresh_token_repo import RefreshTokenRepository


def _fake_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


class TestRefreshTokenRepository:
    async def test_create_token_persists_refresh_token(self, mock_session):
        repo = RefreshTokenRepository(mock_session)
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        token = await repo.create_token(user_id=7, jti="token-jti", expires_at=expires_at)

        mock_session.add.assert_called_once_with(token)
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(token)
        assert token.user_id == 7
        assert token.jti == "token-jti"
        assert token.expires_at == expires_at

    async def test_get_active_token_returns_token_when_found(self, mock_session, make_refresh_token):
        token = make_refresh_token(user_id=3, jti="active-jti")
        mock_session.execute.return_value = _fake_result(token)
        repo = RefreshTokenRepository(mock_session)

        result = await repo.get_active_token(
            user_id=3,
            jti="active-jti",
            now=datetime.now(timezone.utc),
        )

        assert result is token

    async def test_revoke_sets_revoked_at_and_flushes(self, mock_session, make_refresh_token):
        token = make_refresh_token()
        revoked_at = datetime.now(timezone.utc)
        repo = RefreshTokenRepository(mock_session)

        await repo.revoke(token, revoked_at=revoked_at)

        assert token.revoked_at == revoked_at
        mock_session.flush.assert_awaited_once()
