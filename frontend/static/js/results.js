// --- שליפת נתוני המשתמש מה-localStorage ---
const finalData = JSON.parse(localStorage.getItem("finalBusinessData")) || {};

const el = {
  loader: document.getElementById("loader"),
  globalError: document.getElementById("globalError"),
  aiSections: document.getElementById("aiSections"),
  costTime: document.getElementById("costTime"),
  charts: document.getElementById("charts"),
  requirementsSection: document.getElementById("requirementsSection"),
  allRulesSection: document.getElementById("allRulesSection"),

  reportTitle: document.getElementById("reportTitle"),
  reportDate: document.getElementById("reportDate"),

  businessHeader: document.getElementById("businessHeader"),
  bhType: document.getElementById("bhType"),
  bhArea: document.getElementById("bhArea"),
  bhSeats: document.getElementById("bhSeats"),
  bhCity: document.getElementById("bhCity"),
  bhFlags: document.getElementById("bhFlags"),

  executiveSummary: document.getElementById("executiveSummary"),
  recommendations: document.getElementById("recommendations"),

  costEstimate: document.getElementById("costEstimate"),
  timeEstimate: document.getElementById("timeEstimate"),

  requirementsList: document.getElementById("requirementsList"),
  rulesCount: document.getElementById("rulesCount"),

  allRulesList: document.getElementById("allRulesList")
};

function show(node) { node.classList.remove("hidden"); }
function hide(node) { node.classList.add("hidden"); }

async function fetchReport() {
  try {
    // מצב טעינה
    show(el.loader);
    hide(el.globalError);
    hide(el.aiSections);
    hide(el.costTime);
    hide(el.charts);
    hide(el.requirementsSection);
    hide(el.allRulesSection);

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
    hide(el.loader);
    show(el.globalError);
  }
}

// --- עיבוד התוצאה למסך ---
function renderReport(data) {
  // כותרת
  el.reportTitle.innerHTML =
    `דוח רישוי עבור: <span class="text-blue-600">${data.business_name || "—"}</span>`;
  el.reportDate.textContent =
    `הופק בתאריך: ${new Date().toLocaleDateString("he-IL")}, סוג עסק: ${data.business_type || "—"}`;

  // סטריפ מידע כללי
  el.bhType.textContent = data.business_type || "—";
  el.bhArea.textContent = data.area_sqm ?? "—";
  el.bhSeats.textContent = data.seating_capacity ?? "—";
  el.bhCity.textContent = data.city ?? "—";
  el.bhFlags.innerHTML = [
    data.has_gas ? "יש גז" : null,
    data.serves_meat ? "מגיש בשר" : null,
    data.has_delivery ? "יש משלוחים" : null,
    data.has_alcohol ? "מכירת אלכוהול" : null
  ].filter(Boolean).map(f => `<span class="inline-block text-xs bg-gray-100 px-2 py-1 rounded mr-1">${f}</span>`).join(" ");
  show(el.businessHeader);

  // תמצית מנהלים
  el.executiveSummary.innerHTML = `
    <p>${data.executive_summary || "לא התקבל תקציר מה-AI"}</p>
  `;

  // המלצות פעולה
  if (Array.isArray(data.recommendations) && data.recommendations.length > 0) {
    el.recommendations.innerHTML = `
      <ul class="list-disc pl-6 space-y-1">
        ${data.recommendations.map(r => `<li>${r}</li>`).join("")}
      </ul>
    `;
  } else {
    el.recommendations.innerHTML = `<p>אין המלצות נוספות</p>`;
  }
  show(el.aiSections);

  // הערכת עלות/זמן
  el.costEstimate.innerHTML = `
    <h3 class="font-bold text-lg mb-2 flex items-center gap-2">
      <i data-lucide="dollar-sign" class="text-green-600"></i> עלות כוללת משוערת
    </h3>
    <p>${data.estimated_cost || "לא צויין"}</p>
  `;
  el.timeEstimate.innerHTML = `
    <h3 class="font-bold text-lg mb-2 flex items-center gap-2">
      <i data-lucide="clock" class="text-blue-600"></i> לוח זמנים משוער
    </h3>
    <p>${data.estimated_time || "לא צויין"}</p>
  `;
  show(el.costTime);

  // דרישות רגולטוריות - קיבוץ לפי קטגוריה
  const rules = Array.isArray(data.matched_rules) ? data.matched_rules : [];
  el.rulesCount.textContent = `נמצאו ${data.matched_rules_count ?? rules.length} חוקים רלוונטיים`;

  if (rules.length > 0) {
    const grouped = groupByCategory(rules);
    el.requirementsList.innerHTML = Object.keys(grouped).map(cat => `
      <div class="py-2">
        <h3 class="font-bold text-lg text-blue-700">${cat} <span class="text-sm text-gray-500">(${grouped[cat].length})</span></h3>
        ${grouped[cat].map(r => ruleDetails(r)).join("")}
      </div>
    `).join("");
    show(el.requirementsSection);

    // גרפים
    renderCharts(grouped, rules);
    show(el.charts);

    // RAW list (אופציונלי להצלבה)
    el.allRulesList.innerHTML = rules.map(r => `
      <details class="py-3">
        <summary class="cursor-pointer font-semibold">${r.id || ""} – ${r.title || ""}</summary>
        <pre class="mt-2 bg-gray-50 p-3 rounded text-xs overflow-auto">${escapeHtml(JSON.stringify(r, null, 2))}</pre>
      </details>
    `).join("");
    // אפשר להסתיר אם לא צריך:
    // show(el.allRulesSection);
  } else {
    el.requirementsList.innerHTML = `<p>לא נמצאו חוקים</p>`;
    show(el.requirementsSection);
  }

  // סוף טעינה
  hide(el.loader);

  // אייקונים
  lucide.createIcons();
}

