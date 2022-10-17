var API_BASE = "https://hexapi.lukwam.dev"

var books = []
var publications = []
var puzzles = []

var book_codes = {}
var publication_codes = {}
var puzzle_ids = {}
var puzzle_years = []

var book_filter = "";
var publication_filter = "";
var year_filter = "";

// create dropdown for selecting a book
function createBookSelector() {
  var select = document.getElementById("book-selector");
  select.innerHTML = "";
  select.addEventListener("change", function() { filterPuzzlesByBook(this); }, false);
  var default_option = document.createElement("option");
  default_option.innerHTML = "All Books"
  select.appendChild(default_option);
  books.forEach(book => {
    var option = document.createElement("option");
      option.id = book.code;
      option.innerHTML = book.title;
    select.appendChild(option);
  });
}

// create dropdown for selecting a publication
function createPublicationSelector() {
  var select = document.getElementById("publication-selector");
  select.innerHTML = "";
  select.addEventListener("change", function() { filterPuzzlesByPublication(this); }, false);
  var default_option = document.createElement("option");
  default_option.innerHTML = "All Publications"
  select.appendChild(default_option);
  publications.forEach(publication => {
    var option = document.createElement("option");
      option.id = publication.code;
      option.innerHTML = publication.name;
    select.appendChild(option);
  });
}

// create dropdown for selecting a year
function createYearSelector() {
  var select = document.getElementById("year-selector");
  select.innerHTML = "";
  select.addEventListener("change", function() { filterPuzzlesByYear(this); }, false);
  var default_option = document.createElement("option");
  default_option.innerHTML = "All Years"
  select.appendChild(default_option);
  puzzle_years.forEach(year => {
    var option = document.createElement("option");
      option.id = year;
      option.innerHTML = year;
    select.appendChild(option);
  });
}


// display the books on the main page
function displayBooks() {
  var books_list = document.getElementById("books-list");
  books_list.innerHTML = "";
  for (n=0; n<books.length; n++) {
    book = books[n];
    var li = document.createElement("li");
    li.innerHTML = book.title;
    li.setAttribute("data-id", book.id);
    li.setAttribute("data-code", book.code);
    books_list.appendChild(li);
  }
}

// display the publications on the main page
function displayPublications() {
  var publications_list = document.getElementById("publications-list");
  publications_list.innerHTML = "";
  for (n=0; n<publications.length; n++) {
    publication = publications[n];
    var li = document.createElement("li");
    li.innerHTML = publication.name + " (" + publication.code + ")";
    li.setAttribute("data-id", publication.id);
    li.setAttribute("data-pub", publication.code)
    publications_list.appendChild(li);
  }
}

// create the puzzles on the main page
function createPuzzles() {
  var puzzles_list = document.getElementById("puzzles-list");
  puzzles_list.innerHTML = "";
  for (n=0; n<puzzles.length; n++) {
    puzzle = puzzles[n];
    var title_text = puzzle.title;
    if (puzzle.puzzle_link) {
      title_text = '<a href="' + puzzle.puzzle_link + '" target="_puzzle">' + puzzle.title + '</a>';
    } else if (puzzle.web_link) {
      title_text = '<a href="' + puzzle.web_link + '" target="_puzzle">' + puzzle.title + '</a>';
    }
    var answer_text = "";
    if (puzzle.answer_link) {
      answer_text = '<a href="' + puzzle.answer_link + '" target="_puzzle">answer</a>';
    }

    var tr = document.createElement("tr");
    tr.id = "puzzle-" + puzzle.id;
    tr.setAttribute("data-id", puzzle.id);
    tr.setAttribute("data-pub", puzzle.pub);
    tr.setAttribute("data-year", puzzle.date.toISOString().slice(0, 4));

    var date = document.createElement("td");
    date.innerHTML = formatDate(puzzle.date);
    tr.appendChild(date);

    var title = document.createElement("td");
    title.innerHTML = title_text;
    tr.appendChild(title);

    var answer = document.createElement("td");
    answer.innerHTML = answer_text;
    tr.appendChild(answer);

    var publication = document.createElement("td");
    publication.innerHTML = puzzle.pub;
    tr.appendChild(publication);

    puzzles_list.appendChild(tr);
  }
}

// filter a single puzzle
function filterPuzzle(element) {
  var id = element.dataset.id;
  var pub = element.dataset.pub;
  var year = element.dataset.year;
  var puzzle = puzzle_ids[id];
  var books = puzzle.books;

  if (!books) {
    books = [];
  }

  var include = true;

  // apply book filter
  if (book_filter && (!books.includes(book_filter))) {
    console.log(book_filter, books, book_filter in books);
    include = false;
  }

  // apply publication filter
  if (publication_filter && publication_filter != pub) {
    include = false;
  }

  // apply year filter
  if (year_filter && year_filter != year) {
    include = false;
  }

  return include
}

