"""
중개대상물 광고 검증 규칙
Phase 5 완성판: 20개 규칙 → 정밀화 + 관리비/총층수 분리 반영
"""
import re
from datetime import date

EIGHT_DIRECTIONS = {"동향","서향","남향","북향","북동향","남동향","남서향","북서향"}

DETACHED_PURPS = {"단독주택","다중주택","다가구주택","공관"}
HOUSING_PURPS  = {"아파트","연립주택","다세대주택","오피스텔"}
RESIDENTIAL_PURPS = DETACHED_PURPS | HOUSING_PURPS

def _purps(d): return d.get("중개대상물종류","")
def _is_residential(d): return any(p in _purps(d) for p in RESIDENTIAL_PURPS)
def _is_detached(d):    return any(p in _purps(d) for p in DETACHED_PURPS)
def _is_aggregate(d):   return any(p in _purps(d) for p in HOUSING_PURPS)

# ─── 개별 검증 함수 ─────────────────────────────────────────────────────────
def _check_address(d, a):
    addr = d.get("소재지","").strip()
    if not addr:
        return False, "소재지가 입력되지 않았습니다."
    return True, ""

def _check_area(d, a):
    area = d.get("면적")
    if area is None:
        return False, "면적이 입력되지 않았습니다."
    if area <= 0:
        return False, "면적은 0보다 커야 합니다."
    return True, ""

def _check_area_match(d, a):
    disclosed = d.get("면적")
    auto      = a.get("selectedExclusiveArea")
    if disclosed is None or auto is None or auto == 0:
        return True, ""
    if abs(float(disclosed) - float(auto)) > 0.05:
        return False, f"표시 면적({disclosed}㎡)이 건축물대장 전용면적({auto}㎡)과 다릅니다."
    return True, ""

def _check_price(d, a):
    trade = d.get("거래형태","")
    if trade in ("매매","교환"):
        return (True,"") if d.get("가격_매매가") else (False,"매매가격을 입력해야 합니다.")
    if trade == "전세":
        return (True,"") if d.get("가격_보증금") else (False,"보증금을 입력해야 합니다.")
    if trade == "월세":
        if not d.get("가격_보증금"):
            return False, "보증금을 입력해야 합니다."
        if not d.get("가격_차임"):
            return False, "월세(차임)를 입력해야 합니다."
        return True, ""
    return False, "거래 형태가 선택되지 않았습니다."

def _check_purps(d, a):
    if not _purps(d):
        return False, "중개대상물 종류가 입력되지 않았습니다."
    if a.get("isViolationBldg") and d.get("중개대상물종류_특수") != "위반건축물":
        return False, "건축물대장에 위반사항이 있습니다. '위반건축물'을 표시해야 합니다."
    if a.get("isUnregistered") and d.get("중개대상물종류_특수") != "미등기건물":
        return False, "미등기건물은 '미등기건물'로 표시해야 합니다."
    return True, ""

def _check_trade(d, a):
    return (True,"") if d.get("거래형태") in ("매매","교환","전세","월세") \
        else (False,"거래 형태를 선택해야 합니다.")

def _check_floor(d, a):
    grnd = d.get("총층수_지상")
    if grnd is None:
        return False, "지상 총층수가 입력되지 않았습니다."
    if grnd <= 0:
        return False, "지상 총층수는 1층 이상이어야 합니다."
    return True, ""

def _check_floor_match(d, a):
    grnd_disclosed = d.get("총층수_지상")
    grnd_auto      = a.get("totalFloors")
    if grnd_disclosed is None or not grnd_auto:
        return True, ""
    if int(grnd_disclosed) != int(grnd_auto):
        return False, f"지상층수({grnd_disclosed}층)가 건축물대장 기준({grnd_auto}층)과 다릅니다. 필로티 등 임의 제외 불가."
    return True, ""

def _check_movein(d, a):
    val = d.get("입주가능일","").strip()
    if not val:
        return False, "입주가능일이 입력되지 않았습니다."
    if val == "즉시입주":
        return True, ""
    if re.match(r"^\d{4}-\d{2}-(초순|중순|하순)$", val):
        # 날짜가 지났는지 확인
        m = re.match(r"^(\d{4})-(\d{2})-(초순|중순|하순)$", val)
        if m:
            y, mo = int(m.group(1)), int(m.group(2))
            today = date.today()
            if (y < today.year) or (y == today.year and mo < today.month):
                return False, f"입주가능일 '{val}'이 이미 지났습니다. 즉시입주 또는 현재 가능한 날짜로 수정하세요."
        return True, ""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", val):
        try:
            y,mo,d2 = map(int, val.split("-"))
            if date(y,mo,d2) < date.today():
                return False, f"입주가능일 '{val}'이 이미 지났습니다. 즉시입주 또는 현재 가능한 날짜로 수정하세요."
        except ValueError:
            return False, "입주가능일 날짜 형식이 올바르지 않습니다."
        return True, ""
    return False, "입주가능일 형식 오류. (즉시입주 / YYYY-MM-DD / YYYY-MM-초·중·하순)"

def _check_rooms(d, a):
    if _is_residential(d):
        if d.get("욕실수") is None:
            return False, "주택은 욕실 수를 표시해야 합니다 (없으면 0)."
        if d.get("방수") is None:
            return False, "주택은 방 수를 표시해야 합니다 (없으면 0)."
    else:
        if d.get("욕실수") is None:
            return False, "욕실(화장실) 수를 표시해야 합니다 (없으면 0)."
    return True, ""

