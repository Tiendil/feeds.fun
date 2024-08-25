from ffun.feeds_collections.collections import artificial_intelligence, gamedev, feeds_fun
from ffun.feeds_collections.entities import Collection

# temporary solution to fill feeds for a new user
#
# - engilish feeds only (for now)
# - no podcasts
# - no news aggregators
# - https-only
# - only alive
# - lists are highly subjective :-)

# TODO: define explicit rules
# TODO: for each source add short "why added" description and show it in UI

predefines = {
    Collection.feeds_fun: feeds_fun.collection,
    Collection.gamedev: gamedev.collection,
    Collection.artificial_intelligence: artificial_intelligence.collection,
}
