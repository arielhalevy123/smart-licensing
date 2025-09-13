document.getElementById("businessDetailsForm").addEventListener("submit", function (e) {
  e.preventDefault();

  const step1Data = JSON.parse(localStorage.getItem("step1")) || {};

  const data = {
    ...step1Data,
    area_sqm: this.area_sqm.value,
    seating_capacity: this.seating_capacity.value,
    employees: this.employees.value,
    city: this.city.value
  };

  localStorage.setItem("step2", JSON.stringify(data));

  // מעבר לשלב הבא
  window.location.href = "step3.html";
});