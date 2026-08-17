/* ==========================================================================
   AgriVision AI - Farm Journey Engine Script
   Synchronized Filter Controls & Interactive Analytics
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
  // State Management
  let historyData = [];
  let filteredData = [];
  let currentSort = { column: "date", asc: false };
  let currentPage = 1;
  let pageSize = 10;

  // DOM Elements - Main Control Panel
  const fromDateInput = document.getElementById("fromDate");
  const toDateInput = document.getElementById("toDate");
  const rackSelect = document.getElementById("rackSelect");
  const paramSelect = document.getElementById("paramSelect");
  const applyFiltersBtn = document.getElementById("applyFiltersBtn");
  const resetFiltersBtn = document.getElementById("resetFiltersBtn");
  const pillBtns = document.querySelectorAll(".controls-card .pill-btn");

  // DOM Elements - Log Records Filter Panel
  const logFromDateInput = document.getElementById("logFromDate");
  const logToDateInput = document.getElementById("logToDate");
  const logRackSelect = document.getElementById("logRackSelect");
  const logParamSelect = document.getElementById("logParamSelect");
  const logApplyFiltersBtn = document.getElementById("logApplyFiltersBtn");
  const logResetFiltersBtn = document.getElementById("logResetFiltersBtn");
  const logPillBtns = document.querySelectorAll("#logFilterPills .pill-btn");

  const recordCountBadge = document.getElementById("recordCountBadge");
  const resetZoomBtn = document.getElementById("resetZoomBtn");

  // Summary Chips
  const avgTempVal = document.getElementById("avgTempVal");
  const avgHumVal = document.getElementById("avgHumVal");
  const avgSoilVal = document.getElementById("avgSoilVal");
  const avgAirVal = document.getElementById("avgAirVal");
  const avgWaterVal = document.getElementById("avgWaterVal");

  const tableBody = document.getElementById("historyTableBody");
  const tableSearchInput = document.getElementById("tableSearchInput");
  const pageSizeSelect = document.getElementById("pageSizeSelect");
  const prevPageBtn = document.getElementById("prevPageBtn");
  const nextPageBtn = document.getElementById("nextPageBtn");
  const pageNumbers = document.getElementById("pageNumbers");
  const paginationInfo = document.getElementById("paginationInfo");

  const exportCsvBtn = document.getElementById("exportCsvBtn");
  const exportPdfBtn = document.getElementById("exportPdfBtn");

  // Chart setup
  const ctx = document.getElementById("journeyChart").getContext("2d");

  // Helper to convert Air Quality PPM to Percentage (%)
  function formatAirQualityPercent(rawAir) {
    if (rawAir === null || rawAir === undefined) return 0;
    const val = parseFloat(rawAir);
    if (isNaN(val)) return 0;
    if (val > 100) {
      return Math.min(100, Math.max(0, Math.round((val / 1000.0) * 100)));
    }
    return Math.min(100, Math.max(0, Math.round(val)));
  }

  let journeyChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: []
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 900,
        easing: "easeOutQuart"
      },
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            color: "#f8fbff",
            font: { family: "Outfit", size: 13, weight: "500" },
            usePointStyle: true,
            padding: 22
          }
        },
        tooltip: {
          backgroundColor: "rgba(15, 23, 42, 0.92)",
          titleColor: "#34d399",
          bodyColor: "#f8fbff",
          borderColor: "rgba(255, 255, 255, 0.15)",
          borderWidth: 1,
          padding: 14,
          cornerRadius: 12,
          boxPadding: 6,
          usePointStyle: true
        },
        zoom: {
          pan: { enabled: true, mode: "x" },
          zoom: {
            wheel: { enabled: true },
            pinch: { enabled: true },
            mode: "x"
          }
        }
      },
      scales: {
        x: {
          ticks: { color: "#94a3b8", font: { family: "Outfit", size: 12 } },
          grid: { color: "rgba(255, 255, 255, 0.03)", drawBorder: false }
        },
        y: {
          ticks: { color: "#94a3b8", font: { family: "Outfit", size: 12 } },
          grid: { color: "rgba(255, 255, 255, 0.04)", drawBorder: false }
        }
      }
    }
  });

  // Sync Input Helpers
  function syncInputs(source) {
    if (source === "main") {
      logFromDateInput.value = fromDateInput.value;
      logToDateInput.value = toDateInput.value;
      logRackSelect.value = rackSelect.value;
      logParamSelect.value = paramSelect.value;
    } else {
      fromDateInput.value = logFromDateInput.value;
      toDateInput.value = logToDateInput.value;
      rackSelect.value = logRackSelect.value;
      paramSelect.value = logParamSelect.value;
    }
  }

  // Initialize Dates
  initDates("today");

  // Load Data
  fetchHistoryData();

  // ==========================================
  // EVENT LISTENERS - SYNCHRONIZED FILTERS
  // ==========================================

  // Main Pills
  pillBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const filterType = btn.getAttribute("data-filter");
      setActivePill(filterType);
      initDates(filterType);
      fetchHistoryData();
    });
  });

  // Log Pills
  logPillBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const filterType = btn.getAttribute("data-filter");
      setActivePill(filterType);
      initDates(filterType);
      fetchHistoryData();
    });
  });

  function setActivePill(filterType) {
    pillBtns.forEach((b) => b.classList.toggle("active", b.getAttribute("data-filter") === filterType));
    logPillBtns.forEach((b) => b.classList.toggle("active", b.getAttribute("data-filter") === filterType));
  }

  applyFiltersBtn.addEventListener("click", () => {
    syncInputs("main");
    fetchHistoryData();
  });

  logApplyFiltersBtn.addEventListener("click", () => {
    syncInputs("log");
    fetchHistoryData();
  });

  resetFiltersBtn.addEventListener("click", resetAllFilters);
  logResetFiltersBtn.addEventListener("click", resetAllFilters);

  function resetAllFilters() {
    setActivePill("today");
    initDates("today");
    rackSelect.value = "all";
    paramSelect.value = "all";
    logRackSelect.value = "all";
    logParamSelect.value = "all";
    tableSearchInput.value = "";
    fetchHistoryData();
  }

  resetZoomBtn.addEventListener("click", () => {
    if (journeyChart) journeyChart.resetZoom();
  });

  // ==========================================
  // API FETCH & DATA PROCESSING
  // ==========================================
  function initDates(filterType) {
    const now = new Date();
    let from = new Date();

    if (filterType === "today") {
      from.setHours(0, 0, 0, 0);
    } else if (filterType === "yesterday") {
      from.setDate(now.getDate() - 1);
      from.setHours(0, 0, 0, 0);
      now.setDate(now.getDate() - 1);
      now.setHours(23, 59, 59, 999);
    } else if (filterType === "7days") {
      from.setDate(now.getDate() - 7);
    } else if (filterType === "30days") {
      from.setDate(now.getDate() - 30);
    }

    const fromVal = formatDateTimeLocal(from);
    const toVal = formatDateTimeLocal(now);

    fromDateInput.value = fromVal;
    toDateInput.value = toVal;
    logFromDateInput.value = fromVal;
    logToDateInput.value = toVal;
  }

  function formatDateTimeLocal(dateObj) {
    const pad = (n) => (n < 10 ? "0" + n : n);
    return `${dateObj.getFullYear()}-${pad(dateObj.getMonth() + 1)}-${pad(dateObj.getDate())}T${pad(dateObj.getHours())}:${pad(dateObj.getMinutes())}`;
  }

  async function fetchHistoryData() {
    const fromRaw = fromDateInput.value;
    const toRaw = toDateInput.value;
    const rack = rackSelect.value;
    const param = paramSelect.value;

    // Convert datetime-local format "2026-07-31T12:00" to "2026-07-31 12:00:00"
    // because MongoDB timestamps are stored as "YYYY-MM-DD HH:MM:SS"
    function toMongoTimestamp(dtLocal) {
      if (!dtLocal) return "";
      return dtLocal.replace("T", " ") + (dtLocal.length === 16 ? ":00" : "");
    }

    const fromStr = toMongoTimestamp(fromRaw);
    const toStr = toMongoTimestamp(toRaw);

    try {
      const apiBase = (typeof window.API_BASE_URL === "string" ? window.API_BASE_URL : "").replace(/\/+$/, "");
      const url = `${apiBase}/api/history?from_date=${encodeURIComponent(fromStr)}&to_date=${encodeURIComponent(toStr)}&rack=${encodeURIComponent(rack)}&param=${encodeURIComponent(param)}`;
      const res = await fetch(url);
      const result = await res.json();

      if (result.status === "success") {
        historyData = (result.data || []).map(r => ({
          ...r,
          air_quality_percent: formatAirQualityPercent(r.air_quality)
        }));
        filteredData = [...historyData];
        updateUI();
      } else {
        console.error("Failed to load history:", result);
      }
    } catch (err) {
      console.error("Error fetching historical data:", err);
    }
  }

  function updateUI() {
    recordCountBadge.textContent = `${filteredData.length} Records`;

    // Calculate Summary Statistics
    updateSummaryChips();

    // Render Unique Chart
    renderChart();

    // Render Table
    renderTable();
  }

  function updateSummaryChips() {
    if (!filteredData.length) {
      avgTempVal.textContent = "--";
      avgHumVal.textContent = "--";
      avgSoilVal.textContent = "--";
      avgAirVal.textContent = "--";
      avgWaterVal.textContent = "--";
      return;
    }

    const sum = filteredData.reduce(
      (acc, curr) => {
        acc.temp += curr.temperature || 0;
        acc.hum += curr.humidity || 0;
        acc.soil += curr.soil_moisture || 0;
        acc.air += curr.air_quality_percent || 0;
        acc.water += curr.water_tank || 0;
        return acc;
      },
      { temp: 0, hum: 0, soil: 0, air: 0, water: 0 }
    );

    const len = filteredData.length;
    avgTempVal.textContent = `${(sum.temp / len).toFixed(1)}°C`;
    avgHumVal.textContent = `${(sum.hum / len).toFixed(1)}%`;
    avgSoilVal.textContent = `${(sum.soil / len).toFixed(1)}%`;
    avgAirVal.textContent = `${(sum.air / len).toFixed(1)}%`;
    avgWaterVal.textContent = `${(sum.water / len).toFixed(1)}%`;
  }

  // ==========================================
  // FUTURISTIC & UNIQUE GRAPH RENDERING
  // ==========================================
  function renderChart() {
    if (!filteredData.length) {
      journeyChart.data.labels = [];
      journeyChart.data.datasets = [];
      journeyChart.update();
      return;
    }

    const labels = filteredData.map((d) => `${d.date} ${d.time}`);
    const param = paramSelect.value;
    const selectedRack = rackSelect.value;

    let datasets = [];

    // Helper gradient creator
    const makeGradient = (colorStart, colorEnd) => {
      const gradient = ctx.createLinearGradient(0, 0, 0, 400);
      gradient.addColorStop(0, colorStart);
      gradient.addColorStop(1, colorEnd);
      return gradient;
    };

    if (param === "all") {
      // Temperature
      datasets.push({
        label: "Rack 1 Temp (°C)",
        data: filteredData.map((d) => (d.rack === "Rack 1" ? d.temperature : null)),
        borderColor: "#34d399",
        backgroundColor: "transparent",
        tension: 0.4,
        borderWidth: 2.5,
        pointRadius: 2,
        pointHoverRadius: 6
      });
      datasets.push({
        label: "Rack 2 Temp (°C)",
        data: filteredData.map((d) => (d.rack === "Rack 2" ? d.temperature : null)),
        borderColor: "#059669",
        backgroundColor: "transparent",
        tension: 0.4,
        borderWidth: 2.5,
        pointRadius: 2,
        pointHoverRadius: 6
      });
      // Soil Moisture
      datasets.push({
        label: "Rack 1 Soil (%)",
        data: filteredData.map((d) => (d.rack === "Rack 1" ? d.soil_moisture : null)),
        borderColor: "#f59e0b",
        backgroundColor: "transparent",
        tension: 0.4,
        borderWidth: 2.5,
        pointRadius: 2,
        pointHoverRadius: 6
      });
      datasets.push({
        label: "Rack 2 Soil (%)",
        data: filteredData.map((d) => (d.rack === "Rack 2" ? d.soil_moisture : null)),
        borderColor: "#d97706",
        backgroundColor: "transparent",
        tension: 0.4,
        borderWidth: 2.5,
        pointRadius: 2,
        pointHoverRadius: 6
      });
    } else {
      const keyMap = {
        Temperature: "temperature",
        Humidity: "humidity",
        "Soil Moisture": "soil_moisture",
        "Air Quality": "air_quality_percent",
        "Water Tank": "water_tank",
        Pump: "pump",
        Fan: "fan",
        "UV Light": "uv"
      };

      const dataKey = keyMap[param] || "temperature";
      const unitLabel = param === "Temperature" ? "°C" : "%";

      if (selectedRack === "all") {
        datasets.push({
          label: `Rack 1 ${param} (${unitLabel})`,
          data: filteredData.map((d) => (d.rack === "Rack 1" ? d[dataKey] : null)),
          borderColor: "#34d399",
          backgroundColor: makeGradient("rgba(52, 211, 153, 0.22)", "rgba(52, 211, 153, 0.0)"),
          fill: true,
          tension: 0.4,
          borderWidth: 2.5,
          pointRadius: 3
        });
        datasets.push({
          label: `Rack 2 ${param} (${unitLabel})`,
          data: filteredData.map((d) => (d.rack === "Rack 2" ? d[dataKey] : null)),
          borderColor: "#3b82f6",
          backgroundColor: makeGradient("rgba(59, 130, 246, 0.22)", "rgba(59, 130, 246, 0.0)"),
          fill: true,
          tension: 0.4,
          borderWidth: 2.5,
          pointRadius: 3
        });
      } else {
        datasets.push({
          label: `${selectedRack} ${param} (${unitLabel})`,
          data: filteredData.map((d) => d[dataKey]),
          borderColor: "#34d399",
          backgroundColor: makeGradient("rgba(52, 211, 153, 0.28)", "rgba(52, 211, 153, 0.01)"),
          fill: true,
          tension: 0.4,
          borderWidth: 3,
          pointRadius: 4
        });
      }
    }

    journeyChart.data.labels = labels;
    journeyChart.data.datasets = datasets;
    journeyChart.update();
  }

  // ==========================================
  // TABLE SEARCH, SORTING & PAGINATION
  // ==========================================
  tableSearchInput.addEventListener("input", () => {
    currentPage = 1;
    renderTable();
  });

  pageSizeSelect.addEventListener("change", (e) => {
    pageSize = parseInt(e.target.value, 10);
    currentPage = 1;
    renderTable();
  });

  document.querySelectorAll("#historyTable th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const col = th.getAttribute("data-sort");
      if (currentSort.column === col) {
        currentSort.asc = !currentSort.asc;
      } else {
        currentSort.column = col;
        currentSort.asc = true;
      }
      renderTable();
    });
  });

  function renderTable() {
    let rows = [...filteredData];

    // Search Filter
    const searchTerm = tableSearchInput.value.toLowerCase().trim();
    if (searchTerm) {
      rows = rows.filter((r) =>
        Object.values(r).some((v) => String(v).toLowerCase().includes(searchTerm))
      );
    }

    // Sort
    rows.sort((a, b) => {
      let valA = a[currentSort.column];
      let valB = b[currentSort.column];

      if (typeof valA === "string") valA = valA.toLowerCase();
      if (typeof valB === "string") valB = valB.toLowerCase();

      if (valA < valB) return currentSort.asc ? -1 : 1;
      if (valA > valB) return currentSort.asc ? 1 : -1;
      return 0;
    });

    // Pagination
    const totalRows = rows.length;
    const totalPages = Math.ceil(totalRows / pageSize) || 1;
    currentPage = Math.min(currentPage, totalPages);

    const startIdx = (currentPage - 1) * pageSize;
    const endIdx = Math.min(startIdx + pageSize, totalRows);
    const paginatedRows = rows.slice(startIdx, endIdx);

    // Build Table Rows
    tableBody.innerHTML = "";
    if (!paginatedRows.length) {
      tableBody.innerHTML = `<tr><td colspan="13" style="text-align: center; padding: 24px; color: #94a3b8;">No records match your search criteria.</td></tr>`;
    } else {
      paginatedRows.forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${row.date}</td>
          <td>${row.time}</td>
          <td><strong>${row.rack}</strong></td>
          <td>${row.crop}</td>
          <td>${row.stage}</td>
          <td>${row.temperature}°C</td>
          <td>${row.humidity}%</td>
          <td>${row.soil_moisture}%</td>
          <td><strong>${row.air_quality_percent}%</strong></td>
          <td>${row.water_tank}%</td>
          <td><span class="actuator-pill ${row.pump ? "on" : "off"}">${row.pump ? "ON" : "OFF"}</span></td>
          <td><span class="actuator-pill ${row.fan ? "on" : "off"}">${row.fan ? "ON" : "OFF"}</span></td>
          <td><span class="actuator-pill ${row.uv ? "on" : "off"}">${row.uv ? "ON" : "OFF"}</span></td>
        `;
        tableBody.appendChild(tr);
      });
    }

    // Update Pagination Controls
    paginationInfo.textContent = totalRows === 0 ? "Showing 0 records" : `Showing ${startIdx + 1}-${endIdx} of ${totalRows} records`;
    prevPageBtn.disabled = currentPage === 1;
    nextPageBtn.disabled = currentPage === totalPages;

    renderPageNumbers(totalPages);
  }

  function renderPageNumbers(totalPages) {
    pageNumbers.innerHTML = "";
    for (let i = 1; i <= Math.min(totalPages, 5); i++) {
      const btn = document.createElement("button");
      btn.className = `page-num-btn ${i === currentPage ? "active" : ""}`;
      btn.textContent = i;
      btn.addEventListener("click", () => {
        currentPage = i;
        renderTable();
      });
      pageNumbers.appendChild(btn);
    }
  }

  prevPageBtn.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      renderTable();
    }
  });

  nextPageBtn.addEventListener("click", () => {
    currentPage++;
    renderTable();
  });

  // ==========================================
  // EXPORT ENGINE (CSV & PDF)
  // ==========================================
  exportCsvBtn.addEventListener("click", () => {
    if (!filteredData.length) {
      alert("No data available to export.");
      return;
    }

    const headers = ["Date", "Time", "Rack", "Temperature (°C)", "Humidity (%)", "Soil Moisture (%)", "Air Quality (%)", "Water Tank (%)", "Pump", "Fan", "UV Light"];
    const csvRows = [headers.join(",")];

    filteredData.forEach((row) => {
      const line = [
        row.date,
        row.time,
        `"${row.rack}"`,
        row.temperature,
        row.humidity,
        row.soil_moisture,
        row.air_quality_percent,
        row.water_tank,
        row.pump ? "ON" : "OFF",
        row.fan ? "ON" : "OFF",
        row.uv ? "ON" : "OFF"
      ];
      csvRows.push(line.join(","));
    });

    const csvContent = "data:text/csv;charset=utf-8," + csvRows.join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `farm_journey_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });

  exportPdfBtn.addEventListener("click", () => {
    window.print();
  });
});
