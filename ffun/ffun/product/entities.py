import enum


class UserSetting(enum.IntEnum):
    openai_api_key = 1

    # openai_max_tokens_in_month = 2  # noqa

    hide_message_about_setting_up_key = 3

    process_entries_not_older_than = 4

    # openai_allow_use_key_for_collections = 5  # noqa

    max_tokens_cost_in_month = 6

    gemini_api_key = 7
    test_api_key = 8

    hide_message_about_adding_collections = 9
    hide_message_check_your_feed_urls = 10

    view_news_filter_interval = 11
    view_news_filter_sort_by = 12
    view_news_filter_min_tags_count = 13
    view_news_filter_show_read = 14

    # view_feeds_show_feed_descriptions = 15  # noqa
    view_feeds_feed_order = 16
    view_feeds_failed_feeds_first = 17

    view_rules_order = 18

    show_sidebar = 19


class Resource(enum.IntEnum):
    # openai_tokens = 1  # noqa
    tokens_cost = 2
