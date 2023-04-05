
import logging
import uuid
from typing import Iterable

import psycopg
from bidict import bidict
from ffun.core.postgresql import execute

logger = logging.getLogger(__name__)


async def get_tags_mappig() -> bidict[str, int]:
    sql = 'SELECT id, name FROM o_tags'
    rows = await execute(sql)
    return bidict.bidict({row['name']: row['id'] for row in rows})


async def get_id_by_tag(tag: str) -> int|None:
    sql = 'SELECT id FROM o_tags WHERE name = %(tag)s'
    rows = await execute(sql, {'tag': tag})

    if not rows:
        return None

    return rows[0]['id']


async def register_tag(tag: str) -> int:
    sql = '''
    INSERT INTO o_tags (name)
    VALUES (%(tag)s)
    ON CONFLICT (name) DO NOTHING
    RETURNING id'''

    rows = await execute(sql, {'tag': tag})

    if not rows:
        tag_id = await get_id_by_tag(tag)

        assert tag_id is not None

        return tag_id

    return rows[0]['id']


async def get_or_create_id_by_tag(tag: str) -> int:
    tag_id = await get_id_by_tag(tag)

    if tag_id is not None:
        return tag_id

    return await register_tag(tag)


async def get_tags_by_ids(tags_ids: list[int]) -> dict[int, str]:
    sql = 'SELECT name FROM o_tags WHERE id = ANY(%(tags_ids)s)'
    rows = await execute(sql, {'tags_ids': tags_ids})
    return {row['id']: row['name'] for row in rows}


async def apply_tags(entry_id: uuid.UUID, tags_ids: Iterable[int]) -> None:
    sql = '''
    INSERT INTO o_relations (entry_id, tag_id)
    VALUES (%(entry_id)s, %(tag_id)s)
    ON CONFLICT (entry_id, tag_id) DO NOTHING'''

    for tag_id in tags_ids:
        await execute(sql, {'entry_id': entry_id, 'tag_id': tag_id})
