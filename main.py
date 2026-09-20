import flet as ft

from bhoovalaya_engine import (
    analyze_stock,
    BANDHAS,
)
from market_data import get_stock_history, update_stock_history, get_cache_csv_path


APP_TITLE = "Sri Bhoovalaya V5"


def direction_icon(direction):
    if direction == "UP":
        return "↑"
    if direction == "DOWN":
        return "↓"
    return "—"


def hit_icon(value):
    return "✓ HIT" if value else "✗ MISS"


# ============================================================
# TABLE
# ============================================================

def make_table(rows, columns):

    table = ft.DataTable(
        columns=[
            ft.DataColumn(
                ft.Text(
                    c,
                    weight=ft.FontWeight.BOLD
                )
            )
            for c in columns
        ],
        rows=[],
    )

    for row in rows:

        table.rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(
                        ft.Text(
                            str(
                                row.get(c, "")
                            )
                        )
                    )
                    for c in columns
                ]
            )
        )

    return table


# ============================================================
# ACCURACY GRAPH
#
# Native Flet controls.
# No flet-charts required.
# ============================================================

def make_accuracy_graph(
    accuracy,
    selected_bandha,
):

    controls = []

    controls.append(
        ft.Text(
            "BANDHA ACCURACY GRAPH",
            size=20,
            weight=ft.FontWeight.BOLD,
        )
    )

    controls.append(
        ft.Text(
            "Accuracy percentage from the historical backtest",
            size=13,
        )
    )

    for name in BANDHAS:

        value = float(
            accuracy[name]["accuracy"]
        )

        hits = accuracy[name]["hits"]
        tests = accuracy[name]["tests"]

        # Width of bar.
        # Maximum 360 pixels.
        bar_width = max(
            4,
            min(
                360,
                value * 3.6
            )
        )

        # Make selected Bandha more prominent.
        if name == selected_bandha:
            bar_height = 30
            text_size = 16
            weight = ft.FontWeight.BOLD
        else:
            bar_height = 22
            text_size = 13
            weight = ft.FontWeight.NORMAL

        bar = ft.Container(
            width=bar_width,
            height=bar_height,
            bgcolor=(
                ft.Colors.BLUE_700
                if name == selected_bandha
                else ft.Colors.BLUE_300
            ),
            border_radius=5,
        )

        controls.append(
            ft.Row(
                [
                    ft.Container(
                        content=ft.Text(
                            name,
                            size=text_size,
                            weight=weight,
                        ),
                        width=90,
                    ),

                    ft.Container(
                        content=bar,
                        width=370,
                    ),

                    ft.Text(
                        f"{value:.1f}%",
                        size=text_size,
                        weight=weight,
                    ),

                    ft.Text(
                        f"({hits}/{tests})",
                        size=12,
                    ),
                ],
                spacing=5,
            )
        )

    return ft.Container(
        content=ft.Column(
            controls,
            spacing=8,
        ),
        padding=10,
        border=ft.Border.all(
            1,
            ft.Colors.GREY_400,
        ),
        border_radius=8,
    )


# ============================================================
# SELECTED BANDHA SUMMARY
# ============================================================

def make_selected_summary(
    result,
    selected_bandha,
):

    accuracy = result["accuracy"][
        selected_bandha
    ]

    reference = result["bandhas"][
        selected_bandha
    ]

    return ft.Container(

        content=ft.Column(
            [
                ft.Text(
                    f"SELECTED BANDHA: "
                    f"{selected_bandha}",
                    size=21,
                    weight=ft.FontWeight.BOLD,
                ),

                ft.Text(
                    f"Accuracy: "
                    f"{accuracy['accuracy']:.1f}%",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),

                ft.Text(
                    f"Hits: {accuracy['hits']}    "
                    f"Tests: {accuracy['tests']}    "
                    f"Misses: {accuracy['misses']}",
                    size=15,
                ),

                ft.Text(
                    "Reference-day prediction: "
                    f"{direction_icon(reference['signal'])}",
                    size=16,
                ),
            ],
            spacing=5,
        ),

        padding=12,

        border=ft.Border.all(
            1,
            ft.Colors.GREY_400,
        ),

        border_radius=8,
    )


# ============================================================
# SIMPLE PRICE GRAPH
#
# Uses native Flet containers.
# This is deliberately simple and Android-safe.
# ============================================================

