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
    "work",
    "entity",
]


system_3 = (
    "You are an expert on text analysis. "
    # "For provided text, you determine topics and mentioned entities. "
    "For provided text, you describe mentioned entities. "
    # "For provided text, you determine topics. "
    # "For provided text, you determine topics and mentions. " ???
    "You describe text from professional point of view. "
    "You describe text in multiple levels of abstraction. "
    # "You provide entities without ambiguous meaning. "
    "Entity name must be explicitly undestandable without text context. "
    "You MUST provide 100 entities for the text. "
    "All entities MUST be in English."
    # TODO: ask to generate only in plural form
)


# ATTENTION: order of fields is important
function_3 = {
    "name": "register_topics",
    "description": "Saves entities of the text.",
    "parameters": {
        "type": "object",
        "properties": {
            # "topics": {
            #     "type": "array",
            #     "description": "list of topics",
            #     "items": {
            #         "type": "object",
            #         "properties": {
            #             "topic": {
            #                 "type": "string",
            #             },

            #             "category-1": {
            #                 "type": "string",
            #             },

            #             "category-2": {
            #                 "type": "string",
            #             },

            #             "category-3": {
            #                 "type": "string",
            #             },

            #             # "category": {
            #             #     "type": "string",
            #             # },

            #             # "sub-category": {
            #             #     "type": "string",
            #             # },
            #         }
            #     },
            # },

            "entities": {
                "type": "array",
                "description": "list of entities",
                "items": {
                    "type": "object",
                    "properties": {
                        "entity": {
                            "type": "string",
                        },

                        # TODO: add flag is-main-topic?

                        # "category-1": {
                        #     "type": "string",
                        # },

                        # "category-2": {
                        #     "type": "string",
                        # },

                        # "category-3": {
                        #     "type": "string",
                        # },

                        "category": {
                            "type": "string",
                        },

                        # "sub-category": {
                        #     "type": "string",
                        # },

                        "meta-category": {
                            "type": "string",
                        },

                        # "a-lot-of-related-categories": {
                        # "long-list-of-related-categories": {
                        "five-related-categories": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            }
                        },

                        # "full-name": {
                        #     "type": "string",
                        # },
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

    # TODO:
    # - text_2 — no distrupted technology
    # - topics vs entities
    # - text_4 "procedurally generating" -> "proecedurall generation" — "use full termins"?
    # - text_6 "kickstarter money" -> "kickstarter"

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

    # print(tabulate(results[0]['topics'], headers="keys"))

    print(tabulate(results[0]['entities'], headers="keys"))


@app.command()
def experiment() -> None:
    asyncio.run(run_experiment())
