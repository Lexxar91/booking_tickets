"""Интеграционные проверки BFF на изолированной БД с миграциями.

Задайте BFF_TEST_DATABASE_URL=postgresql+asyncpg://... для запуска.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.api.v1.bff import get_http_client
from src.core.database import get_async_session
from src.core.security import decode_token
from src.main import app
from src.models.browser_session import BrowserSession
from src.models.login_attempt import LoginAttempt
from src.models.refresh_token import RefreshToken
from src.models.user import User
from src.repositories.user_repo import UserRepository
from src.schemas.user import UserRegister
from src.services.browser_session_service import COOKIE_NAME


@dataclass
class BrowserHarness:
    """Хранит изолированные HTTP-клиент, БД и перехваченные запросы."""

    client: httpx.AsyncClient
    sessions: async_sessionmaker
    user_id: int
    email: str
    settings: SimpleNamespace
    forwarded: list[httpx.Request]

    async def login(self) -> httpx.Response:
        """Входит через BFF с синтетическими учетными данными."""
        response = await self.client.post(
            "/bff/auth/login", data={"username": self.email,
                                     "password": "Test-password-123"})
        assert response.status_code == 200, response.text
        return response

    async def row(self) -> BrowserSession:
        """Читает серверную запись для текущей cookie."""
        raw_id = self.client.cookies[COOKIE_NAME]
        async with self.sessions() as session:
            browser = await session.get(
                BrowserSession, sha256(raw_id.encode()).hexdigest())
            assert browser is not None
            return browser


@pytest.fixture
async def browser(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[BrowserHarness]:
    """Выдает реальную БД и BFF, подменяя только внешние HTTP-сервисы."""
    url = os.environ.get("BFF_TEST_DATABASE_URL")
    if not url:
        pytest.skip("BFF_TEST_DATABASE_URL is not set")
    config = SimpleNamespace(
        BFF_SESSION_KEY=SecretStr(Fernet.generate_key().decode()),
        BFF_ALLOWED_ORIGINS=["https://testserver"],
        REFRESH_TOKEN_EXPIRE_DAYS=30,
        EVENT_SERVICE_URL="http://events.internal",
        BOOKING_SERVICE_URL="http://bookings.internal",
    )
    monkeypatch.setattr("src.api.v1.bff.settings", config)
    monkeypatch.setattr(
        "src.services.browser_session_service.settings", config)
    engine = create_async_engine(url)
    sessions = async_sessionmaker(
        engine, expire_on_commit=False, autoflush=False)
    email = f"bff-{uuid4().hex}@example.com"
    async with sessions() as session:
        user = await UserRepository(session).create_user(UserRegister(
            email=email, password="Test-password-123"))
        await session.commit()
        user_id = user.id
    forwarded: list[httpx.Request] = []

    async def upstream(request: httpx.Request) -> httpx.Response:
        """Перехватывает HTTP без реального сетевого соединения."""
        forwarded.append(request)
        return httpx.Response(200, json={"ok": True})

    async def get_session() -> AsyncIterator:
        """Создает отдельную транзакцию для каждого HTTP-запроса."""
        async with sessions() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(upstream), follow_redirects=False,
        cookies={"upstream-cookie": "must-not-cross-sessions"},
    ) as upstream_client:
        app.dependency_overrides[get_async_session] = get_session
        app.dependency_overrides[get_http_client] = lambda: upstream_client
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app),
                base_url="https://testserver",
                headers={"Origin": "https://testserver"},
            ) as client:
                yield BrowserHarness(client, sessions, user_id, email,
                                     config, forwarded)
        finally:
            app.dependency_overrides.clear()
            async with sessions() as session:
                await session.execute(delete(User).where(User.id == user_id))
                await session.execute(delete(LoginAttempt).where(
                    LoginAttempt.bucket.endswith(email)))
                await session.commit()
            await engine.dispose()


async def test_login_stores_encrypted_tokens_and_secure_cookie(
    browser: BrowserHarness,
) -> None:
    """JWT зашифрованы в БД; браузер получает только cookie и профиль."""
    response = await browser.login()
    assert set(response.json()) == {"user", "csrf_token"}
    assert response.json()["user"]["id"] == browser.user_id
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text
    assert response.headers["cache-control"] == "no-store"
    cookie = response.headers["set-cookie"]
    flags = ("HttpOnly", "Secure", "SameSite=strict", "Path=/", "Max-Age=")
    for flag in flags:
        assert flag in cookie
    assert "Domain=" not in cookie
    raw_id = browser.client.cookies[COOKIE_NAME]
    row = await browser.row()
    assert row.id_hash == sha256(raw_id.encode()).hexdigest()
    assert raw_id != row.id_hash and len(raw_id) == 43
    key = browser.settings.BFF_SESSION_KEY.get_secret_value()
    cipher = Fernet(key.encode())
    for ciphertext in (row.access_token, row.refresh_token):
        plaintext = cipher.decrypt(ciphertext.encode()).decode()
        assert plaintext != ciphertext
        assert decode_token(plaintext).sub == str(browser.user_id)


async def test_new_browser_client_restores_session(
    browser: BrowserHarness,
) -> None:
    """Новый клиент восстанавливает вход только по cookie из PostgreSQL."""
    await browser.login()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="https://testserver",
        cookies=browser.client.cookies,
    ) as reloaded:
        response = await reloaded.get("/bff/auth/session")
    assert response.status_code == 200
    assert response.json()["user"]["email"] == browser.email
    assert "access_token" not in response.text


@pytest.mark.parametrize(("origin", "csrf"), [
    ("https://evil.example", "correct"),
    ("", "correct"),
    ("https://testserver", ""),
    ("https://testserver", "wrong"),
    ("https://testserver", "\xe9"),
])
async def test_mutations_require_origin_and_session_csrf(
    browser: BrowserHarness, origin: str, csrf: str,
) -> None:
    """Изменяющий запрос блокируется без правильных Origin и CSRF."""
    login = await browser.login()
    token = login.json()["csrf_token"] if csrf == "correct" else csrf
    response = await browser.client.post(
        "/bff/bookings/", json={"event_id": 1},
        headers=[(b"origin", origin.encode()),
                 (b"x-csrf-token", token.encode("latin-1"))],
    )
    assert response.status_code == 403
    assert browser.forwarded == []


async def test_login_rejects_cross_site_origin(
    browser: BrowserHarness,
) -> None:
    """Login CSRF отклоняется до проверки пароля и создания сессии."""
    response = await browser.client.post(
        "/bff/auth/login", headers={"Origin": "https://evil.example"},
        data={"username": browser.email, "password": "Test-password-123"},
    )
    assert response.status_code == 403
    assert COOKIE_NAME not in browser.client.cookies


async def test_forwarding_uses_server_token_without_client_credentials(
    browser: BrowserHarness,
) -> None:
    """Прокси подставляет JWT сервера, удаляя cookie и авторизацию клиента."""
    await browser.login()
    response = await browser.client.get(
        "/bff/bookings/my?limit=5", headers={"Authorization": "Bearer forged"})
    assert response.status_code == 200
    request = browser.forwarded[0]
    assert str(request.url) == (
        "http://bookings.internal/api/v1/bookings/my?limit=5")
    assert "cookie" not in request.headers
    assert "x-csrf-token" not in request.headers
    assert request.headers["authorization"] != "Bearer forged"
    assert decode_token(request.headers["authorization"][7:]).sub == str(
        browser.user_id)


async def test_concurrent_requests_rotate_refresh_once(
    browser: BrowserHarness,
) -> None:
    """Параллельные запросы под блокировкой создают одну новую пару JWT."""
    await browser.login()
    row = await browser.row()
    async with browser.sessions() as session:
        stored = await session.get(BrowserSession, row.id_hash)
        stored.access_expires_at = (
            datetime.now(timezone.utc) - timedelta(minutes=1))
        await session.commit()
    responses = await asyncio.wait_for(asyncio.gather(*[
        browser.client.get("/bff/bookings/my") for _ in range(3)
    ]), timeout=10)
    assert all(response.status_code == 200 for response in responses)
    async with browser.sessions() as session:
        tokens = list((await session.scalars(select(RefreshToken).where(
            RefreshToken.user_id == browser.user_id))).all())
    assert len(tokens) == 2
    assert sum(token.revoked_at is None for token in tokens) == 1
    assert (await browser.row()).refresh_token != row.refresh_token


async def test_logout_revokes_session_and_refresh(
    browser: BrowserHarness,
) -> None:
    """Выход отзывает токены и делает старую cookie недействительной."""
    login = await browser.login()
    raw_id = browser.client.cookies[COOKIE_NAME]
    response = await browser.client.post(
        "/bff/auth/logout",
        headers={"X-CSRF-Token": login.json()["csrf_token"]})
    assert response.status_code == 204
    assert COOKIE_NAME not in browser.client.cookies
    assert "Max-Age=0" in response.headers["set-cookie"]
    response = await browser.client.get(
        "/bff/auth/session", headers={"Cookie": f"{COOKIE_NAME}={raw_id}"})
    assert response.status_code == 401
    async with browser.sessions() as session:
        row = await session.get(
            BrowserSession, sha256(raw_id.encode()).hexdigest())
        assert row is None
        active = await session.scalar(select(func.count()).select_from(
            RefreshToken).where(RefreshToken.user_id == browser.user_id,
                                RefreshToken.revoked_at.is_(None)))
    assert active == 0


async def test_expired_session_rejected(browser: BrowserHarness) -> None:
    """Абсолютный срок сессии запрещает доступ даже при действующем JWT."""
    await browser.login()
    row = await browser.row()
    async with browser.sessions() as session:
        stored = await session.get(BrowserSession, row.id_hash)
        stored.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await session.commit()
    response = await browser.client.get("/bff/bookings/my")
    assert response.status_code == 401
    assert browser.forwarded == []


async def test_relogin_rotates_cookie(browser: BrowserHarness) -> None:
    """Повторный вход заменяет идентификатор и отзывает прежнюю сессию."""
    await browser.login()
    old_id = browser.client.cookies[COOKIE_NAME]
    await browser.login()
    assert browser.client.cookies[COOKIE_NAME] != old_id
    async with browser.sessions() as session:
        row = await session.get(
            BrowserSession, sha256(old_id.encode()).hexdigest())
        assert row is None


async def test_failed_login_persists_rate_limit(
    browser: BrowserHarness,
) -> None:
    """Ошибка входа фиксирует счетчик, как исходный JWT endpoint."""
    response = await browser.client.post(
        "/bff/auth/login",
        data={"username": browser.email, "password": "wrong"})
    assert response.status_code == 401
    async with browser.sessions() as session:
        attempt = await session.scalar(select(LoginAttempt).where(
            LoginAttempt.bucket.endswith(browser.email)))
    assert attempt is not None and attempt.failed_attempts == 1


async def test_public_catalog_and_path_allowlist(
    browser: BrowserHarness,
) -> None:
    """Каталог доступен без входа, произвольный адрес не проксируется."""
    response = await browser.client.get("/bff/events/")
    assert response.status_code == 200
    assert "authorization" not in browser.forwarded[0].headers
    browser.forwarded.clear()
    await browser.login()
    response = await browser.client.get("/bff/bookings/http://evil.example")
    assert response.status_code == 404
    assert browser.forwarded == []


async def test_explicit_refresh_and_booking_mutation(
    browser: BrowserHarness,
) -> None:
    """Refresh и создание брони обходятся без JWT в браузерном запросе."""
    login = await browser.login()
    csrf = {"X-CSRF-Token": login.json()["csrf_token"]}
    before = await browser.row()
    refreshed = await browser.client.post("/bff/auth/refresh", headers=csrf)
    assert refreshed.status_code == 200
    assert "refresh_token" not in refreshed.text
    assert (await browser.row()).refresh_token != before.refresh_token
    response = await browser.client.post(
        "/bff/bookings/", headers=csrf,
        json={"event_id": 1, "user_email": browser.email},
    )
    assert response.status_code == 200
    request = browser.forwarded[0]
    assert request.method == "POST"
    assert request.url.path == "/api/v1/bookings/"
    assert b'"event_id":1' in request.content
    assert "cookie" not in request.headers


async def test_proxy_rejects_upstream_redirect(
    browser: BrowserHarness,
) -> None:
    """Redirect сервиса не выводит браузер за пределы BFF."""
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(
            302, headers={"Location": "https://evil.example"}),
    )) as client:
        app.dependency_overrides[get_http_client] = lambda: client
        response = await browser.client.get("/bff/events/")
    assert response.status_code == 502
    assert "location" not in response.headers
