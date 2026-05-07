"""
건축HUB 건축물대장정보 서비스 API 래퍼
Phase 2: 실제 API 연동 + 엣지케이스 처리
"""
import re
import requests
from config import BUILDING_HUB_BASE, BUILDING_HUB_KEY, BUILDING_HUB_OPS


# ─── 공통 호출 함수 ──────────────────────────────────────────────────────────
def _call(op_name: str, params: dict) -> dict:
    """
    건축HUB API 공통 호출.
    - _type=json 강제
    - resultCode 체크
    - 단건 dict → 리스트 정규화
    """
    url = f"{BUILDING_HUB_BASE}/{BUILDING_HUB_OPS[op_name]}"
    full_params = {
        **params,
        "serviceKey": BUILDING_HUB_KEY,
        "_type":      "json",
        "numOfRows":  100,
        "pageNo":     params.get("pageNo", 1),
    }
    try:
        resp = requests.get(url, params=full_params, timeout=20)
        resp.raise_for_status()

        # 간혹 XML 에러 페이지가 오는 경우 처리
        if resp.text.strip().startswith("<"):
            return {"error": f"XML 에러 응답 (인증키 또는 서비스 확인 필요): {resp.text[:200]}"}

        data = resp.json()
        header = data.get("response", {}).get("header", {})
        result_code = header.get("resultCode", "ERR")

        if result_code != "00":
            msg = header.get("resultMsg", "알 수 없는 오류")
            return {"error": f"건축HUB API 오류: {msg} (code={result_code})"}

        body  = data.get("response", {}).get("body", {})
        items = body.get("items", {})

        if not items or items == "":
            return {"items": [], "totalCount": 0}

        item_list = items.get("item", [])
        if isinstance(item_list, dict):
            item_list = [item_list]

        total = int(body.get("totalCount", len(item_list)))
        return {"items": item_list, "totalCount": total}

    except requests.exceptions.Timeout:
        return {"error": "건축HUB API 응답 시간 초과 (10초)"}
    except requests.exceptions.RequestException as e:
        return {"error": "API 서버 연결 실패. 잠시 후 다시 시도하세요."}
    except ValueError:
        return {"error": f"JSON 파싱 실패. 응답: {resp.text[:300]}"}
    except Exception as e:
        return {"error": f"파싱 오류: {str(e)}"}


def _call_all_pages(op_name: str, base_params: dict, per_page: int = 100) -> dict:
    """전체 페이지 수집 (동/호 목록 등 대용량 처리)"""
    all_items = []
    page = 1

    while True:
        params = {**base_params, "numOfRows": per_page, "pageNo": page}
        result = _call(op_name, params)
        if "error" in result:
            return result

        all_items.extend(result.get("items", []))
        total = result.get("totalCount", 0)

        if len(all_items) >= total or not result.get("items"):
            break
        page += 1

    return {"items": all_items, "totalCount": len(all_items)}


# ─── 자연 정렬 헬퍼 (101동, 102동 / 101호, 501호 숫자 순서) ────────────────
def _natural_key(s: str):
    return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', s or "")]


# ─── 표제부 조회 ─────────────────────────────────────────────────────────────
def get_title_info(sigungu_cd: str, bjdong_cd: str, bun: str, ji: str) -> dict:
    """
    getBrTitleInfo — 표제부
    반환: 주용도, 사용승인일, 총층수, 주차대수, 위반건축물 여부 등
    """
    params = {
        "sigunguCd": sigungu_cd,
        "bjdongCd":  bjdong_cd,
        "bun":       bun.zfill(4),
        "ji":        ji.zfill(4),
    }
    result = _call("title", params)
    if "error" in result:
        return result

    items = result.get("items", [])
    if not items:
        return {"error": "건축물대장 표제부를 찾을 수 없습니다. 주소를 확인해주세요."}

    # 총괄표제부 제외, 일반/집합 표제부 우선
    main = next(
        (i for i in items if i.get("regstrKindCdNm") != "총괄표제부"),
        items[0]
    )

    use_apr = main.get("useAprDay", "")
    if use_apr and len(use_apr) == 8:
        use_apr = f"{use_apr[:4]}-{use_apr[4:6]}-{use_apr[6:]}"

    # 주차대수: totPkngCnt 우선, 없으면 옥내+옥외 합산
    tot_pkg = int(main.get("totPkngCnt") or 0)
    if not tot_pkg:
        tot_pkg = (
            int(main.get("indrMechUtcnt") or 0) +
            int(main.get("indrAutoUtcnt") or 0) +
            int(main.get("oudrMechUtcnt") or 0) +
            int(main.get("oudrAutoUtcnt") or 0)
        )

    # 위반건축물 여부
    is_violation = bool(main.get("vlViolAtNm") or main.get("vlViolAt"))

    return {
        "mainPurps":      main.get("mainPurpsCdNm", ""),
        "etcPurps":       main.get("etcPurps", ""),
        "useAprDay":      use_apr,
        "grndFlrCnt":     int(main.get("grndFlrCnt") or 0),
        "ugrndFlrCnt":    int(main.get("ugrndFlrCnt") or 0),
        "parking":        tot_pkg,
        "regstrGbCdNm":   main.get("regstrGbCdNm", ""),
        "regstrKindCdNm": main.get("regstrKindCdNm", ""),
        "archArea":       float(main.get("archArea") or 0),
        "totArea":        float(main.get("totArea") or 0),
        "isViolationBldg": is_violation,
    }


