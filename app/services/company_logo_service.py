import re
from typing import Dict, Any, Tuple

# Domain mapping for companies appearing in the interview question banks
COMPANY_DOMAINS: Dict[str, str] = {
    "accenture": "accenture.com",
    "accionlabs": "accionlabs.com",
    "acldigital": "acldigital.com",
    "acl digital": "acldigital.com",
    "acqueon": "acqueon.com",
    "altemrik": "altimetrik.com",
    "altimetrik": "altimetrik.com",
    "apexon": "apexon.com",
    "apty": "apty.io",
    "azentio": "azentio.com",
    "bounteous": "bounteous.com",
    "capgemini": "capgemini.com",
    "cepegemini": "capgemini.com",
    "citiustech": "citiustech.com",
    "coforge": "coforge.com",
    "cognissolutions": "cognissolutions.com",
    "cognitivzen": "cognitivzen.com",
    "cognizant": "cognizant.com",
    "curatal": "curatal.com",
    "cyient": "cyient.com",
    "deloitte": "deloitte.com",
    "devon": "devonenergy.com",
    "dotdash meredith": "dotdashmeredith.com",
    "feuji": "feuji.com",
    "gainwell technologies": "gainwelltechnologies.com",
    "grid dynamics": "griddynamics.com",
    "hcl": "hcl.com",
    "innova solutions": "innovasolutions.com",
    "investcloud": "investcloud.com",
    "kpit": "kpit.com",
    "lancesoft": "lancesoft.com",
    "lti mindtree": "ltimindtree.com",
    "ltm": "ltimindtree.com",
    "ltts": "ltts.com",
    "metascope": "metascope.com",
    "mindteck": "mindteck.com",
    "momentive software": "momentivesoftware.com",
    "mphasis": "mphasis.com",
    "mrisoftware": "mrisoftware.com",
    "nisum": "nisum.com",
    "nitor infotech": "nitorinfotech.com",
    "ntt data": "nttdata.com",
    "persistant": "persistent.com",
    "persistent": "persistent.com",
    "photon": "photon.com",
    "planview": "planview.com",
    "protiviti": "protiviti.com",
    "quantiphi": "quantiphi.com",
    "r systems": "rsystems.com",
    "saviynt": "saviynt.com",
    "slk software": "slksoftware.com",
    "streive": "straive.com",
    "straive": "straive.com",
    "synechron": "synechron.com",
    "tenarai": "tenarai.com",
    "transunion": "transunion.com",
    "truglobal": "truglobal.com",
    "vaisesika consulting": "vaisesika.in",
    "valtriix": "valtriix.com",
    "virtusa": "virtusa.com",
    "wipro": "wipro.com",
    "worklife tech": "worklife.io",
    "a5econsulting": "a5econsulting.com"
}

# Dedicated local high-resolution logos for instant zero-latency loading and uncropped display
LOCAL_LOGOS: Dict[str, str] = {
    "cognissolutions": "/static/images/logos/cognissolutions.png",
    "devon": "/static/images/logos/devon.png",
    "quantiphi": "/static/images/logos/quantiphi.png",
    "altemrik": "/static/images/logos/altimetrik.png",
    "altimetrik": "/static/images/logos/altimetrik.png",
    "hcl": "/static/images/logos/hcl.png",
    "worklife tech": "/static/images/logos/worklife.png",
}

# Distinct harmonious color palette for company initials fallback
AVATAR_PALETTES = [
    {"bg": "#eff6ff", "color": "#1d4ed8"},  # Blue
    {"bg": "#f5f3ff", "color": "#6d28d9"},  # Purple
    {"bg": "#ecfdf5", "color": "#047857"},  # Emerald
    {"bg": "#f0fdfa", "color": "#0f766e"},  # Teal
    {"bg": "#fff7ed", "color": "#c2410c"},  # Orange
    {"bg": "#fef2f2", "color": "#b91c1c"},  # Red
    {"bg": "#fdf4ff", "color": "#a21caf"},  # Fuchsia
    {"bg": "#eef2ff", "color": "#4338ca"},  # Indigo
    {"bg": "#f8fafc", "color": "#334155"},  # Slate
    {"bg": "#f0fdf4", "color": "#15803d"},  # Green
]

def get_company_initials(name: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', name).strip()
    words = cleaned.split()
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    elif len(cleaned) >= 2:
        return cleaned[:2].upper()
    elif cleaned:
        return cleaned[0].upper()
    return "CO"

def get_company_palette(name: str) -> Tuple[str, str]:
    hash_val = sum(ord(c) for c in name)
    palette = AVATAR_PALETTES[hash_val % len(AVATAR_PALETTES)]
    return palette["bg"], palette["color"]

def get_company_logo_meta(company_name: str) -> Dict[str, Any]:
    norm = company_name.lower().strip()

    # Special handling for Reference Guides
    if "core fundamentals" in norm:
        return {
            "domain": None,
            "logo_url": None,
            "initials": "CF",
            "avatar_bg": "#eff6ff",
            "avatar_color": "#2563eb",
            "is_guide": True,
            "guide_icon": "fa-solid fa-terminal"
        }
    if "production scenarios" in norm:
        return {
            "domain": None,
            "logo_url": None,
            "initials": "PS",
            "avatar_bg": "#fef2f2",
            "avatar_color": "#dc2626",
            "is_guide": True,
            "guide_icon": "fa-solid fa-shield-halved"
        }

    bg, color = get_company_palette(company_name)
    initials = get_company_initials(company_name)

    safe_slug = re.sub(r'[^a-z0-9_]', '', norm.replace(' ', '_'))
    local_logo = f"/static/images/logos/{safe_slug}.png"
    domain = COMPANY_DOMAINS.get(norm)
    if not domain:
        clean_norm = re.sub(r'[^a-z0-9]', '', norm)
        domain = f"{clean_norm}.com" if clean_norm else "company.com"

    return {
        "domain": domain,
        "logo_url": local_logo,
        "initials": initials,
        "avatar_bg": "#ffffff",
        "avatar_color": color,
        "is_guide": False,
        "guide_icon": "fa-solid fa-building"
    }
