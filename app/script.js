function atlanticYear(select) {
    var year = select.value;
    window.location.href = "/archive/atlantic/" + year;
}

function archiveYear(pub, select) {
    var year = select.value;
    window.location.href = "/archive/" + pub + "/" + year;
}

function wsjYear(select) {
    var year = select.value;
    window.location.href = "/archive/wsj/" + year;
}

// function get(url) {
//     var xmlHttp = new XMLHttpRequest();
//     xmlHttp.open( "GET", url, false );
//     xmlHttp.send( null );
//     return xmlHttp.responseText;
// }

// function loadPuzzles() {
//     // document.title = "Loaded!";
//     var url = "/api/puzzles";
//     var data = get(url);
//     console.log(data);
//     var puzzles = JSON.parse(data)["puzzles"];
//     console.log(puzzles);
//     let table = new DataTable('#puzzles-table', {
//         "data": puzzles,
//         "columns": [
//             {
//                 "data": "date",
//                 "className": "puzzle-list-date",
//             },
//             {
//                 "data": "title",
//                 "className": "puzzle-list-title",
//                 "render": function( data, type, row, meta ) {
//                     return '<a class="puzzle-list-title" href="/puzzles/' + row.id + '">' + data + '</a>';
//                 },
//             },
//             {
//                 "data": "pub",
//                 "className": "puzzle-list-publication",
//             },
//         ],
//         "pageLength": 100,
//     });
// }
