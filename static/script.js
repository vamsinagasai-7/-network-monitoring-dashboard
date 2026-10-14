
"use strict";

let currentFilter = "all";
let previouslyFocusedElement = null;

document.addEventListener("DOMContentLoaded", function () {
    const scanButton = document.getElementById("refreshButton");
    const searchInput = document.getElementById("deviceSearch");
    const modal = document.getElementById("deviceModal");
    const closeButton = document.getElementById("modalClose");

    // SCAN NETWORK
    if (scanButton) {
        scanButton.addEventListener("click", function () {
            if (scanButton.disabled) return;

            scanButton.disabled = true;

            const scanText = document.getElementById("scanText");
            const message = document.getElementById("message");

            if (scanText) {
                scanText.textContent = "Scanning...";
            }

            if (message) {
                message.textContent =
                    "Scanning your LAN. Please wait...";
            }

            // Reload the page and run the Flask scan again.
            window.location.href = "/?scan=" + Date.now();
        });
    }

    // SEARCH
    if (searchInput) {
        searchInput.addEventListener("input", applyFilters);
    }

    // FILTER BUTTONS
    document.querySelectorAll(".filter").forEach(function (button) {
        button.addEventListener("click", function () {
            currentFilter = button.dataset.filter || "all";

            document.querySelectorAll(".filter").forEach(function (item) {
                item.classList.toggle("active", item === button);
            });

            applyFilters();
        });
    });

    // DEVICE ROWS
    document.querySelectorAll(".device-row").forEach(function (row) {
        row.addEventListener("click", function () {
            showDeviceDetails(row);
        });

        row.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                showDeviceDetails(row);
            }
        });
    });

    // CLOSE POPUP
    if (closeButton) {
        closeButton.addEventListener("click", closeDeviceDetails);
    }

    if (modal) {
        modal.addEventListener("click", function (event) {
            if (event.target === modal) {
                closeDeviceDetails();
            }
        });
    }

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeDeviceDetails();
        }
    });

    applyFilters();
});


/* SEARCH AND FILTER */

function applyFilters() {
    const input = document.getElementById("deviceSearch");

    const query = input
        ? input.value.toLowerCase().trim()
        : "";

    const rows = document.querySelectorAll(".device-row");
    const noResults = document.getElementById("noResults");
    const visibleCount = document.getElementById("visibleCount");

    let visible = 0;

    rows.forEach(function (row) {
        const text = (
            row.dataset.search ||
            [
                row.dataset.name,
                row.dataset.ip,
                row.dataset.mac,
                row.dataset.vendor
            ].join(" ")
        ).toLowerCase();

        const status = row.dataset.status || "";

        const matchesSearch = text.includes(query);

        const matchesFilter =
            currentFilter === "all" ||
            (currentFilter === "online" && status === "Online") ||
            (currentFilter === "no-reply" && status !== "Online");

        const show = matchesSearch && matchesFilter;

        row.hidden = !show;

        if (show) {
            visible++;
        }
    });

    if (visibleCount) {
        visibleCount.textContent =
            "Showing " + visible + " of " + rows.length + " devices";
    }

    if (noResults) {
        noResults.hidden = visible !== 0;
    }
}


/* DEVICE DETAILS POPUP */

function showDeviceDetails(row) {
    const modal = document.getElementById("deviceModal");

    if (!modal) return;

    previouslyFocusedElement = row;

    const name = row.dataset.name || "Unknown";
    const ip = row.dataset.ip || "Unknown";
    const mac = row.dataset.mac || "Unknown";
    const vendor = row.dataset.vendor || "Unknown";
    const status = row.dataset.status || "Unknown";
    const latency = row.dataset.latency || "N/A";

    document.getElementById("modalName").textContent = name;
    document.getElementById("modalHostname").textContent = name;
    document.getElementById("modalIP").textContent = ip;
    document.getElementById("modalMAC").textContent = mac;
    document.getElementById("modalVendor").textContent = vendor;

    document.getElementById("modalLatency").textContent =
        status === "Online" ? latency : "N/A";

    const badge = document.getElementById("modalStatus");

    badge.className = "status";

    if (status === "Online") {
        badge.classList.add("online");
    } else if (status === "ARP Detected") {
        badge.classList.add("arp");
    } else {
        badge.classList.add("offline");
    }

    badge.textContent = status;

    document.getElementById("modalMethod").textContent =
        status === "Online"
            ? "ARP + ping"
            : "ARP detected; no ping reply";

    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");

    document.body.style.overflow = "hidden";

    document.getElementById("modalClose").focus();
}


/* CLOSE POPUP */

function closeDeviceDetails() {
    const modal = document.getElementById("deviceModal");

    if (!modal) return;

    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");

    document.body.style.overflow = "";

    if (previouslyFocusedElement) {
        previouslyFocusedElement.focus();
        previouslyFocusedElement = null;
    }
}
