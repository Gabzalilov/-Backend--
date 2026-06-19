const form = document.querySelector("#contact-form");
const result = document.querySelector("#form-result");
const comment = form.elements.comment;
const counter = document.querySelector("#comment-count");
const healthLabel = document.querySelector(".api-state b");

comment.addEventListener("input", () => {
  counter.textContent = comment.value.length;
});

fetch("/api/health")
  .then((response) => response.json())
  .then((data) => {
    healthLabel.textContent = data.status === "ok" ? "API работает" : "API частично доступен";
  })
  .catch(() => {
    healthLabel.textContent = "API недоступен";
  });

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  result.hidden = true;

  if (!form.reportValidity()) return;

  const button = form.querySelector("button[type='submit']");
  const originalText = button.querySelector("span").textContent;
  button.disabled = true;
  button.querySelector("span").textContent = "Отправляем...";

  const payload = Object.fromEntries(new FormData(form).entries());
  try {
    const response = await fetch("/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!response.ok) {
      const fieldErrors = (data.details || []).map((item) => item.message).join("; ");
      throw new Error(fieldErrors || data.message || "Не удалось отправить обращение");
    }

    result.className = "form-result success";
    result.innerHTML = `<strong>Готово!</strong> ${escapeHtml(data.ai.suggested_reply)}<br><small>Номер: ${escapeHtml(data.request_id)}</small>`;
    result.hidden = false;
    form.reset();
    counter.textContent = "0";
  } catch (error) {
    result.className = "form-result error";
    result.textContent = error.message;
    result.hidden = false;
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = originalText;
  }
});

function escapeHtml(value) {
  const node = document.createElement("div");
  node.textContent = value;
  return node.innerHTML;
}
