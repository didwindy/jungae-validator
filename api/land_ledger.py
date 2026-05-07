"""
VWorld 토지임야정보 API 래퍼
엔드포인트: http://api.vworld.kr/ned/data/ladfrlList
응답: XML

INCORRECT_KEY 간헐적 오류 대응:
  - VWorld NED API는 domain 파라미터가 등록된 값과 다르면 INCORRECT_KEY 반환
  - 로컬 테스트 시 domain을 "localhost", "", "127.0.0.1" 순으로 자동 시도
  - 재시도 최대 3회
"""
import time
import requests
import xml.etree.ElementTree as ET
from config import VWORLD_KEY, VWORLD_DOMAIN

VWORLD_LAND_URL = "http://api.vworld.kr/ned/data/ladfrlList"

# domain 후보 목록 (등록 도메인 → localhost → 빈값 순서로 시도)
def _domain_candidates() -> list:
    candidates = [VWORLD_DOMAIN]
    for d in ["localhost", "", "127.0.0.1"]:
        if d not in candidates:
            candidates.append(d)
    return candidates


def _is_dummy_mode() -> bool:
    return not VWORLD_KEY or any(
        kw in VWORLD_KEY for kw in ("YOUR_VWORLD_KEY", "여기에", "입력")
    )


def get_land_info(pnu: str) -> dict:
    """PNU(19자리)로 VWorld 토지임야 목록 조회 — domain 자동 시도 + 재시도"""
    if _is_dummy_mode():
        return _dummy_land(pnu)

    last_error = "알 수 없는 오류"

    for domain in _domain_candidates():
        for attempt in range(2):   # domain당 최대 2회 시도
            result = _try_once(pnu, domain)
            if "error" not in result:
                return result               # 성공 즉시 반환

            err_msg = result["error"]
            last_error = err_msg

            if "INCORRECT_KEY" in err_msg:
                # 이 domain은 틀림 → 다음 domain으로
                break
            if attempt == 0:
                time.sleep(0.5)             # 일시적 오류면 0.5초 후 재시도

    return {"error": f"토지대장 조회 실패: {last_error}\n💡 .env의 VWORLD_DOMAIN을 VWorld 키 발급 시 등록한 도메인으로 설정하세요."}


def _try_once(pnu: str, domain: str) -> dict:
    params = {
        "key":       VWORLD_KEY,
        "domain":    domain,
        "pnu":       pnu,
        "format":    "xml",
        "numOfRows": 10,
        "pageNo":    1,
    }
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/xml, text/xml, */*",
        }
        resp = requests.get(VWORLD_LAND_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)

        err_el = root.find(".//error")
        if err_el is not None:
            reason = err_el.findtext("text") or err_el.text or "알 수 없는 오류"
            return {"error": reason}

        total = int(root.findtext("totalCount") or 0)
        if total == 0:
            return {"error": "해당 PNU의 토지 정보가 없습니다."}

        vo = root.find("ladfrlVOList")
        if vo is None:
            return {"error": f"파싱 실패. 원문: {resp.text[:200]}"}

        return {
            "landArea": float(vo.findtext("lndpclAr") or 0),
            "jimok":    vo.findtext("lndcgrCodeNm") or vo.findtext("lndcgrCode") or "",
            "ldCodeNm": vo.findtext("ldCodeNm") or "",
            "pnu":      pnu,
        }
    except ET.ParseError:
        return {"error": f"XML 파싱 실패: {resp.text[:150]}"}
    except requests.exceptions.Timeout:
        return {"error": "응답 시간 초과 (8초)"}
    except Exception as e:
        return {"error": str(e)}


def _dummy_land(pnu: str) -> dict:
    return {
        "landArea": 330.0, "jimok": "대",
        "ldCodeNm": "[더미] 소재지명", "pnu": pnu,
        "_dummy": True,
    }


def build_pnu(sigungu_cd, bjdong_cd, plat_gb_cd, bun, ji) -> str:
    return (
        sigungu_cd.zfill(5) + bjdong_cd.zfill(5) +
        (plat_gb_cd or "0") + bun.zfill(4) + ji.zfill(4)
    )
