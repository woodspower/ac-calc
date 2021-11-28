import pandas as pd
import streamlit as st

from ac_aqd.aeroplan import AEROPLAN_STATUSES, FARE_BRANDS
from ac_aqd.airlines import AIRLINES, DEFAULT_AIRLINE_INDEX
from ac_aqd.data import AIRPORTS, COUNTRIES, DISTANCES, DEFAULT_ORIGIN_AIRPORT_INDEX
from ac_aqd.itinerary import Itinerary, Segment


def main():
    st.set_page_config(page_title="AC Aeroplan Calculator", layout="wide")

    tools = {
        "Calculate Miles and Dollars": calculate_miles_dollars,
        "Browse Airlines": browse_airlines,
        "Browse Distances": browse_distances,
    }
    tool_title = st.sidebar.radio("Tool", tools.keys())
    tool = tools[tool_title]
    tool(tool_title)


def calculate_miles_dollars(title):
    st.header(title)

    if "itineraries" not in st.session_state:
        st.session_state["itineraries"] = [Itinerary()]

    for itinerary in st.session_state["itineraries"]:
        segments_placeholder = st.empty()

        if st.button("Add Segment"):
            ref_segment = itinerary.segments[-1]

            itinerary.segments.append(Segment(
                airline=ref_segment.airline,
                origin=ref_segment.destination,
                destination=ref_segment.origin,
                fare_class=ref_segment.fare_class,
                fare_brand=ref_segment.fare_brand,
            ))

        with segments_placeholder.container():
            st.markdown("""
            <style>

            </style>
            """, unsafe_allow_html=True)

            for index, segment in enumerate(itinerary.segments):
                is_first = index == 0

                # with st.expander(f"Segment {index + 1}", expanded=True):
                airline_col, origin_col, destination_col, fare_brand_col, fare_class_col = st.columns((3, 2, 2, 3, 1))

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


def browse_airlines(title):
    st.header(title)

    airline = st.selectbox(
        "Airline ✈️",
        AIRLINES,
        index=DEFAULT_AIRLINE_INDEX,
        format_func=lambda airline: airline.name,
        help="Operating airline.",
    )

    st.subheader(airline.name)
    st.markdown(airline.region)


def browse_distances(title):
    st.header(title)

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
