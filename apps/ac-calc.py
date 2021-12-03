from collections import namedtuple
from itertools import groupby
from PIL import ImageColor
import re
import string
from textwrap import dedent

import pydeck as pdk
from pydeck.types import String
import pandas as pd
import streamlit as st
from streamlit.elements.map import _get_zoom_level

from ac_calc.aeroplan import Flex, NoBrand, AEROPLAN_STATUSES, DEFAULT_AEROPLAN_STATUS, DEFAULT_FARE_BRAND_INDEX, FARE_BRANDS
from ac_calc.airlines import AirCanada, AIRLINES
from ac_calc.locations import airports, airports_by_code


Segment = namedtuple("Segment", ("airline", "origin", "destination", "fare_brand", "fare_class", "colour"))


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

        ticket_stock = st.selectbox(
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

        st.radio(
            "Segments Input Style:",
            [
                "Simple Route",
                "Detailed Route",
                "Cowtool",
            ],
            key="segments_input_style",
            help="Segments input interface style.",
        )

    tool = tools[tool_title]
    tool(tool_title)


def calculate_points_miles(title):
    # Get the stored segment data. We can't rely on the component session states,
    # because they are removed if the component isn't present anymore, like when
    # switching between tools.
    if not "segments" in st.session_state:
        st.session_state["segments"] = segments = (Segment(
            AirCanada, airports_by_code()["YYC"], airports_by_code()["YYZ"], Flex, "M", "#d62c35",
        ),)
    else:
        segments = st.session_state["segments"]

    st.markdown("""
        <style>
            div[data-testid="stBlock"] div[data-testid="stBlock"]:not([style]):not(:first-child) label {
                display: none
            }
        </style>
    """, unsafe_allow_html=True)

    # Reserve space for the calculation summary and segments map.
    summary_col, map_col = st.columns([10, 18])

    # Iterate through the segments and present input widgets for the fields.
    # Collect the return field values and construct modified Segment tuples
    # during the loop so that we don't have to grab them from the session
    # state afterwards.
    modified_segments = []
    with st.expander("Segments", expanded=True):
        should_rerun = False
        input_style = st.session_state["segments_input_style"]

        if input_style == "Simple Route":
            # Unpack the segment data into the session state, if needed.
            first_segment_dict = segments[0]._asdict()
            for key in Segment._fields:
                if key == "route":
                    continue
                if not key in st.session_state:
                    st.session_state[key] = first_segment_dict[key]
            if "route" not in st.session_state:
                route_str = ""
                for segment in segments:
                    if not route_str.endswith(segment.origin.airport_code):
                        route_str += f",{segment.origin.airport_code}"
                    route_str += f"-{segment.destination.airport_code}"
                route_str = route_str.strip(",-")
                st.session_state["route"] = route_str

            airline_col, route_col, fare_brand_col, fare_class_col = st.columns((24, 32, 24, 12))

            airline = airline_col.selectbox(
                "Airline ✈️",
                AIRLINES,
                format_func=lambda airline: airline.name,
                help="Flight segment operating airline.",
                key="airline",
            )

            route = route_col.text_input(
                "Route 🛫 🛬",
                key="route",
            )

            if airline == AirCanada:
                fare_brand = fare_brand_col.selectbox(
                    "Service 🍷",
                    FARE_BRANDS,
                    format_func=lambda brand: brand.name,
                    help="Air Canada fare brand.",
                    key=f"fare_brand",
                )
            else:
                fare_brand = NoBrand

            fare_class = fare_class_col.selectbox(
                "Class 🎫",
                list(string.ascii_uppercase) if fare_brand == NoBrand else fare_brand.fare_classes,
                key=f"fare_class",
            )

            # Form new Segments with the values.
            modified_segments = []
            for route_part in re.split(r"[,;]", route):
                last_airport = None
                for airport_code in re.split(r"[-–—]", route_part):
                    airport_code = airport_code.strip().upper()
                    airport = airports_by_code().get(airport_code)

                    if last_airport:
                        modified_segments.append(Segment(
                            airline,
                            last_airport,
                            airport,
                            fare_brand,
                            fare_class,
                            SEGMENT_COLOURS[len(modified_segments) % len(SEGMENT_COLOURS)],
                        ))
                    last_airport = airport

        elif input_style == "Detailed Route":
            # Unpack the segment data into the session state, if needed.
            for index, segment in enumerate(segments):
                for key, value in segment._asdict().items():
                    if not f"{key}-{index}" in st.session_state:
                        st.session_state[f"{key}-{index}"] = value

            for index in range(len(segments)):
                color_col, airline_col, origin_col, destination_col, fare_brand_col, fare_class_col = st.columns((2, 24, 16, 16, 24, 12))

                color_col.markdown(f"""
                <label style="min-height: 1.5rem;"></label><div style="background-color: {SEGMENT_COLOURS[index % len(SEGMENT_COLOURS)]}; line-height: 1.6; width: 5px; padding: 12px 0">&nbsp;</div>
                """, unsafe_allow_html=True)
                st.session_state[f"colour-{index}"] = colour = SEGMENT_COLOURS[index % len(SEGMENT_COLOURS)]
                # color_col.color_picker(
                #     # "🎨",
                #     "",
                #     value=SEGMENT_COLOURS[index % len(SEGMENT_COLOURS)],
                #     key=f"colour-{index}",
                # )

                airline = airline_col.selectbox(
                    "Airline ✈️",
                    AIRLINES,
                    format_func=lambda airline: airline.name,
                    help="Flight segment operating airline.",
                    key=f"airline-{index}",
                )

                origin = origin_col.selectbox(
                    "Origin 🛫",
                    airports(),
                    format_func=lambda airport: f"{airport.city} {airport.airport_code}" if airport.city else airport.airport_code,
                    help="Flight segment origin airport code.",
                    key=f"origin-{index}",
                )

                destination = destination_col.selectbox(
                    "Destination 🛬",
                    airports(),
                    format_func=lambda airport: f"{airport.city} {airport.airport_code}" if airport.city else airport.airport_code,
                    help="Flight segment destination airport code.",
                    key=f"destination-{index}",
                )

                if airline == AirCanada:
                    fare_brand = fare_brand_col.selectbox(
                        "Service 🍷",
                        FARE_BRANDS,
                        format_func=lambda brand: brand.name,
                        help="Air Canada fare brand.",
                        key=f"fare_brand-{index}",
                    )
                else:
                    fare_brand = NoBrand

                fare_class = fare_class_col.selectbox(
                    "Class 🎫",
                    list(string.ascii_uppercase) if fare_brand == NoBrand else fare_brand.fare_classes,
                    key=f"fare_class-{index}",
                )

                # Construct a new Segment with the values.
                modified_segments.append(Segment(
                    airline, origin, destination, fare_brand, fare_class, colour
                ))

            # Present buttons for adding or removing segments.
            _, add_col, _, _, _, remove_col = st.columns((2, 24, 16, 16, 24, 12))
            if add_col.button("Add Segment"):
                last_segment = modified_segments[-1]
                next_segment = Segment(
                    last_segment.airline,
                    last_segment.destination,
                    last_segment.origin,
                    last_segment.fare_brand,
                    last_segment.fare_class,
                    last_segment.colour
                )

                modified_segments.append(next_segment)
                should_rerun = True
            elif len(segments) > 1 and remove_col.button("🗑"):
                del modified_segments[-1]
                should_rerun = True

        elif input_style == "Cowtool":
            # Unpack the segment data into the session state, if needed.
            if not "itinerary" in st.session_state:
                itinerary_parts = []
                for segment in segments:
                    itinerary_parts.append(",".join((
                        segment.airline.codes[0],
                        segment.origin.airport_code,
                        segment.destination.airport_code,
                        segment.fare_class,
                        segment.fare_brand.basis_codes[0] if segment.airline == AirCanada else ""
                    )))
                itinerary = "\n".join(itinerary_parts)
                st.session_state["itinerary"] = itinerary

            itinerary = st.text_area(
                "Itinerary",
                height=160,
                key="itinerary",
                help="Flight itinerary with airline,origin,destination,fare class,brand code per line.",
            )

            # Form new Segments from the itinerary.
            for line in itinerary.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue

                parts = line.split(",")
                if len(parts) == 5:
                    airline_code, origin_airport_code, destination_airport_code, fare_class, fare_brand_code = parts
                elif len(parts) == 4:
                    airline_code, origin_airport_code, destination_airport_code, fare_class = parts
                    fare_brand_code = ""
                else:
                    st.error(f"Line does not have 4 or 5 parts: {line}")

                try:
                    modified_segments.append(Segment(
                        next(filter(lambda airline: airline_code in airline.codes, AIRLINES)),
                        airports_by_code()[origin_airport_code],
                        airports_by_code()[destination_airport_code],
                        next(filter(lambda fare_brand: fare_brand_code in fare_brand.basis_codes, FARE_BRANDS)),
                        fare_class,
                        SEGMENT_COLOURS[len(modified_segments) % len(SEGMENT_COLOURS)],
                    ))
                except:
                    st.error(f"Error parsing line: {line}")

        # Store the modified segments for the next loop.
        segments = tuple(modified_segments)
        st.session_state["segments"] = segments

        # If a segment was added or removed, rerun the app to update the input components.
        if should_rerun:
            st.experimental_rerun()

    # Calculate all the things for the segments.
    calculations = [
        segment.airline.calculate(
            segment.origin,
            segment.destination,
            segment.fare_brand,
            segment.fare_class,
            st.session_state.ticket_number,
            st.session_state.aeroplan_status,
        )
        for segment in segments
    ]

    total_distance = sum((calc.distance for calc in calculations))
    base_pts = sum((calc.pts for calc in calculations))
    bonus_pts = sum((calc.pts_bonus for calc in calculations))
    total_sqm = sum((calc.sqm for calc in calculations))

    # Show the calculation summary.
    with summary_col:
        if len(segments) < 1:
            st.info("No segments.")
            return

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
                font-size: 1.666vw; line-height: 1.125; font-weight: 600;
            }
            #sqx abbr { display: block; font-weight: 500; font-size: .833vw; text-decoration: none }
        </style>
        """)

        summary_code += '<div id="calc-summary">'

        summary_code += dedent(f"""
        <div id="sqx">
            <div><div>{total_sqm} <abbr title="Status Qualifying Miles">SQM</abbr></div></div>
            <div><div>{len(segments)} <abbr title="Status Qualifying Segments">SQS</abbr></div></div>
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
            "Bonus Points Select Privilege",
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
        arclayer_and_textlayer_data = [
            {
                "tooltip": f'<div><strong>{segment.destination.city}</strong> {segment.destination.airport_code}</div><div style="font-size: .833rem">{segment.destination.airport}<br />{calc.distance} miles</div>',
                "source_position": (segment.origin.longitude, segment.origin.latitude),
                "target_position": (segment.destination.longitude, segment.destination.latitude),
                "source_colour": ImageColor.getrgb(segment.colour),
                "target_colour": [c * .85 for c in ImageColor.getrgb(segment.colour)],
                "text": segment.destination.airport_code,
                "position": (segment.destination.longitude, segment.destination.latitude),
            }
            for segment, calc in zip(segments, calculations)
        ]

        first_segment = segments[0]
        iconlayer_data = [
            {
                "tooltip": f'<div><strong>{first_segment.origin.city}</strong> {first_segment.origin.airport_code}</div><div style="font-size: .833rem">{first_segment.origin.airport}</div>',
                "marker": "airplane",
                "position": (first_segment.origin.longitude, first_segment.origin.latitude),
                "size": 48,
            },
            *[
                {
                    "tooltip": f'<div><strong>{segment.destination.city}</strong> {segment.destination.airport_code}</div><div style="font-size: .833rem">{segment.destination.airport}<br />{calc.distance} miles</div>',
                    "marker": f"{segment.destination.market.lower() if segment.destination.market else 'int'}-airport",
                    "position": (segment.destination.longitude, segment.destination.latitude),
                    "size": 56,
                }
                for segment, calc in zip(segments, calculations)
            ]
        ]

        _render_map(arclayer_and_textlayer_data, arclayer_and_textlayer_data, iconlayer_data, height=340)

    # Show the calculation details.
    calculations_data = [
        (
            segment.airline.name,
            f"{segment.origin.airport_code}–{segment.destination.airport_code}",
            "" if calc.region == "*" else calc.region,
            calc.distance,
            segment.fare_brand.name if segment.fare_brand != NoBrand else calc.service,
            segment.fare_class,
            f"{round(calc.sqm_earning_rate * 100)}%",
            calc.sqm,
            0,
            f"{round(calc.pts_earning_rate * 100)}%",
            calc.pts,
            f"{round(calc.pts_bonus_factor * 100)}%",
            calc.pts_bonus,
            calc.pts + calc.pts_bonus,
        )
        for segment, calc in zip(segments, calculations)
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
                "selector": f"th.row{index}",
                "props": f"color: white; background-color: {segment.colour}; border-color: {segment.colour}"
            }
            for index, segment in enumerate(segments)
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
            "tooltip": f'<div><strong>{destination.city}</strong> {destination.airport_code}</div><div style="font-size: .833rem">{destination.airport}<br />{data[-1] or data[-2]} miles</div>',
            "source_position": (origin.longitude, origin.latitude),
            "target_position": (destination.longitude, destination.latitude),
            "source_colour": MARKET_COLOURS.get(destination.market, (180, 180, 180)),
            "target_colour": MARKET_COLOURS.get(destination.market, (180, 180, 180)),
        }
        for destination, data in zip(destination_airports, distances_data)
    ]

    textlayer_data = [
        {
            "tooltip": f'<div><strong>{destination.city}</strong> {destination.airport_code}</div><div style="font-size: .833rem">{destination.airport}<br />{data[-1] or data[-2]} miles</div>',
            "distance": data[-1] or data[-2],
            "text": destination.airport_code,
            "position": (destination.longitude, destination.latitude),
        }
        for destination, data in zip(destination_airports, distances_data)
    ]

    iconlayer_data = [
        {
            "tooltip": f'<div><strong>{origin.city}</strong> {origin.airport_code}</div><div style="font-size: .833rem">{origin.airport}</div>',
            "marker": "airplane",
            "position": (origin.longitude, origin.latitude),
            "size": 48,
        },
        *[
            {
                "tooltip": f'<div><strong>{destination.city}</strong> {destination.airport_code}</div><div style="font-size: .833rem">{destination.airport}<br />{data[-1] or data[-2]} miles</div>',
                "marker": f"{destination.market.lower() if destination.market else 'int'}-airport",
                "position": (destination.longitude, destination.latitude),
                "size": 56,
            }
            for destination, data in zip(destination_airports, distances_data)
        ],
    ]

    _render_map(arclayer_data, textlayer_data, iconlayer_data, ctr_lon=origin.longitude, ctr_lat=origin.latitude, zoom=4, get_width=2, height=540)
    st.table(distances_df)


