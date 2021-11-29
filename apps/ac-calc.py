import pandas as pd
import streamlit as st

from ac_calc.aeroplan import NoBrand, AEROPLAN_STATUSES, DEFAULT_AEROPLAN_STATUS, FARE_BRANDS
from ac_calc.airlines import AirCanada, AIRLINES, DEFAULT_AIRLINE_INDEX
from ac_calc.locations import AIRPORTS, COUNTRIES, DISTANCES, DEFAULT_ORIGIN_AIRPORT_INDEX
from ac_calc.itinerary import Segment


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
    segments = st.session_state["segments"] if "segments" in st.session_state else [Segment()]

    with st.sidebar:
        st.text_input(
            "Ticket Number:",
            value="014",
            help="First three digits or full ticket number. Air Canada is 014.",
            key="ticket_number",
        )

        st.selectbox(
            "Aeroplan Status:",
            AEROPLAN_STATUSES,
            index=AEROPLAN_STATUSES.index(DEFAULT_AEROPLAN_STATUS),
            format_func=lambda status: status.name,
            key="aeroplan_status",
            help="Air Canada Aeroplan elite status."
        )

    earnings_placeholder = st.container()
    segments_placeholder = st.container()

    st.markdown("##### Segments")

    segments_placeholder = st.container()

    if st.button("Add Segment"):
        if segments:
            ref_segment = segments[-1]

            segments.append(Segment(
                airline=ref_segment.airline,
                origin=ref_segment.destination,
                destination=ref_segment.origin,
                fare_class=ref_segment.fare_class,
                fare_brand=ref_segment.fare_brand,
            ))
        else:
            segments.append(Segment())

    st.markdown("""
        <style>
            div[data-testid="stBlock"] div[data-testid="stBlock"]:not([style]):not(:first-child) label {
                display: none
            }
        </style>
        """, unsafe_allow_html=True)

    for index, segment in enumerate(segments):
        is_first = index == 0

        airline_col, origin_col, destination_col, fare_brand_col, fare_class_col, remove_col = segments_placeholder.columns((24, 16, 16, 24, 8, 4))

        segment.airline = airline_col.selectbox(
            "Airline ✈️",
            AIRLINES,
            index=AIRLINES.index(segment.airline),
            format_func=lambda airline: airline.name,
            help="Flight segment operating airline.",
            key=f"airline-{index}",
        )
        segment.origin = origin_col.selectbox(
            "Origin 🛫",
            AIRPORTS,
            index=AIRPORTS.index(segment.origin),
            format_func=lambda airport: airport.iata_code,
            help="Flight segment origin airport code.",
            key=f"origin-{index}",
        )
        segment.destination = destination_col.selectbox(
            "Destination 🛬",
            AIRPORTS,
            index=AIRPORTS.index(segment.destination),
            format_func=lambda airport: airport.iata_code,
            help="Flight segment destination airport code.",
            key=f"destination-{index}",
        )
        if segment.airline == AirCanada:
            segment.fare_brand = fare_brand_col.selectbox(
                "Fare Brand",
                FARE_BRANDS,
                index=FARE_BRANDS.index(segment.fare_brand),
                format_func=lambda brand: brand.name,
                help="Air Canada fare brand. Select “None” for non-Air Canada fares.",
                key=f"fare_brand-{index}",
            )
        segment.fare_class = fare_class_col.selectbox(
            "Fare Class",
            segment.fare_brand.fare_classes,
            index=segment.fare_brand.fare_classes.index(segment.fare_class) if segment.fare_class in segment.fare_brand.fare_classes else 0,
            key=f"fare_class-{index}",
        )

    st.session_state["segments"] = segments

    segment_calculations = [segment.calculate(st.session_state.ticket_number, st.session_state.aeroplan_status) for segment in segments]

    total_distance = sum((calc.distance for calc in segment_calculations))
    total_app = sum((calc.app for calc in segment_calculations))
    total_app_bonus = sum((calc.app_bonus for calc in segment_calculations))
    total_sqm = sum((calc.sqm for calc in segment_calculations))

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
            segment.airline.name,
            f"{segment.origin.iata_code}–{segment.destination.iata_code}",
            f"{segment.fare_class} ({segment.fare_brand.name})" if segment.fare_brand != NoBrand else segment.fare_class,
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
        for segment, calc in zip(segments, segment_calculations)
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
