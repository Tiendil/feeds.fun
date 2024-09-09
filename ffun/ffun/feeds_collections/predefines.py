from ffun.feeds_collections.collections import artificial_intelligence, feeds_fun, gamedev
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

# TODO: uncomment
predefines = {
    Collection.feeds_fun: set(), #feeds_fun.collection,
    Collection.gamedev: set(), #gamedev.collection,
    Collection.artificial_intelligence: set(), #artificial_intelligence.collection,
}
