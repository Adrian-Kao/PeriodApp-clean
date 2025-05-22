document.addEventListener("DOMContentLoaded", function () {
  const calendarGrid = document.getElementById("calendar-grid");

  for (let i = 1; i <= 30; i++) {
    const day = document.createElement("div");
    day.classList.add("day");
    day.textContent = i;

    day.addEventListener("click", function () {
      day.classList.toggle("selected");
    });

    calendarGrid.appendChild(day);
  }
});

