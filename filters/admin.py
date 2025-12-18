from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from typing import Union
from core.database import data_manager


class AdminFilter(Filter):
    async def __call__(
        self,
        event: Union[Message, CallbackQuery]
    ) -> bool:
        user_id = event.from_user.id
        return data_manager.is_admin(user_id)