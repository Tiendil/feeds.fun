import asyncio

import typer
from ffun.application.application import with_app

app = typer.Typer()


system = [
    "You are an expert on the analysis of text semantics.",
    "For provided text, you determine a list of best tags to describe the text.",
    "For each category, you provide 30 tags.",
    "Categories are topics, meta-topics, high-level-topics, low-level-topics, related-topics, indirect-topics, mentions, indirect-mentions.",
    "Tags are only in English. Normalize tags and output them as JSON.",
]

system_2 = [
    "You are an expert on the analysis of text semantics.",
    "For provided text, you determine a list of best tags to describe the text.",
    "You provide tags to describe text from different points of view.",
    "For each category, you provide at least 30 tags.",
    "Tags are only in English.",
]


system_3 = [
    "You are an expert on text semantics.",
    "For provided text, you determine a list of it's topics and mentioned entities.",
    # "For each category, you provide at least 3 items.",
    "You provide topics for each category.",
    "Output only in English.",
]



tags = {
    "type": "array",
    "description": "list of tags",
    "items": {
        "type": "string",
        "description": "name of the tag"
    }
}


categories = [
    "topics",
    "meta-topics",
    "high-level-topics",
    "low-level-topics",
    "related-topics",
    "indirect-topics",
    "mentions",
    "indirect-mentions",
    "persons",
    "organizations",
    "locations",
    "events",
    "dates",
    "movies",
    "games",
    "software",
    "books",
]


# JSON Schema
function_1 = {
    "name": "register_tags_for_text",
    "description": "Saves detected tags in the database.",
    "parameters": {
        "type": "object",
        "description": "parameters of the function",
        "properties": {
            "tags": {
                "type": "object",
                "description": "tags by category",
                "properties": {category: tags for category in categories}
            },
            "explanation": {
                "type": "string",
                "description": "your comment"
            }
        }
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

    from .x import text as text_1
    from .y import text as text_2

    oc.init(settings.openai_chat_35_processor.api_key)

    model = 'gpt-3.5-turbo-16k'
    total_tokens = 16 * 1024
    max_return_tokens = 2 * 1024

    system = system_3
    function = function_3
    text = text_2

    print(function)

    # TODO: add tokens from function
    messages = await oc.prepare_requests(system='\n'.join(system),
                                         text=text,
                                         model=model,
                                         total_tokens=total_tokens,
                                         max_return_tokens=max_return_tokens)

    results = await oc.multiple_requests(model=model,
                                         messages=messages,
                                         function=function,
                                         max_return_tokens=max_return_tokens)

    pprint.pprint(results[0])


@app.command()
def experiment() -> None:
    asyncio.run(run_experiment())
