
from ffun.domain.entities import AuthServiceId
from ffun.users import domain as u_domain
from ffun.users import entities as u_entities


async def remove_user_from_external_service(service: AuthServiceId, external_user_id: str) -> None:
    # TODO: implement user removal from external services
    raise NotImplementedError("This functionality is not implemented yet.")


async def logout_user_from_all_sessions_in_service(service: AuthServiceId, external_user_id: str) -> None:
    # TODO: implement user logout from all sessions in external services
    raise NotImplementedError("This functionality is not implemented yet.")


async def logout_user_from_all_sessions(user_id: u_entities.UserId) -> None:
    external_ids = await u_domain.get_user_external_ids(user_id)

    for service, external_id in external_ids.items():
        await logout_user_from_all_sessions_in_service(service, external_id)
