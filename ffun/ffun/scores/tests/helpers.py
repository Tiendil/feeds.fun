
import pytest

from ffun.core.tests.helpers import (
    TableSizeDelta,
    TableSizeNotChanged,
    assert_logs_has_business_event,
    assert_logs_has_no_business_event,
    capture_logs,
)

from ffun.core import utils
from ffun.domain.domain import new_rule_id, new_user_id
from ffun.domain.entities import TagId, UserId
from ffun.scores import domain, entities


def rule(score: int, required_tags: set[int], excluded_tags: set[int]) -> entities.Rule:
    return entities.Rule(
        id=new_rule_id(),
        user_id=new_user_id(),
        score=score,
        required_tags={TagId(t) for t in required_tags},
        excluded_tags={TagId(t) for t in excluded_tags},
        created_at=utils.now(),
        updated_at=utils.now(),
    )
