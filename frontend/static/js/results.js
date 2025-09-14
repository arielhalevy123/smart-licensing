// --- שליפת נתוני המשתמש מה-localStorage ---
const finalData = JSON.parse(localStorage.getItem("finalBusinessData")) || {};
const aiReportCache = JSON.parse(localStorage.getItem("aiReport")) || null;

// פונקציית קריאה ל-API
async function fetchReport() {
  try {
    let data = aiReportCache;

    if (!data) {
      const res = await fetch("/api/generate-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(finalData)
      });
      if (!res.ok) throw new Error("שגיאה בשרת");
      data = await res.json();
      localStorage.setItem("aiReport", JSON.stringify(data));
    }

    renderReport(data);
  } catch (err) {
    console.error("שגיאה:", err);
    document.getElementById("executiveSummary").innerHTML =
      `<p class="text-red-600">נכשלה שליפת הדוח</p>`;
  }
}

// --- עיבוד התוצאה למסך ---
function renderReport(data) {
  // כותרת
  document.getElementById("reportTitle").innerHTML =
    `דוח רישוי עבור: <span class="text-blue-600">${data.business_name}</span>`;
  document.getElementById("reportDate").textContent =
    `הופק בתאריך: ${new Date().toLocaleDateString("he-IL")}, סוג עסק: ${data.business_type}`;

  // תמצית מנהלים
  document.getElementById("executiveSummary").innerHTML = `
    <p>${data.executive_summary || "לא התקבל תקציר מה-AI"}</p>
  `;

  // הערכת עלות (אפשר לשפר – כרגע נתון לדוגמה או מתוך AI)
  document.getElementById("costEstimate").innerHTML = `
    <h3 class="font-bold text-lg mb-2 flex items-center gap-2">
      <i data-lucide="dollar-sign" class="text-green-600"></i> עלות כוללת משוערת
    </h3>
    <p>${data.estimated_cost || "2,500 ₪ - 8,000 ₪ (הערכה בלבד)"}</p>
  `;

  // הערכת זמן
  document.getElementById("timeEstimate").innerHTML = `
    <h3 class="font-bold text-lg mb-2 flex items-center gap-2">
      <i data-lucide="clock" class="text-blue-600"></i> לוח זמנים משוער
    </h3>
    <p>${data.estimated_time || "6-20 שבועות (הערכה בלבד)"}</p>
  `;

  // דרישות רגולטוריות
  const listEl = document.getElementById("requirementsList");
  if (data.matched_rules && data.matched_rules.length > 0) {
    listEl.innerHTML = data.matched_rules.map((r, i) => `
      <details class="py-3">
        <summary class="cursor-pointer font-semibold flex justify-between items-center">
          <span>${r.title}</span>
          <span class="text-sm text-gray-500">עדיפות: ${r.priority || "לא צוינה"}</span>
        </summary>
        <ul class="list-disc pr-6 mt-2 space-y-1 text-gray-700">
          ${r.actions.map(a => `<li>${a}</li>`).join("")}
        </ul>
      </details>
    `).join("");
  } else {
    listEl.innerHTML = `<p>לא נמצאו דרישות רלוונטיות</p>`;
  }

  lucide.createIcons();
}

// --- קריאה בהטענת הדף ---
fetchReport();