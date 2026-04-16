"""
Re-export of demo market fixtures from mmfm.demo.demo_markets.

Import from here in tests; CLI imports directly from mmfm.demo.demo_markets.
"""
from mmfm.demo.demo_markets import (  # noqa: F401
    PEMBA_EDUARDO_MONDLANE,
    KISUMU_MUNICIPAL,
    TSOKA_LILONGWE,
    LIZULU_LILONGWE,
    CHAINDA_LUSAKA,
    DEMO_PORTFOLIO,
)
