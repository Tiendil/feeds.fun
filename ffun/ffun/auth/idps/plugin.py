

class Plugin:
    __slots__ = ()

    async def remove_user(self, external_user_id: str) -> None:
        raise NotImplementedError()

    async def logout_user_from_all_sessions(self, external_user_id: str) -> None:
        raise NotImplementedError()
