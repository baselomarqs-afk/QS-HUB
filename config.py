# All shared constants for the QTO system

FLOOR_LABELS = {
    "gf": {"en": "Ground Floor", "ar": "الدور الأرضي"},
    "f1": {"en": "1st Floor", "ar": "الدور الأول"},
    "f2": {"en": "2nd Floor", "ar": "الدور الثاني"},
    "roof": {"en": "Roof", "ar": "السطح"},
}

DEFAULT_HEIGHTS = {
    "gf": 4.0,
    "f1": 4.0,
    "f2": 4.0,
    "roof": 3.5,
}

SLAB_THICKNESS_DEFAULT = 0.20  # meters

UNITS = {
    "m3": "m³",
    "m2": "m²",
    "m":  "m",
    "nr": "Nr",
    "ls": "L.S",
}

BOQ_SECTIONS = [
    "Sub-Structure | الأعمال تحت الأرض",
    "Super-Structure | الأعمال العلوية",
    "Finishes - Ground Floor | تشطيبات الأرضي",
    "Finishes - 1st Floor | تشطيبات الأول",
    "Finishes - 2nd Floor | تشطيبات الثاني",
    "Openings | الفتحات",
    "Setting Out | أعمال الموقع",
]
