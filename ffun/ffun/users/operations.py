import uuid

import psycopg

from ffun.core import logging
from ffun.core.postgresql import execute
from ffun.users import errors
from ffun.users.entities import Service

logger = logging.get_module_logger()


async def add_mapping(service: Service, external_id: str) -> uuid.UUID:
    sql = """
        INSERT INTO u_mapping (service_id, external_id, internal_id)
        VALUES (%(service_id)s, %(external_id)s, %(internal_id)s)
    """

    internal_id = uuid.uuid4()

    try:
        await execute(sql, {"service_id": service, "external_id": external_id, "internal_id": internal_id})
    except psycopg.errors.UniqueViolation:
        return await get_mapping(service, external_id)

    return internal_id


async def get_mapping(service: Service, external_id: str) -> uuid.UUID:
    sql = """
        SELECT internal_id
        FROM u_mapping
        WHERE service_id = %(service_id)s
              AND external_id = %(external_id)s
    """

    result = await execute(sql, {"service_id": service, "external_id": external_id})

    if not result:
        raise errors.NoUserMappingFound(service=service, external_id=external_id)

    assert isinstance(result[0]["internal_id"], uuid.UUID)

    return result[0]["internal_id"]
