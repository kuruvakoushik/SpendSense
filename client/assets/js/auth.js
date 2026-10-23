document.addEventListener("DOMContentLoaded", async () => {
  await Api.ensureCsrf();
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");

  if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = loginForm.querySelector("button[type=submit]");
      const errorBox = document.getElementById("form-error");
      errorBox.hidden = true;
      App.setBusy(button, true, "Signing in…");
      try {
        Api.clearCsrf();
        await Api.ensureCsrf();
        await Api.post("/api/auth/login", {
          email: loginForm.email.value,
          password: loginForm.password.value,
        }, { authRedirect: false });
        window.location.href = "/dashboard";
      } catch (error) {
        errorBox.hidden = false;
        errorBox.textContent = error.message;
      } finally {
        App.setBusy(button, false);
      }
    });
  }

  if (registerForm) {
    registerForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = registerForm.querySelector("button[type=submit]");
      const errorBox = document.getElementById("form-error");
      errorBox.hidden = true;
      App.setBusy(button, true, "Creating account…");
      try {
        Api.clearCsrf();
        await Api.ensureCsrf();
        await Api.post("/api/auth/register", {
          full_name: registerForm.full_name.value,
          email: registerForm.email.value,
          password: registerForm.password.value,
          confirm_password: registerForm.confirm_password.value,
        }, { authRedirect: false });
        window.location.href = "/dashboard";
      } catch (error) {
        errorBox.hidden = false;
        errorBox.textContent = error.message;
      } finally {
        App.setBusy(button, false);
      }
    });
  }
});
