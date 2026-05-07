"""
카카오 로컬 REST API — 지번 주소 검색
- VWorld 대체 (해외 서버에서도 정상 작동)
- 응답의 b_code(법정동코드 10자리)에서 sigunguCd/bjdongCd 직접 추출
- 발급: https://developers.kakao.com → 앱 생성 → REST API 키
"""
import re
import requests
from config import KAKAO_REST_KEY

KAKAO_ADDRESS_URL = "https://dapi.kakao.com/v2/local/search/address.json"


def _is_dummy_mode() -> bool:
    return not KAKAO_REST_KEY or any(
        kw in KAKAO_REST_KEY for kw in ("YOUR_KAKAO_REST_KEY", "여기에", "입력")
    )


def search_candidates(query: str, size: int = 10) -> dict:
    """
    카카오 주소 검색 → 후보 목록 반환
    반환: {candidates: [{text, sigunguCd, bjdongCd, platGbCd, bun, ji}]}
    """
    if _is_dummy_mode():
        return _dummy_candidates(query)

    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
    params  = {"query": query, "size": size, "page": 1}

    try:
        resp = requests.get(KAKAO_ADDRESS_URL, headers=headers,
                            params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        docs = data.get("documents", [])
        if not docs:
            return {"candidates": [], "message": "검색 결과가 없습니다."}

        candidates = []
        for doc in docs:
            addr = doc.get("address") or {}
            road = doc.get("road_address") or {}

            b_code = addr.get("b_code", "")         # 법정동코드 10자리
            sg = b_code[:5] if len(b_code) >= 10 else ""
            bd = b_code[5:] if len(b_code) >= 10 else ""

            main_no = addr.get("main_address_no", "0") or "0"
            sub_no  = addr.get("sub_address_no",  "0") or "0"
            bun = str(main_no).zfill(4)
            ji  = str(sub_no).zfill(4) if sub_no not in ("", "0") else "0000"

            plat_gb = "1" if addr.get("mountain_yn") == "Y" else "0"

            full_addr = addr.get("address_name") or doc.get("address_name", "")

            if sg and full_addr:
                candidates.append({
                    "text":        full_addr,
                    "sigunguCd":   sg,
                    "bjdongCd":    bd,
                    "platGbCd":    plat_gb,
                    "bun":         bun,
                    "ji":          ji,
                    "needGeocode": False,
                })

        return {"candidates": candidates}

    except requests.exceptions.Timeout:
        return {"error": "카카오 API 응답 시간 초과"}
    except Exception as e:
        msg = str(e)
        # API 키 노출 방지
        msg = re.sub(r'KakaoAK\s+\S+', 'KakaoAK ***', msg)
        msg = re.sub(r'https?://\S+', '[URL 숨김]', msg)
        return {"error": f"주소 검색 오류: {msg}"}


# ─── 더미 모드 ─────────────────────────────────────────────────────────────
_DUMMY_DB = [
    {"text": "경상남도 창원시 마산회원구 각산동 1043",
     "sigunguCd":"48121","bjdongCd":"11900","platGbCd":"0","bun":"1043","ji":"0000"},
    {"text": "서울특별시 강남구 개포동 12",
     "sigunguCd":"11680","bjdongCd":"10300","platGbCd":"0","bun":"0012","ji":"0000"},
    {"text": "서울특별시 마포구 서교동 395-32",
     "sigunguCd":"11440","bjdongCd":"10900","platGbCd":"0","bun":"0395","ji":"0032"},
    {"text": "서울특별시 강남구 역삼동 823",
     "sigunguCd":"11680","bjdongCd":"10600","platGbCd":"0","bun":"0823","ji":"0000"},
    {"text": "부산광역시 해운대구 우동 1480",
     "sigunguCd":"26350","bjdongCd":"10700","platGbCd":"0","bun":"1480","ji":"0000"},
]

def _dummy_candidates(query: str) -> dict:
    q = query.strip().lower()
    matched = [
        {**d, "needGeocode": False}
        for d in _DUMMY_DB
        if any(t in d["text"].lower() for t in q.split())
    ]
    if not matched:
        import re as _re
        bun_m = _re.search(r'(\d+)-?(\d*)', query)
        bun = bun_m.group(1).zfill(4) if bun_m else "0001"
        ji  = bun_m.group(2).zfill(4) if bun_m and bun_m.group(2) else "0000"
        matched = [{"text": f"[더미] {query}", "sigunguCd":"48121",
                    "bjdongCd":"11900","platGbCd":"0","bun":bun,"ji":ji,
                    "needGeocode":False}]
    return {"candidates": matched, "_dummy": True}
