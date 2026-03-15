"""Affiliation matching for universities and AI companies.

Tier system (lower = more prestigious):
  Tier 1: World top 50 universities + world-class AI companies
  Tier 2: World rank 50-100 universities
  Tier 3: World rank 100-200 universities
  Tier 4: World rank 200-400 universities
  Tier 5: World rank 400-500 universities

Bonus scores by tier:
  Tier 1: +2.0
  Tier 2: +1.5
  Tier 3: +1.0
  Tier 4: +0.5
  Tier 5: +0.3
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Tier 1: World-class AI companies
# ---------------------------------------------------------------------------
AI_COMPANIES: list[str] = [
    # US
    "openai",
    "google",
    "deepmind",
    "google deepmind",
    "google research",
    "google brain",
    "meta",
    "meta ai",
    "facebook",
    "fair",
    "microsoft",
    "microsoft research",
    "anthropic",
    "nvidia",
    "apple",
    "amazon",
    "aws",
    "x.ai",
    "xai",
    "grok",
    "tesla",
    "ibm",
    "ibm research",
    "oracle",
    "adobe",
    "adobe research",
    "salesforce",
    "salesforce research",
    # China
    "deepseek",
    "zhipu",
    "zhipuai",
    "\u667a\u8c31",
    "\u667a\u8c31ai",
    "\u817e\u8baf",
    "tencent",
    "tencent ai",
    "tencent ai lab",
    "\u963f\u91cc\u5df4\u5df4",
    "\u963f\u91cc",
    "alibaba",
    "alibaba group",
    "damo academy",
    "\u8fbe\u6469\u9662",
    "\u534e\u4e3a",
    "huawei",
    "huawei noah",
    "noah's ark",
    "\u5b57\u8282\u8df3\u52a8",
    "\u5b57\u8282",
    "bytedance",
    "douyin",
    "\u767e\u5ea6",
    "baidu",
    "baidu research",
    "\u5546\u6c64",
    "sensetime",
    "\u65f7\u89c6",
    "megvii",
    "\u6708\u4e4b\u6697\u9762",
    "moonshot",
    "moonshot ai",
    "kimi",
    "\u96f6\u4e00\u4e07\u7269",
    "01.ai",
    "yi",
    "\u7a33\u5b9a\u6269\u6563",
    "\u7f8e\u56e2",
    "meituan",
    "\u4eac\u4e1c",
    "jd",
    "jd.com",
    "\u79d1\u5927\u8baf\u98de",
    "iflytek",
    "\u5c0f\u7c73",
    "xiaomi",
    "\u6df1\u52bf\u79d1\u6280",
    "deepsense",
    "\u5149\u5e74\u4e4b\u5916",
    "stepfun",
    "\u5c9a\u5c9a\u667a\u80fd",
    "siliconflow",
    "\u9762\u58c1\u667a\u80fd",
    "minimax",
    # Europe & others
    "samsung",
    "samsung research",
    "sony",
    "sony ai",
    "nec",
    "nec laboratories",
    "bosch",
    "siemens",
    "hugging face",
    "huggingface",
    "stability ai",
    "mistral",
    "mistral ai",
    "cohere",
    "ai21",
    "ai21 labs",
    "databricks",
    "mosaic",
    "mosaicml",
    "together ai",
    "together",
    "inflection",
    "character ai",
    "midjourney",
    "runway",
    "allen institute",
    "allen ai",
    "ai2",
    "allenai",
]

# ---------------------------------------------------------------------------
# Universities grouped by QS/THE approximate tiers
# Using lowercase keywords for matching
# ---------------------------------------------------------------------------

# Tier 1: World top 50
TIER1_UNIVERSITIES: list[str] = [
    # US
    "mit",
    "massachusetts institute of technology",
    "stanford",
    "stanford university",
    "harvard",
    "harvard university",
    "caltech",
    "california institute of technology",
    "uc berkeley",
    "berkeley",
    "university of california, berkeley",
    "ucb",
    "princeton",
    "princeton university",
    "columbia",
    "columbia university",
    "yale",
    "yale university",
    "cornell",
    "cornell university",
    "university of chicago",
    "uchicago",
    "university of pennsylvania",
    "upenn",
    "penn",
    "johns hopkins",
    "jhu",
    "university of michigan",
    "umich",
    "carnegie mellon",
    "cmu",
    "georgia tech",
    "georgia institute of technology",
    "university of washington",
    "uw",
    "ucla",
    "university of california, los angeles",
    "ucsd",
    "university of california, san diego",
    "uiuc",
    "university of illinois",
    "nyu",
    "new york university",
    "usc",
    "university of southern california",
    # UK
    "oxford",
    "university of oxford",
    "cambridge",
    "university of cambridge",
    "imperial college",
    "imperial college london",
    "ucl",
    "university college london",
    "edinburgh",
    "university of edinburgh",
    # Europe
    "eth zurich",
    "eth z\u00fcrich",
    "ethz",
    "epfl",
    "\u00e9cole polytechnique f\u00e9d\u00e9rale de lausanne",
    "max planck",
    # Asia
    "\u6e05\u534e",
    "\u6e05\u534e\u5927\u5b66",
    "tsinghua",
    "\u5317\u5927",
    "\u5317\u4eac\u5927\u5b66",
    "peking university",
    "pku",
    "nus",
    "national university of singapore",
    "ntu",
    "nanyang technological university",
    "\u4e1c\u4eac\u5927\u5b66",
    "university of tokyo",
    "tokyo university",
    "kaist",
    "\u9999\u6e2f\u5927\u5b66",
    "hku",
    "university of hong kong",
    "\u9999\u6e2f\u4e2d\u6587\u5927\u5b66",
    "cuhk",
    "chinese university of hong kong",
    "\u9999\u6e2f\u79d1\u6280\u5927\u5b66",
    "hkust",
    # Other
    "university of toronto",
    "u of t",
    "uoft",
    "university of waterloo",
    "uwaterloo",
    "mcgill",
    "mcgill university",
    "university of melbourne",
    "australian national university",
    "anu",
    "university of sydney",
]

# Tier 2: World rank 50-100
TIER2_UNIVERSITIES: list[str] = [
    "duke",
    "duke university",
    "northwestern",
    "northwestern university",
    "university of wisconsin",
    "uw madison",
    "university of maryland",
    "umd",
    "university of texas",
    "ut austin",
    "purdue",
    "purdue university",
    "ohio state",
    "ohio state university",
    "university of minnesota",
    "rice university",
    "rice",
    "boston university",
    "bu",
    "emory",
    "emory university",
    "university of virginia",
    "uva",
    "brown university",
    "brown",
    "dartmouth",
    "unc",
    "university of north carolina",
    # UK
    "manchester",
    "university of manchester",
    "king's college london",
    "kcl",
    "london school of economics",
    "lse",
    "warwick",
    "university of warwick",
    "bristol",
    "university of bristol",
    # Europe
    "tu munich",
    "technical university of munich",
    "tum",
    "lmu munich",
    "kit",
    "karlsruhe institute",
    "tu berlin",
    "rwth aachen",
    "sorbonne",
    "psl",
    "paris sciences et lettres",
    "delft",
    "tu delft",
    "kth",
    "kth royal",
    "Uppsala",
    # Asia
    "\u6d59\u6c5f\u5927\u5b66",
    "\u6d59\u5927",
    "zhejiang university",
    "zju",
    "\u590d\u65e6\u5927\u5b66",
    "\u590d\u65e6",
    "fudan university",
    "\u4e0a\u6d77\u4ea4\u901a\u5927\u5b66",
    "\u4e0a\u6d77\u4ea4\u5927",
    "shanghai jiao tong",
    "sjtu",
    "\u4e2d\u56fd\u79d1\u5b66\u6280\u672f\u5927\u5b66",
    "\u4e2d\u79d1\u5927",
    "ustc",
    "\u4e2d\u56fd\u79d1\u5b66\u9662",
    "\u4e2d\u79d1\u9662",
    "chinese academy of sciences",
    "cas",
    "\u5357\u4eac\u5927\u5b66",
    "\u5357\u5927",
    "nanjing university",
    "nju",
    "seoul national university",
    "snu",
    "yonsei",
    "korea university",
    "\u4eac\u90fd\u5927\u5b66",
    "kyoto university",
    "osaka university",
    "technion",
    "hebrew university",
    "tel aviv university",
]

# Tier 3: World rank 100-200
TIER3_UNIVERSITIES: list[str] = [
    "penn state",
    "pennsylvania state",
    "university of florida",
    "university of colorado",
    "michigan state",
    "msu",
    "arizona state",
    "asu",
    "virginia tech",
    "iowa state",
    "indiana university",
    "stony brook",
    "rutgers",
    "uc davis",
    "uc irvine",
    "uci",
    "uc santa barbara",
    "ucsb",
    "uc santa cruz",
    "university of massachusetts",
    "umass",
    "university of pittsburgh",
    "university of rochester",
    "northeastern university",
    # UK
    "leeds",
    "university of leeds",
    "sheffield",
    "university of sheffield",
    "birmingham",
    "university of birmingham",
    "glasgow",
    "university of glasgow",
    "southampton",
    "nottingham",
    "st andrews",
    "queen mary",
    # Europe
    "aalto",
    "vienna",
    "university of vienna",
    "tu wien",
    "lund university",
    "helsinki",
    "copenhagen",
    "oslo",
    "amsterdam",
    "university of amsterdam",
    "uva amsterdam",
    "leiden",
    "ghent",
    "leuven",
    "ku leuven",
    "zurich",
    "university of zurich",
    "politecnico di milano",
    "sapienza",
    "barcelona",
    "pompeu fabra",
    # Asia
    "\u54c8\u5c14\u6ee8\u5de5\u4e1a\u5927\u5b66",
    "\u54c8\u5de5\u5927",
    "harbin institute of technology",
    "hit",
    "\u6b66\u6c49\u5927\u5b66",
    "\u6b66\u5927",
    "wuhan university",
    "\u534e\u4e2d\u79d1\u6280\u5927\u5b66",
    "\u534e\u79d1",
    "huazhong university",
    "hust",
    "\u4e2d\u5c71\u5927\u5b66",
    "\u4e2d\u5927",
    "sun yat-sen university",
    "sysu",
    "\u5317\u4eac\u822a\u7a7a\u822a\u5929\u5927\u5b66",
    "\u5317\u822a",
    "beihang",
    "\u5317\u4eac\u7406\u5de5\u5927\u5b66",
    "\u5317\u7406\u5de5",
    "bit",
    "beijing institute of technology",
    "\u540c\u6d4e\u5927\u5b66",
    "\u540c\u6d4e",
    "tongji",
    "\u5929\u6d25\u5927\u5b66",
    "\u5929\u5927",
    "tianjin university",
    "\u897f\u5b89\u4ea4\u901a\u5927\u5b66",
    "\u897f\u5b89\u4ea4\u5927",
    "xi'an jiaotong",
    "\u4e2d\u56fd\u4eba\u6c11\u5927\u5b66",
    "\u4eba\u5927",
    "renmin university",
    "ruc",
    "\u5317\u4eac\u5e08\u8303\u5927\u5b66",
    "\u5317\u5e08\u5927",
    "beijing normal",
    "\u5357\u5f00\u5927\u5b66",
    "\u5357\u5f00",
    "nankai",
    "\u56fd\u9632\u79d1\u6280\u5927\u5b66",
    "\u56fd\u9632\u79d1\u5927",
    "nudt",
    "\u4e2d\u56fd\u4eba\u6c11\u89e3\u653e\u519b",
    "pla",
    "keio",
    "keio university",
    "waseda",
    "tohoku university",
    "nagoya university",
    "city university of hong kong",
    "cityu",
    "hong kong polytechnic",
    "polyu",
    "indian institute of technology",
    "iit",
    "iit bombay",
    "iit delhi",
    "iit madras",
    "iit kanpur",
    "iisc",
    "indian institute of science",
    "monash",
    "unsw",
    "university of new south wales",
    "university of queensland",
    # Middle East
    "kaust",
    "king abdullah",
]

# Tier 4: World rank 200-400
TIER4_UNIVERSITIES: list[str] = [
    "university of utah",
    "temple university",
    "george mason",
    "university of oregon",
    "university of kansas",
    "university of delaware",
    "drexel",
    "wayne state",
    "university of houston",
    "university of connecticut",
    "uconn",
    "university of kentucky",
    "university of alabama",
    "clemson",
    "oregon state",
    "colorado state",
    "washington state",
    "university of tennessee",
    "university of oklahoma",
    "university of south carolina",
    "university of nebraska",
    "university of iowa",
    "university of arkansas",
    "marquette",
    # Europe
    "tu dresden",
    "tu darmstadt",
    "university of freiburg",
    "university of bonn",
    "university of hamburg",
    "university of stuttgart",
    "stockholm university",
    "chalmers",
    "dtu",
    "technical university of denmark",
    "ntnu",
    "trinity college dublin",
    "university of lisbon",
    "politecnico di torino",
    "universidad autonoma de madrid",
    "university of groningen",
    "radboud",
    "eindhoven",
    "tu eindhoven",
    "university of twente",
    # Asia
    "\u5357\u65b9\u79d1\u6280\u5927\u5b66",
    "\u5357\u79d1\u5927",
    "sustech",
    "\u4e1c\u5357\u5927\u5b66",
    "\u4e1c\u5927",
    "southeast university",
    "seu",
    "\u7535\u5b50\u79d1\u6280\u5927\u5b66",
    "\u7535\u5b50\u79d1\u5927",
    "\u6210\u7535",
    "uestc",
    "\u5927\u8fde\u7406\u5de5\u5927\u5b66",
    "\u5927\u8fde\u7406\u5de5",
    "dalian university of technology",
    "\u5409\u6797\u5927\u5b66",
    "\u5409\u5927",
    "jilin university",
    "\u5c71\u4e1c\u5927\u5b66",
    "\u5c71\u5927",
    "shandong university",
    "\u53a6\u95e8\u5927\u5b66",
    "\u53a6\u5927",
    "xiamen university",
    "xmu",
    "\u91cd\u5e86\u5927\u5b66",
    "\u91cd\u5927",
    "chongqing university",
    "\u5170\u5dde\u5927\u5b66",
    "\u5170\u5927",
    "lanzhou university",
    "\u897f\u5317\u5de5\u4e1a\u5927\u5b66",
    "\u897f\u5de5\u5927",
    "nwpu",
    "\u4e2d\u56fd\u519c\u4e1a\u5927\u5b66",
    "\u4e2d\u519c",
    "china agricultural university",
    "\u5317\u4eac\u90ae\u7535\u5927\u5b66",
    "\u5317\u90ae",
    "bupt",
    "\u6cb3\u6d77\u5927\u5b66",
    "kyushu university",
    "hokkaido university",
    "chulalongkorn",
    "national taiwan university",
    "ntu taiwan",
    "tsinghua taiwan",
    "nthu",
    "ncku",
]

# Tier 5: World rank 400-500
TIER5_UNIVERSITIES: list[str] = [
    "baylor",
    "university of new mexico",
    "university of vermont",
    "university of rhode island",
    "university of nevada",
    "university of wyoming",
    "university of idaho",
    "north carolina state",
    "nc state",
    "san diego state",
    "university of tulsa",
    "university of mississippi",
    # Europe
    "university of exeter",
    "university of bath",
    "university of surrey",
    "university of aberdeen",
    "university of dundee",
    "university of swansea",
    "university of bern",
    "university of basel",
    "university of innsbruck",
    "university of graz",
    "jagiellonian",
    "charles university",
    "university of tartu",
    "university of turku",
    # Asia
    "\u4e2d\u5357\u5927\u5b66",
    "\u4e2d\u5357",
    "central south university",
    "\u82cf\u5dde\u5927\u5b66",
    "\u82cf\u5927",
    "soochow university",
    "\u6df1\u5733\u5927\u5b66",
    "\u6df1\u5927",
    "shenzhen university",
    "\u6e56\u5357\u5927\u5b66",
    "\u6e56\u5927",
    "hunan university",
    "\u4e1c\u5317\u5927\u5b66",
    "\u4e1c\u5927",
    "northeastern university china",
    "\u90d1\u5dde\u5927\u5b66",
    "\u90d1\u5927",
    "zhengzhou university",
    "\u798f\u5dde\u5927\u5b66",
    "\u798f\u5927",
    "fuzhou university",
    "\u5b89\u5fbd\u5927\u5b66",
    "\u5b89\u5927",
    "anhui university",
    "\u4e91\u5357\u5927\u5b66",
    "\u4e91\u5927",
    "yunnan university",
    "\u5e7f\u5dde\u5927\u5b66",
    "\u5e7f\u5927",
    "guangzhou university",
    "\u6cb3\u5317\u5de5\u4e1a\u5927\u5b66",
    "hiroshima university",
    "kobe university",
    "chiba university",
    "kanazawa university",
    "inha university",
    "hanyang university",
]

# ---------------------------------------------------------------------------
# Research institutes (treated as Tier 2)
# ---------------------------------------------------------------------------
RESEARCH_INSTITUTES: list[str] = [
    # China
    "\u4e2d\u56fd\u79d1\u5b66\u9662",
    "\u4e2d\u79d1\u9662",
    "chinese academy of sciences",
    "cas",
    "\u4e0a\u6d77\u4eba\u5de5\u667a\u80fd\u5b9e\u9a8c\u5ba4",
    "shanghai ai lab",
    "shanghai ailab",
    "\u5317\u4eac\u667a\u6e90\u4eba\u5de5\u667a\u80fd\u7814\u7a76\u9662",
    "baai",
    "\u9e4f\u57ce\u5b9e\u9a8c\u5ba4",
    "peng cheng lab",
    "\u4e4b\u6c5f\u5b9e\u9a8c\u5ba4",
    "zhejiang lab",
    "zhijiang lab",
    "\u7d2b\u4e1c\u79d1\u6280",
    "\u7d2b\u4e1c",
    # International
    "inria",
    "cnrs",
    "riken",
    "csiro",
    "fraunhofer",
    "mila",
    "mila quebec",
    "vector institute",
    "turing institute",
    "alan turing",
]

# ---------------------------------------------------------------------------
# Build lookup structures
# ---------------------------------------------------------------------------

_TIER_MAP: dict[int, list[str]] = {
    1: [k.lower() for k in AI_COMPANIES + TIER1_UNIVERSITIES],
    2: [k.lower() for k in TIER2_UNIVERSITIES + RESEARCH_INSTITUTES],
    3: [k.lower() for k in TIER3_UNIVERSITIES],
    4: [k.lower() for k in TIER4_UNIVERSITIES],
    5: [k.lower() for k in TIER5_UNIVERSITIES],
}

TIER_BONUS: dict[int, float] = {
    1: 2.0,
    2: 1.5,
    3: 1.0,
    4: 0.5,
    5: 0.3,
}


def match_affiliation_tier(text: str) -> int | None:
    """Match text against known affiliations and return the best (lowest) tier.

    Args:
        text: Any text that may contain affiliation info (abstract, author names,
              organization field, etc.)

    Returns:
        Tier number (1-5) or None if no match found.
    """
    if not text:
        return None

    text_lower = text.lower()

    best_tier: int | None = None
    for tier in range(1, 6):
        for keyword in _TIER_MAP[tier]:
            if keyword in text_lower:
                if best_tier is None or tier < best_tier:
                    best_tier = tier
                    if best_tier == 1:
                        return 1  # Can't get better than tier 1
                break  # Found match in this tier, move on
        # Optimization: if we found tier 1 already, stop
        if best_tier == 1:
            return 1

    return best_tier


def get_affiliation_bonus(tier: int | None) -> float:
    """Get the bonus score for a given affiliation tier."""
    if tier is None:
        return 0.0
    return TIER_BONUS.get(tier, 0.0)


def get_affiliation_label(tier: int | None) -> str:
    """Get a human-readable label for the affiliation tier."""
    labels = {
        1: "Top50/AI\u540d\u4f01",
        2: "Top100/\u7814\u7a76\u6240",
        3: "Top200",
        4: "Top400",
        5: "Top500",
    }
    if tier is None:
        return "\u672a\u77e5\u673a\u6784"
    return labels.get(tier, "\u672a\u77e5\u673a\u6784")


def extract_affiliation_text(item_metadata: dict) -> str:
    """Extract searchable affiliation text from item metadata.

    Combines authors, organization, and any affiliation fields.
    """
    parts: list[str] = []

    # Author names (some contain affiliation in parentheses)
    authors = item_metadata.get("authors", [])
    if isinstance(authors, list):
        parts.extend(authors)

    # Organization field (HuggingFace)
    org = item_metadata.get("organization", "")
    if org:
        parts.append(org)

    # Explicit affiliations field
    affiliations = item_metadata.get("affiliations", [])
    if isinstance(affiliations, list):
        parts.extend(affiliations)

    return " ".join(parts)
