
import fastapi
from ffun.feeds import domain as f_domain

from . import entities

router = fastapi.APIRouter()


@router.post('/api/get-feeds')
async def api_get_feeds(request: entities.GetFeedsRequest) -> entities.GetFeedsResponse:
    feeds = await f_domain.get_all_feeds()

    return entities.GetFeedsResponse(feeds=[entities.Feed.parse_obj(feed) for feed in feeds])
