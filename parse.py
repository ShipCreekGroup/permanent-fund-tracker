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
    total_amount_listed: int
    """The amount listed in the "Total" row of the table. Sometimes this isn't
    actually the same as if you sum up all the lineitems!, so we keep it separate.

    eg for
    
    | PORTFOLIO NAME                  | THURSDAY APRIL 24, 2025 |
    | ------------------------------- | ----------------------- |
    | Stocks                          | $26,432,400,000         |
    | Bonds                           | $15,826,300,000         |
    | Private Equity                  | $14,605,400,000         |
    | Real Estate                     | $9,315,200,000          |
    | Private Income and Infrastructure | $7,432,700,000          |
    | Absolute Return                 | $5,938,000,000          |
    | Tactical Opportunities          | $527,700,000            |
    | Cash                            | $1,168,700,000          |
    | **Total** | **$81,246,100,000** |
    
    It says the total amount is $81,246,100,000, but if you sum up the lineitems,
    you get $81,246,400,000
    """
    total_amount_from_lineitems: int
    """The amount you get if you sum up all the lineitems. This is not always
    the same as total_amount_listed, so we keep it separate.
    """
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
    return PFDValue(
        date=internal.date.date(),
        total_amount_listed=internal.total_amount,
        total_amount_from_lineitems=sum(amount for name, amount in lineitems),
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
