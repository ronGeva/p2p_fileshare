import sys
from typing import Optional
from flask import Flask, request, render_template
from files_manager import FilesManager
from p2p_fileshare.framework.channel import Channel
from main import initialize_communication_channel


app = Flask(__name__)
communication_channel = None  # type: Optional[Channel]
files_manager = None  # type: Optional[FilesManager]


@app.route('/search/<filename>')
def search_file(filename):
    result = files_manager.search_file(filename)
    response = {"files": []}
    for file in result:
        response["files"].append({
            "description": f"Name: {file.name}, modification time: {file.modification_time}, size: {file.size}",
            "unique_id": file.unique_id})
    return response


@app.route('/share/<file_path>')
def share_file(file_path):
    files_manager.share_file(file_path)


@app.route('/download')
def download_file():
    unique_id = request.args.get('unique_id', None)
    local_path = request.args.get('local_path', None)
    files_manager.download_file(unique_id, local_path)


@app.route('/list-downloads')
def list_downloads():
    downloaders = files_manager.list_downloads()
    response = {"downloads": []}
    for downloader_id in downloaders.keys():
        downloader = downloaders[downloader_id]
        response["downloads"].append({
            "local_path": downloader.local_path,
            "name": downloader.file_info.name,
            "id": downloader_id,
            "done": downloader.is_done()
        })
    return response


@app.route('/remote-download/<download_id>')
def remove_download(download_id):
    files_manager.remove_download(download_id)


@app.route('/')
def main_page():
    return render_template('app.html')


def main(args):
    global communication_channel
    global files_manager

    communication_channel = initialize_communication_channel(args)
    files_manager = FilesManager(communication_channel)
    app.run("localhost", 5050, debug=True)


if __name__ == '__main__':
    main(sys.argv)