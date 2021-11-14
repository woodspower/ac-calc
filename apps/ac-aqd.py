import pandas as pd
import streamlit as st

from ac_aqd.data import AIRPORTS, COUNTRIES, DISTANCES


def main():
    st.set_page_config(page_title="AC Aeroplan Calculator", layout="wide")

    tools = {
        "Calculate SQM and SQD": calculate_sqm_sqd,
        "Browse Distances": browse_distances,
    }
    tool_title = st.sidebar.radio("Tool", tools.keys())
    tool = tools[tool_title]
    tool(tool_title)


def calculate_sqm_sqd(title):
    st.header(title)


def browse_distances(title):
    st.header(title)

    origin = st.selectbox(
        "Origin 🛫",
        AIRPORTS,
        # index=DEFAULT_ORIGIN_AIRPORT_INDEX,
        index=0,
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
