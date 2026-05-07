"""
검증 엔진: RULES 배열을 순회하며 결과 생성
"""
from validators.rules import RULES


def validate(disclosure: dict, address_data: dict, office: dict) -> dict:
    """
    disclosure: 탭2 명시사항 데이터
    address_data: 탭1 주소/대장 데이터 (자동 입력된 공부상 수치 포함)
    office: 탭3 중개사무소 데이터

    반환:
    {
        total: int,
        passed: int,
        failed: int,
        categories: {명시의무: [...], 거짓광고: [...], 사무소: [...]},
        details: [...]
    }
    """
    # office를 address_data에 병합 (규칙이 a 파라미터로 접근)
    combined_address = {**address_data, "_office": office}

    results = []
    for rule in RULES:
        try:
            ok, fail_msg = rule["check"](disclosure, combined_address)
        except Exception as e:
            ok, fail_msg = False, f"검증 오류: {str(e)}"

        results.append({
            "id": rule["id"],
            "category": rule["category"],
            "subject": rule["subject"],
            "law": rule["law"],
            "passed": ok,
            "message": "" if ok else fail_msg,
        })

    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed

    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    return {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "categories": categories,
        "details": results,
    }
