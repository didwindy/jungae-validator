"""
중개대상물 광고 검증 시스템 - Flask 백엔드
"""
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from validators.engine import validate
from api.vworld import (
    search_candidates_with_fallback,
    geocode_single_with_fallback,
)
from api.building_hub import (
    get_title_info_safe as get_title_info,
    get_recap_title_info_safe as get_recap_title_info,
    get_expos_info_safe as get_expos_info,
    get_exclusive_area_safe as get_exclusive_area_by_address,
    get_dong_title_info_safe as get_dong_title_info,
)
from api.land_ledger import get_land_info, build_pnu

app = Flask(__name__)
CORS(app)


@app.route("/")
def index():
    return render_template("index.html")


# ─── 헬스체크 (UptimeRobot 슬립 방지용) ─────────────────────────────────
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200


# ─── 탭1: 주소 후보 목록 ────────────────────────────────────────────────
@app.route("/api/search-candidates", methods=["POST"])
def search_candidates_api():
    data  = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "검색어를 입력해주세요."}), 400
    result = search_candidates_with_fallback(query)
    return jsonify(result)


@app.route("/api/geocode-single", methods=["POST"])
def geocode_single_api():
    data    = request.get_json()
    address = data.get("address", "").strip()
    if not address:
        return jsonify({"error": "주소가 없습니다."}), 400
    result = geocode_single_with_fallback(address)
    return jsonify(result)


# ─── 탭1: 토지/건축물 조회 ──────────────────────────────────────────────
@app.route("/api/land-info", methods=["POST"])
def land_info_api():
    data = request.get_json()
    try:
        pnu = build_pnu(
            data["sigunguCd"], data["bjdongCd"],
            data.get("platGbCd", "0"),
            data["bun"], data["ji"]
        )
        return jsonify(get_land_info(pnu))
    except KeyError as e:
        return jsonify({"error": f"필수 파라미터 누락: {e}"}), 400


@app.route("/api/building-title", methods=["POST"])
def building_title_api():
    data = request.get_json()
    sg, bd = data.get("sigunguCd",""), data.get("bjdongCd","")
    bun, ji = data.get("bun",""), data.get("ji","")

    title = get_title_info(sg, bd, bun, ji)
    recap = get_recap_title_info(sg, bd, bun, ji)

    has_recap    = "error" not in recap
    parking      = recap.get("parking")     or title.get("parking", 0)
    total_floors = recap.get("grndFlrCnt")  or title.get("grndFlrCnt", 0)
    under_floors = recap.get("ugrndFlrCnt") or title.get("ugrndFlrCnt", 0)
    use_apr      = recap.get("useAprDay")   or title.get("useAprDay", "")
    main_purps   = recap.get("mainPurps")   or title.get("mainPurps", "")

    return jsonify({
        "parking":      parking,
        "totalFloors":  total_floors,
        "underFloors":  under_floors,
        "useAprDay":    use_apr,
        "mainPurps":    main_purps,
        "etcPurps":     title.get("etcPurps", ""),
        "regstrGbCdNm": title.get("regstrGbCdNm", ""),
        "isAggregate":  has_recap,
        "error":        title.get("error"),
    })


@app.route("/api/building-dong-ho", methods=["POST"])
def building_dong_ho_api():
    data = request.get_json()
    result = get_expos_info(
        data.get("sigunguCd",""), data.get("bjdongCd",""),
        data.get("bun",""), data.get("ji","")
    )
    return jsonify(result)


@app.route("/api/dong-floors", methods=["POST"])
def dong_floors_api():
    data = request.get_json()
    result = get_dong_title_info(
        data.get("sigunguCd",""), data.get("bjdongCd",""),
        data.get("bun",""), data.get("ji",""),
        data.get("dongNm","")
    )
    return jsonify(result)


@app.route("/api/exclusive-area", methods=["POST"])
def exclusive_area_api():
    data = request.get_json()
    result = get_exclusive_area_by_address(
        data.get("sigunguCd",""), data.get("bjdongCd",""),
        data.get("bun",""), data.get("ji",""),
        data.get("dongNm",""), data.get("hoNm","")
    )
    return jsonify(result)


# ─── 탭4: 검증 ──────────────────────────────────────────────────────────
@app.route("/api/validate", methods=["POST"])
def validate_api():
    data = request.get_json()
    result = validate(
        data.get("disclosure", {}),
        data.get("address", {}),
        data.get("office", {})
    )
    return jsonify(result)


# ─── API 키 상태 확인 ────────────────────────────────────────────────────
@app.route("/api/test-keys", methods=["GET"])
def test_keys_api():
    from api.building_hub import _is_dummy_mode as hub_dummy
    from api.land_ledger  import _is_dummy_mode as land_dummy
    from api.vworld       import _is_dummy_mode as vworld_dummy

    return jsonify({
        "buildingHub": {"keySet": not hub_dummy()},
        "vworld":      {"keySet": not vworld_dummy()},
        "land":        {"keySet": not land_dummy()},
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
