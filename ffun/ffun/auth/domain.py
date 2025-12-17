import datetime

from ffun.auth import errors
from ffun.auth.settings import settings as auth_settings
from ffun.domain.entities import IdPId
from ffun.users import domain as u_domain
from ffun.users import entities as u_entities


async def remove_user_from_external_service(service: IdPId, external_user_id: str) -> None:
    idp = auth_settings.get_idp_by_internal_id(service)

    if idp is None:
        raise errors.NoIdPFound()

    await idp.plugin.remove_user(external_user_id)


async def logout_user_from_all_sessions_in_service(service: IdPId, external_user_id: str) -> None:
    idp = auth_settings.get_idp_by_internal_id(service)

    if idp is None:
        raise errors.NoIdPFound()

    await idp.plugin.revoke_all_user_sessions(external_user_id)


async def logout_user_from_all_sessions(user_id: u_entities.UserId) -> None:
    external_ids = await u_domain.get_user_external_ids(user_id)

    for service, external_id in external_ids.items():
        await logout_user_from_all_sessions_in_service(service, external_id)


async def import_user_to_external_service(
    service: IdPId, external_user_id: str, email: str, created_at: datetime.datetime, verify_internal_user_exists: bool
) -> None:

    idp = auth_settings.get_idp_by_internal_id(service)

    if idp is None:
        raise errors.NoIdPFound()

    if verify_internal_user_exists:
        if not await u_domain.check_external_user_exists(service, external_user_id):
            raise errors.InternalUserDoesNotExistForImportedUser()

    await idp.plugin.import_user(external_user_id, email, created_at)
