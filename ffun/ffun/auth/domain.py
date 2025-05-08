
from ffun.auth.supertokens import remove_supertokens_user
from ffun.users import entities as u_entities


# TODO: test
async def remove_user(service: u_entities.Service, user_id: str) -> None:
    match service:
        case u_entities.Service.supertokens:
            await remove_supertokens_user(user_id)
        case u_entities.Service.single:
            # do nothing because we have no external service in this case
            pass
