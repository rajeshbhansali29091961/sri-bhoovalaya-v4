import requests
from datetime import datetime, timedelta


YAHOO_CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/"
)


def _to_date(timestamp):
    return datetime.fromtimestamp(
        int(timestamp)
    ).date()


def get_stock_history(
    symbol,
    period_days=30,
):
    """
    Download historical daily OHLC data from
    Yahoo Finance Chart API.

    No yfinance.
    No pandas.
    No numpy.

    Returns:

        [
            {
                "date": date,
                "open": float,
                "high": float,
                "low": float,
                "close": float,
                "volume": int,
            }
        ]
    """

    symbol = symbol.strip().upper()

    if not symbol:
        raise ValueError(
            "Stock symbol is empty."
        )

    # Add some extra calendar days because
    # weekends and holidays are not trading days.
    calendar_days = max(
        int(period_days * 1.7),
        30,
    )

    end_date = datetime.utcnow()

    start_date = (
        end_date
        - timedelta(
            days=calendar_days
        )
    )

    period1 = int(
        start_date.timestamp()
    )

    period2 = int(
        end_date.timestamp()
    )

    url = (
        YAHOO_CHART_URL
        + symbol
    )

    params = {
        "period1": period1,
        "period2": period2,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }

    headers = {
        "User-Agent":
            "Mozilla/5.0 "
            "(Android; Mobile) "
            "AppleWebKit/537.36 "
            "Chrome/120 Safari/537.36"
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=20,
    )

    response.raise_for_status()

    payload = response.json()

    chart = payload.get(
        "chart",
        {},
    )

    error = chart.get(
        "error"
    )

    if error:
        description = error.get(
            "description",
            "Yahoo Finance error",
        )

        raise RuntimeError(
            description
        )

    results = chart.get(
        "result"
    )

    if not results:
        raise RuntimeError(
            "No Yahoo Finance result returned."
        )

    result = results[0]

    timestamps = result.get(
        "timestamp",
        [],
    )

    quote_list = result.get(
        "indicators",
        {},
    ).get(
        "quote",
        [],
    )

    if not quote_list:
        raise RuntimeError(
            "No quote data returned."
        )

    quote = quote_list[0]

    opens = quote.get(
        "open",
        [],
    )

    highs = quote.get(
        "high",
        [],
    )

    lows = quote.get(
        "low",
        [],
    )

    closes = quote.get(
        "close",
        [],
    )

    volumes = quote.get(
        "volume",
        [],
    )

    data = []

    for i, timestamp in enumerate(
        timestamps
    ):

        if i >= len(closes):
            continue

        close = closes[i]

        if close is None:
            continue

        open_value = (
            opens[i]
            if i < len(opens)
            else None
        )

        high_value = (
            highs[i]
            if i < len(highs)
            else None
        )

        low_value = (
            lows[i]
            if i < len(lows)
            else None
        )

        volume_value = (
            volumes[i]
            if i < len(volumes)
            else 0
        )

        if open_value is None:
            open_value = close

        if high_value is None:
            high_value = close

        if low_value is None:
            low_value = close

        if volume_value is None:
            volume_value = 0

        data.append(
            {
                "date": _to_date(
                    timestamp
                ),
                "open": float(
                    open_value
                ),
                "high": float(
                    high_value
                ),
                "low": float(
                    low_value
                ),
                "close": float(
                    close
                ),
                "volume": int(
                    volume_value
                ),
            }
        )

    # Keep chronological order.
    data.sort(
        key=lambda x: x["date"]
    )

    # Return the requested number of
    # trading sessions.
    if len(data) > period_days:
        data = data[
            -period_days:
        ]

    return data


def get_last_close(symbol):
    """
    Convenience function.
    """

    data = get_stock_history(
        symbol,
        period_days=5,
    )

    if not data:
        return None

    return data[-1]["close"]


if __name__ == "__main__":

    # Simple desktop test.
    symbol = "RELIANCE.NS"

    try:
        data = get_stock_history(
            symbol,
            period_days=20,
        )

        print(
            f"Downloaded {len(data)} sessions."
        )

        for row in data:
            print(
                row["date"],
                row["close"],
            )

    except Exception as ex:

        print(
            "ERROR:",
            type(ex).__name__,
            ex,
        )
