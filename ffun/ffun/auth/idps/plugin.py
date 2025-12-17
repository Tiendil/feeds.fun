import datetime


class Plugin:
    __slots__ = ()

    async def remove_user(self, external_user_id: str) -> None:
        pass

    async def revoke_all_user_sessions(self, external_user_id: str) -> None:
        pass

    async def import_user(self, external_user_id: str, email: str, created_at: datetime.datetime) -> None:
        pass
