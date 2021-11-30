from collections import defaultdict, namedtuple
import csv
import json
from functools import cache
from importlib import resources


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


@cache
def _load_aeroplan_distances():
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


@cache
def _load_airports():
    _distances = _load_aeroplan_distances()

    # Load and return list of airports, including distances to other airports.
    with resources.open_text("ac_calc.locations", "airports.json") as f:
        airports_data = json.load(f)
        airports = [
            Airport(**airport_data, distances=_distances.get(airport_data["airport_code"], {}))
            for airport_data in airports_data
        ]

    return airports


AIRPORTS = _load_airports()


DEFAULT_ORIGIN_AIRPORT_INDEX, DEFAULT_ORIGIN_AIRPORT = next(
    filter(lambda e: e[1].airport_code == "YYC", enumerate(AIRPORTS))
)
DEFAULT_DESTINATION_AIRPORT_INDEX, DEFAULT_DESTINATION_AIRPORT = next(
    filter(lambda e: e[1].airport_code == "YYZ", enumerate(AIRPORTS))
)
