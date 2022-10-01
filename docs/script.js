var API_BASE = "https://hexapi.lukwam.dev"

var books = []
var publications = []
var puzzles = []

var book_codes = {}
var publication_codes = {}
var puzzle_ids = {}

function displayBooks() {
    var books_list = document.getElementById("books-list");
    books_list.innerHTML = "";
    for (n=0; n<books.length; n++) {
        book = books[n];
        var title = '<a id="' + book.id + '" onclick="filterPuzzlesByBook(this);">' + book.title + '</a>';
        var li = document.createElement("li");
        li.innerHTML = title;
        li.setAttribute("data-id", book.id);
        li.setAttribute("data-code", book.code);
        books_list.appendChild(li);
    }
}

function displayPublications() {
    var publications_list = document.getElementById("publications-list");
    publications_list.innerHTML = "";
    for (n=0; n<publications.length; n++) {
        publication = publications[n];
        var name = '<a id="' + publication.id + '" onclick="filterPuzzlesByPub(this);">' + publication.name + '</a>';
        var li = document.createElement("li");
        li.innerHTML = name + " (" + publication.code + ")";
        li.setAttribute("data-id", publication.id);
        li.setAttribute("data-pub", publication.code)
        publications_list.appendChild(li);
    }
}

function displayPuzzles() {
    var puzzles_list = document.getElementById("puzzles-list");
    puzzles_list.innerHTML = "";
    for (n=0; n<puzzles.length; n++) {
        puzzle = puzzles[n];
        var title = puzzle.title;
        if (puzzle.puzzle_link) {
            title = '<a href="' + puzzle.puzzle_link + '" target="_puzzle">' + puzzle.title + '</a>';
        } else if (puzzle.web_link) {
            title = '<a href="' + puzzle.web_link + '" target="_puzzle">' + puzzle.title + '</a>';
        }
        var answer = "";
        if (puzzle.answer_link) {
            answer = ' | <a href="' + puzzle.answer_link + '" target="_puzzle">answer</a>';
        }
        var li = document.createElement("li");
        li.id = "puzzle-" + puzzle.id;
        li.setAttribute("data-id", puzzle.id);
        li.setAttribute("data-pub", puzzle.pub);
        li.innerHTML = formatDate(puzzle.date) + " " + title + answer + " (" + puzzle.pub + ")";
        puzzles_list.appendChild(li);
    }
}

// filter puzzles by book
function filterPuzzlesByBook(book_link) {
    var code = book_link.parentElement.dataset.code;
    var puzzle_list = document.getElementById("puzzles-list");
    [...puzzle_list.children].forEach(element => {
        var puzzle_id = element.dataset.id;
        var puzzle = puzzle_ids[puzzle_id];
        if (puzzle.books && puzzle.books.includes(code)) {
            element.style.display = "list-item";
        } else {
            element.style.display = "none";
        }
        element.date = new Date(Date.parse(element.date));
    });
}

// filter puzzles by publication
function filterPuzzlesByPub(pub_link) {
    var pub = pub_link.parentElement.dataset.pub;
    var puzzle_list = document.getElementById("puzzles-list");
    [...puzzle_list.children].forEach(element => {
        if (element.dataset.pub == pub) {
            element.style.display = "list-item";
        } else {
            element.style.display = "none";
        }
        element.date = new Date(Date.parse(element.date));
    });
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
    displayPuzzles();
    console.log("Puzzles: " + puzzles.length);



}

// show all puzzles
function showAllPuzzles() {
    var puzzle_list = document.getElementById("puzzles-list");
    [...puzzle_list.children].forEach(element => {
        element.style.display = "list-item";
    });
}
