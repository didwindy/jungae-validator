import os
from dotenv import load_dotenv

load_dotenv()

# ─── API Keys (.env 파일에 입력하세요) ────────────────────────────────────────
BUILDING_HUB_KEY = os.getenv("BUILDING_HUB_KEY", "YOUR_BUILDING_HUB_KEY")
VWORLD_KEY       = os.getenv("VWORLD_KEY",       "YOUR_VWORLD_KEY")
# VWorld NED API 도메인 — 발급 시 등록한 도메인 (로컬: localhost)
# ★ 기본값을 오라클 클라우드 서버 주소로 변경
VWORLD_DOMAIN    = os.getenv("VWORLD_DOMAIN",    "http://168.110.112.29:5000")

# ─── 건축HUB 엔드포인트 ──────────────────────────────────────────────────────
BUILDING_HUB_BASE = "https://apis.data.go.kr/1613000/BldRgstHubService"
BUILDING_HUB_OPS = {
    "recap_title":  "getBrRecapTitleInfo",
    "title":        "getBrTitleInfo",
    "area":         "getBrExposPubuseAreaInfo",
    "expos":        "getBrExposInfo",
    "floor":        "getBrFlrOulnInfo",
    "basis":        "getBrBasisOulnInfo",
}

# ─── VWorld 엔드포인트 ────────────────────────────────────────────────────────
VWORLD_GEOCODER  = "https://api.vworld.kr/req/address"
VWORLD_SEARCH    = "https://api.vworld.kr/req/search"
VWORLD_LAND_URL  = "https://api.vworld.kr/ned/data/ladfrlList"