# ─── 총괄표제부 조회 (집합건물) ───────────────────────────────────────────────
def get_recap_title_info(sigungu_cd: str, bjdong_cd: str, bun: str, ji: str) -> dict:
    """
    getBrRecapTitleInfo — 총괄표제부 (집합건물 전용)
    반환: 총주차대수, 세대수, 총층수
    """
    params = {
        "sigunguCd": sigungu_cd,
        "bjdongCd":  bjdong_cd,
        "bun":       bun.zfill(4),
        "ji":        ji.zfill(4),
    }
    result = _call("recap_title", params)
    if "error" in result:
        return result

    items = result.get("items", [])
    if not items:
        return {"error": "총괄표제부 없음 (단독/일반 건물)"}

    recap = items[0]
    tot_pkg = int(recap.get("totPkngCnt") or 0)
    if not tot_pkg:
        tot_pkg = (
            int(recap.get("indrMechUtcnt") or 0) +
            int(recap.get("indrAutoUtcnt") or 0) +
            int(recap.get("oudrMechUtcnt") or 0) +
            int(recap.get("oudrAutoUtcnt") or 0)
        )

    use_apr = recap.get("useAprDay", "")
    if use_apr and len(use_apr) == 8:
        use_apr = f"{use_apr[:4]}-{use_apr[4:6]}-{use_apr[6:]}"

    return {
        "parking":     tot_pkg,
        "hhldCnt":     int(recap.get("hhldCnt") or 0),
        "grndFlrCnt":  int(recap.get("grndFlrCnt") or 0),
        "ugrndFlrCnt": int(recap.get("ugrndFlrCnt") or 0),
        "useAprDay":   use_apr,
        "mainPurps":   recap.get("mainPurpsCdNm", ""),
    }


# ─── 전유부 동/호 목록 ────────────────────────────────────────────────────────
def get_expos_info(sigungu_cd: str, bjdong_cd: str, bun: str, ji: str) -> dict:
    """
    getBrExposInfo — 집합건물 전유부 목록 (전체 페이지 수집)
    반환: {dongList: [{dongNm, hoList: [{hoNm, flrNo, mgmBldrgstPk}]}]}
    """
    params = {
        "sigunguCd": sigungu_cd,
        "bjdongCd":  bjdong_cd,
        "bun":       bun.zfill(4),
        "ji":        ji.zfill(4),
    }
    result = _call_all_pages("expos", params)
    if "error" in result:
        return result

    items = result.get("items", [])
    if not items:
        return {"error": "전유부 목록 없음 — 단독/다가구 건물이거나 집합건물이 아닐 수 있습니다."}

    dong_map: dict = {}
    for item in items:
        dong = item.get("dongNm", "") or "본동"
        ho   = item.get("hoNm", "")
        # flrNo: 문자열 "5"이거나 숫자 5이거나 None
        try:
            flr_no = int(item.get("flrNo") or 0)
        except (ValueError, TypeError):
            flr_no = 0
        pk = item.get("mgmBldrgstPk", "")

        if dong not in dong_map:
            dong_map[dong] = []
        dong_map[dong].append({
            "hoNm":          ho,
            "flrNo":         flr_no,
            "mgmBldrgstPk":  pk,
        })

    # 자연 정렬: 101동 → 102동 → 201동 (문자열 정렬 방지)
    dong_list = [
        {
            "dongNm": dong,
            "hoList": sorted(hos, key=lambda x: (_natural_key(str(x["flrNo"])),
                                                  _natural_key(x["hoNm"]))),
        }
        for dong, hos in sorted(dong_map.items(), key=lambda x: _natural_key(x[0]))
    ]

    # 전체 동 중 최고층번호 추출 → 총괄표제부 grndFlrCnt=0일 때 폴백용
    all_flr_nos = [
        h["flrNo"] for d in dong_list for h in d["hoList"] if h["flrNo"] > 0
    ]
    max_flr_no = max(all_flr_nos) if all_flr_nos else 0

    return {"dongList": dong_list, "totalCount": result["totalCount"], "maxFlrNo": max_flr_no}


