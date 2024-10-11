from ffun.core import errors


class Error(errors.Error):
    pass


class DuplicateCollectionIds(Error):
    pass


class CollectionNotFound(Error):
    pass


class DuplicateCollectionOrders(Error):
    pass


class CollectionIsEmpty(Error):
    pass


class FeedNotFound(Error):
    pass
