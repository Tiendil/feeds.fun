from ffun.core import errors


class Error(errors.Error):
    pass


class MalformedOPML(Error):
    pass


class OPMLParsingError(MalformedOPML):
    pass


class OPMLNoRoot(MalformedOPML):
    pass


class OPMLNoBody(MalformedOPML):
    pass
