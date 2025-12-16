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
        window.location.href = "step3.html";
      }
    });
  }

  // טוען את כל המידע מהשלבים הקודמים
  const step1 = JSON.parse(localStorage.getItem("step1")) || {};
  const step2 = JSON.parse(localStorage.getItem("step2")) || {};
  const step3 = JSON.parse(localStorage.getItem("step3")) || {};

  // מאחד הכל
  const finalData = { ...step1, ...step2, ...step3 };

  // מציג את הנתונים על המסך
  const summaryEl = document.getElementById("summaryCard");
  if (summaryEl) {
    summaryEl.innerHTML = `
      <h2 class="text-xl font-bold mb-4">פרטי העסק:</h2>
      <ul class="space-y-2 text-gray-700">
        <li><b>שם העסק:</b> ${finalData.business_name || "-"}</li>
        <li><b>סוג העסק:</b> ${finalData.business_type || "-"}</li>
        <li><b>שטח:</b> ${finalData.area_sqm || "-"} מ"ר</li>
        <li><b>מקומות ישיבה:</b> ${finalData.seating_capacity || "-"}</li>
        <li><b>עובדים:</b> ${finalData.employees || "-"}</li>
        <li><b>עיר:</b> ${finalData.city || "-"}</li>
        <li><b>מאפיינים:</b>
          <ul class="list-disc pr-6">
            ${finalData.has_gas ? "<li>שימוש בגז</li>" : ""}
            ${finalData.serves_meat ? "<li>הגשת בשר</li>" : ""}
            ${finalData.has_delivery ? "<li>משלוחים</li>" : ""}
            ${finalData.has_alcohol ? "<li>מכירת אלכוהול</li>" : ""}
          </ul>
        </li>
      </ul>
    `;
  }

  // כפתור אישור → מעבר ל-results.html
  const confirmBtn = document.getElementById("confirmBtn");
  if (confirmBtn) {
    confirmBtn.addEventListener("click", () => {
      localStorage.setItem("finalBusinessData", JSON.stringify(finalData));
      window.location.href = "results.html";
    });
  }
});
