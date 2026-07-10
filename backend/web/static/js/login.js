(async function () {
  const session = await DSA.session();
  if (session.user) {
    window.location.href = "/";
    return;
  }

  const form = document.getElementById("login-form");
  const errorEl = document.getElementById("login-error");

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorEl.hidden = true;
    try {
      await DSA.login(
        document.getElementById("username").value.trim(),
        document.getElementById("password").value
      );
      window.location.href = "/";
    } catch (err) {
      errorEl.textContent = err.message || "Sign in failed";
      errorEl.hidden = false;
    }
  });
})();