# ─── 전용면적 조회 ────────────────────────────────────────────────────────────
def get_exclusive_area_by_address(
    sigungu_cd: str, bjdong_cd: str, bun: str, ji: str,
    dong_nm: str = "", ho_nm: str = ""
) -> dict:
    """
    getBrExposPubuseAreaInfo — 전유공용면적에서 '전유' 행만 합산
    exposPubuseGbCdNm 값: "전유" 또는 "공용" (전유만 합산)
    """
    params = {
        "sigunguCd": sigungu_cd,
        "bjdongCd":  bjdong_cd,
        "bun":       bun.zfill(4),
        "ji":        ji.zfill(4),
    }
    result = _call_all_pages("area", params)
    if "error" in result:
        return result

    items = result.get("items", [])
    if not items:
        return {"error": "전유공용면적 정보가 없습니다."}

    # 동/호 매칭 + "전유" 필터
    # exposPubuseGbCdNm이 "전유"인 것만 합산 (공용 제외)
    filtered = []
    for i in items:
        dong_match = (not dong_nm) or (i.get("dongNm", "") == dong_nm)
        ho_match   = (not ho_nm)   or (i.get("hoNm", "")   == ho_nm)
        is_jeonyu  = i.get("exposPubuseGbCdNm", "") == "전유"
        if dong_match and ho_match and is_jeonyu:
            filtered.append(i)

    if not filtered:
        # 필터 결과 없으면 전체에서 전유만 (동명 불일치 가능성)
        filtered = [i for i in items if i.get("exposPubuseGbCdNm", "") == "전유"]

    exclusive_area = sum(float(i.get("area") or 0) for i in filtered)

    return {
        "exclusiveArea": round(exclusive_area, 4),
        "unit":   "㎡",
        "dongNm": dong_nm,
        "hoNm":   ho_nm,
        "rowCount": len(filtered),
    }



# ─── 동별 표제부 조회 (동 선택 후 해당 동의 총층수 확정용) ───────────────────
def get_dong_title_info(sigungu_cd: str, bjdong_cd: str, bun: str, ji: str,
                        dong_nm: str = "") -> dict:
    """
    특정 동(棟)의 표제부 조회 → 해당 동의 지상 총층수(grndFlrCnt) 반환
    아파트 단지에서 동마다 층수가 다를 수 있으므로 동 선택 후 호출
    """
    params = {
        "sigunguCd": sigungu_cd,
        "bjdongCd":  bjdong_cd,
        "bun":       bun.zfill(4),
        "ji":        ji.zfill(4),
    }
    if dong_nm:
        params["dongNm"] = dong_nm

    result = _call("title", params)
    if "error" in result:
        return result

    items = result.get("items", [])
    if not items:
        return {"error": f"{dong_nm} 표제부 없음"}

    # 동 이름으로 필터링 (dongNm 파라미터가 서버 필터링 안 될 경우 클라이언트 필터)
    if dong_nm:
        matched = [i for i in items
                   if i.get("dongNm", "") == dong_nm
                   and i.get("regstrKindCdNm") != "총괄표제부"]
        target = matched[0] if matched else next(
            (i for i in items if i.get("regstrKindCdNm") != "총괄표제부"), items[0])
    else:
        target = next(
            (i for i in items if i.get("regstrKindCdNm") != "총괄표제부"), items[0])

    grnd = int(target.get("grndFlrCnt") or 0)
    ugrd = int(target.get("ugrndFlrCnt") or 0)

    return {
        "dongNm":     target.get("dongNm", dong_nm),
        "grndFlrCnt": grnd,
        "ugrndFlrCnt": ugrd,
    }


