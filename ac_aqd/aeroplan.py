from collections import namedtuple


AeroplanStatus = namedtuple("AeroplanStatus", ("name,bonus_factor,min_status_value"))
FareBrand = namedtuple("FareBrand", ("name", "basis_codes", "fare_classes", "status_factor", "redeemable_factor"))


NoStatus = AeroplanStatus("None", 0.0, 0)
Prestige25K = AeroplanStatus("Prestige 25K", 0.25, 250)
Elite35K = AeroplanStatus("Elite 35K", 0.35, 250)
Elite50K = AeroplanStatus("Elite 50K", 0.50, 250)
Elite75K = AeroplanStatus("Elite 75K", 0.75, 250)
SuperElite100K = AeroplanStatus("Super Elite 100K", 1.0, 250)


AEROPLAN_STATUSES = (
    NoStatus,
    Prestige25K,
    Elite35K,
    Elite50K,
    Elite75K,
    SuperElite100K,
)


NoBrand = FareBrand("None", tuple(), [c for c in "JCDZPOENYBMUHQVWGSTLAK"], 0.0, 0.0),
Basic = FareBrand("Basic", ("BA", "GT"), [c for c in "YBMUHQVWGSTLAK"], 0.25, 0.25),
Standard = FareBrand("Standard", ("TG",), [c for c in "YBMUHQVWGSTLAK"], 0.5, 0.25),
Flex = FareBrand("Flex", ("FL",), [c for c in "YBMUHQVWGSTLAK"], 1.0, 1.0),
Comfort = FareBrand("Comfort", ("CO",), [c for c in "YBMUHQVWGSTLAK"], 1.15, 1.15),
Latitude = FareBrand("Latitude", ("LT",), [c for c in "YBMUHQVWGSTLAK"], 1.25, 1.25),
PremiumEconomyLowest = FareBrand("Premium Economy (Lowest)", ("PL",), ["O", "E", "N"], 1.25, 1.25),
PremiumEconomyFlexible = FareBrand("Premium Economy (Flexible)", ("PF",), ["O", "E", "N"], 1.25, 1.25),
BusinessLowest = FareBrand("Business (Lowest)", ("EL",), ["J", "C", "D", "Z", "P"], 1.50, 1.50),
BusinessFlexible = FareBrand("Business (Flexible)", ("EF",), ["J", "C", "D", "Z", "P"], 1.50, 1.50),


FARE_BRANDS = (
    NoBrand,
    Basic,
    Standard,
    Flex,
    Comfort,
    Latitude,
    PremiumEconomyLowest,
    PremiumEconomyFlexible,
    BusinessLowest,
    BusinessFlexible,
)


DEFAULT_FARE_BRAND = Flex
DEFAULT_FARE_CLASS = "M"
