document.getElementById("businessFeaturesForm").addEventListener("submit", function (e) {
  e.preventDefault();

  const step2Data = JSON.parse(localStorage.getItem("step2")) || {};

  const data = {
    ...step2Data,
    has_gas: this.has_gas.checked,
    serves_meat: this.serves_meat.checked,
    has_delivery: this.has_delivery.checked,
    has_alcohol: this.has_alcohol.checked
  };

  localStorage.setItem("step3", JSON.stringify(data));

  window.location.href = "step4.html";
});