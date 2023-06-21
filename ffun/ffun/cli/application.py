import asyncio

import typer
from ffun.application.application import with_app
from tabulate import tabulate

app = typer.Typer()


categories = [
    # "topic",
    # "meta-topic",
    # "high-level-topic",
    # "low-level-topic",
    # "related-topic",
    # "indirect-topic",
    # "mention",
    # "indirect-mention",
    "concept",
    "person",
    "organization",
    "location",
    "event",
    "date",
    "movie",
    "game",
    "software",
    "book",
    "phenomenon",
    "industry",
    "activity",
    "genre",
]


system = [
    "You are an expert on the analysis of text semantics.",
    "For provided text, you determine a list of best tags to describe the text.",
    "For each category, you provide 30 tags.",
    "Categories are topics, meta-topics, high-level-topics, low-level-topics, related-topics, indirect-topics, mentions, indirect-mentions.",
    "Tags are only in English. Normalize tags and output them as JSON.",
]

system_2 = (
    "You are an expert on the analysis of text semantics. "
    "For provided text, you determine a list of best tags to describe the text. "
    "You provide tags to describe text from different points of view. "
    "For each category, you provide at least 30 tags. "
    "Tags are only in English."
)


system_3 = (
    "You are an expert on text semantics. "
    # "You are an expert in text semantics. "
    # "You are an expert librarian. "
    # "You classify text for a library. "
    # "You are a moderator of Wikipedia. "
    # "You a professor. "
    # "You have a PhD. "
    # "For provided text, you determine a list of it's topics and mentioned entities. "
    "For provided text, you determine topics and mentioned entities. "
    # "For provided text, you determine list of topics. "
    "You provide topics to describe text from different points of view. "
    # " Output only in English."
    "All topics must be in English."
)



tags = {
    "type": "array",
    "description": "list of tags",
    "items": {
        "type": "string",
        "description": "name of the tag"
    }
}


function_2 = {
    "name": "register_tags_for_text",
    "description": "Saves detected tags in the database.",
    "parameters": {
        "type": "object",
        "description": "tags per category",
        "properties": {category: tags for category in categories}
    }
}


function_3 = {
    "name": "register_topics",
    "description": "Saves detected topics in the database.",
    "parameters": {
        "type": "object",
        "properties": {
            "topics": {
                "type": "array",
                "description": "list of topics",
                "items": {
                    "type": "object",
                    "description": "topic",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "name of the topic"
                        },
                        "category": {
                            "type": "string",
                            "description": "category of the topic",
                            "enum": categories
                        },

                        "meta-topic-level-1": {
                            "type": "string",
                            "description": "level 1 meta-topic of the topic"
                        },

                        "meta-topic-level-2": {
                            "type": "string",
                            "description": "level 2 meta-topic of the topic"
                        }
                    }
                }
            }
        }
    }
}


async def run_experiment() -> None:
    import pprint

    from ffun.librarian import openai_client as oc
    from ffun.librarian.settings import settings

    from .q import text as text_4
    from .x import text as text_1
    from .y import text as text_2
    from .z import text as text_3

    oc.init(settings.openai_chat_35_processor.api_key)

    model = 'gpt-3.5-turbo-16k'
    total_tokens = 16 * 1024
    max_return_tokens = 2 * 1024

    system = system_3
    function = function_3
    text = text_4

    # print(function)

    # TODO: add tokens from function
    messages = await oc.prepare_requests(system=system,
                                         text=text,
                                         model=model,
                                         total_tokens=total_tokens,
                                         max_return_tokens=max_return_tokens)

    results = await oc.multiple_requests(model=model,
                                         messages=messages,
                                         function=function,
                                         max_return_tokens=max_return_tokens)

    # pprint.pprint(results[0])

    print(tabulate(results[0]['topics'], headers="keys"))


@app.command()
def experiment() -> None:
    asyncio.run(run_experiment())
