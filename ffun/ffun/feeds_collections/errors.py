from ffun.core import errors


class Error(errors.Error):
    pass


class DuplicateCollectionIds(Error):
    pass


class CollectionNotFound(Error):
    pass
