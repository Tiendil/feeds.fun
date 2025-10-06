from ffun.core import errors


class Error(errors.Error):
    pass


class NoRuleFound(Error):
    pass


class TagsIntersection(Error):
    pass


class AtLeastOneFilterMustBeDefined(Error):
    pass


class CircularTagReplacement(Error):
    pass


class RuleTagsIntersection(Error):
    pass
