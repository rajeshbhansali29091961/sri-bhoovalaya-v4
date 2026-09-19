import flet as ft

from bhoovalaya_engine import (
    BANDHAS,
    analyze_stock,
)


# ============================================================
# APP SETTINGS
# ============================================================

APP_TITLE = "Sri Bhoovalaya V5"

LOCATION_NAME = "Mumbai, India"
TIMEZONE_NAME = "Asia/Kolkata"
TIMEZONE_DISPLAY = "Mumbai, India — IST (UTC+5:30)"

DEFAULT_SYMBOL = "RELIANCE.NS"
DEFAULT_HINDI_NAME = "रिलायंस"
DEFAULT_DAYS = 60
DEFAULT_BANDHA = "Saras"


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def direction_symbol(direction):
    if direction == "UP":
        return "↑"

    if direction == "DOWN":
        return "↓"

    return "—"


def direction_text(direction):
    if direction == "UP":
        return "UP"

    if direction == "DOWN":
        return "DOWN"

    return "—"


def accuracy_color(accuracy):

    if accuracy >= 70:
        return ft.Colors.GREEN

    if accuracy >= 50:
        return ft.Colors.ORANGE

    return ft.Colors.RED


# ============================================================
# SMALL INFORMATION CARD
# ============================================================

def info_card(title, value, subtitle=""):

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    title,
                    size=11,
                    color=ft.Colors.GREY_600,
                ),

                ft.Text(
                    value,
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),

                ft.Text(
                    subtitle,
                    size=10,
                    color=ft.Colors.GREY_600,
                ),
            ],
            spacing=2,
        ),

        padding=10,

        border=ft.Border.all(
            1,
            ft.Colors.GREY_300,
        ),

        border_radius=10,

        expand=True,
    )


# ============================================================
# SELECTED BANDHA ACCURACY GRAPH
# ============================================================

def make_selected_accuracy_graph(
    backtest,
    selected_bandha,
):

    hits = 0
    tests = 0

    for item in backtest:

        actual = item.get("actual")

        prediction = item.get(
            selected_bandha
        )

        if actual not in ("UP", "DOWN"):
            continue

        if prediction not in ("UP", "DOWN"):
            continue

        tests += 1

        if prediction == actual:
            hits += 1

    misses = tests - hits

    if tests:
        accuracy = (
            hits / tests
        ) * 100.0
    else:
        accuracy = 0.0

    hit_fraction = (
        hits / tests
        if tests
        else 0.0
    )

    miss_fraction = (
        misses / tests
        if tests
        else 0.0
    )

    acc_color = accuracy_color(
        accuracy
    )

    return ft.Container(

        content=ft.Column(
            [

                # ------------------------------------------------
                # TITLE + BIG ACCURACY
                # ------------------------------------------------

                ft.Row(
                    [

                        ft.Text(
                            f"{selected_bandha} — "
                            f"Historical Backtest",
                            size=17,
                            weight=ft.FontWeight.BOLD,
                        ),

                        ft.Container(
                            expand=True
                        ),

                        ft.Text(
                            f"{accuracy:.1f}%",
                            size=25,
                            weight=ft.FontWeight.BOLD,
                            color=acc_color,
                        ),
                    ],

                    vertical_alignment=
                    ft.CrossAxisAlignment.CENTER,
                ),

                ft.Text(
                    "Historical accuracy only — "
                    "not a future guarantee.",
                    size=10,
                    color=ft.Colors.GREY_600,
                ),

                ft.Container(
                    height=5
                ),

                # ------------------------------------------------
                # ACCURACY BAR
                # ------------------------------------------------

                ft.ProgressBar(
                    value=max(
                        0.0,
                        min(
                            1.0,
                            accuracy / 100.0
                        ),
                    ),

                    color=acc_color,

                    bgcolor=ft.Colors.GREY_300,

                    height=12,
                ),

                ft.Container(
                    height=8
                ),

                # ------------------------------------------------
                # HIT
                # ------------------------------------------------

                ft.Text(
                    f"HIT   {hits}   "
                    f"({hit_fraction * 100:.1f}%)",

                    size=12,

                    weight=ft.FontWeight.BOLD,
                ),

                ft.ProgressBar(
                    value=hit_fraction,

                    color=ft.Colors.GREEN,

                    bgcolor=ft.Colors.GREY_200,

                    height=9,
                ),

                ft.Container(
                    height=5
                ),

                # ------------------------------------------------
                # MISS
                # ------------------------------------------------

                ft.Text(
                    f"MISS   {misses}   "
                    f"({miss_fraction * 100:.1f}%)",

                    size=12,

                    weight=ft.FontWeight.BOLD,
                ),

                ft.ProgressBar(
                    value=miss_fraction,

                    color=ft.Colors.RED,

                    bgcolor=ft.Colors.GREY_200,

                    height=9,
                ),

                ft.Container(
                    height=8
                ),

                # ------------------------------------------------
                # SUMMARY CARDS
                # ------------------------------------------------

                ft.Row(
                    [

                        info_card(
                            "HIT",
                            str(hits),
                            "Correct",
                        ),

                        info_card(
                            "MISS",
                            str(misses),
                            "Incorrect",
                        ),

                        info_card(
                            "TESTS",
                            str(tests),
                            "Completed",
                        ),

                    ],

                    spacing=7,
                ),
            ],

            spacing=4,
        ),

        padding=13,

        border=ft.Border.all(
            1,
            ft.Colors.GREY_300,
        ),

        border_radius=12,
    )


