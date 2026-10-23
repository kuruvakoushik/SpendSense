const Api = (() => {
  let csrfToken = "";

  async function ensureCsrf() {
    if (csrfToken) return csrfToken;
    const response = await fetch("/api/auth/csrf", { credentials: "same-origin" });
    const body = await response.json();
    csrfToken = body?.data?.csrf_token || "";
    return csrfToken;
  }

  function clearCsrf() {
    csrfToken = "";
  }

  async function request(path, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const headers = Object.assign({ Accept: "application/json" }, options.headers || {});
    if (options.body && !(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    if (method !== "GET" && method !== "HEAD") {
      headers["X-CSRFToken"] = await ensureCsrf();
    }
    let response;
    try {
      response = await fetch(path, {
        method,
        credentials: "same-origin",
        headers,
        body: options.body && !(options.body instanceof FormData)
          ? JSON.stringify(options.body)
          : options.body || undefined,
      });
    } catch (error) {
      throw new Error("Network error. Check your connection and try again.");
    }

    let body = null;
    try {
      body = await response.json();
    } catch (_error) {
      body = null;
    }

    if (body?.data?.csrf_token) {
      csrfToken = body.data.csrf_token;
    }

    if (response.status === 401 && options.authRedirect !== false) {
      if (!window.location.pathname.includes("login") && window.location.pathname !== "/") {
        window.location.href = "/login";
      }
    }

    if (!response.ok || (body && body.success === false)) {
      const message = body?.error?.message || "The request could not be completed.";
      const error = new Error(message);
      error.status = response.status;
      error.code = body?.error?.code;
      throw error;
    }
    return body?.data;
  }

  return {
    request,
    ensureCsrf,
    clearCsrf,
    get: (path, options) => request(path, options),
    post: (path, body, options) => request(path, Object.assign({ method: "POST", body }, options)),
    put: (path, body) => request(path, { method: "PUT", body }),
    patch: (path, body) => request(path, { method: "PATCH", body }),
    del: (path) => request(path, { method: "DELETE" }),
  };
})();
