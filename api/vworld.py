"""
VWorld API 래퍼 v2
- 후보 목록 검색: /req/search (주소 자동완성용)
- 단건 좌표변환: /req/address (선택 후 코드 추출용)
"""
import re
import time
import requests
from config import VWORLD_KEY, VWORLD_DOMAIN

VWORLD_SEARCH   = "https://api.vworld.kr/req/search"
VWORLD_GEOCODER = "https://api.vworld.kr/req/address"

_RETRY_STATUS     = {502, 503, 504}
_MAX_RETRIES      = 5
_MAX_CONN_RETRIES = 3  # WAF silent-drop(RemoteDisconnected) 시 빠른 실패 한도


def _vworld_headers() -> dict:
    """VWorld 도메인 인증용 Referer 헤더 — 등록된 서비스 URL과 일치해야 함."""
    domain = VWORLD_DOMAIN.rstrip("/")
    if not domain.startswith("http"):
        domain = f"https://{domain}"
    return {
        "Referer":    domain + "/",
        "User-Agent": "python-requests/2.31.0",
        "Accept":     "application/json",
        "Connection": "close",
    }


def _vworld_get(url: str, params: dict) -> requests.Response:
    """재시도 GET: 5xx는 지수 백오프, WAF 연결 차단은 3회 후 빠른 실패."""
    headers = _vworld_headers()
    last_exc = None
    conn_fail = 0
    for attempt in range(_MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code not in _RETRY_STATUS:
                return resp
        except requests.exceptions.ConnectionError as e:
            # RemoteDisconnected 등 WAF silent-drop: 짧은 재시도 후 포기
            last_exc = e
            resp = None
            conn_fail += 1
            if conn_fail >= _MAX_CONN_RETRIES:
                raise ConnectionError(
                    "VWorld 연결 차단: 서버 IP가 방화벽에 차단된 것으로 보입니다. "
                    "잠시 후 다시 시도하거나 UptimeRobot 등으로 서버 슬립을 방지하세요."
                ) from e
            time.sleep(5)
            continue
        if attempt < _MAX_RETRIES - 1:
            time.sleep(2 ** attempt)  # 1, 2, 4, 8초
    if last_exc:
        raise last_exc
    return resp


def search_candidates(query: str, size: int = 10) -> dict:
    """
    지번 주소 키워드로 후보 목록 반환.
    반환: {candidates: [{text, sigunguCd, bjdongCd, platGbCd, bun, ji}, ...]}
    """
    params = {
        "service":  "search",
        "request":  "search",
        "version":  "2.0",
        "crs":      "epsg:4326",
        "size":     size,
        "page":     1,
        "type":     "address",
        "category": "parcel",   # 지번 주소
        "query":    query,
        "key":      VWORLD_KEY,
        "format":   "json",
        "errorformat": "json",
    }
    try:
        resp = _vworld_get(VWORLD_SEARCH, params)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("response", {}).get("status", "ERROR")
        if status == "NOT_FOUND":
            return {"candidates": [], "message": "검색 결과가 없습니다."}
        if status != "OK":
            reason = data.get("response", {}).get("error", {}).get("text", "알 수 없는 오류")
            return {"error": f"VWorld 검색 실패: {reason}"}

        items = data["response"]["result"].get("items", [])
        candidates = []
        for item in items:
            address = item.get("address", {})
            parcel  = address.get("parcel", "")   # "경상남도 창원시 마산회원구 각산동 1043"

            # id 필드에 법정동코드 포함 여부 확인
            addr_id = item.get("id", "")           # 예: "4812111900101043000"
            # id가 19자리 PNU 형식이면 바로 분리
            sg, bd, pgb, bun, ji = _parse_id_to_codes(addr_id)

            if not sg:
                # fallback: parcel 텍스트에서 파싱
                bun, ji = _parse_bun_ji(parcel)
                # 코드는 별도 geocoding 필요 → 선택 시 추가 호출

            candidates.append({
                "text":       parcel or item.get("title", ""),
                "sigunguCd":  sg,
                "bjdongCd":   bd,
                "platGbCd":   pgb,
                "bun":        bun,
                "ji":         ji,
                "needGeocode": not bool(sg),  # True면 선택 시 geocoding 추가 호출
            })

        return {"candidates": candidates}

    except requests.exceptions.Timeout:
        return {"error": "VWorld 검색 API 응답 시간 초과"}
    except Exception as e:
        return {"error": f"후보 검색 오류: {str(e)}"}


def geocode_single(full_address: str) -> dict:
    """
    전체 주소로 단건 코드 추출 (후보 선택 후 코드 없을 때 호출).
    """
    params = {
        "service":     "address",
        "request":     "getCoord",
        "type":        "parcel",
        "address":     full_address,
        "key":         VWORLD_KEY,
        "format":      "json",
        "errorformat": "json",
        "crs":         "EPSG:4326",
    }
    try:
        resp = _vworld_get(VWORLD_GEOCODER, params)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("response", {}).get("status", "ERROR")
        if status != "OK":
            return {"error": "좌표 변환 실패"}

        result = data["response"]["result"]
        text   = result.get("text", full_address)
        parcel = result.get("structure", {})

        level4lc = parcel.get("level4LC", "")
        sg = level4lc[:5] if len(level4lc) >= 10 else ""
        bd = level4lc[5:] if len(level4lc) >= 10 else ""

        level5 = parcel.get("level5", "")
        bun, ji = _parse_bun_ji(level5 + "번지") if level5 else _parse_bun_ji(text)
        pgb = "1" if "산" in text.split()[:3] else "0"

        return {
            "fullAddress": text,
            "sigunguCd":   sg,
            "bjdongCd":    bd,
            "platGbCd":    pgb,
            "bun":         bun,
            "ji":          ji,
        }
    except Exception as e:
        return {"error": str(e)}


# ─── 내부 유틸 ─────────────────────────────────────────────────────────────

def _parse_id_to_codes(addr_id: str):
    """
    VWorld search 결과의 id 필드(19자리 PNU)에서 코드 분리.
    형식: 시군구(5) + 법정동(5) + 산구분(1) + 본번(4) + 부번(4) = 19자리
    """
    if len(addr_id) == 19 and addr_id.isdigit():
        sg  = addr_id[0:5]
        bd  = addr_id[5:10]
        pgb = addr_id[10]
        bun = addr_id[11:15]
        ji  = addr_id[15:19]
        return sg, bd, pgb, bun, ji
    return "", "", "0", "0000", "0000"


def _parse_bun_ji(s: str):
    m = re.search(r'(\d+)-(\d+)번지?', s)
    if m:
        return m.group(1).zfill(4), m.group(2).zfill(4)
    m = re.search(r'(\d+)번지?', s)
    if m:
        return m.group(1).zfill(4), "0000"
    return "0000", "0000"


# ─── 더미 모드 ─────────────────────────────────────────────────────────────

def _is_dummy_mode() -> bool:
    return not VWORLD_KEY or any(
        kw in VWORLD_KEY for kw in ("YOUR_VWORLD_KEY", "여기에", "입력")
    )


DUMMY_DB = [
    {
        "text": "경상남도 창원시 마산회원구 각산동 1043",
        "sigunguCd": "48121", "bjdongCd": "11900",
        "platGbCd": "0", "bun": "1043", "ji": "0000",
    },
    {
        "text": "서울특별시 강남구 개포동 12",
        "sigunguCd": "11680", "bjdongCd": "10300",
        "platGbCd": "0", "bun": "0012", "ji": "0000",
    },
    {
        "text": "서울특별시 마포구 서교동 395-32",
        "sigunguCd": "11440", "bjdongCd": "10900",
        "platGbCd": "0", "bun": "0395", "ji": "0032",
    },
    {
        "text": "서울특별시 강남구 역삼동 823",
        "sigunguCd": "11680", "bjdongCd": "10600",
        "platGbCd": "0", "bun": "0823", "ji": "0000",
    },
    {
        "text": "부산광역시 해운대구 우동 1480",
        "sigunguCd": "26350", "bjdongCd": "10700",
        "platGbCd": "0", "bun": "1480", "ji": "0000",
    },
]


def search_candidates_with_fallback(query: str) -> dict:
    if not _is_dummy_mode():
        return search_candidates(query)

    # 더미: 쿼리와 일치하는 항목 필터링
    q = query.strip().lower()
    matched = [
        {**d, "needGeocode": False}
        for d in DUMMY_DB
        if any(token in d["text"].lower() for token in q.split())
    ]
    # 하나도 없으면 쿼리 자체로 더미 후보 1개 생성
    if not matched:
        bun, ji = _parse_bun_ji(query)
        matched = [{
            "text": f"[더미] {query}",
            "sigunguCd": "48121", "bjdongCd": "11900",
            "platGbCd": "0",
            "bun": bun if bun != "0000" else "0001",
            "ji": ji,
            "needGeocode": False,
        }]

    return {"candidates": matched, "_dummy": True}


def geocode_single_with_fallback(full_address: str) -> dict:
    if not _is_dummy_mode():
        return geocode_single(full_address)
    # 더미: 그냥 반환
    for d in DUMMY_DB:
        if d["text"] == full_address:
            return {**d, "fullAddress": full_address}
    return {"fullAddress": full_address, "sigunguCd": "", "bjdongCd": "",
            "platGbCd": "0", "bun": "0000", "ji": "0000"}