# ============================================================
# DATE-BY-DATE HIT / MISS GRAPH
# ============================================================

def make_hit_miss_graph(
    backtest,
    selected_bandha,
):

    rows = []

    for item in backtest:

        actual = item.get("actual")

        prediction = item.get(
            selected_bandha
        )

        if actual not in ("UP", "DOWN"):
            continue

        date_value = str(
            item.get(
                "date",
                ""
            )
        )

        pred_symbol = direction_symbol(
            prediction
        )

        actual_symbol = direction_symbol(
            actual
        )

        is_hit = (
            prediction == actual
        )

        if is_hit:

            bg = ft.Colors.GREEN_100

            status = "HIT"

            status_color = ft.Colors.GREEN

        else:

            bg = ft.Colors.RED_100

            status = "MISS"

            status_color = ft.Colors.RED

        rows.append(

            ft.Container(

                content=ft.Row(
                    [

                        ft.Container(
                            content=ft.Text(
                                date_value,
                                size=11,
                                weight=ft.FontWeight.BOLD,
                            ),

                            width=75,
                        ),

                        ft.Container(
                            content=ft.Text(
                                pred_symbol,
                                size=21,
                                weight=ft.FontWeight.BOLD,
                            ),

                            width=35,

                            alignment=ft.Alignment.CENTER,
                        ),

                        ft.Container(
                            content=ft.Text(
                                actual_symbol,
                                size=21,
                                weight=ft.FontWeight.BOLD,
                            ),

                            width=35,

                            alignment=ft.Alignment.CENTER,
                        ),

                        ft.Container(
                            content=ft.Text(
                                status,
                                size=11,
                                weight=ft.FontWeight.BOLD,
                                color=status_color,
                            ),

                            width=55,
                        ),

                        ft.Text(
                            f"{direction_text(prediction)} / "
                            f"{direction_text(actual)}",

                            size=10,

                            expand=True,
                        ),
                    ],

                    vertical_alignment=
                    ft.CrossAxisAlignment.CENTER,
                ),

                padding=7,

                margin=ft.Margin(
                    bottom=2
                ),

                bgcolor=bg,

                border_radius=7,
            )
        )

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    header = ft.Container(

        content=ft.Row(
            [

                ft.Container(
                    content=ft.Text(
                        "DATE",
                        size=10,
                        weight=ft.FontWeight.BOLD,
                    ),
                    width=75,
                ),

                ft.Container(
                    content=ft.Text(
                        "PRED",
                        size=10,
                        weight=ft.FontWeight.BOLD,
                    ),
                    width=35,
                ),

                ft.Container(
                    content=ft.Text(
                        "ACT",
                        size=10,
                        weight=ft.FontWeight.BOLD,
                    ),
                    width=35,
                ),

                ft.Container(
                    content=ft.Text(
                        "RESULT",
                        size=10,
                        weight=ft.FontWeight.BOLD,
                    ),
                    width=55,
                ),

                ft.Text(
                    "PRED / ACT",
                    size=10,
                    weight=ft.FontWeight.BOLD,
                ),
            ]
        ),

        padding=7,
    )

    return ft.Container(

        content=ft.Column(
            [

                ft.Text(
                    f"{selected_bandha} — "
                    f"Day-by-Day Result",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                ),

                ft.Text(
                    "Green = HIT     Red = MISS",
                    size=10,
                    color=ft.Colors.GREY_600,
                ),

                header,

                ft.Column(
                    rows,

                    spacing=1,

                    scroll=ft.ScrollMode.AUTO,
                ),
            ],

            spacing=3,
        ),

        padding=11,

        border=ft.Border.all(
            1,
            ft.Colors.GREY_300,
        ),

        border_radius=12,
    )


