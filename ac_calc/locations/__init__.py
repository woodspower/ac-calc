from collections import defaultdict, namedtuple
import csv
import json
from functools import cache
from importlib import resources

import streamlit as st


Airport = namedtuple("Airport", (
    "airport",
    "airport_code",
    "latitude",
    "longitude",
    "continent",
    "country",
    "country_code",
    "state",
    "state_code",
    "city",
    "city_code",
    "group",
    "market",
    "nearby",
    "distances",
), defaults=(None,) * 15)


Distance = namedtuple("Distance", ("origin,destination,old_distance,distance"))


@st.experimental_singleton
def aeroplan_distances():
    with resources.open_text("ac_calc.locations", "aeroplan_distances.csv") as f:
        reader = csv.reader(f)
        assert(next(reader) == ["origin", "destination", "old_distance", "distance"])
        distances = defaultdict(dict)
        for distance in map(Distance._make, reader):
            old_distance = int(distance.old_distance) if distance.old_distance else 0
            new_distance = int(distance.distance) if distance.distance else 0

            distances[distance.origin][distance.destination] = Distance(
                distance.origin,
                distance.destination,
                old_distance,
                new_distance,
            )
            distances[distance.destination][distance.origin] = Distance(
                distance.destination,
                distance.origin,
                old_distance,
                new_distance,
            )

    return distances


@st.experimental_singleton
def airports():
    _distances = aeroplan_distances()

    # Load and return list of airports, including distances to other airports.
    with resources.open_text("ac_calc.locations", "airports.json") as f:
        airports_data = json.load(f)
        airports = [
            Airport(**airport_data, distances=_distances.get(airport_data["airport_code"], {}))
            for airport_data in airports_data
        ]

    return airports


@st.experimental_singleton
def airports_by_code():
    return {
        airport.airport_code: airport
        for airport in airports()
    }
