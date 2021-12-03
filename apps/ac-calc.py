from itertools import groupby
from PIL import ImageColor
import string
from textwrap import dedent

import pydeck as pdk
from pydeck.types import String
import pandas as pd
import streamlit as st
from streamlit.elements.map import _get_zoom_level

from ac_calc.aeroplan import NoBrand, AEROPLAN_STATUSES, DEFAULT_AEROPLAN_STATUS, DEFAULT_FARE_BRAND_INDEX, FARE_BRANDS
from ac_calc.airlines import AirCanada, AIRLINES
from ac_calc.locations import airports, airports_by_code


SEGMENT_KEYS = ("airline", "origin", "destination", "fare_brand", "fare_class", "colour")
SEGMENT_COLOURS = (
    "#d62c35",
    "#8dd15a",
    "#ffc133",
    "#732d9d",
    "#00afed",
    "#fc9650",
    "#808080",
)
MARKET_COLOURS = {
    "DOM": (202, 42, 54),
    "TNB": (34, 132, 161),
    "SUN": (253, 192, 68),
    "INT": (100, 100, 100),
}


def main():
    st.set_page_config(
        page_title="AC Calculator",
        layout="wide",
        menu_items={
            "Get help": "https://www.flyertalk.com/forum/air-canada-aeroplan/2047742-calculator-sqm-aeroplan-miles-sqd.html",
            "Report a Bug": None,
            "About": "Aeroplan points and miles calculator. Based on [github.com/scottkennedy/ac-aqd](https://github.com/scottkennedy/ac-aqd).",
        }
    )

    tools = {
        "Calculate Points and Miles": calculate_points_miles,
        "Browse Airlines": browse_airlines,
        "Browse Airports": browse_airports,
    }

    with st.sidebar:
        tool_title = st.radio("Tool:", tools.keys())
        tool = tools[tool_title]

        st.markdown("<hr />", unsafe_allow_html=True)

        ticket_stock = st.radio(
            "Ticket Stock:",
            ("Air Canada", "Other"),
            index=0,
            key="ticket_stock",
            help="The airline that issued the ticket.",
        )
        st.session_state["ticket_number"] = "014" if ticket_stock == "Air Canada" else ""

        st.radio(
            "Aeroplan Status:",
            AEROPLAN_STATUSES,
            index=AEROPLAN_STATUSES.index(DEFAULT_AEROPLAN_STATUS),
            format_func=lambda status: status.name,
            key="aeroplan_status",
            help="Air Canada Aeroplan elite status.",
        )

    tool = tools[tool_title]
    tool(tool_title)


