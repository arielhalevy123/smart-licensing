document.addEventListener("DOMContentLoaded", () => {
  // Initialize Icons
  if (window.lucide) window.lucide.createIcons();

  // Handle Back Button
  const backBtn = document.getElementById("backBtn");
  if (backBtn) {
    backBtn.addEventListener("click", () => {
      if (window.history.length > 1) {
        window.history.back();
      } else {
        window.location.href = "step1.html";
      }
    });
  }

  // Handle Form Submit
  const form = document.getElementById("businessDetailsForm");
  if (form) {
    form.addEventListener("submit", function (e) {
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
      window.location.href = "step3.html";
    });
  }

});
