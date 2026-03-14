(function () {
  const root = document.getElementById("providersRoot");
  if (!root) return;

  const createUrl = root.dataset.createUrl;
  const updateBase = root.dataset.updateBase;
  const deleteBase = root.dataset.deleteBase;

  const createForm = document.getElementById("createProviderForm");
  const createBtn = document.getElementById("createProviderBtn");
  const tbody = document.getElementById("providersTableBody");

  const editModal = document.getElementById("editProviderModal");
  const editForm = document.getElementById("editProviderForm");
  const editProviderId = document.getElementById("editProviderId");
  const editFirstName = document.getElementById("editFirstName");
  const editLastName = document.getElementById("editLastName");
  const editContact = document.getElementById("editContact");
  const saveEditBtn = document.getElementById("saveEditProviderBtn");
  const closeEditModalBtn = document.getElementById("closeEditModalBtn");
  const cancelEditModalBtn = document.getElementById("cancelEditModalBtn");

  const deleteModal = document.getElementById("deleteProviderModal");
  const deleteProviderId = document.getElementById("deleteProviderId");
  const deleteProviderName = document.getElementById("deleteProviderName");
  const confirmDeleteBtn = document.getElementById("confirmDeleteProviderBtn");
  const cancelDeleteModalBtn = document.getElementById("cancelDeleteModalBtn");

  const PLACEHOLDER_ID = "0";

  function showToast(message, type = "info") {
    if (window.fsToast) {
      window.fsToast(message, type);
    }
  }

  function getCsrfToken() {
    const input = document.querySelector("input[name='csrfmiddlewaretoken']");
    return input ? input.value : "";
  }

  function buildUrl(base, id) {
    if (!base) return "#";
    return base.replace(`/${PLACEHOLDER_ID}/`, `/${id}/`);
  }

  function openModal(modal) {
    if (!modal) return;
    modal.classList.remove("hidden");
    modal.classList.add("flex");
    document.body.classList.add("overflow-hidden");
  }

  function closeModal(modal) {
    if (!modal) return;
    modal.classList.add("hidden");
    modal.classList.remove("flex");
    document.body.classList.remove("overflow-hidden");
  }

  function clearCreateErrors() {
    ["FirstName", "LastName", "Contact"].forEach((field) => {
      const el = document.getElementById(`createError${field}`);
      if (el) {
        el.textContent = "";
        el.classList.add("hidden");
      }
    });
  }

  function clearEditErrors() {
    ["FirstName", "LastName", "Contact"].forEach((field) => {
      const el = document.getElementById(`editError${field}`);
      if (el) {
        el.textContent = "";
        el.classList.add("hidden");
      }
    });
  }

  function renderFieldErrors(prefix, errors = {}) {
    const map = {
      first_name: `${prefix}ErrorFirstName`,
      last_name: `${prefix}ErrorLastName`,
      contact: `${prefix}ErrorContact`,
    };

    Object.entries(map).forEach(([key, id]) => {
      const el = document.getElementById(id);
      if (!el) return;

      const msgs = errors[key];
      if (msgs && msgs.length) {
        el.textContent = msgs.join(" ");
        el.classList.remove("hidden");
      } else {
        el.textContent = "";
        el.classList.add("hidden");
      }
    });
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function createProviderRow(provider) {
    const tr = document.createElement("tr");
    tr.className = "border-t";
    tr.dataset.id = provider.id;
    tr.dataset.firstName = provider.first_name;
    tr.dataset.lastName = provider.last_name;
    tr.dataset.contact = provider.contact;

    tr.innerHTML = `
      <td class="p-3 text-gray-800 provider-name-cell">
        ${escapeHtml(provider.first_name)} ${escapeHtml(provider.last_name)}
      </td>
      <td class="p-3 text-gray-700 provider-contact-cell">
        ${escapeHtml(provider.contact)}
      </td>
      <td class="p-3 text-gray-500 provider-created-cell">
        ${escapeHtml(provider.created_at)}
      </td>
      <td class="p-3">
        <div class="flex items-center gap-2">
          <button
            type="button"
            class="edit-provider-btn inline-flex items-center justify-center px-3 py-1.5 rounded-lg
                   text-xs font-semibold border border-[#d8c7b5] text-[#6b4b2a] bg-[#fbf7f2]
                   hover:bg-[#f3ebe2] transition"
          >
            Editar
          </button>

          <button
            type="button"
            class="delete-provider-btn inline-flex items-center justify-center px-3 py-1.5 rounded-lg
                   text-xs font-semibold border border-red-200 text-red-700 bg-red-50
                   hover:bg-red-100 transition"
          >
            Borrar
          </button>
        </div>
      </td>
    `;

    return tr;
  }

  function removeEmptyRow() {
    const emptyRow = document.getElementById("providersEmptyRow");
    if (emptyRow) emptyRow.remove();
  }

  function ensureEmptyRow() {
    if (!tbody) return;
    if (tbody.querySelector("tr[data-id]")) return;
    if (document.getElementById("providersEmptyRow")) return;

    const tr = document.createElement("tr");
    tr.id = "providersEmptyRow";
    tr.innerHTML = `
      <td class="p-4 text-gray-500" colspan="4">
        Aún no hay proveedores. Crea el primero arriba.
      </td>
    `;
    tbody.appendChild(tr);
  }

  async function fetchJson(url, options = {}) {
    const res = await fetch(url, {
      credentials: "include",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
        ...(options.headers || {}),
      },
      ...options,
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok || data.ok === false) {
      throw data;
    }

    return data;
  }

  function openEditFromRow(row) {
    if (!row) return;

    clearEditErrors();

    const id = row.dataset.id || "";
    const firstName = row.dataset.firstName || "";
    const lastName = row.dataset.lastName || "";
    const contact = row.dataset.contact || "";

    editProviderId.value = id;

    editFirstName.value = firstName;
    editLastName.value = lastName;
    editContact.value = contact;

    editFirstName.placeholder = firstName || "Nombre(s)";
    editLastName.placeholder = lastName || "Apellidos";
    editContact.placeholder = contact || "Teléfono 10 dígitos o correo";

    openModal(editModal);
  }

  function openDeleteFromRow(row) {
    if (!row) return;

    const id = row.dataset.id || "";
    const firstName = row.dataset.firstName || "";
    const lastName = row.dataset.lastName || "";

    deleteProviderId.value = id;
    deleteProviderName.textContent = `${firstName} ${lastName}`.trim() || "este proveedor";

    openModal(deleteModal);
  }

  async function handleCreateProvider(e) {
    e.preventDefault();
    clearCreateErrors();

    const firstNameInput = createForm.querySelector("[name='first_name']");
    const lastNameInput = createForm.querySelector("[name='last_name']");
    const contactInput = createForm.querySelector("[name='contact']");

    const payload = {
      first_name: firstNameInput?.value?.trim() || "",
      last_name: lastNameInput?.value?.trim() || "",
      contact: contactInput?.value?.trim() || "",
    };

    createBtn.disabled = true;
    createBtn.classList.add("opacity-60", "pointer-events-none");

    try {
      const data = await fetchJson(createUrl, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      removeEmptyRow();

      const row = createProviderRow(data.provider);
      tbody.prepend(row);

      createForm.reset();
      showToast(data.message || "Proveedor creado correctamente.", "success");
    } catch (err) {
      console.error(err);

      if (err.errors) {
        renderFieldErrors("create", err.errors);
        showToast(err.message || "Corrige los campos del formulario.", "warning");
      } else {
        showToast(err.message || "No se pudo crear el proveedor.", "error");
      }
    } finally {
      createBtn.disabled = false;
      createBtn.classList.remove("opacity-60", "pointer-events-none");
    }
  }

  async function handleEditProvider(e) {
    e.preventDefault();
    clearEditErrors();

    const id = editProviderId.value;
    if (!id) {
      showToast("Proveedor inválido.", "error");
      return;
    }

    const payload = {
      first_name: editFirstName.value.trim(),
      last_name: editLastName.value.trim(),
      contact: editContact.value.trim(),
    };

    saveEditBtn.disabled = true;
    saveEditBtn.classList.add("opacity-60", "pointer-events-none");

    try {
      const data = await fetchJson(buildUrl(updateBase, id), {
        method: "POST",
        body: JSON.stringify(payload),
      });

      const row = tbody.querySelector(`tr[data-id="${id}"]`);
      if (row) {
        row.dataset.firstName = data.provider.first_name;
        row.dataset.lastName = data.provider.last_name;
        row.dataset.contact = data.provider.contact;

        const nameCell = row.querySelector(".provider-name-cell");
        const contactCell = row.querySelector(".provider-contact-cell");

        if (nameCell) {
          nameCell.textContent = `${data.provider.first_name} ${data.provider.last_name}`;
        }

        if (contactCell) {
          contactCell.textContent = data.provider.contact;
        }
      }

      closeModal(editModal);
      showToast(data.message || "Proveedor actualizado correctamente.", "success");
    } catch (err) {
      console.error(err);

      if (err.errors) {
        renderFieldErrors("edit", err.errors);
        showToast(err.message || "Corrige los campos del proveedor.", "warning");
      } else {
        showToast(err.message || "No se pudo actualizar el proveedor.", "error");
      }
    } finally {
      saveEditBtn.disabled = false;
      saveEditBtn.classList.remove("opacity-60", "pointer-events-none");
    }
  }

  async function handleDeleteProvider() {
    const id = deleteProviderId.value;
    if (!id) {
      showToast("Proveedor inválido.", "error");
      return;
    }

    confirmDeleteBtn.disabled = true;
    confirmDeleteBtn.classList.add("opacity-60", "pointer-events-none");

    try {
      const data = await fetchJson(buildUrl(deleteBase, id), {
        method: "POST",
        body: JSON.stringify({}),
      });

      const row = tbody.querySelector(`tr[data-id="${id}"]`);
      if (row) row.remove();

      ensureEmptyRow();
      closeModal(deleteModal);
      showToast(data.message || "Proveedor eliminado correctamente.", "success");
    } catch (err) {
      console.error(err);
      showToast(err.message || "No se pudo borrar el proveedor.", "error");
    } finally {
      confirmDeleteBtn.disabled = false;
      confirmDeleteBtn.classList.remove("opacity-60", "pointer-events-none");
    }
  }

  function bindRowActions() {
    tbody?.addEventListener("click", (e) => {
      const editBtn = e.target.closest(".edit-provider-btn");
      const deleteBtn = e.target.closest(".delete-provider-btn");
      const row = e.target.closest("tr[data-id]");

      if (editBtn && row) {
        openEditFromRow(row);
        return;
      }

      if (deleteBtn && row) {
        openDeleteFromRow(row);
      }
    });
  }

  function bindModalClose() {
    closeEditModalBtn?.addEventListener("click", () => closeModal(editModal));
    cancelEditModalBtn?.addEventListener("click", () => closeModal(editModal));
    cancelDeleteModalBtn?.addEventListener("click", () => closeModal(deleteModal));

    editModal?.addEventListener("click", (e) => {
      if (e.target === editModal) closeModal(editModal);
    });

    deleteModal?.addEventListener("click", (e) => {
      if (e.target === deleteModal) closeModal(deleteModal);
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeModal(editModal);
        closeModal(deleteModal);
      }
    });
  }

  createForm?.addEventListener("submit", handleCreateProvider);
  editForm?.addEventListener("submit", handleEditProvider);
  confirmDeleteBtn?.addEventListener("click", handleDeleteProvider);

  bindRowActions();
  bindModalClose();
})();
