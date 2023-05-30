from ffun.core import errors


class Error(errors.Error):
    pass


class CanNotAccessPostgreSQL(Error):
    pass