function groupByCategory(rules) {
  const out = {};
  rules.forEach(r => {
    const cat = r.category || "לא מסווג";
    if (!out[cat]) out[cat] = [];
    out[cat].push(r);
  });
  return out;
}

function ruleDetails(r) {
  const actions = Array.isArray(r.actions) ? r.actions : [];
  const steps = Array.isArray(r.steps) ? r.steps : []; // אם תוסיף later שלבי "לפני/במהלך/אחרי"

  return `
    <details class="mb-2 p-3 border rounded-lg bg-gray-50">
      <summary class="cursor-pointer font-semibold flex justify-between items-center">
        <span>${r.id || ""} – ${r.title || ""}</span>
        <span class="text-xs bg-gray-100 px-2 py-0.5 rounded">${r.priority || "לא צויין"}</span>
      </summary>
      <div class="mt-2 text-sm text-gray-700 space-y-2">
        ${actions.length ? `
          <div>
            <b>פעולות נדרשות:</b>
            <ul class="list-disc pr-5 mt-1">
              ${actions.map(a => `<li>${a}</li>`).join("")}
            </ul>
          </div>
        ` : ""}

        ${r.estimated_cost ? `<p><b>עלות משוערת:</b> ${r.estimated_cost}</p>` : ""}
        ${r.estimated_time ? `<p><b>זמן משוער:</b> ${r.estimated_time}</p>` : ""}

        ${steps.length ? `
          <div class="mt-2">
            <b>שלבים:</b>
            <div class="grid md:grid-cols-3 gap-3 mt-2">
              ${renderStepColumn("לפני פתיחה", steps.filter(s => s.phase === "before"))}
              ${renderStepColumn("במהלך תהליך הרישוי", steps.filter(s => s.phase === "during"))}
              ${renderStepColumn("אחרי פתיחה / תחזוקה שוטפת", steps.filter(s => s.phase === "after"))}
            </div>
          </div>
        ` : ""}
      </div>
    </details>
  `;
}

function renderStepColumn(title, items) {
  if (!items || items.length === 0) {
    return `<div class="bg-white p-3 rounded border"><div class="text-sm text-gray-500">${title}</div><div class="text-xs text-gray-400 mt-1">—</div></div>`;
  }
  return `
    <div class="bg-white p-3 rounded border">
      <div class="text-sm font-semibold">${title}</div>
      <ul class="list-disc pr-5 mt-2 text-sm">
        ${items.map(i => `<li>${i.text}</li>`).join("")}
      </ul>
    </div>
  `;
}

function renderCharts(grouped, rules) {
  // Pie לפי קטגוריה
  const labels = Object.keys(grouped);
  const values = labels.map(l => grouped[l].length);

  const pieCtx = document.getElementById("rulesPie").getContext("2d");
  new Chart(pieCtx, {
    type: "pie",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: ["#2563eb","#16a34a","#f59e0b","#dc2626","#9333ea","#0d9488","#64748b"]
      }]
    },
    options: { plugins: { legend: { position: "bottom" } } }
  });

  // Bar לפי עדיפות
  const priorities = ["קריטי","גבוה","בינוני","נמוך","לא צויין"];
  const prCounts = { "קריטי":0,"גבוה":0,"בינוני":0,"נמוך":0,"לא צויין":0 };
  rules.forEach(r => { prCounts[r.priority || "לא צויין"] = (prCounts[r.priority || "לא צויין"] || 0) + 1; });

  const barCtx = document.getElementById("priorityBar").getContext("2d");
  new Chart(barCtx, {
    type: "bar",
    data: {
      labels: priorities,
      datasets: [{
        label: "מספר חוקים",
        data: priorities.map(p => prCounts[p] || 0),
        backgroundColor: "#2563eb"
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
    }
  });
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, m => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[m]));
}

// --- קריאה בהטענת הדף ---
fetchReport();