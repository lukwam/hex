/* global GLightbox */
/* exported getPuzzlesByID, getPuzzlesByYear, loadPuzzles, searchPuzzles, filterPuzzles */

// get a url via http
function get(url) {
  const xmlHttp = new XMLHttpRequest();
  xmlHttp.open("GET", url, false);
  xmlHttp.send(null);
  return xmlHttp.responseText;
}

// get json response from an HTTP get request
function getJson(url) {
  const response = get(url);
  return JSON.parse(response);
}

// get the data for all puzzles from the json file
function getPuzzles() {
  return getJson("data.json");
}

// get puzzles by id
function getPuzzlesByID() {
  const ids = {};
  const data = getPuzzles();
  for (let i = 0; i < data.length; i++) {
    const puzzle = data[i];
    ids[puzzle.id] = puzzle;
  }
  return ids;
}

// get puzzles by year
function getPuzzlesByYear() {
  const years = {};
  const data = getPuzzles();
  for (let i = 0; i < data.length; i++) {
    const puzzle = data[i];
    if (!(puzzle.year in years)) {
      years[puzzle.year] = [];
    }
    years[puzzle.year].push(puzzle);
  }
  return years;
}

function loadPuzzles(data = null) {
  if (data === null) {
    data = getJson("data.json");
  }
  console.log("Puzzles: " + data.length);

  const puzzles = document.getElementById("puzzles");
  for (let i = 0; i < data.length; i++) {
    const li = document.createElement("li");
    const puzzle = data[i];

    // add the date div
    const dateDiv = document.createElement("div");
    dateDiv.innerHTML = puzzle.date;
    // dateDiv.classList.add("col-sm-4")
    dateDiv.classList.add("float-start");
    dateDiv.classList.add("me-2");
    dateDiv.classList.add("puzzle-list-date");
    dateDiv.classList.add("text-center");
    // dateDiv.style.whiteSpace = "nowrap";
    li.appendChild(dateDiv);

    // create title link
    const a = document.createElement("a");
    a.href = "/puzzles/" + puzzle.id;
    a.innerHTML = puzzle.title;

    // add the title div
    const titleDiv = document.createElement("div");
    titleDiv.appendChild(a);
    titleDiv.classList.add("puzzle-list-title");
    titleDiv.classList.add("float-start");
    // titleDiv.classList.add("col-sm-8")
    li.appendChild(titleDiv);

    li.id = "puzzle-" + puzzle.id;
    li.classList.add("list-group-item");
    puzzles.appendChild(li);
  }
}

// Combined filter: text search + publication dropdown + year dropdown
function filterPuzzles() {
  const queryEl = document.getElementById("search-query");
  const pubEl = document.getElementById("filter-publication");
  const yearEl = document.getElementById("filter-year");

  const query = queryEl ? queryEl.value.toLowerCase() : "";
  const pubFilter = pubEl ? pubEl.value : "";
  const yearFilter = yearEl ? yearEl.value : "";

  const titles = document.getElementsByClassName("puzzle-title");
  let visible = 0;
  const total = titles.length;

  for (let i = 0; i < titles.length; i++) {
    const titleDiv = titles[i];
    const title = titleDiv.dataset.title;
    const date = titleDiv.previousElementSibling.dataset.date;
    const publication = titleDiv.nextElementSibling.dataset.publication;
    const year = date.substring(0, 4);
    const puzzleDiv = titleDiv.parentElement.parentElement;

    // Check all filters
    const matchesQuery =
      !query ||
      title.toLowerCase().includes(query) ||
      date.toLowerCase().includes(query) ||
      publication.toLowerCase().includes(query);
    const matchesPub = !pubFilter || publication === pubFilter;
    const matchesYear = !yearFilter || year === yearFilter;

    if (matchesQuery && matchesPub && matchesYear) {
      puzzleDiv.style.display = "block";
      visible++;
    } else {
      puzzleDiv.style.display = "none";
    }
  }

  // Update count display
  const countEl = document.getElementById("filter-count");
  if (countEl) {
    if (query || pubFilter || yearFilter) {
      countEl.textContent = "Showing " + visible + " of " + total + " puzzles";
    } else {
      countEl.textContent = "";
    }
  }
}

// Alias for search input compatibility
function searchPuzzles() {
  filterPuzzles();
}

// Initialize GLightbox for puzzle images
if (typeof GLightbox !== "undefined") {
  GLightbox({
    selector: ".glightbox",
    touchNavigation: true,
    zoomable: true,
    draggable: true,
  });
}
