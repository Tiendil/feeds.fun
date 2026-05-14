from ffun.domain.urls import str_to_absolute_url
from ffun.library.entities import Reference, ReferenceKind
from ffun.library.utils import merge_references_list


class TestMergeReferencesList:
    def test_skips_none_values(self) -> None:
        reference = Reference(
            kind=ReferenceKind.page,
            url=str_to_absolute_url("https://example.com/page"),
        )

        assert merge_references_list([None, reference, None]) == [reference]

    def test_merges_references_by_url_and_keeps_highest_priority_kind(self) -> None:
        page_reference = Reference(
            kind=ReferenceKind.page,
            url=str_to_absolute_url("https://example.com/media"),
            title="Page",
        )
        video_reference = Reference(
            kind=ReferenceKind.video,
            url=str_to_absolute_url("https://example.com/media"),
            mime_type="video/mp4",
        )

        assert merge_references_list([page_reference, video_reference]) == [
            Reference(
                kind=ReferenceKind.video,
                url=str_to_absolute_url("https://example.com/media"),
                title="Page",
                mime_type="video/mp4",
            )
        ]

    def test_sorts_by_url(self) -> None:
        second_reference = Reference(
            kind=ReferenceKind.page,
            url=str_to_absolute_url("https://example.com/b"),
        )
        first_reference = Reference(
            kind=ReferenceKind.page,
            url=str_to_absolute_url("https://example.com/a"),
        )

        assert merge_references_list([second_reference, first_reference]) == [first_reference, second_reference]

    def test_merges_complex_reference_set(self) -> None:
        # Group A: three references merge into an author reference and fill metadata from lower-priority entries.
        first_page = Reference(
            kind=ReferenceKind.page,
            url=str_to_absolute_url("https://example.com/a"),
            title="Page A",
        )
        first_document = Reference(
            kind=ReferenceKind.document,
            url=str_to_absolute_url("https://example.com/a"),
            mime_type="application/pdf",
        )
        first_author = Reference(
            kind=ReferenceKind.author,
            url=str_to_absolute_url("https://example.com/a"),
            extra={"source": "profile"},
        )

        # Group B: three references with equal high-priority media kinds keep the first high-priority kind.
        second_unknown = Reference(
            kind=ReferenceKind.unknown,
            url=str_to_absolute_url("https://example.com/b"),
            title="Unknown B",
        )
        second_video = Reference(
            kind=ReferenceKind.video,
            url=str_to_absolute_url("https://example.com/b"),
            width=640,
        )
        second_image = Reference(
            kind=ReferenceKind.image,
            url=str_to_absolute_url("https://example.com/b"),
            height=360,
        )

        # Group C: two references merge into comments while keeping the comments title.
        third_page = Reference(
            kind=ReferenceKind.page,
            url=str_to_absolute_url("https://example.com/c"),
            title="Page C",
        )
        third_comments = Reference(
            kind=ReferenceKind.comments,
            url=str_to_absolute_url("https://example.com/c"),
            title="Comments C",
        )

        # These references have unique URLs and must survive unchanged.
        standalone_audio = Reference(
            kind=ReferenceKind.audio,
            url=str_to_absolute_url("https://example.com/d"),
        )
        standalone_image = Reference(
            kind=ReferenceKind.image,
            url=str_to_absolute_url("https://example.com/e"),
        )

        # The input is intentionally unsorted and includes None values between merge groups.
        assert merge_references_list(
            [
                second_unknown,
                None,
                standalone_image,
                first_page,
                second_video,
                third_page,
                first_document,
                standalone_audio,
                second_image,
                None,
                third_comments,
                first_author,
            ]
        ) == [
            # Output is sorted by URL after each URL group has been merged.
            Reference(
                kind=ReferenceKind.author,
                url=str_to_absolute_url("https://example.com/a"),
                title="Page A",
                mime_type="application/pdf",
                extra={"source": "profile"},
            ),
            Reference(
                kind=ReferenceKind.video,
                url=str_to_absolute_url("https://example.com/b"),
                title="Unknown B",
                width=640,
                height=360,
            ),
            Reference(
                kind=ReferenceKind.comments,
                url=str_to_absolute_url("https://example.com/c"),
                title="Comments C",
            ),
            standalone_audio,
            standalone_image,
        ]
