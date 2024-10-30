import psycopg

from ffun.core import logging
from ffun.core.postgresql import execute
from ffun.domain.domain import new_user_id
from ffun.domain.entities import UserId
from ffun.users import errors
from ffun.users.entities import Service

logger = logging.get_module_logger()


async def add_mapping(service: Service, external_id: str) -> UserId:
    sql = """
        INSERT INTO u_mapping (service_id, external_id, internal_id)
        VALUES (%(service_id)s, %(external_id)s, %(internal_id)s)
    """

    internal_id = new_user_id()

    try:
        await execute(sql, {"service_id": service, "external_id": external_id, "internal_id": internal_id})

        logger.business_event("user_created", user_id=internal_id)

    except psycopg.errors.UniqueViolation:
        return await get_mapping(service, external_id)

    return internal_id


async def get_mapping(service: Service, external_id: str) -> UserId:
    sql = """
        SELECT internal_id
        FROM u_mapping
        WHERE service_id = %(service_id)s
              AND external_id = %(external_id)s
    """

    result = await execute(sql, {"service_id": service, "external_id": external_id})

    if not result:
        raise errors.NoUserMappingFound(service=service, external_id=external_id)

    return result[0]["internal_id"]  # type: ignore