def get_dong_title_info_safe(sigungu_cd, bjdong_cd, bun, ji, dong_nm=""):
    if _is_dummy_mode():
        # 더미: 동마다 층수가 다른 케이스 시뮬레이션
        dummy_floors = {"101동": 15, "102동": 25}
        grnd = dummy_floors.get(dong_nm, 20)
        return {"dongNm": dong_nm, "grndFlrCnt": grnd, "ugrndFlrCnt": 2, "_dummy": True}
    return get_dong_title_info(sigungu_cd, bjdong_cd, bun, ji, dong_nm)

# ─── API 키 테스트 ────────────────────────────────────────────────────────────
def test_api_key() -> dict:
    """건축HUB API 키 유효성 빠른 확인 (서울 강남구 개포동 12번지로 테스트)"""
    result = _call("title", {
        "sigunguCd": "11680",
        "bjdongCd":  "10300",
        "bun":       "0012",
        "ji":        "0000",
    })
    if "error" in result:
        return {"valid": False, "message": result["error"]}
    return {"valid": True, "message": f"API 키 정상 (결과 {result['totalCount']}건)"}


# ─── 더미 모드 폴백 ──────────────────────────────────────────────────────────
def _is_dummy_mode() -> bool:
    return not BUILDING_HUB_KEY or any(
        kw in BUILDING_HUB_KEY for kw in ("YOUR_BUILDING_HUB_KEY", "여기에", "입력")
    )

_DUMMY_TITLE = {
    "mainPurps": "공동주택", "etcPurps": "아파트",
    "useAprDay": "2003-08-15", "grndFlrCnt": 25, "ugrndFlrCnt": 2,
    "parking": 412, "regstrGbCdNm": "집합",
    "archArea": 3200.0, "totArea": 84000.0, "isViolationBldg": False,
}
_DUMMY_RECAP = {
    "parking": 412, "hhldCnt": 1800,
    "grndFlrCnt": 25, "ugrndFlrCnt": 2,
    "useAprDay": "2003-08-15", "mainPurps": "공동주택",
}
_DUMMY_DONG_LIST = [
    {"dongNm": "101동", "hoList": [
        {"hoNm": "101호", "flrNo": 1,  "mgmBldrgstPk": "dummy_101_101"},
        {"hoNm": "201호", "flrNo": 2,  "mgmBldrgstPk": "dummy_101_201"},
        {"hoNm": "501호", "flrNo": 5,  "mgmBldrgstPk": "dummy_101_501"},
        {"hoNm": "1001호","flrNo": 10, "mgmBldrgstPk": "dummy_101_1001"},
    ]},
    {"dongNm": "102동", "hoList": [
        {"hoNm": "101호", "flrNo": 1, "mgmBldrgstPk": "dummy_102_101"},
        {"hoNm": "301호", "flrNo": 3, "mgmBldrgstPk": "dummy_102_301"},
    ]},
]

def get_title_info_safe(sigungu_cd, bjdong_cd, bun, ji):
    if _is_dummy_mode():
        return {**_DUMMY_TITLE, "_dummy": True}
    return get_title_info(sigungu_cd, bjdong_cd, bun, ji)

def get_recap_title_info_safe(sigungu_cd, bjdong_cd, bun, ji):
    if _is_dummy_mode():
        return {**_DUMMY_RECAP, "_dummy": True}
    return get_recap_title_info(sigungu_cd, bjdong_cd, bun, ji)

def get_expos_info_safe(sigungu_cd, bjdong_cd, bun, ji):
    if _is_dummy_mode():
        return {"dongList": _DUMMY_DONG_LIST, "totalCount": 6, "maxFlrNo": 10, "_dummy": True}
    return get_expos_info(sigungu_cd, bjdong_cd, bun, ji)

def get_exclusive_area_safe(sigungu_cd, bjdong_cd, bun, ji, dong_nm, ho_nm):
    if _is_dummy_mode():
        return {"exclusiveArea": 84.97, "unit": "㎡",
                "dongNm": dong_nm, "hoNm": ho_nm, "_dummy": True}
    return get_exclusive_area_by_address(
        sigungu_cd, bjdong_cd, bun, ji, dong_nm, ho_nm)