def make_price_graph(
    backtest,
    selected_bandha,
):

    if not backtest:

        return ft.Text(
            "No price data available."
        )

    values = []

    for item in backtest:

        try:
            values.append(
                float(item["close"])
            )
        except Exception:
            pass

    if not values:

        return ft.Text(
            "No numeric price data."
        )

    minimum = min(values)
    maximum = max(values)

    if maximum == minimum:
        maximum = minimum + 1

    graph_height = 220
    graph_width = 700

    # Only show last 30 points if
    # very large test is selected.
    display = backtest[-30:]

    bars = []

    for item in display:

        try:
            price = float(
                item["close"]
            )
        except Exception:
            continue

        ratio = (
            price - minimum
        ) / (
            maximum - minimum
        )

        height = max(
            5,
            ratio * graph_height
        )

        bars.append(
            ft.Column(
                [
                    ft.Text(
                        f"{price:.0f}",
                        size=8,
                    ),

                    ft.Container(
                        width=10,
                        height=height,
                        bgcolor=(
                            ft.Colors.GREEN_500
                            if item[
                                selected_bandha
                            ] == item[
                                "actual"
                            ]
                            else ft.Colors.RED_400
                        ),
                        border_radius=3,
                    ),

                    ft.Text(
                        str(
                            item["date"]
                        )[-5:],
                        size=8,
                    ),
                ],
                alignment=ft.MainAxisAlignment.END,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    return ft.Container(

        content=ft.Column(
            [
                ft.Text(
                    f"PRICE / BACKTEST GRAPH — "
                    f"{selected_bandha}",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),

                ft.Text(
                    "Green = selected Bandha matched "
                    "the next trading-day direction; "
                    "Red = MISS",
                    size=12,
                ),

                ft.Container(
                    content=ft.Row(
                        bars,
                        spacing=8,
                        scroll=ft.ScrollMode.AUTO,
                        vertical_alignment=(
                            ft.CrossAxisAlignment.END
                        ),
                    ),
                    height=300,
                    width=graph_width,
                ),
            ],
            spacing=5,
        ),

        padding=10,

        border=ft.Border.all(
            1,
            ft.Colors.GREY_400,
        ),

        border_radius=8,
    )


# ============================================================
# SELECTED BANDHA DETAILS
# ============================================================

def build_selected_bandha_section(
    result,
    selected_bandha,
):

    controls = []

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    controls.append(
        make_selected_summary(
            result,
            selected_bandha,
        )
    )

    # --------------------------------------------------------
    # ACCURACY GRAPH
    # --------------------------------------------------------

    controls.append(
        make_accuracy_graph(
            result["accuracy"],
            selected_bandha,
        )
    )

    # --------------------------------------------------------
    # PRICE GRAPH
    # --------------------------------------------------------

    controls.append(
        make_price_graph(
            result["backtest"],
            selected_bandha,
        )
    )

    # --------------------------------------------------------
    # SELECTED BANDHA BACKTEST
    # --------------------------------------------------------

    controls.append(
        ft.Text(
            f"{selected_bandha} — "
            "DAY N → NEXT DAY",
            size=19,
            weight=ft.FontWeight.BOLD,
        )
    )

    rows = []

    for item in result["backtest"]:

        signal = item[
            selected_bandha
        ]

        actual = item[
            "actual"
        ]

        rows.append(
            {
                "Date": item["date"],
                "Close": item["close"],
                "Actual": direction_icon(
                    actual
                ),
                "Signal": direction_icon(
                    signal
                ),
                "Result": hit_icon(
                    signal == actual
                ),
            }
        )

    controls.append(
        ft.Row(
            [
                make_table(
                    rows,
                    [
                        "Date",
                        "Close",
                        "Actual",
                        "Signal",
                        "Result",
                    ],
                )
            ],
            scroll=ft.ScrollMode.AUTO,
        )
    )

    # --------------------------------------------------------
    # NEXT 9 DAYS
    # --------------------------------------------------------

    controls.append(
        ft.Text(
            f"NEXT 9 EXPERIMENTAL SIGNALS — "
            f"{selected_bandha}",
            size=19,
            weight=ft.FontWeight.BOLD,
        )
    )

    future_rows = []

    for item in result["future"]:

        future_rows.append(
            {
                "Date": item["date"],
                "Prediction": direction_icon(
                    item[
                        selected_bandha
                    ]
                ),
            }
        )

    controls.append(
        make_table(
            future_rows,
            [
                "Date",
                "Prediction",
            ],
        )
    )

    return controls


# ============================================================
# MAIN
# ============================================================

def main(page: ft.Page):

    page.title = APP_TITLE

    page.padding = 10

    page.scroll = ft.ScrollMode.AUTO

    # ========================================================
    # INPUTS
    # ========================================================

    symbol = ft.TextField(
        label="NSE Symbol",
        value="RELIANCE.NS",
        width=260,
    )

    hindi_name = ft.TextField(
        label="Hindi Stock Name",
        value="रिलायंस",
        width=260,
    )

    days_field = ft.TextField(
        label="Test days",
        value="60",
        width=150,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    selected_bandha = ft.Dropdown(
        label="Select Bandha",
        width=230,
        value="Saras",
        options=[
            ft.DropdownOption(
                key=name,
                text=name,
            )
            for name in BANDHAS
        ],
    )

    status = ft.Text(
        "Ready"
    )

    summary = ft.Text(
        "",
        size=14,
        selectable=True,
    )

    result_column = ft.Column(
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
    )

    # Latest result
    state = {
        "result": None
    }

    # ========================================================
    # SELECTED BANDHA AREA
    # ========================================================

    selected_section = ft.Column(
        spacing=10
    )

    # ========================================================
    # BANDHA CHANGE
    # ========================================================

    def bandha_changed(e):

        result = state["result"]

        if result is None:
            return

        name = selected_bandha.value

        if name not in BANDHAS:
            return

        # THIS IS THE IMPORTANT FIX.
        #
        # Rebuild the entire selected Bandha
        # section every time dropdown changes.

        selected_section.controls.clear()

        selected_section.controls.extend(
            build_selected_bandha_section(
                result,
                name,
            )
        )

        page.update()

    selected_bandha.on_select = (
        bandha_changed
    )

    # ========================================================
    # UPDATE NSE MARKET DATA
    # ========================================================

    def update_market_data(e):

        try:
            sym = symbol.value.strip().upper()

            if not sym:
                status.value = "Enter NSE symbol."
                page.update()
                return

            try:
                days = int(days_field.value)
            except Exception:
                days = 60

            allowed = [30, 60, 90, 120, 180]
            if days not in allowed:
                days = min(allowed, key=lambda x: abs(x - days))
                days_field.value = str(days)

            status.value = f"Downloading {days} NSE sessions for {sym}..."
            page.update()

            rows, csv_path = update_stock_history(
                sym,
                period_days=days,
            )

            status.value = (
                f"NSE download complete: {len(rows)} sessions saved. "
                f"Local file: {csv_path}"
            )
            page.update()

        except Exception as ex:
            status.value = f"NSE UPDATE ERROR: {type(ex).__name__}: {ex}"
            page.update()


    # ========================================================
    # RUN TEST
    # ========================================================

    def run_test(e):

        result_column.controls.clear()

        selected_section.controls.clear()

        summary.value = ""

        state["result"] = None

        try:

            sym = (
                symbol.value
                .strip()
                .upper()
            )

            if not sym:

                status.value = (
                    "Enter NSE symbol."
                )

                page.update()

                return

            # ------------------------------------------------
            # DAYS
            # ------------------------------------------------

            try:
                days = int(
                    days_field.value
                )
            except Exception:
                days = 60

            allowed = [
                30,
                60,
                90,
                120,
                180,
            ]

            if days not in allowed:

                days = min(
                    allowed,
                    key=lambda x:
                    abs(x - days)
                )

                days_field.value = (
                    str(days)
                )

            # ------------------------------------------------
            # DOWNLOAD
            # ------------------------------------------------

            status.value = (
                f"Loading {days} NSE trading sessions..."
            )

            page.update()

            data = get_stock_history(
                sym,
                period_days=days,
                force_refresh=False,
            )

            if not data:

                status.value = (
                    "No market data received."
                )

                page.update()

                return

            if len(data) < 10:

                status.value = (
                    f"Only {len(data)} "
                    "sessions received. "
                    "At least 10 are required."
                )

                page.update()

                return

            # ------------------------------------------------
            # CALCULATE
            # ------------------------------------------------

            status.value = (
                "Calculating "
                "Bhoovalaya signals..."
            )

            page.update()

            result = analyze_stock(
                hindi_name.value.strip(),
                data,
            )

            state["result"] = result

            # ------------------------------------------------
            # SUMMARY
            # ------------------------------------------------

            ak = result["akshara"]

            moon = result["moon"]

            summary.value = (

                f"Stock: {sym}\n"

                f"Hindi name: "
                f"{hindi_name.value.strip()}\n"

                f"Akshara value: "
                f"{ak['total']}\n"

                f"Nakshatra: "
                f"{moon['nakshatra']}\n"

                f"Pada: "
                f"{moon['pada']}\n"

                f"729 cell: "
                f"{result['cell']}\n"

                f"Row: "
                f"{result['row'] + 1}\n"

                f"Column: "
                f"{result['col'] + 1}\n"

                f"Cell value: "
                f"{result['cell_value']}\n"

                f"Reference date: "
                f"{result['reference_date']}\n"

                f"Backtest sessions: "
                f"{len(result['backtest'])}"
            )

            # ------------------------------------------------
            # 729 CELL
            # ------------------------------------------------

            result_column.controls.append(

                ft.Text(
                    "729-CELL / CHAKRA",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                )
            )

            result_column.controls.append(

                ft.Text(
                    f"Selected cell = "
                    f"{result['cell']}\n"

                    f"Row = "
                    f"{result['row'] + 1}\n"

                    f"Column = "
                    f"{result['col'] + 1}\n"

                    f"Cell value = "
                    f"{result['cell_value']}"
                )
            )

            # ------------------------------------------------
            # ALL BANDHA ACCURACY TABLE
            # ------------------------------------------------

            result_column.controls.append(

                ft.Text(
                    "SIX BANDHA ACCURACY",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                )
            )

            accuracy_rows = []

            for name in BANDHAS:

                a = result[
                    "accuracy"
                ][name]

                accuracy_rows.append(
                    {
                        "Bandha": name,
                        "Hits": a["hits"],
                        "Tests": a["tests"],
                        "Misses": a["misses"],
                        "Accuracy":
                            f"{a['accuracy']:.1f}%",
                    }
                )

            result_column.controls.append(

                ft.Row(
                    [
                        make_table(
                            accuracy_rows,
                            [
                                "Bandha",
                                "Hits",
                                "Tests",
                                "Misses",
                                "Accuracy",
                            ],
                        )
                    ],
                    scroll=ft.ScrollMode.AUTO,
                )
            )

            # ------------------------------------------------
            # BANDHA SELECTOR
            # ------------------------------------------------

            result_column.controls.append(
                ft.Divider()
            )

            result_column.controls.append(

                ft.Text(
                    "CHECK ONE BANDHA",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                )
            )

            result_column.controls.append(

                ft.Row(
                    [
                        selected_bandha,

                        ft.Text(
                            "Change Bandha to "
                            "recalculate the display "
                            "for that Bandha.",
                            size=13,
                        ),
                    ],
                    wrap=True,
                )
            )

            # ------------------------------------------------
            # INITIAL SELECTED BANDHA
            # ------------------------------------------------

            initial_name = (
                selected_bandha.value
            )

            if initial_name not in BANDHAS:
                initial_name = "Saras"

                selected_bandha.value = (
                    initial_name
                )

            selected_section.controls.extend(

                build_selected_bandha_section(
                    result,
                    initial_name,
                )
            )

            result_column.controls.append(
                selected_section
            )

            # ------------------------------------------------
            # PREVIOUS 9
            # ------------------------------------------------

            result_column.controls.append(
                ft.Divider()
            )

            result_column.controls.append(

                ft.Text(
                    "PREVIOUS 9 TRADING SESSIONS",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                )
            )

            previous_rows = []

            for item in result[
                "previous"
            ]:

                previous_rows.append(
                    {
                        "Date":
                            item["date"],

                        "Close":
                            item["close"],

                        "Direction":
                            direction_icon(
                                item[
                                    "direction"
                                ]
                            ),
                    }
                )

            result_column.controls.append(

                ft.Row(
                    [
                        make_table(
                            previous_rows,
                            [
                                "Date",
                                "Close",
                                "Direction",
                            ],
                        )
                    ],
                    scroll=ft.ScrollMode.AUTO,
                )
            )

            status.value = (
                f"Completed: "
                f"{len(data)} trading sessions."
            )

            page.update()

        except Exception as ex:

            status.value = (
                f"ERROR: "
                f"{type(ex).__name__}: "
                f"{ex}"
            )

            page.update()

    # ========================================================
    # RUN BUTTON
    # ========================================================

    update_button = ft.Button(
        content="UPDATE NSE DATA",
        icon=ft.Icons.DOWNLOAD,
        on_click=update_market_data,
    )

    run_button = ft.Button(
        content="RUN TEST",
        icon=ft.Icons.PLAY_ARROW,
        on_click=run_test,
    )

    # ========================================================
    # PAGE
    # ========================================================

    page.add(

        ft.Text(
            APP_TITLE,
            size=26,
            weight=ft.FontWeight.BOLD,
        ),

        ft.Text(
            "Experimental Sri Bhoovalaya stock research"
        ),

        ft.Divider(),

        ft.Row(
            [
                symbol,
                hindi_name,
            ],
            wrap=True,
        ),

        ft.Row(
            [
                days_field,
                update_button,
                run_button,
            ],
            wrap=True,
        ),

        status,

        ft.Divider(),

        summary,

        ft.Divider(),

        result_column,
    )


if __name__ == "__main__":
    ft.run(main)
