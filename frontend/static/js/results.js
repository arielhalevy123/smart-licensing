// --- שליפת נתוני המשתמש מה-localStorage ---
const finalData = JSON.parse(localStorage.getItem("finalBusinessData")) || {};

// --- קריאה ל-API ---
async function fetchReport() {
  try {
    const res = await fetch("/api/generate-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(finalData)
    });

    if (!res.ok) throw new Error("שגיאה בשרת");

    const data = await res.json();

    // הצגת תמצית מנהלים
    const aiSumEl = document.getElementById("aiSummary");
    aiSumEl.innerHTML = `
      <h2 class="font-bold text-xl mb-2">תמצית מנהלים</h2>
      <p>${data.executive_summary}</p>
    `;

    // הצגת הערכות כלליות (בשלב ראשון GPT נותן תקציר כולל המלצות)
    const aiEstEl = document.getElementById("aiEstimates");
    aiEstEl.innerHTML = `
      <div class="p-4 bg-white border rounded-lg shadow"><b>סוג עסק:</b> ${data.business_type}</div>
      <div class="p-4 bg-white border rounded-lg shadow"><b>שם עסק:</b> ${data.business_name}</div>
    `;

    // הצגת דרישות רגולטוריות שחזרו מה-json_rules
    const listEl = document.getElementById("requirementsList");
    if (data.matched_rules && data.matched_rules.length > 0) {
      listEl.innerHTML = `
        <h2 class="font-bold text-xl mb-2">דרישות רגולטוריות</h2>
        <ul class="list-disc pr-6 space-y-1">
          ${data.matched_rules.map(r => `<li><b>${r.title}:</b> ${r.actions.join(", ")}</li>`).join("")}
        </ul>
      `;
    } else {
      listEl.innerHTML = `<p>לא נמצאו דרישות רלוונטיות</p>`;
    }

  } catch (err) {
    console.error("שגיאה:", err);
    document.getElementById("aiSummary").innerHTML = `<p class="text-red-600">נכשלה שליפת הדוח</p>`;
  }
}

// קריאה לפונקציה בהטענת הדף
fetchReport();