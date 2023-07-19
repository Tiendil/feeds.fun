from .predefines import predefines


def get_collections():
    return predefines.keys()


def get_feeds_for_collecton(collection):
    return predefines[collection]
