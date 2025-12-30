document.addEventListener("DOMContentLoaded", () => {
  // Initialize Icons
  if (window.lucide) window.lucide.createIcons();

  // RAG Frontend Logic
  const el = {
    questionInput: document.getElementById("questionInput"),
    askBtn: document.getElementById("askBtn"),
    loader: document.getElementById("loader"),
    resultArea: document.getElementById("resultArea"),
    answerText: document.getElementById("answerText"),
    sourcesList: document.getElementById("sourcesList"),
    errorBox: document.getElementById("errorBox"),
    errorText: document.getElementById("errorText"),
    presetQuestionsContainer: document.getElementById("presetQuestions")
  };

  // Preset Questions Data
  const presetQuestions = [
    "אילו דרישות בטיחות אש חלות על העסק לפי התקנות?",
    "האם העסק חייב במערכת גילוי אש ועשן? באילו תנאים?",
    "אילו תקנים ישראליים חלים על מערכות המתזים בעסק?",
    "אילו בדיקות תקופתיות נדרשות למערכות כיבוי האש?",
    "האם חובה לספק מים חמים וקרים?",
    "אילו תקנות חלות על איכות מי השתייה בעסק?",
    "מה האחריות של בעל העסק לגבי תחזוקת מערכות המים?",
    "באיזו טמפרטורה יש לאחסן מזון בקירור ובהקפאה?",
    "כיצד יש להגן על המחסן מפני מזיקים ובעלי חיים?",
    "איזה תקנים ישראליים חלים על העסק ומה תפקידם?"
  ];

  // Render Preset Questions
  if (el.presetQuestionsContainer) {
    presetQuestions.forEach(q => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "px-3 py-1.5 bg-blue-50 text-blue-700 text-sm font-medium rounded-full border border-blue-100 hover:bg-blue-100 hover:border-blue-200 transition-colors text-right";
      chip.textContent = q;
      chip.addEventListener("click", () => {
        el.questionInput.value = q;
        el.questionInput.focus();
        // Optional: Auto-scroll to input smoothly
        el.questionInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
      el.presetQuestionsContainer.appendChild(chip);
    });
  }

  function show(element) {
    if (element) element.classList.remove("hidden");
  }

  function hide(element) {
    if (element) element.classList.add("hidden");
  }

  async function handleQuestion() {
    const question = el.questionInput.value.trim();
    
    if (!question) {
      alert("אנא הזן שאלה.");
      return;
    }

    // Reset UI
    hide(el.resultArea);
    hide(el.errorBox);
    show(el.loader);
    el.askBtn.disabled = true;

    try {
      const response = await fetch("/api/rag", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question }),
      });

      let data;
      try {
        data = await response.json();
      } catch (jsonError) {
        // If response is not valid JSON, read as text
        const text = await response.text();
        throw new Error(`שגיאה בשרת: ${text || "תגובה לא תקינה"}`);
      }

      if (!response.ok) {
        throw new Error(data.error || `שגיאה ${response.status}: ${response.statusText}`);
      }

      // Render Answer
      el.answerText.textContent = data.answer;

      // Render Sources
      el.sourcesList.innerHTML = "";
      if (data.sources && data.sources.length > 0) {
        data.sources.forEach((source) => {
          const sourceCard = document.createElement("div");
          sourceCard.className = "bg-white p-4 rounded-lg shadow-sm border text-sm text-gray-600";
          sourceCard.innerHTML = `
            <div class="font-bold mb-1 text-blue-600">קטע #${source.id}</div>
            <p class="leading-relaxed text-gray-700">${source.preview}</p>
          `;
          el.sourcesList.appendChild(sourceCard);
        });
      } else {
        el.sourcesList.innerHTML = "<p class='text-gray-500'>לא נמצאו מקורות רלוונטיים.</p>";
      }

      show(el.resultArea);

    } catch (error) {
      console.error(error);
      el.errorText.textContent = error.message;
      show(el.errorBox);
    } finally {
      hide(el.loader);
      el.askBtn.disabled = false;
    }
  }

  // Event Listeners
  if (el.askBtn) {
    el.askBtn.addEventListener("click", handleQuestion);
  }

  // Allow Ctrl+Enter to submit
  if (el.questionInput) {
    el.questionInput.addEventListener("keydown", (e) => {
      if (e.ctrlKey && e.key === "Enter") {
        handleQuestion();
      }
    });
  }

});
