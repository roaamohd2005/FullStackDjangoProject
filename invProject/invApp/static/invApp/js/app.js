async function loadChartData() {
    const canvas = document.getElementById("stockChart");
    if (!canvas) return;

    try {
        const response = await fetch("/api/stock-chart/");
        const data = await response.json();
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
    }
}

function bindProductEditModal() {
    const form = document.getElementById("productForm");
    if (!form) return;

    document.querySelectorAll(".edit-product-btn").forEach((button) => {
        button.addEventListener("click", () => {
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
    productModal.addEventListener("hidden.bs.modal", () => {
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