def _check_use_apr(d, a):
    val = d.get("사용승인일","").strip()
    if not val:
        return False, "사용승인일이 입력되지 않았습니다."
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", val):
        return False, "사용승인일은 YYYY-MM-DD 형식으로 정확히 표기해야 합니다 (연도·월만 표시 불가)."
    return True, ""

def _check_parking(d, a):
    if d.get("주차대수_총") is None and d.get("주차대수_세대당") is None:
        return False, "주차대수(총 또는 세대당)를 입력해야 합니다."
    return True, ""

def _check_parking_match(d, a):
    disclosed = d.get("주차대수_총")
    auto      = a.get("parkingTotal")
    if disclosed is None or not auto:
        return True, ""
    if int(disclosed) != int(auto):
        if d.get("주차대수_실제메모","").strip():
            return True, ""  # 병기 있으면 허용
        return False, f"주차대수({disclosed}대)가 건축물대장 기준({auto}대)과 다릅니다."
    return True, ""

def _check_manage(d, a):
    t = d.get("관리비_정액여부","")
    if not t:
        return False, "관리비 유형을 선택해야 합니다 (정액/월평균/없음)."
    if t == "없음":
        return True, ""
    total = d.get("관리비_총액") or 0
    if t in ("정액","월평균") and not total:
        return False, "관리비 금액을 입력해야 합니다."
    # 월 10만원 이상 정액: 비목 합계 확인
    if t == "정액" and total >= 100000:
        bimok = d.get("관리비_비목",{})
        bimok_sum = sum(v or 0 for v in bimok.values())
        if bimok_sum == 0:
            return False, "월 10만원 이상 정액 관리비는 8개 비목별 금액을 입력해야 합니다. (의뢰인이 세부내역 미제공 시 생략 가능)"
    return True, ""

def _check_direction(d, a):
    direction = d.get("방향","")
    basis     = d.get("방향_기준","")
    if not direction:
        return False, "방향이 입력되지 않았습니다."
    if direction not in EIGHT_DIRECTIONS:
        return False, f"방향은 8가지 중 하나여야 합니다: {', '.join(sorted(EIGHT_DIRECTIONS))}"
    if not basis:
        return False, "방향 기준(거실/안방/주된 출입구)을 함께 표시해야 합니다."
    return True, ""

def _check_office_field(field):
    def fn(d, a):
        return (True,"") if a.get("_office",{}).get(field) else (False, f"중개사무소 {field} 미기재")
    return fn

# ─── 규칙 배열 ──────────────────────────────────────────────────────────────
RULES = [
    # 명시의무
    {"id":"R01","category":"명시의무","subject":"소재지",
     "law":"명시사항 세부기준 제6조 1호","check":_check_address},
    {"id":"R02","category":"명시의무","subject":"면적",
     "law":"명시사항 세부기준 제6조 2호","check":_check_area},
    {"id":"R03","category":"명시의무","subject":"가격",
     "law":"명시사항 세부기준 제6조 3호","check":_check_price},
    {"id":"R04","category":"명시의무","subject":"중개대상물종류",
     "law":"명시사항 세부기준 제6조 4호","check":_check_purps},
    {"id":"R05","category":"명시의무","subject":"거래형태",
     "law":"명시사항 세부기준 제6조 5호","check":_check_trade},
    {"id":"R06","category":"명시의무","subject":"총층수(지상)",
     "law":"명시사항 세부기준 제6조 6호","check":_check_floor},
    {"id":"R07","category":"명시의무","subject":"입주가능일",
     "law":"명시사항 세부기준 제6조 7호","check":_check_movein},
    {"id":"R08","category":"명시의무","subject":"방수/욕실수",
     "law":"명시사항 세부기준 제6조 8호","check":_check_rooms},
    {"id":"R09","category":"명시의무","subject":"사용승인일",
     "law":"명시사항 세부기준 제6조 9호","check":_check_use_apr},
    {"id":"R10","category":"명시의무","subject":"주차대수",
     "law":"명시사항 세부기준 제6조 10호","check":_check_parking},
    {"id":"R11","category":"명시의무","subject":"관리비",
     "law":"명시사항 세부기준 제6조 11호","check":_check_manage},
    {"id":"R12","category":"명시의무","subject":"방향",
     "law":"명시사항 세부기준 제6조 12호","check":_check_direction},
    # 거짓·과장
    {"id":"R13","category":"거짓광고","subject":"면적-대장일치",
     "law":"부당 표시·광고 고시 제6조 1항 2호","check":_check_area_match},
    {"id":"R14","category":"거짓광고","subject":"총층수-대장일치",
     "law":"부당 표시·광고 고시 제6조","check":_check_floor_match},
    {"id":"R15","category":"거짓광고","subject":"주차대수-대장일치",
     "law":"명시사항 세부기준 제6조 10호","check":_check_parking_match},
    # 사무소
    {"id":"R16","category":"사무소","subject":"사무소 명칭",
     "law":"명시사항 세부기준 제3조 1호","check":_check_office_field("명칭")},
    {"id":"R17","category":"사무소","subject":"사무소 소재지",
     "law":"명시사항 세부기준 제3조 2호","check":_check_office_field("소재지")},
    {"id":"R18","category":"사무소","subject":"사무소 연락처",
     "law":"명시사항 세부기준 제3조 3호","check":_check_office_field("연락처")},
    {"id":"R19","category":"사무소","subject":"등록번호",
     "law":"명시사항 세부기준 제3조 4호","check":_check_office_field("등록번호")},
    {"id":"R20","category":"사무소","subject":"개업공인중개사 성명",
     "law":"명시사항 세부기준 제4조","check":_check_office_field("성명")},
]
