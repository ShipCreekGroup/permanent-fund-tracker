# /// script
# requires-python = "==3.14.*"
# dependencies = [
#     "fire==0.7.1",
#     "llm==0.35",
#     "llm-gemini==0.34",
#     "pydantic==2.13.5",
# ]
# ///
import datetime
import os
import re
import sys
from pathlib import Path

import fire
import llm
import pydantic


class _LineItem(pydantic.BaseModel):
    name: str
    amount: int


class _PFDValueInternal(pydantic.BaseModel):
    """The schema sent to the LLM.

    PFDValue can't be used directly: pydantic describes `list[tuple[str, int]]`
    with the JSON Schema keyword `prefixItems`, which llm-gemini passes to
    Gemini's `response_schema`, and that rejects it.
    """

    date: datetime.date
    total_amount: int
    lineitems: list[_LineItem]


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


class ValidationError(ValueError):
    pass


# APFC sometimes leaves the page un-updated for a few days (lags of 6 days
# have been observed), so allow some slack before calling a date wrong.
MAX_DATE_LAG = datetime.timedelta(days=14)


def dollar_amounts_in(html: str) -> set[int]:
    """Every dollar amount in the HTML, with punctuation ignored.

    APFC's page has typos like "$1,643.000,000", so compare digits only.
    Some versions of the page put a non-breaking space after the "$".
    """
    matches = re.findall(r"\$(?:\s|&nbsp;)*(\d[\d,.]*)", html)
    return {int(re.sub(r"\D", "", m)) for m in matches}


def validate(val: PFDValue, html: str, scraped_at: datetime.datetime) -> None:
    """Sanity-check LLM output, since the LLM occasionally makes things up.

    eg it once returned the date "0805-08-05" for a page that said
    "Tuesday August 5, 2025".

    This deliberately does not require the lineitems to sum to the total:
    APFC's own numbers sometimes don't add up, and PFDValue records both.
    """
    lag = scraped_at.date() - val.date
    if not (datetime.timedelta(0) <= lag <= MAX_DATE_LAG):
        raise ValidationError(
            f"date {val.date} is not within {MAX_DATE_LAG.days} days before the scrape time {scraped_at}"
        )
    amounts_in_html = dollar_amounts_in(html)
    for name, amount in [("total", val.total_amount_listed), *val.lineitems]:
        if amount not in amounts_in_html:
            raise ValidationError(f"amount for {name!r} (${amount:,}) does not appear in the HTML")


# Tried in order. Gemini models return "This model is currently experiencing
# high demand" errors during demand spikes, and each model has its own
# capacity, so a busy model is skipped in favor of the next one.
MODEL_IDS = [
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
    "gemini-3.1-pro-preview",
]


def prompt_with_fallback(prompt: str, schema: type[pydantic.BaseModel]) -> str:
    """Return the text of the first model in MODEL_IDS that responds without an error."""
    errors: list[str] = []
    for model_id in MODEL_IDS:
        model = llm.get_model(model_id)
        try:
            return model.prompt(prompt, schema=schema).text()
        except llm.ModelError as e:
            print(f"{model_id} failed, trying the next model: {e}", file=sys.stderr)
            errors.append(f"{model_id}: {e}")
    raise llm.ModelError("All models failed:\n" + "\n".join(errors))


def parse(html: str) -> PFDValue:
    prompt = f"""
    Get the breakdown of the current (daily updated) value of the PFD portfolio from the following HTML:
    {html}
    """
    text = prompt_with_fallback(prompt, _PFDValueInternal)
    internal = _PFDValueInternal.model_validate_json(text)
    lineitems = [(item.name, item.amount) for item in internal.lineitems]
    return PFDValue(
        date=internal.date,
        total_amount_listed=internal.total_amount,
        total_amount_from_lineitems=sum(amount for name, amount in lineitems),
        lineitems=lineitems,
    )


def default_scraped_at(path: str | None) -> datetime.datetime:
    """Files in htmls/ are named by their UTC scrape time; anything else was scraped now."""
    if path is not None:
        try:
            return datetime.datetime.fromisoformat(Path(path).stem)
        except ValueError:
            pass
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def cli(path: str | None = None, scraped_at: str | None = None) -> None:
    r"""
    Usage:
        LLM_GEMINI_KEY=... uv run parse.py htmls/2025-04-25T00\:20\:01.html
        or
        curl https://apfc.org/performance | LLM_GEMINI_KEY=... uv run parse.py

    scraped_at is the UTC time the HTML was fetched, eg 2025-04-25T00:20:01.
    It defaults to the filename's timestamp if there is one, otherwise now.
    Exits with an error if the parsed values fail validation.
    """
    if "LLM_GEMINI_KEY" not in os.environ:
        raise ValueError("LLM_GEMINI_KEY not set")
    html = get_html(path)
    val = parse(html)
    if scraped_at is None:
        scraped_at_dt = default_scraped_at(path)
    else:
        scraped_at_dt = datetime.datetime.fromisoformat(scraped_at)
    validate(val, html, scraped_at_dt)
    print(val.model_dump_json(indent=2))


if __name__ == "__main__":
    fire.Fire(cli)
