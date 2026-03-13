(() => {
  const shownIds = new Set();
  const POLL_MS = 15000;

  async function fetchActiveAlerts() {
    try {
      const res = await fetch("/dashboard/api/alerts/active/?only_unseen=1&limit=10", {
        method: "GET",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
        credentials: "same-origin",
      });

      if (!res.ok) return;

      const data = await res.json();
      if (!data?.ok || !Array.isArray(data.results)) return;

      for (const alert of data.results) {
        if (shownIds.has(alert.id)) continue;
        shownIds.add(alert.id);

        const type =
          alert.severity === "critical" || alert.severity === "error"
            ? "error"
            : alert.severity === "warning"
            ? "warning"
            : "info";

        const text = `${alert.title}: ${alert.message}`;

        if (typeof window.fsToast === "function") {
          window.fsToast(text, type);
        }

        markSeen(alert.id);
      }
    } catch (err) {
      console.error("Error cargando alertas:", err);
    }
  }

  async function markSeen(alertId) {
    try {
      await fetch(`/dashboard/api/alerts/${alertId}/seen/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCSRFToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        credentials: "same-origin",
      });
    } catch (err) {
      console.error("Error marcando alerta como vista:", err);
    }
  }

  function getCSRFToken() {
    const cookie = document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="));
    return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
  }

  document.addEventListener("DOMContentLoaded", () => {
    fetchActiveAlerts();
    setInterval(fetchActiveAlerts, POLL_MS);
  });
})();
