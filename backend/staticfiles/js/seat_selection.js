// AKI Cinema — Seat Selection
(function () {
  const PRICE_PER_SEAT = parseFloat(PRICE) || 0;
  const selectedIds = new Set();

  const seatsCountEl   = document.getElementById('seatsCount');
  const totalAmountEl  = document.getElementById('totalAmount');
  const checkoutTotalEl= document.getElementById('checkoutTotal');
  const checkoutBtn    = document.getElementById('checkoutBtn');
  const seatsInput     = document.getElementById('selectedSeatsInput');
  const seatsList      = document.getElementById('selectedSeatsList');
  const noSeatsMsg     = document.getElementById('noSeatsMsg');

  function updateSummary() {
    const count = selectedIds.size;
    const total = count * PRICE_PER_SEAT;

    seatsCountEl.textContent  = count;
    totalAmountEl.textContent = total.toFixed(0) + ' сом';
    checkoutTotalEl.textContent = count > 0 ? ' — ' + total.toFixed(0) + ' сом' : '';
    seatsInput.value = Array.from(selectedIds).join(',');
    checkoutBtn.disabled = count === 0;

    // Update selected seats list
    seatsList.querySelectorAll('.selected-seat-item').forEach(el => el.remove());
    noSeatsMsg.style.display = count === 0 ? 'block' : 'none';

    selectedIds.forEach(id => {
      const btn = document.querySelector(`.seat[data-seat-id="${id}"]`);
      if (!btn) return;
      const item = document.createElement('div');
      item.className = 'selected-seat-item d-flex justify-content-between align-items-center mb-1';
      item.dataset.seatId = id;
      item.innerHTML = `
        <span class="text-light small">
          <i class="fas fa-chair text-danger me-1"></i>
          ${LANG === 'ky' ? 'Ряд' : 'Ряд'} ${btn.dataset.row},
          ${LANG === 'ky' ? 'Орун' : 'Место'} ${btn.dataset.num}
        </span>
        <span class="text-danger small fw-bold">${PRICE_PER_SEAT} сом</span>
      `;
      seatsList.appendChild(item);
    });
  }

  function handleSeatClick(e) {
    const btn = e.currentTarget;
    if (btn.disabled || btn.classList.contains('booked')) return;

    const id = btn.dataset.seatId;

    if (selectedIds.has(id)) {
      selectedIds.delete(id);
      btn.classList.remove('selected');
      btn.classList.add('free');
    } else {
      selectedIds.add(id);
      btn.classList.remove('free');
      btn.classList.add('selected');
    }

    updateSummary();
  }

  // Attach click handlers to all free seats
  document.querySelectorAll('.seat.free').forEach(btn => {
    btn.addEventListener('click', handleSeatClick);
  });

  // Prevent form submit if no seats
  document.getElementById('checkoutForm').addEventListener('submit', function (e) {
    if (selectedIds.size === 0) {
      e.preventDefault();
      alert(LANG === 'ky' ? 'Орун тандаңыз!' : 'Выберите хотя бы одно место!');
    }
  });

  updateSummary();
})();
