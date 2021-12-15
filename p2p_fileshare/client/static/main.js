function searchFile() {
    const filename = document.getElementById("file_search").value;
    let request = new XMLHttpRequest();
    request.open("GET", "/search/" + filename, false);
    request.send(null);
    let responseJSON = JSON.parse(request.responseText);
    let files = responseJSON["files"];
    let searchResultDiv = document.getElementById("search-results");
    let searchResultContent = "";
    for(let i = 0; i < files.length; i++) {
        searchResultContent += files[i]["description"] +
            "<input type='button' value='download' class=\"btn btn-success\" onclick='downloadFile(\""
            + files[i]["unique_id"] + "\")'>" + "<br/>";
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
        let extraString = "";
        if (downloads[i]["done"]) {
            disabledAttribute += "disabled";
            extraString = "<b class=\"text-success\">FINISHED</b>";
        }
        else
            isThereADownloadInProgress = true; // found at least one download in progress
        if (downloads[i]["failed"])
            extraString = "<b class=\"text-danger\">FAILED</b>";

        currentDownloadsContent += downloads[i]["name"] + " -> " + downloads[i]["local_path"] +
            "<input type='button' value='stop' class=\"btn btn-warning\" onclick='removeDownload(" + i + ")'" +
            disabledAttribute + ">" + extraString + "<br/>";
    }
    currentDownloadsDiv.innerHTML = currentDownloadsContent;
    if (isThereADownloadInProgress)
        // There is still a download in progress, schedule listDownloads again to check for its status.
        setTimeout(listDownloads, 1000);
}

function removeDownload(downloadID) {
    let request = new XMLHttpRequest();
    request.open("GET", "/remove-download/" + downloadID, false);
    request.send(null);
    listDownloads();
}

function newShare() {
    const local_path = prompt("Enter file path:");
    let request = new XMLHttpRequest();
    request.open("GET", "/share?local_path=" + local_path, false);
    request.send(null);
    let responseJSON = JSON.parse(request.responseText);
    if (!responseJSON["success"])
        window.alert(responseJSON["error"]);
    listShares();
}

function listShares() {
    let request = new XMLHttpRequest();
    request.open("GET", "/list-shares", false);
    request.send(null);
    let responseJSON = JSON.parse(request.responseText);
    let currentSharesDiv = document.getElementById("shares-div");
    let currentSharesContent = "";
    if (!responseJSON["success"])
        // let the user know something went wrong without prompting an infinite amount of dialog boxes
        currentSharesContent = responseJSON["error"];
    else {
        const shares = responseJSON["shares"];
        for (let i = 0; i < shares.length; i++) {
            currentSharesContent += "Local path: " + shares[i]["local_path"] +
                "<input type='button' class=\"btn btn-warning\" value='stop sharing' " +
                "onclick='stopSharing(\"" + shares[i]["unique_id"] + "\")'>" +
                "<br/>";
        }
    }
    currentSharesDiv.innerHTML = currentSharesContent;
}

function stopSharing(uniqueID) {
    let request = new XMLHttpRequest();
    request.open("GET", "/remove-share/" + uniqueID, false);
    request.send(null);
    let responseJSON = JSON.parse(request.responseText);
    if (!responseJSON["success"])
        window.alert(responseJSON["error"]);
    else
        listShares();
}

// initialize dynamic panels
listDownloads();
listShares();
