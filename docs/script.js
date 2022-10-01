var API_BASE = "https://hexapi.lukwam.dev"

var books = []
var publications = []
var puzzles = []

var book_codes = {}
var publication_codes = {}
// var puzzle_stats = {}

function displayBooks() {
    var books_list = document.getElementById("books-list");
    books_list.innerHTML = "";
    for (n=0; n<books.length; n++) {
        book = books[n];
        var li = document.createElement("li");
        li.innerHTML = book.title;
        books_list.appendChild(li);
    }
}

function displayPublications() {
    var publications_list = document.getElementById("publications-list");
    publications_list.innerHTML = "";
    for (n=0; n<publications.length; n++) {
        publication = publications[n];
        var li = document.createElement("li");
        li.innerHTML = publication.name + " (" + publication.code + ")";
        publications_list.appendChild(li);
    }
}

function displayPuzzles() {
    var puzzles_list = document.getElementById("puzzles-list");
    puzzles_list.innerHTML = "";
    for (n=0; n<puzzles.length; n++) {
        puzzle = puzzles[n];
        var li = document.createElement("li");
        li.innerHTML = formatDate(puzzle.date) + " " + puzzle.title + " (" + puzzle.pub + ")";
        puzzles_list.appendChild(li);
    }
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

// load data from the API
function loadData() {
    books = getBooks();
    getBooksByCode();
    console.log("Books: " + books.length);

    publications = getPublications();
    getPublicationsByCode();
    console.log("Publications: " + publications.length);

    puzzles = getPuzzles();
    console.log("Puzzles: " + puzzles.length);

    displayBooks();
    displayPublications();
    displayPuzzles();
}