def calculate_points_miles(title):
    if not "num_segments" in st.session_state:
        st.session_state["num_segments"] = 1

    def segments():
        for i in range(st.session_state["num_segments"]):
            yield [i] + [st.session_state[f"{key}-{i}"] for key in SEGMENT_KEYS]

    st.markdown("""
        <style>
            div[data-testid="stBlock"] div[data-testid="stBlock"]:not([style]):not(:first-child) label {
                display: none
            }
        </style>
        """, unsafe_allow_html=True)

    # calc1_col, calc2_col, map_col = st.columns([6, 6, 18])
    summary_col, map_col = st.columns([10, 18])

    # Render segment inputs, first.
    DEFAULT_AIRLINE, DEFAULT_AIRLINE_INDEX = AirCanada, 0
    DEFAULT_ORIGIN_AIRPORT_INDEX, DEFAULT_ORIGIN_AIRPORT = next(
        filter(lambda e: e[1].airport_code == "YYC", enumerate(airports()))
    )
    DEFAULT_DESTINATION_AIRPORT_INDEX, DEFAULT_DESTINATION_AIRPORT = next(
        filter(lambda e: e[1].airport_code == "YYZ", enumerate(airports()))
    )

    # with st.container():
    with st.expander("Segments", expanded=True):
        for index in range(st.session_state["num_segments"]):
            color_col, airline_col, origin_col, destination_col, fare_brand_col, fare_class_col = st.columns((2, 24, 16, 16, 24, 12))

            color_col.markdown(f"""
            <label style="min-height: 1.5rem;"></label><div style="background-color: {SEGMENT_COLOURS[index % len(SEGMENT_COLOURS)]}; line-height: 1.6; width: 5px; padding: 12px 0">&nbsp;</div>
            """, unsafe_allow_html=True)
            st.session_state[f"colour-{index}"] = SEGMENT_COLOURS[index % len(SEGMENT_COLOURS)]
            # color_col.color_picker(
            #     # "🎨",
            #     "",
            #     value=SEGMENT_COLOURS[index % len(SEGMENT_COLOURS)],
            #     key=f"colour-{index}",
            # )

            airline = airline_col.selectbox(
                "Airline ✈️",
                AIRLINES,
                index=DEFAULT_AIRLINE_INDEX,
                format_func=lambda airline: airline.name,
                help="Flight segment operating airline.",
                key=f"airline-{index}",
            )

            origin_col.selectbox(
                "Origin 🛫",
                airports(),
                index=DEFAULT_ORIGIN_AIRPORT_INDEX,
                format_func=lambda airport: f"{airport.city} {airport.airport_code}" if airport.city else airport.airport_code,
                help="Flight segment origin airport code.",
                key=f"origin-{index}",
            )

            destination_col.selectbox(
                "Destination 🛬",
                airports(),
                index=DEFAULT_DESTINATION_AIRPORT_INDEX,
                format_func=lambda airport: f"{airport.city} {airport.airport_code}" if airport.city else airport.airport_code,
                help="Flight segment destination airport code.",
                key=f"destination-{index}",
            )

            if airline == AirCanada:
                fare_brand = fare_brand_col.selectbox(
                    "Service 🍷",
                    FARE_BRANDS,
                    index=DEFAULT_FARE_BRAND_INDEX,
                    format_func=lambda brand: brand.name,
                    help="Air Canada fare brand.",
                    key=f"fare_brand-{index}",
                )
            else:
                st.session_state[f"fare_brand-{index}"] = fare_brand = NoBrand

            fare_class_col.selectbox(
                "Class 🎫",
                list(string.ascii_uppercase) if fare_brand == NoBrand else fare_brand.fare_classes,
                key=f"fare_class-{index}",
            )

        _, add_col, _, _, _, remove_col = st.columns((2, 24, 16, 16, 24, 12))

        if add_col.button("Add Segment"):
            last_segment = st.session_state["num_segments"] - 1
            next_segment = last_segment + 1

            st.session_state[f"airline-{next_segment}"] = st.session_state[f"airline-{last_segment}"]
            st.session_state[f"origin-{next_segment}"] = st.session_state[f"destination-{last_segment}"]
            st.session_state[f"destination-{next_segment}"] = st.session_state[f"origin-{last_segment}"]
            st.session_state[f"fare_brand-{next_segment}"] = st.session_state[f"fare_brand-{last_segment}"]
            st.session_state[f"fare_class-{next_segment}"] = st.session_state[f"fare_class-{last_segment}"]

            st.session_state["num_segments"] = next_segment + 1

            st.experimental_rerun()
        if st.session_state["num_segments"] > 1 and remove_col.button("🗑"):
            st.session_state["num_segments"] -= 1
            st.experimental_rerun()

    # Perform calculations for the segments.
    segments_and_calculations = [
        (index, airline, origin, destination, fare_brand, fare_class, colour, airline.calculate(origin, destination, fare_brand, fare_class, st.session_state.ticket_number, st.session_state.aeroplan_status))
        for index, airline, origin, destination, fare_brand, fare_class, colour in segments()
    ]

    total_distance = sum((calc.distance for _,  _, _, _, _, _, _, calc in segments_and_calculations))
    base_pts = sum((calc.pts for _, _, _, _, _, _, _, calc in segments_and_calculations))
    bonus_pts = sum((calc.pts_bonus for _, _, _, _, _, _, _, calc in segments_and_calculations))
    total_sqm = sum((calc.sqm for _, _, _, _, _, _, _, calc in segments_and_calculations))

    with summary_col:
        summary_code = dedent("""
        <style>
            #calc-summary { position: relative; height: 340px }

            #sqx { display: flex; flex-direction: row; justify-content: space-around; max-height: 180px }
            #sqx > div:before { content: ""; float: left; padding-top: 100% }
            #sqx > div {
                display: flex; flex: 1 0 auto; margin: 0 3%;
                width: 28%; height: auto;
                align-items: center; justify-content: center; text-align: center;
                border: .375rem solid #d62c35; border-radius: 50%;
                background-color: #f9f8f6;
                font-size: 2rem; line-height: 1.125; font-weight: 600;
            }
            #sqx abbr { display: block; font-weight: 500; font-size: 1rem; text-decoration: none }
        </style>
        """)

        summary_code += '<div id="calc-summary">'

        summary_code += dedent(f"""
        <div id="sqx">
            <div><div>{total_sqm} <abbr title="Status Qualifying Miles">SQM</abbr></div></div>
            <div><div>{st.session_state["num_segments"]} <abbr title="Status Qualifying Segments">SQS</abbr></div></div>
            <div><div>0 <abbr title="Status Qualifying Dollars">SQD</abbr></div></div>
        </div>
        """)

        summary_df = pd.DataFrame(((
            f"{total_distance} miles",
            base_pts,
            bonus_pts,
            f"{base_pts + bonus_pts} points",
        )), index=(
            "Total Distance",
            "Aeroplan Base Points",
            "Aeroplan Bonus Points Select Privilege",
            "Aeroplan Base + Bonus Points"
        ))
        summary_df = summary_df.style.set_table_styles((
            {
                "selector": "",  # table
                "props": "position: absolute; bottom: 0; width: 100%",
            },
            {
                "selector": "thead",
                "props": "display: none",
            },
            {
                "selector": "tbody th",
                "props": "border: 0; padding: .25rem .5rem; background-color: #4a4f55; color: #f8fafd; font-weight: 500"
            },
            {
                "selector": "tbody td",
                "props": "border-color: #dbdfe5; padding: .25rem .5rem; color: #333; text-align: right"
            },
            {
                "selector": "tbody td.row0",
                "props": "color: #000; font-weight: 600; background-color: #f9f8f6"
            },
            {
                "selector": "tbody td.row3",
                "props": "color: #000; font-weight: 600; background-color: #efefef"
            },

        ))
        summary_code += summary_df.to_html()

        summary_code += "</div>"

        st.markdown(summary_code, unsafe_allow_html=True)

    # Show the map.
    with map_col:
        arclayer_data = [
            {
                "label": f"{origin.airport_code}–{destination.airport_code}",
                "distance": calc.distance,
                "source_position": (origin.longitude, origin.latitude),
                "target_position": (destination.longitude, destination.latitude),
                "source_colour": ImageColor.getrgb(colour),
                "target_colour": [c * .85 for c in ImageColor.getrgb(colour)],
            }
            for index, airline, origin, destination, fare_brand, fare_class, colour, calc in segments_and_calculations
        ]

        textlayer_data = [
            {
                "label": f"{origin.airport_code}–{destination.airport_code}",
                "distance": calc.distance,
                "text": destination.airport_code,
                "position": (destination.longitude, destination.latitude),
            }
            for index, airline, origin, destination, fare_brand, fare_class, colour, calc in segments_and_calculations
        ]

        _render_map(arclayer_data, textlayer_data)

    # Show the calculation details.
    # with st.expander("Calculation Details", expanded=True):
    calculations_data = [
        (
            airline.name,
            f"{origin.airport_code}–{destination.airport_code}",
            "" if calc.region == "*" else calc.region,
            calc.distance,
            fare_brand.name if fare_brand != NoBrand else calc.service,
            fare_class,
            f"{round(calc.sqm_earning_rate * 100)}%",
            calc.sqm,
            0,
            f"{round(calc.pts_earning_rate * 100)}%",
            calc.pts,
            f"{round(calc.pts_bonus_factor * 100)}%",
            calc.pts_bonus,
            calc.pts + calc.pts_bonus,
        )
        for index, airline, origin, destination, fare_brand, fare_class, colour, calc in segments_and_calculations
    ]
    calculations_cols = pd.MultiIndex.from_tuples([
        ("Flight", "Airline"),
        ("Flight", "Route"),
        ("Flight", "Region"),
        ("Flight", "Distance"),
        ("Fare", "Service"),
        ("Fare", "Class"),
        ("Status Qualifying", "Rate"),
        ("Status Qualifying", "Miles"),
        ("Status Qualifying", "Dollars"),
        ("Aeroplan", "Rate"),
        ("Aeroplan", "Points"),
        ("Aeroplan", "Bonus Rate"),
        ("Aeroplan", "Bonus Points"),
        ("Aeroplan", "Total Points"),
    ])

    calculations_df = pd.DataFrame(calculations_data, columns=calculations_cols)

    calculations_df.index += 1
    calculations_df = calculations_df.style.set_table_styles((
        {
            "selector": "",  # table
            "props": "margin-bottom: 1rem; width: 100%",
        },
        {
            "selector": "th",
            "props": "border-color: #a8afb8; padding: .25rem .5rem",
        },
        {
            "selector": "td",
            "props": "border-color: #dbdfe5; padding: .25rem .5rem; color: #333",
        },
        {
            "selector": "thead th.index_name",
            "props": "visibility: hidden",
        },
        {
            "selector": "thead th",
            "props": "border: 0",
        },
        {
            "selector": "thead th.level0",
            "props": "background-color: #4a4f55; color: #f8fafd; font-weight: 500; border-right: 1px solid #6f767f; padding: 1rem .5rem .25rem .5rem",
        },
        {
            "selector": "thead th.level0:last-child",
            "props": "border-right: 0",
        },
        {
            "selector": "thead th.level1",
            "props": "background-color: #6f767f; color: #f8fafd; font-weight: 500; font-size: .833rem",
        },
        {
            "selector": "tbody th",
            "props": "font-weight: 500; font-size: 1rem; text-align: center",
        },
        {
            "selector": "tbody tr:first-child, tbody tr:first-child th, tbody tr:first-child td",
            "props": "border-top: 0",
        },
        {
            "selector": ".data.col1",
            "props": "white-space: nowrap",
        },
        {
            "selector": ".data.col3",
            "props": "color: #000; font-weight: 600; background-color: #f9f8f6",
        },
        {
            "selector": ".data.col7, .data.col8, .data.col13",
            "props": "color: #000; font-weight: 600; background-color: #efefef",
        },
        {
            "selector": ".data.col3, .data.col6, .data.col7, .data.col8, .data.col9, .data.col10, .data.col11, .data.col12, .data.col13",
            "props": "text-align: right",
        },
        *[
            {
                "selector": f"th.row{i}",
                "props": f"color: white; background-color: {st.session_state[f'colour-{i}']}; border-color: {st.session_state[f'colour-{i}']}"
                # "props": f"color: white; background-color: {SEGMENT_COLOURS[index % len(SEGMENT_COLOURS)]}",
            }
            for i in range(st.session_state["num_segments"])
        ],
    ))

    st.markdown(calculations_df.to_html(), unsafe_allow_html=True)


