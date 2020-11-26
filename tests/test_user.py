import pytest

from fastapi_users.user import CreateUserProtocol, UserAlreadyExists, get_create_user
from tests.conftest import UserCreate, UserDB


@pytest.fixture
def create_user(
    mock_user_db,
) -> CreateUserProtocol:
    return get_create_user(mock_user_db, UserDB)


@pytest.mark.router
@pytest.mark.asyncio
class TestCreateUser:
    @pytest.mark.parametrize(
        "phone", ["king.arthur@camelot.bt", "King.Arthur@camelot.bt"]
    )
    async def test_existing_user(self, phone, create_user):
        user = UserCreate(phone=phone, password="guinevere")
        with pytest.raises(UserAlreadyExists):
            await create_user(user)

    @pytest.mark.parametrize("phone", ["lancelot@camelot.bt", "Lancelot@camelot.bt"])
    async def test_regular_user(self, phone, create_user):
        user = UserCreate(phone=phone, password="guinevere")
        created_user = await create_user(user)
        assert type(created_user) == UserDB

    @pytest.mark.parametrize("safe,result", [(True, False), (False, True)])
    async def test_superuser(self, create_user, safe, result):
        user = UserCreate(
            phone="lancelot@camelot.b", password="guinevere", is_superuser=True
        )
        created_user = await create_user(user, safe)
        assert type(created_user) == UserDB
        assert created_user.is_superuser is result

    @pytest.mark.parametrize("safe,result", [(True, True), (False, False)])
    async def test_is_active(self, create_user, safe, result):
        user = UserCreate(
            phone="lancelot@camelot.b", password="guinevere", is_active=False
        )
        created_user = await create_user(user, safe)
        assert type(created_user) == UserDB
        assert created_user.is_active is result
