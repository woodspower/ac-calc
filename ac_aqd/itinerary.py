from dataclasses import dataclass, field

from .aeroplan import FareBrand, DEFAULT_FARE_BRAND, DEFAULT_FARE_CLASS
from .carriers import Carrier, DEFAULT_CARRIER
from .data import Airport, DEFAULT_ORIGIN_AIRPORT, DEFAULT_DESTINATION_AIRPORT


@dataclass
class Segment:
    airline: Carrier = DEFAULT_CARRIER
    origin: Airport = DEFAULT_ORIGIN_AIRPORT
    destination: Airport = DEFAULT_DESTINATION_AIRPORT
    fare_brand: FareBrand = DEFAULT_FARE_BRAND
    fare_class: str = DEFAULT_FARE_CLASS


@dataclass
class Itinerary:
    segments: list[Segment] = field(default_factory=lambda: list([Segment()]))