def browse_airlines(title):
    airline = st.selectbox(
        "Airline ✈️",
        AIRLINES,
        index=0,
        format_func=lambda airline: airline.name,
        help="Operating airline.",
    )

    st.markdown(f'<div style="font-size:1.666rem">{airline.name}</div>', unsafe_allow_html=True)

    website_col, star_col, pts_col, sqm_col = st.columns(4)
    website_col.markdown(f'<div><a href="{airline.website}">{airline.website}</a></div>', unsafe_allow_html=True)
    star_col.markdown(
        "⭐️ Star Alliance member" if airline.star_alliance_member
        else "✈️ Codeshare partner" if airline.codeshare_partner
        else "🧳 Aeroplan partner")
    pts_col.markdown("👍 Earn Aeroplan points" if airline.earns_pts else "👎 No Aeroplan points")
    sqm_col.markdown("👍 Earn SQM" if airline.earns_sqm else "👎 No SQM")

    # Show the eligible flights for each region and class of service.
    if not airline.earning_rates:
        if airline.codeshare_partner:
            st.markdown(f"Earn Aeroplan points on flights operated by **{airline.name}** with a **4-digit Air Canada flight number**. See **Air Canada** for accrual details.")
        else:
            st.markdown("Redeem Aeroplan points only.")
        return

    for col, earning_rates_item in zip(st.columns(max(len(airline.earning_rates), 2)), airline.earning_rates.items()):
        region, services = earning_rates_item

        with col:
            rates = []
            for service, fare_classes in services.items():
                rates.extend([
                    (service, ", ".join(code[0] for code in codes), f"{int(rate * 100)}%")
                    for rate, codes in groupby(fare_classes.items(), key=lambda item: item[1])
                ])

            rates_df = pd.DataFrame(rates, columns=(
                "Class of service", "Eligible booking classes", "Rate",
            ))
            rates_df = rates_df.set_index(["Class of service"])
            rates_df.index.rename(None, inplace=True)
            rates_df = rates_df.rename_axis("Class of Service", axis=1)
            rates_df = rates_df.style.set_table_styles((
                {
                    "selector": "",  # table
                    "props": "width: 100%",
                },
                {
                    "selector": "th",
                    "props": "border-color: #a8afb8; padding: .25rem .5rem",
                },
                {
                    "selector": "td",
                    "props": "border-color: #dbdfe5; padding: .25rem .5rem; color: #333",
                },
                {
                    "selector": "thead th.level0",
                    "props": "background-color: #4a4f55; color: #f8fafd; font-weight: 500; border-right: 1px solid #6f767f; padding: 1rem .5rem .25rem .5rem",
                },
                {
                    "selector": "tbody th",
                    "props": "background-color: #6f767f; color: #f8fafd; font-weight: 500",
                },
                {
                    "selector": "tbody td.col1",
                    "props": "text-align: right",
                }
            ))

            st.markdown("#### " +  ("All Regions" if region == "*" else region) + "\n" + rates_df.to_html(), unsafe_allow_html=True)


