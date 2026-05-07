import os
from dotenv import load_dotenv

load_dotenv()

# ─── API Keys (.env 파일에 입력하세요) ────────────────────────────────────────
BUILDING_HUB_KEY = os.getenv("BUILDING_HUB_KEY", "YOUR_BUILDING_HUB_KEY")
VWORLD_KEY       = os.getenv("VWORLD_KEY",       "YOUR_VWORLD_KEY")
# 카카오 REST API 키 (주소 검색용 — 해외서버에서도 작동)
KAKAO_REST_KEY   = os.getenv("KAKAO_REST_KEY",   "YOUR_KAKAO_REST_KEY")
# VWorld NED API 도메인 — 발급 시 등록한 도메인 (로컬: localhost)
VWORLD_DOMAIN    = os.getenv("VWORLD_DOMAIN",    "localhost")

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
VWORLD_LAND_URL  = "http://api.vworld.kr/ned/data/ladfrlList"   # ← ladfrlList 고정