# ============================================================
# SELECTED BANDHA SECTION
# ============================================================

def build_selected_bandha_section(
    result,
    selected_bandha,
):

    backtest = result.get(
        "backtest",
        []
    )

    return ft.Column(
        [

            ft.Text(
                f"Selected Bandha: "
                f"{selected_bandha}",

                size=19,

                weight=ft.FontWeight.BOLD,
            ),

            make_selected_accuracy_graph(
                backtest,
                selected_bandha,
            ),

            make_hit_miss_graph(
                backtest,
                selected_bandha,
            ),
        ],

        spacing=10,
    )


# ============================================================
# ALL BANDHA COMPARISON
# ============================================================

def make_bandha_comparison_graph(
    accuracy
):

    controls = []

    for name in BANDHAS:

        data = accuracy.get(
            name,
            {
                "accuracy": 0.0
            },
        )

        value = safe_float(
            data.get(
                "accuracy",
                0.0
            )
        )

        controls.append(

            ft.Container(

                content=ft.Column(
                    [

                        ft.Row(
                            [

                                ft.Text(
                                    name,
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                ),

                                ft.Container(
                                    expand=True
                                ),

                                ft.Text(
                                    f"{value:.1f}%",
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ]
                        ),

                        ft.ProgressBar(

                            value=max(
                                0.0,
                                min(
                                    1.0,
                                    value / 100.0
                                ),
                            ),

                            height=9,
                        ),
                    ],

                    spacing=3,
                ),

                padding=4,
            )
        )

    return ft.Container(

        content=ft.Column(
            [

                ft.Text(
                    "All Bandhas — "
                    "Historical Accuracy",

                    size=16,

                    weight=ft.FontWeight.BOLD,
                ),

                ft.Text(
                    "For comparison only.",
                    size=10,
                    color=ft.Colors.GREY_600,
                ),

                ft.Column(
                    controls,
                    spacing=3,
                ),
            ],

            spacing=4,
        ),

        padding=11,

        border=ft.Border.all(
            1,
            ft.Colors.GREY_300,
        ),

        border_radius=12,
    )


# ============================================================
# ACCURACY TABLE
# ============================================================

def make_table(
    accuracy
):

    rows = []

    for name in BANDHAS:

        data = accuracy.get(
            name,
            {
                "hits": 0,
                "tests": 0,
                "misses": 0,
                "accuracy": 0.0,
            },
        )

        rows.append(

            ft.DataRow(

                cells=[

                    ft.DataCell(
                        ft.Text(name)
                    ),

                    ft.DataCell(
                        ft.Text(
                            str(
                                data.get(
                                    "hits",
                                    0
                                )
                            )
                        )
                    ),

                    ft.DataCell(
                        ft.Text(
                            str(
                                data.get(
                                    "misses",
                                    0
                                )
                            )
                        )
                    ),

                    ft.DataCell(
                        ft.Text(
                            str(
                                data.get(
                                    "tests",
                                    0
                                )
                            )
                        )
                    ),

                    ft.DataCell(
                        ft.Text(
                            f'{safe_float(data.get("accuracy", 0)):.1f}%'
                        )
                    ),
                ]
            )
        )

    return ft.DataTable(

        columns=[

            ft.DataColumn(
                ft.Text("Bandha")
            ),

            ft.DataColumn(
                ft.Text("HIT")
            ),

            ft.DataColumn(
                ft.Text("MISS")
            ),

            ft.DataColumn(
                ft.Text("TEST")
            ),

            ft.DataColumn(
                ft.Text("Accuracy")
            ),
        ],

        rows=rows,

        column_spacing=18,

        heading_row_height=38,

        data_row_min_height=36,
    )


# ============================================================
# PREVIOUS 9 DAYS
# ============================================================

def make_previous_table(
    previous
):

    rows = []

    for item in previous:

        rows.append(

            ft.DataRow(

                cells=[

                    ft.DataCell(
                        ft.Text(
                            str(
                                item.get(
                                    "date",
                                    ""
                                )
                            )
                        )
                    ),

                    ft.DataCell(
                        ft.Text(
                            direction_symbol(
                                item.get(
                                    "actual"
                                )
                            ),

                            size=19,

                            weight=ft.FontWeight.BOLD,
                        )
                    ),
                ]
            )
        )

    return ft.DataTable(

        columns=[

            ft.DataColumn(
                ft.Text("Date")
            ),

            ft.DataColumn(
                ft.Text("Actual")
            ),
        ],

        rows=rows,

        column_spacing=30,
    )


# ============================================================
# NEXT 9 SIGNALS
# ============================================================

def make_next_table(
    next_signals,
    selected_bandha,
):

    rows = []

    for item in next_signals:

        prediction = item.get(
            selected_bandha
        )

        rows.append(

            ft.DataRow(

                cells=[

                    ft.DataCell(
                        ft.Text(
                            str(
                                item.get(
                                    "date",
                                    ""
                                )
                            )
                        )
                    ),

                    ft.DataCell(

                        ft.Text(

                            direction_symbol(
                                prediction
                            ),

                            size=20,

                            weight=ft.FontWeight.BOLD,
                        )
                    ),
                ]
            )
        )

    return ft.DataTable(

        columns=[

            ft.DataColumn(
                ft.Text("Date")
            ),

            ft.DataColumn(
                ft.Text(
                    f"{selected_bandha} Signal"
                )
            ),
        ],

        rows=rows,

        column_spacing=25,
    )


# ============================================================
# MAIN
# ============================================================

def main(page: ft.Page):

    page.title = APP_TITLE

    page.padding = 10

    page.scroll = ft.ScrollMode.AUTO

    page.theme_mode = ft.ThemeMode.LIGHT

    # --------------------------------------------------------
    # INPUT FIELDS
    # --------------------------------------------------------

    symbol_field = ft.TextField(

        label="Stock Symbol",

        value=DEFAULT_SYMBOL,

        dense=True,

        expand=True,
    )

    hindi_field = ft.TextField(

        label="Hindi Stock Name",

        value=DEFAULT_HINDI_NAME,

        dense=True,

        expand=True,
    )

    days_field = ft.TextField(

        label="Test Days",

        value=str(
            DEFAULT_DAYS
        ),

        dense=True,

        keyboard_type=
        ft.KeyboardType.NUMBER,

        expand=True,
    )

    bandha_dropdown = ft.Dropdown(

        label="Select Bandha",

        value=DEFAULT_BANDHA,

        options=[

            ft.DropdownOption(

                key=name,

                text=name,
            )

            for name in BANDHAS
        ],

        expand=True,
    )

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    status_text = ft.Text(

        "Enter stock details and press RUN TEST.",

        size=11,

        color=ft.Colors.GREY_700,
    )

    selected_area = ft.Column(
        spacing=10
    )

    result_area = ft.Column(
        spacing=10
    )

    # Store latest result
    latest_result = {
        "value": None
    }

    # --------------------------------------------------------
    # RUN TEST
    # --------------------------------------------------------

    def run_test(e=None):

        status_text.value = (
            "Running test..."
        )

        selected_area.controls.clear()

        result_area.controls.clear()

        page.update()

        try:

            symbol = (
                symbol_field.value
                or DEFAULT_SYMBOL
            ).strip()

            hindi_name = (
                hindi_field.value
                or DEFAULT_HINDI_NAME
            ).strip()

            try:

                days = int(
                    days_field.value
                    or DEFAULT_DAYS
                )

            except Exception:

                days = DEFAULT_DAYS

            if days < 1:
                days = DEFAULT_DAYS

            selected_bandha = (
                bandha_dropdown.value
                or DEFAULT_BANDHA
            )

            # =================================================
            # IMPORTANT:
            # Current engine expects:
            #
            # analyze_stock(
            #     symbol,
            #     hindi_name,
            #     days=...,
            #     timezone_name=...
            # )
            #
            # It does NOT accept history=.
            # =================================================

            result = analyze_stock(

                symbol,

                hindi_name,

                days=days,

                timezone_name=
                TIMEZONE_NAME,
            )

            latest_result["value"] = result

            accuracy = result.get(
                "accuracy",
                {}
            )

            backtest = result.get(
                "backtest",
                []
            )

            previous = result.get(
                "previous_9",
                []
            )

            next_signals = result.get(
                "next_9",
                []
            )

            # ------------------------------------------------
            # HEADER
            # ------------------------------------------------

            result_area.controls.append(

                ft.Container(

                    content=ft.Column(
                        [

                            ft.Text(
                                "Sri Bhoovalaya V5",

                                size=22,

                                weight=
                                ft.FontWeight.BOLD,
                            ),

                            ft.Text(
                                f"{symbol} | "
                                f"{hindi_name}",

                                size=13,
                            ),

                            ft.Text(
                                TIMEZONE_DISPLAY,

                                size=10,

                                color=
                                ft.Colors.GREY_600,
                            ),
                        ],

                        spacing=2,
                    ),

                    padding=8,
                )
            )

            # ------------------------------------------------
            # SELECTED BANDHA
            # ------------------------------------------------

            selected_area.controls.append(

                build_selected_bandha_section(

                    result,

                    selected_bandha,
                )
            )

            # ------------------------------------------------
            # ALL BANDHAS
            # ------------------------------------------------

            result_area.controls.append(

                ft.Text(

                    "All Bandhas",

                    size=18,

                    weight=
                    ft.FontWeight.BOLD,
                )
            )

            result_area.controls.append(

                make_bandha_comparison_graph(
                    accuracy
                )
            )

            # ------------------------------------------------
            # TABLE
            # ------------------------------------------------

            result_area.controls.append(

                ft.Container(

                    content=ft.Column(
                        [

                            ft.Text(
                                "Accuracy Table",

                                size=15,

                                weight=
                                ft.FontWeight.BOLD,
                            ),

                            ft.Row(

                                [
                                    make_table(
                                        accuracy
                                    )
                                ],

                                scroll=
                                ft.ScrollMode.AUTO,
                            ),
                        ],

                        spacing=4,
                    ),

                    padding=8,

                    border=
                    ft.Border.all(
                        1,
                        ft.Colors.GREY_300,
                    ),

                    border_radius=10,
                )
            )

            # ------------------------------------------------
            # PREVIOUS 9
            # ------------------------------------------------

            result_area.controls.append(

                ft.Text(

                    "Previous 9 Trading Days",

                    size=17,

                    weight=
                    ft.FontWeight.BOLD,
                )
            )

            result_area.controls.append(

                ft.Row(

                    [
                        make_previous_table(
                            previous
                        )
                    ],

                    scroll=
                    ft.ScrollMode.AUTO,
                )
            )

            # ------------------------------------------------
            # NEXT 9
            # ------------------------------------------------

            result_area.controls.append(

                ft.Text(

                    "Next 9 Signals",

                    size=17,

                    weight=
                    ft.FontWeight.BOLD,
                )
            )

            result_area.controls.append(

                ft.Row(

                    [
                        make_next_table(
                            next_signals,
                            selected_bandha,
                        )
                    ],

                    scroll=
                    ft.ScrollMode.AUTO,
                )
            )

            status_text.value = (
                "Test completed successfully."
            )

        except Exception as ex:

            status_text.value = (
                f"Error: {ex}"
            )

            result_area.controls.append(

                ft.Container(

                    content=ft.Text(

                        str(ex),

                        color=ft.Colors.RED,
                    ),

                    padding=10,

                    border=
                    ft.Border.all(
                        1,
                        ft.Colors.RED,
                    ),

                    border_radius=8,
                )
            )

        page.update()

    # --------------------------------------------------------
    # BANDHA CHANGE
    # --------------------------------------------------------

    def bandha_changed(e):

        result = latest_result["value"]

        if result is None:
            return

        selected_bandha = (
            bandha_dropdown.value
            or DEFAULT_BANDHA
        )

        selected_area.controls.clear()

        selected_area.controls.append(

            build_selected_bandha_section(

                result,

                selected_bandha,
            )
        )

        page.update()

    bandha_dropdown.on_change = (
        bandha_changed
    )

    # --------------------------------------------------------
    # RUN BUTTON
    # --------------------------------------------------------

    run_button = ft.Button(

        content="RUN TEST",

        icon=ft.Icons.PLAY_ARROW,

        on_click=run_test,
    )

    # --------------------------------------------------------
    # INPUT ROWS
    # --------------------------------------------------------

    input_row_1 = ft.Row(

        [
            symbol_field,
            hindi_field,
        ],

        spacing=8,
    )

    input_row_2 = ft.Row(

        [
            days_field,
            bandha_dropdown,
        ],

        spacing=8,
    )

    # --------------------------------------------------------
    # PAGE
    # --------------------------------------------------------

    page.add(

        ft.Text(

            APP_TITLE,

            size=24,

            weight=
            ft.FontWeight.BOLD,
        ),

        ft.Text(

            "Experimental Sri Bhoovalaya stock research",

            size=11,

            color=
            ft.Colors.GREY_600,
        ),

        input_row_1,

        input_row_2,

        ft.Row(
            [
                run_button
            ]
        ),

        status_text,

        ft.Divider(),

        selected_area,

        ft.Divider(),

        result_area,

        ft.Container(
            height=25
        ),

        ft.Text(

            "Note: Historical backtest accuracy is "
            "experimental and does not guarantee "
            "future market direction.",

            size=10,

            color=
            ft.Colors.GREY_600,
        ),
    )


# ============================================================
# START APP
# ============================================================

if __name__ == "__main__":
    ft.run(main)