def _render_map(arclayer_data=None, textlayer_data=None, iconlayer_data=None, ctr_lon=None, ctr_lat=None, zoom=None, get_width=6, height=400):
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

    if iconlayer_data:
        # https://deck.gl/docs/api-reference/layers/icon-layer
        layers.append(pdk.Layer(
            "IconLayer",
            iconlayer_data,
            pickable=True,
            icon_atlas="https://raw.githubusercontent.com/kinghuang/ac-calc/map-icons/icons/map-icons.png",
            icon_mapping={
                "airplane": {"x": 0, "y": 0, "width": 128, "height": 128},
                "small-airplane": {"x": 128, "y": 0, "width": 128, "height": 128},
                "airplane-taking-off": {"x": 256, "y": 0, "width": 128, "height": 128},
                "airplane-landing": {"x": 384, "y": 0, "width": 128, "height": 128},

                "dom-airport": {"x": 0, "y": 256, "width": 128, "height": 128},
                "tnb-airport": {"x": 128, "y": 256, "width": 128, "height": 128},
                "sun-airport": {"x": 256, "y": 256, "width": 128, "height": 128},
                "int-airport": {"x": 384, "y": 256, "width": 128, "height": 128},
            },
            get_icon="marker",
            get_position="position",
            get_size="size",
        ))

    if textlayer_data:
        # https://deck.gl/docs/api-reference/layers/text-layer
        layers.append(pdk.Layer(
            "TextLayer",
            textlayer_data,
            pickable=True,
            get_position="position",
            get_text="text",
            get_font_family='"Source Sans Pro", sans-serif',
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
        tooltip={"html": "{tooltip}"},
    )
    deck.picking_radius = 20

    st.pydeck_chart(deck)


if __name__ == "__main__":
    main()
