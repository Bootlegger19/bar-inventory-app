// Submits any <form data-pin-form> in the background and navigates on success.
// data-mode="assign"  -> normal navigation (adds a history entry)
// data-mode="replace" -> swaps the current page out of history
document.querySelectorAll("[data-pin-form]").forEach(function (form) {
  const errorBox = form.querySelector("[data-error]");

  function showError(message) {
    errorBox.textContent = message;
    errorBox.classList.remove("d-none");
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();  // stop the normal page-navigating form submit
    fetch(form.action, { method: "POST", body: new FormData(form) })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        if (!data.success) {
          showError(data.error);
          form.reset();
          form.querySelector("input").focus();
          return;
        }
        if (form.dataset.mode === "replace") {
          window.location.replace(data.redirect);
        } else {
          window.location.assign(data.redirect);
        }
      })
      .catch(function () {
        showError("Couldn't reach the server. Try again.");
      });
  });
});