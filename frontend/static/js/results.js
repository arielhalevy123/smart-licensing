// --- שליפת נתוני המשתמש מה-localStorage ---
const finalData = JSON.parse(localStorage.getItem("finalBusinessData")) || {};

async function fetchReport() {
  try {
    // נוודא שתמיד נשלחת בקשה חדשה
    localStorage.removeItem("aiReport");

    const res = await fetch("/api/generate-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(finalData)
    });
    if (!res.ok) throw new Error("שגיאה בשרת");

    const data = await res.json();
    localStorage.setItem("aiReport", JSON.stringify(data));

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

  // המלצות פעולה
  const recEl = document.getElementById("recommendations");
  if (data.recommendations && data.recommendations.length > 0) {
    recEl.innerHTML = `
      <h3 class="font-bold text-lg mb-2 flex items-center gap-2">
        <i data-lucide="check-circle" class="text-green-600"></i> המלצות לפעולה
      </h3>
      <ul class="list-disc pl-6 space-y-1">
        ${data.recommendations.map(r => `<li>${r}</li>`).join("")}
      </ul>
    `;
  } else {
    recEl.innerHTML = `<p>אין המלצות נוספות</p>`;
  }

  // הערכת עלות
  document.getElementById("costEstimate").innerHTML = `
    <h3 class="font-bold text-lg mb-2 flex items-center gap-2">
      <i data-lucide="dollar-sign" class="text-green-600"></i> עלות כוללת משוערת
    </h3>
    <p>${data.estimated_cost || "לא צויין"}</p>
  `;

  // הערכת זמן
  document.getElementById("timeEstimate").innerHTML = `
    <h3 class="font-bold text-lg mb-2 flex items-center gap-2">
      <i data-lucide="clock" class="text-blue-600"></i> לוח זמנים משוער
    </h3>
    <p>${data.estimated_time || "לא צויין"}</p>
  `;

  // דרישות רגולטוריות
  const listEl = document.getElementById("requirementsList");
  if (data.requirements_by_priority && data.requirements_by_priority.length > 0) {
    listEl.innerHTML = data.requirements_by_priority.map(r => `
      <details class="mb-3 p-4 border rounded-lg shadow bg-white">
        <summary class="cursor-pointer font-semibold flex justify-between items-center">
          <span>${r.title} <span class="ml-2 text-sm text-gray-500">(${r.priority})</span></span>
          <span class="text-xs bg-gray-100 px-2 py-0.5 rounded">${r.category || ""}</span>
        </summary>
        <div class="mt-2 text-sm text-gray-700 space-y-1">
          <p><b>פעולות נדרשות:</b> ${r.actions ? r.actions.join(", ") : "לא צויין"}</p>
          <p><b>עלות משוערת:</b> ${r.estimated_cost || "לא צויין"}</p>
          <p><b>זמן משוער:</b> ${r.estimated_time || "לא צויין"}</p>
        </div>
      </details>
    `).join("");
  } else {
    listEl.innerHTML = `<p>לא נמצאו דרישות רלוונטיות</p>`;
  }

  // אייקונים
  lucide.createIcons();
}

// --- קריאה בהטענת הדף ---
fetchReport();