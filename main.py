from PySide6.QtWidgets import QApplication, QWidget  # type:ignore
from PySide6.QtWebEngineWidgets import QWebEngineView  # type:ignore
from PySide6.QtCore import QByteArray, QUrl  # type:ignore
from PySide6.QtWebEngineQuick import QtWebEngineQuick  # type:ignore

# Only needed for access to command line arguments
import sys
import os.path as path

def startApp(filePath, basePath):
    # You need one (and only one) QApplication instance per application.
    # Pass in sys.argv to allow command line arguments for your app.
    # If you know you won't use command line arguments QApplication([]) works too.
    app = QApplication(sys.argv)

    # Create a Qt widget, which will be our window.
    window = QWebEngineView()
    with open(filePath, encoding='utf-8') as file:
        data = file.readlines()
    data = ''.join(data)
    data = QByteArray(data.encode())
    window.setContent(data, mimeType="text/html;charset=UTF-8", baseUrl=QUrl.fromLocalFile(basePath))
    window.show()  # IMPORTANT!!!!! Windows are hidden by default.

    # Start the event loop.
    app.exec()


if __name__ == '__main__':
    filePath1 = 'resources/html/common_tasks.xhtml'
    basePath1 = path.dirname(__file__) + '/'
    fp2 = 'books/pantadeusz/nav.xhtml'
    bp2 = basePath1 + 'books/pantadeusz/'

    startApp(fp2, bp2)
