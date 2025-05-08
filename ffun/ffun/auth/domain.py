from ffun.auth import supertokens
from ffun.users import domain as u_domain
from ffun.users import entities as u_entities


async def remove_user_from_external_service(service: u_entities.Service, external_user_id: str) -> None:
    match service:
        case u_entities.Service.supertokens:
            await supertokens.remove_user(external_user_id)
        case u_entities.Service.single:
            # do nothing because we have no external service in this case
            pass


async def logout_user_from_all_sessions_in_service(service: u_entities.Service, external_user_id: str) -> None:
    match service:
        case u_entities.Service.supertokens:
            await supertokens.logout_user_from_all_sessions(external_user_id)
        case u_entities.Service.single:
            # do nothing because user is always logged in in this case
            pass


async def logout_user_from_all_sessions(user_id: u_entities.UserId) -> None:
    external_ids = await u_domain.get_user_external_ids(user_id)

    for service, external_id in external_ids.items():
        await logout_user_from_all_sessions_in_service(service, external_id)
