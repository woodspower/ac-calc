from itertools import groupby
from PIL import ImageColor
import string

import pydeck as pdk
import pandas as pd
import streamlit as st
from streamlit.elements.map import _get_zoom_level

from ac_calc.aeroplan import NoBrand, AEROPLAN_STATUSES, DEFAULT_AEROPLAN_STATUS, DEFAULT_FARE_BRAND_INDEX, FARE_BRANDS
from ac_calc.airlines import AirCanada, AIRLINES
from ac_calc.locations import airports, airports_by_code


SEGMENT_KEYS = ("airline", "origin", "destination", "fare_brand", "fare_class", "colour")
SEGMENT_COLOURS = (
    "#c50014",
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
    "SUN": (233, 171, 154),
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
    tool_title = st.sidebar.radio("Tool:", tools.keys())
    tool = tools[tool_title]
    tool(tool_title)


def calculate_points_miles(title):
    def segments():
        for i in range(st.session_state["num_segments"]):
            yield [st.session_state[f"{key}-{i}"] for key in SEGMENT_KEYS]

    with st.sidebar:
        st.text_input(
            "Ticket Number:",
            value="014",
            key="ticket_number",
            help="First three digits or full ticket number. Air Canada is 014.",
        )

        st.radio(
            "Aeroplan Status:",
            AEROPLAN_STATUSES,
            index=AEROPLAN_STATUSES.index(DEFAULT_AEROPLAN_STATUS),
            format_func=lambda status: status.name,
            key="aeroplan_status",
            help="Air Canada Aeroplan elite status.",
        )

        st.number_input(
            "Number of Segments:",
            min_value=1,
            max_value=99,
            value=1,
            key="num_segments",
            help="Number of segments.",
        )

    st.markdown("""
        <style>
            div[data-testid="stBlock"] div[data-testid="stBlock"]:not([style]):not(:first-child) label {
                display: none
            }
        </style>
        """, unsafe_allow_html=True)

    calc1_col, calc2_col, map_col = st.columns([6, 6, 18])

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
            airline_col, origin_col, destination_col, fare_brand_col, fare_class_col, color_col = st.columns((24, 16, 16, 24, 12, 4))

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
                    "Fare Brand 🍷",
                    FARE_BRANDS,
                    index=DEFAULT_FARE_BRAND_INDEX,
                    format_func=lambda brand: brand.name,
                    help="Air Canada fare brand.",
                    key=f"fare_brand-{index}",
                )
            else:
                st.session_state[f"fare_brand-{index}"] = fare_brand = NoBrand

            fare_class_col.selectbox(
                "Fare Class 🎫",
                list(string.ascii_uppercase) if fare_brand == NoBrand else fare_brand.fare_classes,
                key=f"fare_class-{index}",
            )

            color_col.color_picker(
                "🎨",
                value=SEGMENT_COLOURS[index % len(SEGMENT_COLOURS)],
                key=f"colour-{index}",
            )

    # Perform calculations for the segments.
    segments_and_calculations = [
        (airline, origin, destination, fare_brand, fare_class, colour, airline.calculate(origin, destination, fare_brand, fare_class, st.session_state.ticket_number, st.session_state.aeroplan_status))
        for airline, origin, destination, fare_brand, fare_class, colour in segments()
    ]

    total_distance = sum((calc.distance for _, _, _, _, _, _, calc in segments_and_calculations))
    total_app = sum((calc.app for _, _, _, _, _, _, calc in segments_and_calculations))
    total_app_bonus = sum((calc.app_bonus for _, _, _, _, _, _, calc in segments_and_calculations))
    total_sqm = sum((calc.sqm for _, _, _, _, _, _, calc in segments_and_calculations))

    # Show the itinerary/segments stats.
    with calc1_col:
        st.metric("Distance", f"{total_distance} miles")
        st.metric("Aeroplan Points", total_app)
        st.metric("Aeroplan Points + Status Bonus", total_app + total_app_bonus, delta=total_app_bonus or None)

    # Show the overall calculation.
    with calc2_col:
        st.metric("Status Qualifying Miles", f"{total_sqm} SQM")
        st.metric("Status Qualifying Dollars", f"0 SQD")

    # Show the map.
    with map_col:
        map_data = [
            {
                "label": f"{origin.airport_code}–{destination.airport_code}",
                "distance": calc.distance,
                "source_position": (origin.longitude, origin.latitude),
                "target_position": (destination.longitude, destination.latitude),
                "source_colour": ImageColor.getrgb(colour),
                "target_colour": [c * .85 for c in ImageColor.getrgb(colour)],
            }
            for airline, origin, destination, fare_brand, fare_class, colour, calc in segments_and_calculations
        ]

        _render_map(map_data)

    # Show the calculation details.
    with st.expander("Calculation Details", expanded=True):
        calculations_df = pd.DataFrame([
            (
                airline.name,
                f"{origin.airport_code}–{destination.airport_code}",
                f"{fare_class} ({fare_brand.name})" if fare_brand != NoBrand else fare_class,
                calc.distance,
                round(calc.sqm_earning_rate * 100),
                calc.sqm,
                0.00,
                round(calc.app_earning_rate * 100),
                calc.app,
                round(calc.app_bonus_factor * 100),
                calc.app_bonus,
                calc.app + calc.app_bonus,
            )
            for airline, origin, destination, fare_brand, fare_class, colour, calc in segments_and_calculations
        ], columns=("Airline", "Flight", "Fare (Brand)", "Distance", "SQM %", "SQM", "SQD", "Aeroplan %", "Aeroplan", "Bonus %", "Bonus", "Aeroplan Points"))

        st.dataframe(calculations_df)


