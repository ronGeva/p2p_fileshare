function searchFile() {
    const filename = document.getElementById("file_search").value;
    let request = new XMLHttpRequest()
    request.open("GET", "/search/" + filename, false);
    request.send(null);
    let responseJSON = JSON.parse(request.responseText);
    let files = responseJSON["files"];
    let searchResultDiv = document.getElementById("search-results");
    let searchResultContent = "";
    for(let i = 0; i < files.length; i++) {
        searchResultContent += files[i]["description"] +
            "<input type='button' value='download' onclick='downloadFile(\"" + files[i]["unique_id"] + "\")'>" +
            "<br/>";
    }
    searchResultDiv.innerHTML = searchResultContent;
}

function downloadFile(uniqueID) {
    const local_path = prompt("Path to download to: ", "");
    let request = new XMLHttpRequest();
    request.open("GET", "/download?unique_id=" + uniqueID + "&local_path=" + local_path);
    request.send(null);
}
