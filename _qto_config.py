"""
Central configuration for the villa_qto pipeline.

All paths, API keys, model names, and tunable thresholds live here.
Any other module that needs them imports from this file.

Environment variables (read at import time):
    GOOGLE_API_KEY / AI_API_KEY  — AI Vision key
    ANTHROPIC_API_KEY                — Anthropic key
    STR_PDF_PATH                     — default STR pdf
    ARCH_PDF_PATH                    — default ARCH pdf
    QTO_LOG_LEVEL                    — DEBUG | INFO | WARNING | ERROR
"""
import os, logging, sys

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR             = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR            = os.path.join(ROOT_DIR, ".qto_cache")
SCHEDULE_IMG_DIR     = os.path.join(ROOT_DIR, "_schedule_images")
LOG_DIR              = os.path.join(ROOT_DIR, "_logs")

CLASSIFICATION_JSON  = os.path.join(ROOT_DIR, "_page_classification.json")
SCHEDULE_JSON        = os.path.join(ROOT_DIR, "_schedule_data.json")
ARCH_JSON            = os.path.join(ROOT_DIR, "_arch_data.json")
OPENINGS_JSON        = os.path.join(ROOT_DIR, "_openings_data.json")
WALL_JSON            = os.path.join(ROOT_DIR, "_wall_data.json")
PROJECT_JSON         = os.path.join(ROOT_DIR, "_project_data.json")
REFERENCE_DB_JSON    = os.path.join(ROOT_DIR, "engine", "reference_ranges.json")

for d in (CACHE_DIR, SCHEDULE_IMG_DIR, LOG_DIR):
    os.makedirs(d, exist_ok=True)

# ── AI ────────────────────────────────────────────────────────────────────
AI_MODEL         = "gemini-3.1-flash-lite"
AI_API_KEY       = (os.environ.get("GOOGLE_API_KEY")
                        or os.environ.get("AI_API_KEY", ""))
AI_RETRIES       = 4
AI_RETRY_WAIT_S  = 15        # seconds; multiplied by attempt number
AI_CACHE_ENABLED = True

# ── Default PDFs (overridable via env var or CLI) ─────────────────────────────
DEFAULT_STR_PDF      = os.environ.get("STR_PDF_PATH",  r"B:\work\2 villas\New folder\STR-002.pdf")
DEFAULT_ARCH_PDF     = os.environ.get("ARCH_PDF_PATH", r"B:\work\2 villas\New folder\ARCH-002.pdf")

# ── DPI tiers ─────────────────────────────────────────────────────────────────
DPI_CLASSIFY         = 180       # fast page-type identification
DPI_LAYOUT           = 220       # full-page layouts (count beams etc.)
DPI_SCHEDULE         = 300       # small schedule tables — need fine text
DPI_ELEVATION        = 250       # facades need decent detail for dimension text

# ── Sanity-check ranges (UAE villa typical) ───────────────────────────────────
SANITY = {
    "plot_area":           (200,  5000),    # m²
    "gf_area":             (100,  1500),    # m²
    "external_perimeter":  (30,   250),     # m
    "total_villa_height":  (4,    20),      # m
    "footing_depth_mm":    (300,  1000),
    "footing_long_mm":     (600,  6000),
    "tie_beam_width_mm":   (150,  500),
    "tie_beam_depth_mm":   (400,  800),
    "column_width_mm":     (150,  600),
    "column_depth_mm":     (200,  1000),
    "slab_thickness_mm":   (150,  350),
    "beam_width_mm":       (150,  600),
    "beam_depth_mm":       (300,  900),
    "foundation_total_m3": (20,   200),
    "wall_to_area_ratio":  (0.3,  5.0),     # internal walls m per floor m²
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = getattr(logging, os.environ.get("QTO_LOG_LEVEL", "INFO").upper(), logging.INFO)
LOG_FILE  = os.path.join(LOG_DIR, "qto.log")


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger. Idempotent — safe to call multiple times."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(LOG_LEVEL)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)-30s | %(message)s",
        datefmt="%H:%M:%S",
    )
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(LOG_LEVEL)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    # File handler (always DEBUG so we have a paper trail)
    try:
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass
    logger.propagate = False
    return logger


# ── Villa-type derivation ─────────────────────────────────────────────────────
def derive_villa_type(structural_levels: int | None) -> str:
    """
    Derive UAE villa nomenclature from total structural levels.

      1 → G        (ground floor only)
      2 → G        (GF + roof)
      3 → G+1      (GF + 1F + roof)
      4 → G+2      (GF + 1F + 2F + roof)
      5 → G+3      etc.
    """
    if structural_levels is None or structural_levels < 1:
        return "unknown"
    if structural_levels <= 2:
        return "G"
    return f"G+{structural_levels - 2}"