def browse_airlines(title):
    airline = st.selectbox(
        "Airline ✈️",
        AIRLINES,
        index=0,
        format_func=lambda airline: airline.name,
        help="Operating airline.",
    )

    st.markdown(f'<div style="font-size:1.666rem">{airline.name}</div>', unsafe_allow_html=True)

    website_col, star_col, app_col, sqm_col = st.columns(4)
    website_col.markdown(f'<div><a href="{airline.website}">{airline.website}</a></div>', unsafe_allow_html=True)
    star_col.markdown(
        "⭐️ Star Alliance member" if airline.star_alliance_member
        else "✈️ Codeshare partner" if airline.codeshare_partner
        else "🧳 Aeroplan partner")
    app_col.markdown("👍 Earn Aeroplan points" if airline.earns_app else "👎 No Aeroplan points")
    sqm_col.markdown("👍 Earn SQM" if airline.earns_sqm else "👎 No SQM")

    # Show the eligible flights for each region and class of service.
    if not airline.earning_rates:
        if airline.codeshare_partner:
            st.markdown(f"Earn Aeroplan points on flights operated by **{airline.name}** with a **4-digit Air Canada flight number**. See **Air Canada** for accrual details.")
        else:
            st.markdown("Redeem Aeroplan points only.")
        return

    for col, earning_rates_item in zip(st.columns(len(airline.earning_rates)), airline.earning_rates.items()):
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
            rates_df.set_index(["Class of service"], inplace=True)

            st.markdown("#### " +  ("All Regions" if region == "*" else region))
            st.dataframe(rates_df)


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

    destination_airports = []
    destination_names = []
    destination_codes = []
    countries = []
    old_distances = []
    new_distances = []

    for _, distance in origin.distances.items():
        destination_airport = airports_by_code()[distance.destination]
        destination_airports.append(destination_airport)

        destination_names.append(destination_airport.airport)
        destination_codes.append(destination_airport.airport_code)
        countries.append(destination_airport.country)
        old_distances.append(distance.old_distance)
        new_distances.append(distance.distance)

    distances_df = pd.DataFrame({
        "Destination Name": destination_names,
        "Destination Code": destination_codes,
        "Country": countries,
        "Distance (Old)": old_distances,
        "Distance (New)": new_distances,
    })

    map_data = [
        {
            "label": destination.airport_code,
            "distance": new_distance or old_distance,
            "source_position": (origin.longitude, origin.latitude),
            "target_position": (destination.longitude, destination.latitude),
            "source_colour": MARKET_COLOURS.get(destination.market, (180, 180, 180)),
            "target_colour": MARKET_COLOURS.get(destination.market, (180, 180, 180)),
        }
        for destination, old_distance, new_distance in zip(destination_airports, old_distances, new_distances)
    ]

    _render_map(map_data, ctr_lon=origin.longitude, ctr_lat=origin.latitude, zoom=4, get_width=2)
    st.table(distances_df)


def _render_map(routes, ctr_lon=None, ctr_lat=None, zoom=None, get_width=6):
    if not ctr_lon or not ctr_lat:
        positions = [
            pos for route_positions in (
                (route["source_position"], route["target_position"])
                for route in routes
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

    # https://deck.gl/docs/api-reference/geo-layers/great-circle-layer
    layer = pdk.Layer(
        "ArcLayer",
        routes,
        pickable=True,
        greatCircle=True,
        get_width=get_width,
        get_height=0,
        get_source_position="source_position",
        get_target_position="target_position",
        get_source_color="source_colour",
        get_target_color="target_colour",
        auto_highlight=True,
    )
    deck = pdk.Deck(
        initial_view_state=pdk.ViewState(
            latitude=ctr_lat,
            longitude=ctr_lon,
            zoom=zoom,
            bearing=0,
            pitch=0,
            height=320,
        ),
        map_style="road",
        layers=[layer],
        tooltip={"html": "<strong>{label}</strong><br/>{distance} miles"}
    )
    deck.picking_radius = 20

    st.pydeck_chart(deck)


if __name__ == "__main__":
    main()
