from typing import Any, AsyncGenerator, Dict, cast
from unittest.mock import MagicMock

import asynctest
import httpx
import pytest
from fastapi import FastAPI, Request, status

from fastapi_users.router import ErrorCode, get_register_router
from fastapi_users.user import get_create_user
from tests.conftest import User, UserCreate, UserDB

SECRET = "SECRET"
LIFETIME = 3600


def after_register_sync():
    return MagicMock(return_value=None)


def after_register_async():
    return asynctest.CoroutineMock(return_value=None)


@pytest.fixture(params=[after_register_sync, after_register_async])
def after_register(request):
    return request.param()


@pytest.fixture
@pytest.mark.asyncio
async def test_app_client(
    mock_user_db, after_register, get_test_client
) -> AsyncGenerator[httpx.AsyncClient, None]:
    create_user = get_create_user(mock_user_db, UserDB)
    register_router = get_register_router(
        create_user,
        User,
        UserCreate,
        after_register,
    )

    app = FastAPI()
    app.include_router(register_router)

    async for client in get_test_client(app):
        yield client


@pytest.mark.router
@pytest.mark.asyncio
class TestRegister:
    async def test_empty_body(self, test_app_client: httpx.AsyncClient, after_register):
        response = await test_app_client.post("/register", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert after_register.called is False

    async def test_missing_phone(
        self, test_app_client: httpx.AsyncClient, after_register
    ):
        json = {"password": "guinevere"}
        response = await test_app_client.post("/register", json=json)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert after_register.called is False

    async def test_missing_password(
        self, test_app_client: httpx.AsyncClient, after_register
    ):
        json = {"phone": "king.arthur@camelot.bt"}
        response = await test_app_client.post("/register", json=json)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert after_register.called is False

    async def test_wrong_phone(
        self, test_app_client: httpx.AsyncClient, after_register
    ):
        json = {"phone": "king.arthur", "password": "guinevere"}
        response = await test_app_client.post("/register", json=json)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert after_register.called is False

    @pytest.mark.parametrize(
        "phone", ["king.arthur@camelot.bt", "King.Arthur@camelot.bt"]
    )
    async def test_existing_user(
        self, phone, test_app_client: httpx.AsyncClient, after_register
    ):
        json = {"phone": phone, "password": "guinevere"}
        response = await test_app_client.post("/register", json=json)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = cast(Dict[str, Any], response.json())
        assert data["detail"] == ErrorCode.REGISTER_USER_ALREADY_EXISTS
        assert after_register.called is False

    @pytest.mark.parametrize("phone", ["lancelot@camelot.bt", "Lancelot@camelot.bt"])
    async def test_valid_body(
        self, phone, test_app_client: httpx.AsyncClient, after_register
    ):
        json = {"phone": phone, "password": "guinevere"}
        response = await test_app_client.post("/register", json=json)
        assert response.status_code == status.HTTP_201_CREATED
        assert after_register.called is True

        data = cast(Dict[str, Any], response.json())
        assert "hashed_password" not in data
        assert "password" not in data
        assert data["id"] is not None

        actual_user = after_register.call_args[0][0]
        assert str(actual_user.id) == data["id"]
        assert str(actual_user.phone) == phone
        request = after_register.call_args[0][1]
        assert isinstance(request, Request)

    async def test_valid_body_is_superuser(
        self, test_app_client: httpx.AsyncClient, after_register
    ):
        json = {
            "phone": "lancelot@camelot.bt",
            "password": "guinevere",
            "is_superuser": True,
        }
        response = await test_app_client.post("/register", json=json)
        assert response.status_code == status.HTTP_201_CREATED
        assert after_register.called is True

        data = cast(Dict[str, Any], response.json())
        assert data["is_superuser"] is False

    async def test_valid_body_is_active(
        self, test_app_client: httpx.AsyncClient, after_register
    ):
        json = {
            "phone": "lancelot@camelot.bt",
            "password": "guinevere",
            "is_active": False,
        }
        response = await test_app_client.post("/register", json=json)
        assert response.status_code == status.HTTP_201_CREATED
        assert after_register.called is True

        data = cast(Dict[str, Any], response.json())
        assert data["is_active"] is True
