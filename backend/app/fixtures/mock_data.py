"""Simulated fixtures for mock mode.

Everything here is fictional. Brands, shops, addresses and URLs are invented
(URLs use the reserved example.com domain) and are always labelled as simulated.
"""

MOCK_SCENARIOS = {
    "normal": "Normal condition: light cosmetic wear only",
    "visible_damage": "Visible damage in one view, other views look normal",
    "suspected_risk": "Suspected battery swelling (safety risk)",
    "unknown_model": "No readable identity evidence",
    "missing_market_data": "No local price data found",
    "provider_failure": "Price and service providers fail (partial results)",
}
DEFAULT_SCENARIO = "visible_damage"

UNASSESSABLE = {
    "mobile": [
        "Battery health and charge capacity",
        "Internal components and liquid exposure indicators",
        "Display and touch function (device is off)",
        "Storage, account locks and software state",
    ],
    "laptop": [
        "Battery health and charge capacity",
        "Internal components, fans and storage drive",
        "Display function (device is off)",
        "Keyboard and touchpad function",
    ],
}

COSMETIC = {
    "mobile": {
        "kind": "cosmetic_wear",
        "part": "Back panel",
        "description": "Light scratches across the back panel.",
        "views": ["back"],
        "visible_evidence": "Fine scratches visible in reflected light; no cracks or dents.",
        "uncertainty": "low",
        "uncertainty_reason": "Marks are clearly visible and appear to be surface-level.",
        "risk_type": None,
    },
    "laptop": {
        "kind": "cosmetic_wear",
        "part": "Outer lid corners",
        "description": "Scuffs on two corners of the outer lid.",
        "views": ["lid"],
        "visible_evidence": "Paint worn at the corners; the lid surface is otherwise flat.",
        "uncertainty": "low",
        "uncertainty_reason": "Wear is clearly visible; no deformation seen.",
        "risk_type": None,
    },
}

DAMAGE = {
    "mobile": {
        "kind": "physical_damage",
        "part": "Front glass",
        "description": "Cracked front glass, spreading from the lower-left corner.",
        "views": ["front"],
        "visible_evidence": "Crack lines visible across the lower half of the screen glass.",
        "uncertainty": "medium",
        "uncertainty_reason": (
            "Cannot tell from photos whether the crack is in a screen protector or the display glass, "
            "or whether the display underneath is affected."
        ),
        "risk_type": None,
    },
    "laptop": {
        "kind": "physical_damage",
        "part": "Left hinge cover",
        "description": "Hinge cover on the left side is cracked and partly detached.",
        "views": ["left"],
        "visible_evidence": "A gap and crack line where the hinge cover meets the base.",
        "uncertainty": "medium",
        "uncertainty_reason": "The hinge mechanism itself is not visible; only the cover is.",
        "risk_type": None,
    },
}

RISK = {
    "mobile": {
        "kind": "suspected_safety_risk",
        "part": "Back panel / battery area",
        "description": "Back panel appears lifted along the left edge, which can indicate battery swelling.",
        "views": ["back", "left"],
        "visible_evidence": "A visible gap between the back panel and the frame on the left edge.",
        "uncertainty": "medium",
        "uncertainty_reason": "A lifted panel can also come from adhesive failure or a case; photos cannot confirm swelling.",
        "risk_type": "swelling",
    },
    "laptop": {
        "kind": "suspected_safety_risk",
        "part": "Underside / battery area",
        "description": "Underside panel bulges near the battery area and the touchpad sits raised.",
        "views": ["underside", "keyboard"],
        "visible_evidence": "Uneven underside surface and a raised touchpad edge.",
        "uncertainty": "medium",
        "uncertainty_reason": "Photos cannot confirm battery swelling; a warped panel is also possible.",
        "risk_type": "swelling",
    },
}

IDENTITY_KNOWN = {
    "mobile": {
        "evidence_strength": "moderate",
        "candidates": [
            {"brand": "Examplephone", "model": "X12 (simulated)", "evidence": "Simulated logo on the back panel."},
            {"brand": "Examplephone", "model": "X12 Plus (simulated)", "evidence": "Similar camera layout."},
        ],
        "visible_specs": ["Simulated label: 128 GB"],
        "notes": "Simulated identity suggestion. Confirm or correct it; photos alone do not prove the model.",
    },
    "laptop": {
        "evidence_strength": "moderate",
        "candidates": [
            {"brand": "Examplebook", "model": "Air 14 (simulated)", "evidence": "Simulated label on the underside."},
        ],
        "visible_specs": ["Simulated label: 8 GB RAM, 256 GB SSD"],
        "notes": "Simulated identity suggestion. Confirm or correct it; photos alone do not prove the model.",
    },
}

IDENTITY_UNKNOWN = {
    "evidence_strength": "none",
    "candidates": [],
    "visible_specs": [],
    "notes": "No readable logo, label or model number in the photos (simulated).",
}

# Simulated Thai market price fixtures, keyed by device type. Amounts in THB.
# Only "TH" has simulated data so the "no foreign price substitution" rule is visible elsewhere.
MOCK_PRICE_COUNTRIES = {"TH": "THB"}

PRICES = {
    "mobile": {
        "asking_working": (9000, 11000),
        "asking_damaged": (4000, 5500),
        "buyback_working": (6500, 7500),
        "buyback_damaged": (2500, 3200),
        "quotes": {
            "front_glass_or_screen": [("repair_quote", "aftermarket", (1800, 2400)), ("part_price", "genuine", (2800, 3200)), ("repair_labor", "not_applicable", (500, 800))],
            "charging_port": [("repair_quote", "unknown", (800, 1200))],
            "battery": [("repair_quote", "unknown", (1200, 1800))],
            "display_panel": [("repair_quote", "unknown", (2500, 3500))],
            "back_panel": [("repair_quote", "unknown", (900, 1400))],
        },
    },
    "laptop": {
        "asking_working": (12000, 15000),
        "asking_damaged": (5000, 7000),
        "buyback_working": (8000, 9500),
        "buyback_damaged": (3000, 4000),
        "quotes": {
            "hinge": [("repair_quote", "unknown", (1500, 2500))],
            "charging_port": [("repair_quote", "unknown", (1000, 1600))],
            "battery": [("part_price", "aftermarket", (1400, 2000)), ("repair_labor", "not_applicable", (300, 500))],
            "display_panel": [("repair_quote", "unknown", (3500, 5000))],
            "keyboard": [("repair_quote", "unknown", (1500, 2200))],
        },
    },
}

# Fictional services, placed at small offsets from the user's coordinates when supplied.
SERVICES = [
    ("Example Device Repair (simulated)", "repair", 0.010, 0.012, "Lists phone and laptop repair (simulated listing)."),
    ("Sample Fix Corner (simulated)", "repair", -0.021, 0.006, "Lists screen and battery repair (simulated listing)."),
    ("Demo Trade-in Desk (simulated)", "buyback", 0.004, -0.018, "Lists used device buyback (simulated listing)."),
    ("Placeholder E-waste Drop-off (simulated)", "recycling", -0.030, -0.025, "Lists electronics recycling drop-off (simulated listing)."),
]