def browse_airports(title):
    DEFAULT_ORIGIN_AIRPORT_INDEX, _ = next(
        filter(lambda e: e[1].airport_code == "YYC", enumerate(airports()))
    )

    origin = st.selectbox(
        "Origin 🛫",
        airports(),
        index=DEFAULT_ORIGIN_AIRPORT_INDEX,
        format_func=lambda airport: f"{airport.city} {airport.airport_code}" if airport.city else airport.airport_code,
        help="Flight origin airport code.",
    )

    st.markdown(f"<div style='font-size:1.666rem'>{origin.airport}</div>\n\n**{origin.city}**, " + (f"{origin.state}, " if origin.state else "") + origin.country, unsafe_allow_html=True)

    distances_data = []
    destination_airports = []

    for _, distance in origin.distances.items():
        destination_airport = airports_by_code()[distance.destination]
        destination_airports.append(destination_airport)

        distances_data.append((
            destination_airport.market,
            destination_airport.airport,
            destination_airport.airport_code,
            destination_airport.country,
            distance.old_distance,
            distance.distance,
            distance.distance or distance.old_distance,
        ))

    distances_df = pd.DataFrame(distances_data, columns=(
        "Market", "Airport", "Code", "Country", "Distance (Old)", "Distance (New)", "Distance (Combined)",
    ))
    distances_df["Market"] = distances_df["Market"].astype(pd.CategoricalDtype(("DOM", "TNB", "SUN", "INT"), ordered=True))
    distances_df = distances_df.sort_values(["Market", "Distance (Combined)"])
    distances_df.set_index("Market", inplace=True)

    arclayer_data = [
        {
            "label": destination.airport_code,
            "distance": data[-1] or data[-2],
            "source_position": (origin.longitude, origin.latitude),
            "target_position": (destination.longitude, destination.latitude),
            "source_colour": MARKET_COLOURS.get(destination.market, (180, 180, 180)),
            "target_colour": MARKET_COLOURS.get(destination.market, (180, 180, 180)),
        }
        for destination, data in zip(destination_airports, distances_data)
    ]

    textlayer_data = [
        {
            "label": destination.airport_code,
            "distance": data[-1] or data[-2],
            "text": destination.airport_code,
            "position": (destination.longitude, destination.latitude),
        }
        for destination, data in zip(destination_airports, distances_data)
    ]

    _render_map(arclayer_data, textlayer_data, ctr_lon=origin.longitude, ctr_lat=origin.latitude, zoom=4, get_width=2, height=540)
    st.table(distances_df)


