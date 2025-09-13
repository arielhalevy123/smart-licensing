// שולף את כל הנתונים שאוחסנו
const finalData = JSON.parse(localStorage.getItem("finalBusinessData")) || {};

// --- הדמיה של דוח AI (בפרויקט האמיתי זה מגיע מ-API של GPT/Claude) ---
const aiReport = {
  executive_summary: `על פי הנתונים שסיפקת, העסק מסוג "${finalData.business_type}" 
  בעיר "${finalData.city}" צפוי לעמוד בדרישות בסיסיות.`,
  recommendations: "מומלץ לבצע בדיקות בטיחות, ולהגיש מסמכים למשרד הבריאות.",
  estimated_timeline: "כ-30 יום",
  estimated_total_cost: "כ-5,000 ₪"
};

// שמור ל-localStorage אם תרצה
localStorage.setItem("aiReport", JSON.stringify(aiReport));

// --- הצגת סיכום ---
const aiSumEl = document.getElementById("aiSummary");
aiSumEl.innerHTML = `
  <h2 class="font-bold text-xl mb-2">תמצית מנהלים</h2>
  <p>${aiReport.executive_summary}</p>
  <h3 class="mt-4 font-semibold">המלצות:</h3>
  <p>${aiReport.recommendations}</p>
`;

// --- הצגת הערכות ---
const aiEstEl = document.getElementById("aiEstimates");
aiEstEl.innerHTML = `
  <div class="p-4 bg-white border rounded-lg shadow"><b>זמן:</b> ${aiReport.estimated_timeline}</div>
  <div class="p-4 bg-white border rounded-lg shadow"><b>עלות:</b> ${aiReport.estimated_total_cost}</div>
`;

// --- הצגת דרישות רגולטוריות (בשלב הזה אפשר לסנן מתוך JSONים אמיתיים) ---
const requirementsList = [
  { title: "היגיינה", description: "שמירה על ניקיון המטבח לפי תקן 1234" },
  { title: "בטיחות אש", description: "מערכת כיבוי אש תקינה ואישור מכבי אש" },
  { title: "בריאות", description: "בדיקות מים תקופתיות בהתאם להנחיות משרד הבריאות" }
];

const listEl = document.getElementById("requirementsList");
listEl.innerHTML = `
  <h2 class="font-bold text-xl mb-2">דרישות רגולטוריות</h2>
  <ul class="list-disc pr-6 space-y-1">
    ${requirementsList.map(r => `<li><b>${r.title}:</b> ${r.description}</li>`).join("")}
  </ul>
`;