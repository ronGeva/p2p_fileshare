"""
This module serves as a gateway for the web page into the application.
Clients should start this local web server and then use the application through the web interface (by accessing
localhost:5050 in their browser). All information transfers between the web page and the client application itself
are done via REST API which is implemented in this module.
"""

import sys
from typing import Optional
from flask import Flask, request, render_template
from p2p_fileshare.client.files_manager import FilesManager
from main import initialize_files_manager


app = Flask(__name__)
files_manager = None  # type: Optional[FilesManager]


def wrap_response(func):
    """
    This decorator wrap each "landing spot" function defined in this module to allow us to easily return an appropriate
    error to the frontend in case something goes wrong.
    """
    def inner(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            if response is None:
                response = {}
            response["success"] = True
            return response
        except Exception as e:
            return {"success": False, "error": e.args}
    inner.__name__ = func.__name__ + "_inner"  # required so that Flask will allow us to wrap our functions
    return inner


@app.route('/search/<filename>')
@wrap_response
def search_file(filename):
    result = files_manager.search_file(filename)
    response = {"files": []}
    for file in result:
        response["files"].append({
            "description": f"Name: {file.name}, modification time: {file.modification_time}, size: {file.size}",
            "unique_id": file.unique_id})
    return response


@app.route('/share')
@wrap_response
def share_file():
    file_path = request.args.get('local_path')
    files_manager.share_file(file_path)


@app.route('/download')
@wrap_response
def download_file():
    unique_id = request.args.get('unique_id')
    local_path = request.args.get('local_path')
    files_manager.download_file(unique_id, local_path)


@app.route('/list-downloads')
@wrap_response
def list_downloads():
    downloaders = files_manager.list_downloads()
    response = {"downloads": []}
    for downloader in downloaders:
        response["downloads"].append({
            "local_path": downloader.local_path,
            "name": downloader.file_info.name,
            "progress": "{}%".format(downloader.progress),
            "done": downloader.is_done(),
            "failed": downloader.failed
        })
    return response


@app.route('/remove-download/<download_id>')
@wrap_response
def remove_download(download_id):
    files_manager.remove_download(int(download_id))


@app.route('/list-shares')
@wrap_response
def list_shares():
    shares = files_manager.list_shares()
    response = {"shares": []}
    for share in shares:
        response["shares"].append({
            "local_path": share[0],
            "unique_id": share[1]
        })
    return response


@app.route('/remove-share/<unique_id>')
@wrap_response
def stop_shring(unique_id):
    files_manager.remove_share(unique_id)


@app.route('/')
def main_page():
    return render_template('app.html')


def get_web_server_port(args):
    web_port = 5050
    if len(args) >= 5:
        web_port = args[4]
        assert web_port.isdigit()
        web_port = int(web_port)
    return web_port


def main(args):
    global files_manager
    files_manager = initialize_files_manager(args)

    app.run("localhost", get_web_server_port(args))


if __name__ == '__main__':
    main(sys.argv)