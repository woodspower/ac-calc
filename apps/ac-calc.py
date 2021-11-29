import string

import pandas as pd
import streamlit as st

from ac_calc.aeroplan import NoBrand, AEROPLAN_STATUSES, DEFAULT_AEROPLAN_STATUS, DEFAULT_FARE_BRAND_INDEX, FARE_BRANDS
from ac_calc.airlines import AirCanada, AIRLINES, DEFAULT_AIRLINE_INDEX
from ac_calc.locations import AIRPORTS, COUNTRIES, DISTANCES, DEFAULT_ORIGIN_AIRPORT_INDEX, DEFAULT_DESTINATION_AIRPORT_INDEX


SEGMENT_KEYS = ("airline", "origin", "destination", "fare_brand", "fare_class")


def main():
    st.set_page_config(
        page_title="AC Calculator",
        layout="wide",
        menu_items={
            "Get help": "https://www.flyertalk.com/forum/air-canada-aeroplan/1744575-new-improved-calculator-aqm-aeroplan-miles-aqd.html",
            "Report a Bug": None,
            "About": "Aeroplan points and miles calculator. Based on [github.com/scottkennedy/ac-aqd](https://github.com/scottkennedy/ac-aqd).",
        }
    )

    tools = {
        "Calculate Points and Miles": calculate_points_miles,
        "Browse Airlines": browse_airlines,
        "Browse Distances": browse_distances,
    }
    tool_title = st.sidebar.radio("Tool:", tools.keys())
    tool = tools[tool_title]
    tool(tool_title)


def calculate_points_miles(title):
    def adjust_segments():
        num_segments = st.session_state["num_segments"]

        for i in range(num_segments, 99 + 1):
            for key in SEGMENT_KEYS:
                if f"{key}-{i}" in st.session_state:
                    del st.session_state[f"{key}-{i}"]

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

        st.selectbox(
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
            on_change=adjust_segments,
        )

    earnings_placeholder = st.container()

    st.markdown("##### Segments")

    st.markdown("""
        <style>
            div[data-testid="stBlock"] div[data-testid="stBlock"]:not([style]):not(:first-child) label {
                display: none
            }
        </style>
        """, unsafe_allow_html=True)

    with st.container():
        for index in range(st.session_state["num_segments"]):
            airline_col, origin_col, destination_col, fare_brand_col, fare_class_col, remove_col = st.columns((24, 16, 16, 24, 8, 4))

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
                AIRPORTS,
                index=DEFAULT_ORIGIN_AIRPORT_INDEX,
                format_func=lambda airport: airport.iata_code,
                help="Flight segment origin airport code.",
                key=f"origin-{index}",
            )

            destination_col.selectbox(
                "Destination 🛬",
                AIRPORTS,
                index=DEFAULT_DESTINATION_AIRPORT_INDEX,
                format_func=lambda airport: airport.iata_code,
                help="Flight segment destination airport code.",
                key=f"destination-{index}",
            )

            if airline == AirCanada:
                fare_brand = fare_brand_col.selectbox(
                    "Fare Brand",
                    FARE_BRANDS,
                    index=DEFAULT_FARE_BRAND_INDEX,
                    format_func=lambda brand: brand.name,
                    help="Air Canada fare brand.",
                    key=f"fare_brand-{index}",
                )
            else:
                st.session_state[f"fare_brand-{index}"] = fare_brand = NoBrand

            fare_class_col.selectbox(
                "Fare Class",
                list(string.ascii_uppercase) if fare_brand == NoBrand else fare_brand.fare_classes,
                key=f"fare_class-{index}",
            )

    segments_and_calculations = [
        (airline, origin, destination, fare_brand, fare_class, airline.calculate(origin, destination, fare_brand, fare_class, st.session_state.ticket_number, st.session_state.aeroplan_status))
        for airline, origin, destination, fare_brand, fare_class in segments()
    ]

    total_distance = sum((calc.distance for _, _, _, _, _, calc in segments_and_calculations))
    total_app = sum((calc.app for _, _, _, _, _, calc in segments_and_calculations))
    total_app_bonus = sum((calc.app_bonus for _, _, _, _, _, calc in segments_and_calculations))
    total_sqm = sum((calc.sqm for _, _, _, _, _, calc in segments_and_calculations))

    # with earnings_placeholder.expander("Earnings", expanded=True):
    with earnings_placeholder:
        distance_col, app_col, app_total_col, sqm_col, sqd_col = st.columns(5)

        distance_col.metric("Distance", f"{total_distance} miles")
        app_col.metric("Aeroplan Points", total_app)
        app_total_col.metric("Aeroplan Points + Status Bonus", total_app + total_app_bonus, delta=total_app_bonus or None)
        sqm_col.metric("Status Qualifying Miles", f"{total_sqm} SQM")
        sqd_col.metric("Status Qualifying Dollars", f"0 SQD")

    st.markdown("##### Calculation Details")

    calculations_df = pd.DataFrame([
        (
            airline.name,
            f"{origin.iata_code}–{destination.iata_code}",
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
        for airline, origin, destination, fare_brand, fare_class, calc in segments_and_calculations
    ], columns=("Airline", "Flight", "Fare (Brand)", "Distance", "SQM %", "SQM", "SQD", "Aeroplan %", "Aeroplan", "Bonus %", "Bonus", "Aeroplan Points"))

    st.dataframe(calculations_df)


def browse_airlines(title):
    airline = st.selectbox(
        "Airline ✈️",
        AIRLINES,
        index=DEFAULT_AIRLINE_INDEX,
        format_func=lambda airline: airline.name,
        help="Operating airline.",
    )

    st.header(airline.name)
    st.markdown(airline.region)


def browse_distances(title):
    origin = st.selectbox(
        "Origin 🛫",
        AIRPORTS,
        index=DEFAULT_ORIGIN_AIRPORT_INDEX,
        format_func=lambda airport: airport.iata_code,
        help="Flight origin airport code.",
    )

    destinations = []
    old_distances = []
    new_distances = []

    for _, distance in origin.distances.items():
        destinations.append(distance.destination)
        old_distances.append(distance.old_distance)
        new_distances.append(distance.distance)

    distances_df = pd.DataFrame({
        "destination": destinations,
        "old": old_distances,
        "new": new_distances,
    })

    st.table(distances_df)


if __name__ == "__main__":
    main()
