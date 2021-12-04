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
    request.open("GET", "/download?unique_id=" + uniqueID + "&local_path=" + local_path, false);
    request.send(null);
    listDownloads();
}

function listDownloads() {
    let request = new XMLHttpRequest()
    request.open("GET", "/list-downloads", false);
    request.send(null);
    let responseJSON = JSON.parse(request.responseText);
    let downloads = responseJSON["downloads"]
    let currentDownloadsDiv = document.getElementById("current-downloads");
    let currentDownloadsContent = "";
    let isThereADownloadInProgress = false;
    for(let i = 0; i < downloads.length; i++) {
        let disabledAttribute = "";
        if (downloads[i]["done"])
            disabledAttribute += "disabled";
        else
            isThereADownloadInProgress = true; // found at least one download in progress

        currentDownloadsContent += downloads[i]["name"] + " -> " + downloads[i]["local_path"] +
            "<input type='button' value='stop' onclick='removeDownload(\"" + downloads[i]["id"] + "\")'" +
            disabledAttribute + ">" + "<br/>";
    }
    currentDownloadsDiv.innerHTML = currentDownloadsContent;
    if (isThereADownloadInProgress)
        setTimeout(listDownloads, 1000); // list downloads again in 1 second
}

listDownloads();