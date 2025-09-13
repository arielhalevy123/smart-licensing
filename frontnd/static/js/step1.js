document.getElementById("businessTypeForm").addEventListener("submit", function (e) {
  e.preventDefault();

  const data = {
    business_name: this.business_name.value,
    business_type: this.business_type.value,
  };

  localStorage.setItem("step1", JSON.stringify(data));

  window.location.href = "step2.html";
});