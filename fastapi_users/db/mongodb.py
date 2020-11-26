from typing import Optional, Type

from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import UUID4
from pymongo.collation import Collation

from fastapi_users.db.base import BaseUserDatabase
from fastapi_users.models import UD


class MongoDBUserDatabase(BaseUserDatabase[UD]):
    """
    Database adapter for MongoDB.

    :param user_db_model: Pydantic model of a DB representation of a user.
    :param collection: Collection instance from `motor`.
    """

    collection: AsyncIOMotorCollection
    phone_collation: Collation

    def __init__(
        self,
        user_db_model: Type[UD],
        collection: AsyncIOMotorCollection,
        phone_collation: Optional[Collation] = None,
    ):
        super().__init__(user_db_model)
        self.collection = collection
        self.collection.create_index("id", unique=True)
        self.collection.create_index("phone", unique=True)

        if phone_collation:
            self.phone_collation = phone_collation  # pragma: no cover
        else:
            self.phone_collation = Collation("en", strength=2)

        self.collection.create_index(
            "phone",
            name="phone_number_index",
            collation=self.phone_collation,
        )

    async def get(self, id: UUID4) -> Optional[UD]:
        user = await self.collection.find_one({"id": id})
        return self.user_db_model(**user) if user else None

    async def get_by_phone(self, phone: str) -> Optional[UD]:
        user = await self.collection.find_one(
            {"phone": phone}, collation=self.phone_collation
        )
        return self.user_db_model(**user) if user else None

    async def get_by_oauth_account(self, oauth: str, account_id: str) -> Optional[UD]:
        user = await self.collection.find_one(
            {
                "oauth_accounts.oauth_name": oauth,
                "oauth_accounts.account_id": account_id,
            }
        )
        return self.user_db_model(**user) if user else None

    async def create(self, user: UD) -> UD:
        await self.collection.insert_one(user.dict())
        return user

    async def update(self, user: UD) -> UD:
        await self.collection.replace_one({"id": user.id}, user.dict())
        return user

    async def delete(self, user: UD) -> None:
        await self.collection.delete_one({"id": user.id})
