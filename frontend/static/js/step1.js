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
        window.location.href = "index.html";
      }
    });
  }

  // Handle Form Submit
  const form = document.getElementById("businessTypeForm");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();

      const data = {
        business_name: this.business_name.value,
        business_type: this.business_type.value,
      };

      localStorage.setItem("step1", JSON.stringify(data));
      window.location.href = "step2.html";
    });
  }

  // --- Timed Unlock Logic ---
  // Wait 500ms and then remove 'readonly' from all shielded inputs
  setTimeout(() => {
    const protectedInputs = document.querySelectorAll('input[readonly], textarea[readonly]');
    protectedInputs.forEach(input => {
      input.removeAttribute('readonly');
    });
  }, 500);
});
