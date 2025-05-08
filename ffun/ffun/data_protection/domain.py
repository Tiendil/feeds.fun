from ffun.auth import domain as a_domain
from ffun.core import logging
from ffun.domain.entities import UserId
from ffun.users import domain as u_domain

logger = logging.get_module_logger()


async def remove_user(user_id: UserId) -> None:
    auth_services_ids = await u_domain.get_user_external_ids(user_id)

    if not auth_services_ids:
        return

    for service_id, external_id in auth_services_ids.items():
        await u_domain.unlink_user(service_id, user_id)
        await a_domain.remove_user_from_external_service(service_id, external_id)

    logger.business_event("user_removed", user_id=user_id)
