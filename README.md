# AK Permanent Fund Scraper

We want to be able to see the historical trend of the
Alaska Permanent Fund.
The current value is published daily at https://apfc.org/performance/,
but we haven't found a way to get daily values from past dates.
The only historical data we can find is monthly summaries.
This doesn't have the needed granularity to capture some
rapid fluctuations, like are happening now, in April 2025.

At this point, we are only storing the raw html from every day.
At some later point, perhaps we can run some more processing over it
to get it to an easier format.

The idea for this technique of "Git Scraping" comes from
[Simon Wilson](https://simonwillison.net/series/git-scraping/).