// שליפת הדוח מה-localStorage
const report = JSON.parse(localStorage.getItem("aiReport")) || {};

// כותרת
document.getElementById("reportTitle").textContent = `דוח רישוי עבור: ${report.business_name || "-"}`;
document.getElementById("reportDate").textContent = `הופק בתאריך: ${new Date().toLocaleDateString("he-IL")}`;
document.getElementById("businessTypeTag").textContent = report.business_type || "-";

// חלקי AI
const aiSections = [
  { title: "המלצות מנהלים", content: report.executive_summary || "" },
  { title: "דרישות בעדיפות עליונה", content: (report.priority_requirements || []).join("<br>") },
  { title: "המלצות לצעדים הבאים", content: report.next_steps || "" }
];
document.getElementById("aiSections").innerHTML = aiSections.map(s => `
  <div>
    <h3 class="font-semibold text-purple-700 mb-1">${s.title}</h3>
    <p class="text-gray-700">${s.content || "לא נמצאו נתונים"}</p>
  </div>
`).join("");

// עלות ולו"ז
document.getElementById("estimatedCost").textContent = report.estimated_total_cost || "לא הוגדר";
document.getElementById("estimatedTimeline").textContent = report.estimated_timeline || "לא הוגדר";

// דרישות מפורטות (Accordion)
const requirementsList = document.getElementById("requirementsList");
(requirementsList.innerHTML = (report.matched_rules || []).map((r, i) => `
  <div class="border rounded-lg">
    <button class="w-full flex justify-between items-center p-4 font-semibold hover:bg-gray-50"
      onclick="toggleReq(${i})">
      <span>${r.title}</span>
      <span class="text-sm text-gray-500">עדיפות: ${r.priority || "רגיל"}</span>
    </button>
    <div id="req-${i}" class="hidden p-4 border-t space-y-2">
      ${(r.actions || []).map(a => `<p>• ${a}</p>`).join("")}
      ${r.cost ? `<p class="text-orange-600"><b>עלות משוערת:</b> ${r.cost}</p>` : ""}
      ${r.timeline ? `<p class="text-green-600"><b>זמן טיפול:</b> ${r.timeline}</p>` : ""}
    </div>
  </div>
`).join(""));

function toggleReq(i) {
  const el = document.getElementById(`req-${i}`);
  el.classList.toggle("hidden");
}