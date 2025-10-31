

class Plugin:
    __slots__ = ()

    async def remove_user(self, external_user_id: str) -> None:
        raise NotImplementedError()

    async def revoke_all_user_sessions(self, external_user_id: str) -> None:
        raise NotImplementedError()
