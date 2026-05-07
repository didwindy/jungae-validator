/**
 * tab3_office.js — 중개사무소 및 개업공인중개사 5개 항목
 */

function renderTab3() {
  const o = AppState.office;
  document.getElementById("t3-name").value     = o.명칭;
  document.getElementById("t3-address").value  = o.소재지;
  document.getElementById("t3-phone").value    = o.연락처;
  document.getElementById("t3-regnum").value   = o.등록번호;
  document.getElementById("t3-broker").value   = o.성명;
}

function onSaveOffice() {
  const o = AppState.office;
  o.명칭    = document.getElementById("t3-name").value.trim();
  o.소재지  = document.getElementById("t3-address").value.trim();
  o.연락처  = document.getElementById("t3-phone").value.trim();
  o.등록번호 = document.getElementById("t3-regnum").value.trim();
  o.성명    = document.getElementById("t3-broker").value.trim();

  AppState.saveOfficeToStorage();

  const btn = document.getElementById("t3-save-btn");
  btn.textContent = "✓ 저장됨";
  btn.classList.add("saved");
  setTimeout(() => {
    btn.textContent = "저장";
    btn.classList.remove("saved");
  }, 1500);
}

function onClearOffice() {
  if (!confirm("중개사무소 정보를 초기화하시겠습니까?")) return;
  AppState.office = { 명칭: "", 소재지: "", 연락처: "", 등록번호: "", 성명: "" };
  localStorage.removeItem("officeInfo");
  renderTab3();
}
