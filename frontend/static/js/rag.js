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
};

function show(element) {
  element.classList.remove("hidden");
}

function hide(element) {
  element.classList.add("hidden");
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

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "שגיאה בתקשורת עם השרת");
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
el.askBtn.addEventListener("click", handleQuestion);

// Allow Ctrl+Enter to submit
el.questionInput.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key === "Enter") {
    handleQuestion();
  }
});
