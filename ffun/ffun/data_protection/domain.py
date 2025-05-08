
from ffun.domain.entities import UserId

from ffun.auth import domain as a_domain
from ffun.users import domain as u_domain


# TODO: test
async def remove_user(user_id: UserId) -> None:
    auth_services_ids = await u_domain.get_user_external_ids(user_id)

    for service_id, external_id in auth_services_ids.items():
        await u_domain.unlink_user(service_id, user_id)
        await a_domain.remove_user(service_id, external_id)
