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

// --- ניהול זיכרון דוח (Persistence) ---
const ReportStore = {
  KEY: "saved_report_v1",

  get() {
    try {
      const saved = localStorage.getItem(this.KEY);
      if (!saved) return null;
      const parsed = JSON.parse(saved);
      // בדיקה שתוקף הדוח לא פג (למשל 24 שעות) או שהנתונים תקינים
      return parsed; 
    } catch {
      return null;
    }
  },

  set(data) {
    const obj = {
      content: data,
      createdAt: Date.now()
    };
    localStorage.setItem(this.KEY, JSON.stringify(obj));
  },

  clear() {
    localStorage.removeItem(this.KEY);
  }
};

async function fetchReport(forceRefresh = false) {
  try {
    // מצב טעינה
    show(el.loader);
    hide(el.globalError);
    hide(el.aiSections);
    hide(el.costTime);
    hide(el.charts);
    hide(el.requirementsSection);
    hide(el.allRulesSection);

    // 1. בדיקה אם קיים דוח שמור (אם לא ביקשו רענון כפוי)
    if (!forceRefresh) {
      const savedReport = ReportStore.get();
      // התיקון: בדיקת קיום של data object מלא, לא רק content
      // הוספנו בדיקה ש-savedReport עצמו קיים ושאינו אובייקט ריק
      if (savedReport && savedReport.content && Object.keys(savedReport.content).length > 0) {
        renderReport(savedReport.content, true); // true = loaded from memory
        return;
      }
    }

    // 2. אם אין שמור או ביקשו חדש -> קריאה לשרת
    const res = await fetch("/api/generate-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(finalData)
    });
    
    if (!res.ok) throw new Error("שגיאה בשרת");

    const data = await res.json();
    
    // 3. שמירה בזיכרון
    if (data && !data.error) {
       ReportStore.set(data);
    }

    renderReport(data, false); // false = fresh from server

  } catch (err) {
    console.error("שגיאה:", err);
    // אם הייתה שגיאה בעת רענון יזום, נמחק את הדוח הישן כדי לא להציג מידע לא רלוונטי
    if (forceRefresh) {
        ReportStore.clear();
    }
    hide(el.loader);
    show(el.globalError);
  }
}

// --- עיבוד התוצאה למסך ---
function renderReport(data, fromMemory = false) {
  // אינדיקטור לדיבאג / משתמש
  if (fromMemory) {
    const indicator = document.createElement("div");
    indicator.className = "bg-green-100 text-green-800 text-sm px-4 py-2 rounded mb-4 text-center font-semibold border border-green-300";
    indicator.textContent = "✔ הדוח נטען מהזיכרון (לא נשלחה בקשה חדשה ל־GPT)";
    
    // הוספה בראש הדף (מתחת לכותרת הראשית למשל)
    const container = document.querySelector("main");
    if (container) container.insertBefore(indicator, container.firstChild);
  }
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

  // המלצות פעולה בשלבים
  if (data.recommendations && typeof data.recommendations === "object") {
    const rec = data.recommendations;
    el.recommendations.innerHTML = `
      <h3 class="font-bold text-lg mb-3">המלצות לפעולה לפי שלבים</h3>
      <div class="grid md:grid-cols-3 gap-4">
        ${renderRecColumn("לפני פתיחה", rec.before_opening)}
        ${renderRecColumn("במהלך ההקמה", rec.during_setup)}
        ${renderRecColumn("לאחר פתיחה", rec.after_opening)}
      </div>
    `;
  } else {
    el.recommendations.innerHTML = `<p>לא התקבלו המלצות מה-AI</p>`;
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

    renderCharts(grouped, rules);
    show(el.charts);

    el.allRulesList.innerHTML = rules.map(r => `
      <details class="py-3">
        <summary class="cursor-pointer font-semibold">${r.id || ""} – ${r.title || ""}</summary>
        <pre class="mt-2 bg-gray-50 p-3 rounded text-xs overflow-auto">${escapeHtml(JSON.stringify(r, null, 2))}</pre>
      </details>
    `).join("");
  } else {
    el.requirementsList.innerHTML = `<p>לא נמצאו חוקים</p>`;
    show(el.requirementsSection);
  }

  hide(el.loader);
  lucide.createIcons();
}

function renderRecColumn(title, items) {
  if (!Array.isArray(items) || items.length === 0) {
    return `<div class="p-4 bg-white border rounded shadow-sm">
      <h4 class="font-semibold mb-2">${title}</h4>
      <p class="text-gray-500 text-sm">—</p>
    </div>`;
  }
  return `<div class="p-4 bg-white border rounded shadow-sm">
    <h4 class="font-semibold mb-2">${title}</h4>
    <ul class="list-disc pr-5 space-y-1 text-sm">
      ${items.map(i => `<li>${i}</li>`).join("")}
    </ul>
  </div>`;
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
      </div>
    </details>
  `;
}

function renderCharts(grouped, rules) {
  const labels = Object.keys(grouped);
  const values = labels.map(l => grouped[l].length);

  const pieCtx = document.getElementById("rulesPie").getContext("2d");
  new Chart(pieCtx, {
    type: "pie",
    data: { labels, datasets: [{ data: values, backgroundColor: ["#2563eb","#16a34a","#f59e0b","#dc2626","#9333ea","#0d9488","#64748b"] }] },
    options: { plugins: { legend: { position: "bottom" } } }
  });

  const priorities = ["קריטי","גבוה","בינוני","נמוך","לא צויין"];
  const prCounts = { "קריטי":0,"גבוה":0,"בינוני":0,"נמוך":0,"לא צויין":0 };
  rules.forEach(r => { prCounts[r.priority || "לא צויין"] = (prCounts[r.priority || "לא צויין"] || 0) + 1; });

  const barCtx = document.getElementById("priorityBar").getContext("2d");
  new Chart(barCtx, {
    type: "bar",
    data: { labels: priorities, datasets: [{ label: "מספר חוקים", data: priorities.map(p => prCounts[p] || 0), backgroundColor: "#2563eb" }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
  });
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, m => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[m]));
}

// --- קריאה בהטענת הדף ---
window.addEventListener("DOMContentLoaded", () => {
  fetchReport();
});

// כפתור רענון
document.getElementById("regenerateBtn").addEventListener("click", () => {
  if (confirm("האם אתה בטוח שברצונך ליצור דוח חדש? פעולה זו תשלח בקשה ל-GPT ותמחק את הדוח השמור.")) {
    ReportStore.clear(); // מחיקת הדוח הישן לפני יצירת חדש
    fetchReport(true);
  }
});