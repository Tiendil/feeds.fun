
from ffun.auth import supertokens
from ffun.users import entities as u_entities


async def remove_user_from_external_service(service: u_entities.Service, external_user_id: str) -> None:
    match service:
        case u_entities.Service.supertokens:
            await supertokens.remove_user(external_user_id)
        case u_entities.Service.single:
            # do nothing because we have no external service in this case
            pass
