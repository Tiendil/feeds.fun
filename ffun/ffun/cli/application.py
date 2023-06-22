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
    "work"
]


system_3 = (
    "You are an expert on text analysis. "
    "For provided text, you determine topics and mentioned entities. "
    # "For provided text, you determine list of topics. "
    "You provide topics to describe text from different points of view. "
    # "You MUST provide at least 30 topics for each text. "
    "You MUST provide 100 topics for the text. "
    "All topics MUST be in English."
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
                        "number": {
                            "type": "integer",
                            "description": "number of the topic in the list"
                        },
                        "topic": {
                            "type": "string",
                            "description": "name of the topic"
                        },
                        "category": {
                            "type": "string",
                            "description": "category of the topic",
                            "enum": categories
                        },

                        # TODO: add something to transalte long topics into short ones

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

    from .p import text as text_6
    from .q import text as text_4
    from .r import text as text_7
    from .t import text as text_8
    from .w import text as text_5
    from .x import text as text_1
    from .y import text as text_2
    from .z import text as text_3

    oc.init(settings.openai_chat_35_processor.api_key)

    model = 'gpt-3.5-turbo-16k'
    total_tokens = 16 * 1024
    max_return_tokens = 2 * 1024

    system = system_3
    function = function_3
    text = text_8

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
