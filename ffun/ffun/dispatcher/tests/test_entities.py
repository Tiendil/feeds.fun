import datetime

from ffun.dispatcher.entities import EntryAuthorization
from ffun.domain.domain import new_entry_id, new_user_id
from ffun.resources.entities import ResourceReservation


class TestEntryAuthorization:
    def test_dispatch_allowed__globally_visible(self) -> None:
        authorization = EntryAuthorization(
            entry_id=new_entry_id(),
            globally_visible=True,
            reservations=(),
        )

        assert authorization.dispatch_allowed

    def test_dispatch_allowed__resource_reserved(self) -> None:
        reservation = ResourceReservation(
            user_id=new_user_id(),
            kind=1,
            interval_started_at=datetime.datetime.now(tz=datetime.UTC),
            amount=1,
        )
        authorization = EntryAuthorization(
            entry_id=new_entry_id(),
            globally_visible=False,
            reservations=(reservation,),
        )

        assert authorization.dispatch_allowed

    def test_dispatch_allowed__not_authorized(self) -> None:
        authorization = EntryAuthorization(
            entry_id=new_entry_id(),
            globally_visible=False,
            reservations=(),
        )

        assert not authorization.dispatch_allowed
