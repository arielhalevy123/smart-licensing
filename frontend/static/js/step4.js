// שליפת הנתונים מה-localStorage
const step1 = JSON.parse(localStorage.getItem("step1")) || {};
const step2 = JSON.parse(localStorage.getItem("step2")) || {};
const step3 = JSON.parse(localStorage.getItem("step3")) || {};

// מילוי הסיכום
document.getElementById("summaryName").textContent = step1.business_name || "-";
document.getElementById("summaryType").textContent = step1.business_type || "-";
document.getElementById("summaryArea").textContent = step2.area_sqm || "-";
document.getElementById("summarySeats").textContent = step2.seating_capacity || "-";
document.getElementById("summaryLocation").textContent = step2.location_type || "אזור מגורים";

const featuresList = document.getElementById("summaryFeatures");
featuresList.innerHTML = (step3.features || []).map(f => `<li>${f}</li>`).join("");

// כפתור יצירת דוח
document.getElementById("generateBtn").addEventListener("click", async () => {
  const finalData = {
    ...step1,
    ...step2,
    ...step3
  };

  // שמור ב-localStorage
  localStorage.setItem("finalBusinessData", JSON.stringify(finalData));

  try {
    const res = await fetch("/api/generate-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(finalData)
    });
    const data = await res.json();

    localStorage.setItem("aiReport", JSON.stringify(data));
    window.location.href = "results.html";
  } catch (err) {
    alert("שגיאה ביצירת הדוח: " + err.message);
  }
});