def _render_map(arclayer_data=None, textlayer_data=None, ctr_lon=None, ctr_lat=None, zoom=None, get_width=6, height=340):
    if not ctr_lon or not ctr_lat:
        positions = [
            pos for route_positions in (
                (route["source_position"], route["target_position"])
                for route in arclayer_data
            ) for pos in route_positions
        ]
        min_lon = min(c[0] for c in positions)
        max_lon = max(c[0] for c in positions)
        min_lat = min(c[1] for c in positions)
        max_lat = max(c[1] for c in positions)
        ctr_lon = ctr_lon or ((min_lon + max_lon) / 2.0)
        ctr_lat = ctr_lat or ((min_lat + max_lat) / 2.0)
        rng_lon = abs(max_lon - min_lon)
        rng_lat = abs(max_lat - min_lat)
        zoom = zoom or (min(5, max(1, _get_zoom_level(max(rng_lon, rng_lat)))))

    layers = []

    if arclayer_data:
        # https://deck.gl/docs/api-reference/geo-layers/great-circle-layer
        layers.append(pdk.Layer(
            "ArcLayer",
            arclayer_data,
            pickable=True,
            greatCircle=True,
            get_width=get_width,
            get_height=0,
            get_source_position="source_position",
            get_target_position="target_position",
            get_source_color="source_colour",
            get_target_color="target_colour",
            auto_highlight=True,
        ))

    if textlayer_data:
        # https://deck.gl/docs/api-reference/layers/text-layer
        layers.append(pdk.Layer(
            "TextLayer",
            textlayer_data,
            pickable=True,
            get_position="position",
            get_text="text",
            get_size=18,
            get_text_anchor=String("middle"),
            get_alignment_baseline=String("center"),
        ))

    deck = pdk.Deck(
        initial_view_state=pdk.ViewState(
            latitude=ctr_lat,
            longitude=ctr_lon,
            zoom=zoom,
            bearing=0,
            pitch=0,
            height=height,
        ),
        map_style="road",
        layers=layers,
        tooltip={"html": "<strong>{label}</strong><br/>{distance} miles"}
    )
    deck.picking_radius = 20

    st.pydeck_chart(deck)


if __name__ == "__main__":
    main()