// filter puzzles by book, publication, and/or year
function filterPuzzles() {
  var puzzle_list = document.getElementById("puzzles-list");
  var count = 0;
  [...puzzle_list.children].forEach(element => {
    if (filterPuzzle(element)) {
      element.style.display = "table-row";
      count += 1;
    } else {
      element.style.display = "none";
    }
  });

  // update filter text
  var filter_text = document.getElementById("puzzles-filter-text");
  if (!book_filter && !publication_filter && !year_filter) {
    filter_text.innerHTML = " Showing all " + count + " puzzles.";
  } else {
    var text = "Showing " + count + " puzzles where ";
    var where = [];
    if (book_filter) {
      where.push("book = " + book_filter)
    }
    if (publication_filter) {
      where.push("pub = " + publication_filter)
    }
    if (year_filter) {
      where.push("year = " + year_filter)
    }
    text += where.join(" and ");
    filter_text.innerHTML = text + ".";
  }
  return count;
}

// filter puzzles by book
function filterPuzzlesByBook(select) {
  var selected = select.options[select.selectedIndex];
  book_filter = selected.id;
  filterPuzzles();
  var show_all = document.getElementById("puzzles-show-all");
  show_all.style.display = "block";
}

// filter puzzles by publication
function filterPuzzlesByPublication(select) {
  var selected = select.options[select.selectedIndex];
  publication_filter = selected.id;
  filterPuzzles();
  var show_all = document.getElementById("puzzles-show-all");
  show_all.style.display = "block";
}

// filter puzzles by year
function filterPuzzlesByYear(select) {
  var selected = select.options[select.selectedIndex];
  year_filter = selected.id;
  filterPuzzles();
  var show_all = document.getElementById("puzzles-show-all");
  show_all.style.display = "block";
}

// format dates to yyyy-mm-dd format
function formatDate(date) {
  return date.toISOString().split('T')[0]
}

// get response from an HTTP get request
function get(url) {
  var xmlHttp = new XMLHttpRequest();
  xmlHttp.open( "GET", url, false );
  xmlHttp.send( null );
  return xmlHttp.responseText;
}

// get json response from an HTTP get request
function getJson(url) {
  var response = get(url);
  return JSON.parse(response);
}

// get books from the API
function getBooks() {
  var url = API_BASE + "/books"
  var books = getJson(url)["books"];
  books.sort((a, b) => (a.title > b.title) ? 1 : -1)
  return books
}

// update book_codes dict
function getBooksByCode() {
  for (n=0; n<books.length; n++) {
    var book = books[n];
    var code = book["code"];
    book_codes[code] = book;
  }
}

// get publications from the API
function getPublications() {
  var url = API_BASE + "/publications"
  var publications = getJson(url)["publications"];
  publications.sort((a, b) => (a.name > b.name) ? 1 : -1)
  return publications
}

// update publication_codes dict
function getPublicationsByCode() {
  for (n=0; n<publications.length; n++) {
    var publication = publications[n];
    var code = publication["code"];
    publication_codes[code] = publication;
  }
}

// get puzzles from the API
function getPuzzles() {
  var url = API_BASE + "/puzzles"
  var puzzles = getJson(url)["puzzles"];
  puzzles.forEach(element => {
      element.date = new Date(Date.parse(element.date));
  });
  puzzles.sort((a, b) => (a.date > b.date) ? 1 : -1)
  return puzzles
}

// update puzzles_ids dict
function getPuzzlesById() {
  for (n=0; n<puzzles.length; n++) {
    var puzzle = puzzles[n];
    var id = puzzle["id"];
    puzzle_ids[id] = puzzle;
  }
}

// update puzzle_years list
function getPuzzleYears() {
  for (n=0; n<puzzles.length; n++) {
    var puzzle = puzzles[n];
    var year = puzzle["date"].toISOString().slice(0, 4);
    if (!puzzle_years.includes(year)) {
      puzzle_years.push(year);
    }
  }
}

// load content based on the fragment
function loadContent(){
  var fragmentId = location.hash.substr(1);
  var pages = {
    "about": "About",
    "books": "Books",
    "home": "Hex",
    "publications": "Publications",
    "puzzles": "Puzzles",
  };
  if (!(fragmentId in pages)) {
    fragmentId = "home";
  }
  console.log("Page: " + fragmentId);

  // set the title
  var title = pages[fragmentId];
  document.title = title;

  // hide all pages except the selected one
  for (const page in pages) {
    var page_id = page + "-page";
    var element = document.getElementById(page_id);
    if (page == fragmentId) {
      element.style.display = "block";
    } else {
      element.style.display = "none";
    }
  }
}

// load data from the API
function loadData() {
  books = getBooks();
  getBooksByCode();
  displayBooks();
  console.log("Books: " + books.length);

  publications = getPublications();
  getPublicationsByCode();
  displayPublications();
  console.log("Publications: " + publications.length);

  puzzles = getPuzzles();
  getPuzzlesById();
  getPuzzleYears();
  createPuzzles();
  console.log("Puzzles: " + puzzles.length);

  createBookSelector();
  createPublicationSelector();
  createYearSelector();

  loadContent();
}

// show all puzzles
function showAllPuzzles() {
  var puzzle_list = document.getElementById("puzzles-list");
  [...puzzle_list.children].forEach(element => {
      element.style.display = "table-row";
  });
  var filter_text = document.getElementById("puzzles-filter-text");
  filter_text.innerHTML = "Showing all " + puzzles.length + " puzzles.";
  var show_all = document.getElementById("puzzles-show-all");
  show_all.style.display = "none";

  // reset the three filter selectors to 0

}

// set the default fragment to #home
if(!location.hash) {
  location.hash = "#home";
}

// watch for has changes and load appropriate content
window.addEventListener("hashchange", loadContent)
