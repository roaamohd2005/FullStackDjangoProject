async function loadChartData() {
  const canvas = document.getElementById("stockChart");
  const loadingState = document.getElementById("chartLoadingState");
  const emptyState = document.getElementById("chartEmptyState");
  const errorState = document.getElementById("chartErrorState");
  if (!canvas) return;

  const hideState = (node) => node && node.classList.add("d-none");
  const showState = (node) => node && node.classList.remove("d-none");

  try {
    const response = await fetch("/api/stock-chart/");
    if (!response.ok) {
      throw new Error(`Chart request failed: ${response.status}`);
    }
    const data = await response.json();
    hideState(loadingState);

    if (!data.labels || data.labels.length === 0) {
      canvas.classList.add("d-none");
      showState(emptyState);
      hideState(errorState);
      return;
    }

    canvas.classList.remove("d-none");
    hideState(emptyState);
    hideState(errorState);
    const ctx = canvas.getContext("2d");
    new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels || [],
        datasets: [
          {
            label: "Stock Quantity",
            data: data.quantities || [],
            borderRadius: 6,
            backgroundColor: "rgba(13, 110, 253, 0.7)",
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
        },
      },
    });
  } catch (error) {
    console.error("Could not load stock chart data", error);
    hideState(loadingState);
    canvas.classList.add("d-none");
    hideState(emptyState);
    showState(errorState);
  }
}

function bindProductEditModal() {
  const form = document.getElementById("productForm");
  const state = document.getElementById("dashboardState");
  const modalState = state?.dataset.modalState || "";
  const editingProductId = state?.dataset.editingProductId || "";
  if (!form) return;

  let shouldResetProductForm = true;

  document.querySelectorAll(".edit-product-btn").forEach((button) => {
    button.addEventListener("click", () => {
      shouldResetProductForm = true;
      const id = button.dataset.id;
      const name = button.dataset.name;
      const category = button.dataset.category;
      const sku = button.dataset.sku;
      const price = button.dataset.price;
      const quantity = button.dataset.quantity;
      const supplier = button.dataset.supplier;

      document.getElementById("productModalTitle").innerText = "Edit Product";
      form.action = `/products/${id}/edit/`;
      form.querySelector("#id_name").value = name;
      form.querySelector("#id_category").value = category;
      form.querySelector("#id_sku").value = sku;
      form.querySelector("#id_price").value = price;
      form.querySelector("#id_quantity").value = quantity;
      form.querySelector("#id_supplier").value = supplier;
    });
  });

  const productModal = document.getElementById("productModal");
  const categoryModal = document.getElementById("categoryModal");

  if (modalState === "product_create" || modalState === "product_edit") {
    shouldResetProductForm = false;
    if (modalState === "product_edit" && editingProductId) {
      form.action = `/products/${editingProductId}/edit/`;
      document.getElementById("productModalTitle").innerText = "Edit Product";
    }
    const bootstrapProductModal =
      bootstrap.Modal.getOrCreateInstance(productModal);
    bootstrapProductModal.show();
  }

  if (modalState === "category" && categoryModal) {
    const bootstrapCategoryModal =
      bootstrap.Modal.getOrCreateInstance(categoryModal);
    bootstrapCategoryModal.show();
  }

  productModal.addEventListener("hidden.bs.modal", () => {
    if (!shouldResetProductForm) {
      shouldResetProductForm = true;
      return;
    }

    document.getElementById("productModalTitle").innerText = "Add Product";
    form.action = "/products/add/";
    form.reset();
  });
}

function showToasts() {
  document.querySelectorAll(".toast").forEach((toastNode) => {
    const toast = new bootstrap.Toast(toastNode);
    toast.show();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  loadChartData();
  bindProductEditModal();
  showToasts();
});
