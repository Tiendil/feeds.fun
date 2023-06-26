import asyncio

import typer
from ffun.application.application import with_app
from tabulate import tabulate

app = typer.Typer()


system_3 = (
    "You are an expert on text analysis. "
    "For provided text, you describe mentioned topics. "
    "You describe text from professional point of view. "
    "You describe text in multiple levels of abstraction. "
    "Topic name must be explicitly undestandable without text context. "
    "You MUST provide 100 topics for the text. "
    "All topics MUST be in English."
)


# ATTENTION: order of fields is important
function_3 = {
    "name": "register_topics",
    "description": "Saves topics of the text.",
    "parameters": {
        "type": "object",
        "properties": {

            "topics": {
                "type": "array",
                "description": "list of topics",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                        },

                        "category": {
                            "type": "string",
                        },

                        "meta-category": {
                            "type": "string",
                        },

                        "five-related-categories": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            }
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
    max_return_tokens = 4 * 1024

    system = system_3
    function = function_3
    text = text_8

    # TODO:
    # - text_3 — no "emacs" tag
    # - text_4 — Dungeons & Dragons Players Handbook -> Dungeons & Dragons
    # - text_6 "kickstarter money" -> "kickstarter"
    # - text_8 Binding of Isaac style -> Binding of Isaac

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

    print(tabulate(results[0]['topics'], headers="keys"))


@app.command()
def experiment() -> None:
    asyncio.run(run_experiment())
