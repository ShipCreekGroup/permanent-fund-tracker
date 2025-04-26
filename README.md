# AK Permanent Fund Scraper

We want to be able to see the historical trend of the
[Alaska Permanent Fund](https://en.wikipedia.org/wiki/Alaska_Permanent_Fund).
The current value is published daily at https://apfc.org/performance/,
but we haven't found a way to get daily values from the past.
The only historical data we can find is monthly summaries.
This doesn't have the needed granularity to capture some
rapid fluctuations, like are happening now, in April 2025.

We first store the raw HTML (about 206kb per page as of april 2025)
in the `htmls/` folder. This is so we have the raw source of truth
and can re-compute derived metrics later as needed.
We also run the HTML through an LLM to get structured data out,
that is stored in the `jsons/` folder.
We do this scraping twice a day through github actions.

The idea for this technique of "Git Scraping" comes from
[Simon Wilson](https://simonwillison.net/series/git-scraping/).