from collections import defaultdict, namedtuple
import csv
from functools import cache
from importlib import resources


Airport = namedtuple("Airport", ("iata_code,country,latitude,longitude,distances"))
Country = namedtuple("Country", ("country", "continent"))
Distance = namedtuple("Distance", ("origin,destination,old_distance,distance"))


@cache
def _load_country_continents():
    with resources.open_text("ac_aqd.locations", "country_continents.csv") as f:
        reader = csv.reader(f)
        assert(next(reader) == ["country", "continent"])
        countries = tuple(map(Country._make, reader))

    return {country.country: country for country in countries}


@cache
def _load_aeroplan_distances():
    with resources.open_text("ac_aqd.locations", "aeroplan_distances.csv") as f:
        reader = csv.reader(f)
        assert(next(reader) == ["origin", "destination", "old_distance", "distance"])
        distances = defaultdict(dict)
        for distance in map(Distance._make, reader):
            distances[distance.origin][distance.destination] = distance
            distances[distance.destination][distance.origin] = Distance(
                distance.destination,
                distance.origin,
                distance.old_distance,
                distance.distance,
            )

    return distances


@cache
def _load_airports():
    _countries = _load_country_continents()
    _distances = _load_aeroplan_distances()

    # Load and return list of airports, resolving the countries to
    # Country tuples and including distances to other airports.
    with resources.open_text("ac_aqd.locations", "airports.csv") as f:
        reader = csv.reader(f)
        assert(next(reader) == ["iata_code", "country", "latitude", "longitude"])
        airports = [
            Airport(
                row[0],
                _countries[row[1]],
                row[2],
                row[3],
                _distances.get(row[0], {})
            )
            for row in reader
        ]

    return airports


AIRPORTS = _load_airports()
COUNTRIES = _load_country_continents()
DISTANCES = _load_aeroplan_distances()


DEFAULT_ORIGIN_AIRPORT_INDEX, DEFAULT_ORIGIN_AIRPORT = next(
    filter(lambda e: e[1].iata_code == "YYC", enumerate(AIRPORTS))
)
DEFAULT_DESTINATION_AIRPORT_INDEX, DEFAULT_DESTINATION_AIRPORT = next(
    filter(lambda e: e[1].iata_code == "YYZ", enumerate(AIRPORTS))
)
