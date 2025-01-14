import functools
import time
from typing import Dict, Union

import requests

from discogs_alert import types as da_types


def conditions_satisfied(
    listing: da_types.Listing,
    release: da_types.Release,
    seller_filters: da_types.SellerFilters,
    record_filters: da_types.RecordFilters,
):
    """Validates that a given listing satisfies all conditions and filters, including both global filters
    (set via environment variables or via the CLI at runtime) and per-release filters (set in wantlist.json).

    Args:
        listing: the listing to validate
        release: the release object, defined by the user, corresponding to the given listing
        seller_filters: the global seller filters
        record_filters: the global record (media & sleeve condition) filters

    Returns: True if the given listing satisfies all conditions, False otherwise.
    """

    # verify seller conditions
    if (
        listing.seller_avg_rating is not None
        and seller_filters.min_seller_rating is not None
        and listing.seller_avg_rating < seller_filters.min_seller_rating
    ):
        return False
    if (
        seller_filters.min_seller_sales is not None
        and listing.seller_num_ratings is not None
        and listing.seller_num_ratings < seller_filters.min_seller_sales
    ):
        return False

    # verify media condition, either globally or for this specific release
    if listing.media_condition < (release.min_media_condition or record_filters.min_media_condition):
        return False

    # optionally verify all sleeve conditions, either globally or for this specific release
    # NB: we have to check all conditions before we know whether they're satisfied
    we_good = (listing.sleeve_condition == da_types.CONDITION.GENERIC) and (
        release.accept_generic_sleeve or record_filters.accept_generic_sleeve
    )
    we_good = we_good or (
        (listing.sleeve_condition == da_types.CONDITION.NO_COVER)
        and (release.accept_no_sleeve or record_filters.accept_no_sleeve)
    )
    we_good = we_good or (
        (listing.sleeve_condition == da_types.CONDITION.NOT_GRADED)
        and (release.accept_ungraded_sleeve and record_filters.accept_ungraded_sleeve)
    )
    we_good = we_good or (
        listing.sleeve_condition >= (release.min_sleeve_condition or record_filters.min_sleeve_condition)
    )

    return we_good


def time_cache(seconds: int, maxsize=None, typed=False):
    """Least-recently-used cache decorator with time-based cache invalidation.
    Inspired by https://stackoverflow.com/a/63674816/16592116

    Args:
        max_age: Time to live for cached results (in seconds).
        maxsize: Maximum cache size (see `functools.lru_cache`).
        typed: Cache on distinct input types (see `functools.lru_cache`).
    """

    def _decorator(fn):
        @functools.lru_cache(maxsize=maxsize, typed=typed)
        def _new(*args, __time_salt, **kwargs):
            return fn(*args, **kwargs)

        @functools.wraps(fn)
        def _wrapped(*args, **kwargs):
            return _new(*args, **kwargs, __time_salt=int(time.time() / seconds))

        return _wrapped

    return _decorator


@time_cache(seconds=3600)
def get_currency_rates(base_currency: str) -> Dict[str, float]:
    """Get live currency exchange rates (from one base currency). Cached for one hour at a time,
    per currency.

    Args:
        base_currency: one of the 3-character currency identifiers from above.

    Returns: a dict containing exchange rates _to_ all major currencies _from_ the given base currency
    """
    return requests.get(f"https://api.exchangerate.host/latest?base={base_currency}").json().get("rates")


def convert_currency(value: float, old_currency: str, new_currency: str) -> float:
    """Convert `value` from old_currency to new_currency

    Args:
        value: the value in the old currency
        old_currency: the existing currency
        new_currency: the currency to convert to

    Returns: value in the new currency.
    """

    rates = get_currency_rates(new_currency)
    return float(value) / rates.get(old_currency)


def convert_listing_price_currency(
    listing_price: da_types.ListingPrice, new_currency: str
) -> Union[da_types.ListingPrice, bool]:
    """Converts a `ListingPrice` object from its existing currency to another."""

    # convert listing price to new currency
    if listing_price.currency != new_currency:
        try:
            converted_price = convert_currency(listing_price.value, listing_price.currency, new_currency)
        except AttributeError:
            return False
        listing_price.currency = new_currency
        listing_price.value = converted_price

    # convert listing price shipping to new currency
    if listing_price.shipping is not None and listing_price.shipping.currency != new_currency:
        try:
            converted_shipping = convert_currency(
                listing_price.shipping.value, listing_price.shipping.currency, new_currency
            )
        except AttributeError:
            return False
        listing_price.shipping = da_types.Shipping(currency=new_currency, value=converted_shipping)

    return listing_price
