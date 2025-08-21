document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("darkModeToggle");
  const isDark = localStorage.getItem("darkMode") === "true";

  if (isDark) {
    document.body.classList.add("dark-mode");
    if (toggle) toggle.checked = true;
  }

  if (toggle) {
    toggle.addEventListener("change", () => {
      document.body.classList.toggle("dark-mode");
      localStorage.setItem("darkMode", document.body.classList.contains("dark-mode"));
    });
  }
});


// Hide flash messages after 4 seconds
setTimeout(function () {
  // Find all elements with class "flash"
  var messages = document.querySelectorAll('.flash');

  // Loop through each message
  messages.forEach(function (msg) {
    msg.style.display = 'none'; // Simply hide it
  });
}, 4000);
