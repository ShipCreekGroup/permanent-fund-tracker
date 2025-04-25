# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fire",
#     "llm",
#     "llm-gemini",
#     "pydantic",
# ]
# ///
import datetime
import json
import os
import sys
from pathlib import Path

import fire
import llm
import pydantic


class _PFDValueInternal(pydantic.BaseModel):
    date: datetime.datetime
    total_amount: int
    # We need this indirection because apparently either gemini or the LLM python
    # lib can't handle a `list[tuple[str, int]]` type hint directly.
    lineitem_json: str = pydantic.Field(
        # This is needed so that this is sent in the jsonschema to the LLM
        # so that it respects the format.
        description="""The lineitems in a format such as '{"Equity": 10000, "Fixed Income", 250000}'""",
    )


class PFDValue(pydantic.BaseModel):
    date: datetime.date
    total_amount: int
    lineitems: list[tuple[str, int]]


def get_html(path: str | None = None) -> str:
    if path is None:
        # read from stdin
        if sys.stdin.isatty():
            raise ValueError("No path provided and stdin is not a pipe")
        return sys.stdin.read()
    return Path(path).read_text()


def parse(html: str) -> PFDValue:
    model = llm.get_model("gemini-2.0-flash")
    prompt = f"""
    Get the breakdown of the current (daily updated) value of the PFD portfolio from the following HTML:
    {html}
    """
    response = model.prompt(prompt, schema=_PFDValueInternal)
    text = response.text()
    internal = _PFDValueInternal.model_validate_json(text)
    lineitem_dict = json.loads(internal.lineitem_json)
    lineitems = [(k, v) for k, v in lineitem_dict.items()]
    amounts = [v for k, v in lineitems]
    expected_total = sum(amounts)
    if expected_total != internal.total_amount:
        raise ValueError(
            f"Total amount {expected_total} from lineitems {lineitems} does not match total {internal.total_amount} that the LLM returned"
        )
    return PFDValue(
        date=internal.date.date(),
        total_amount=internal.total_amount,
        lineitems=lineitems,
    )


def cli(path: str | None = None) -> None:
    """
    Usage:
        LLM_GEMINI_KEY=... uv run parse.py htmls/2025-04-25T00\:20\:01.html
        or
        curl https://apfc.org/performance | LLM_GEMINI_KEY=... uv run parse.py
    """
    if "LLM_GEMINI_KEY" not in os.environ:
        raise ValueError("LLM_GEMINI_KEY not set")
    html = get_html(path)
    val = parse(html)
    print(val.model_dump_json(indent=2))


if __name__ == "__main__":
    fire.Fire(cli)
