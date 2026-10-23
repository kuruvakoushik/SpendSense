document.addEventListener("DOMContentLoaded", async () => {
  const user = await App.requireUser();
  if (!user) return;
  App.bindLayout(user);
  const profile = await Api.get("/api/profile");
  const form = document.getElementById("profile-form");
  form.full_name.value = profile.full_name;
  form.email.value = profile.email;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    App.setBusy(button, true, "Saving…");
    try {
      const updated = await Api.put("/api/profile", { full_name: form.full_name.value });
      App.qsa("[data-user-name]").forEach((el) => {
        el.textContent = updated.full_name;
      });
      App.toast("Profile updated.", "success");
    } catch (error) {
      App.toast(error.message, "error");
    } finally {
      App.setBusy(button, false);
    }
  });
  document.getElementById("password-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const pwForm = event.target;
    const button = pwForm.querySelector("button[type=submit]");
    App.setBusy(button, true, "Updating…");
    try {
      await Api.post("/api/auth/change-password", {
        current_password: pwForm.current_password.value,
        new_password: pwForm.new_password.value,
        confirm_password: pwForm.confirm_password.value,
      });
      pwForm.reset();
      App.toast("Password updated.", "success");
    } catch (error) {
      App.toast(error.message, "error");
    } finally {
      App.setBusy(button, false);
    }
  });
});
