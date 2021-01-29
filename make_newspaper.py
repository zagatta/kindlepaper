import requests
import json
import os
from lib.auth import Auth
import datetime
import re
from shutil import copyfile
import getpass


class Constants:
    DATE_FORMAT_WALLABAG = '%Y-%m-%dT%H:%M:%S+%f'
    DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
    NEWLINE = "\n"
    LAST_UDATE_FILE = ".last_update"
    URL_ENTRIES_KINDLE = "https://app.wallabag.it/api/entries.json?tags=kindle"
    URL_EXPORT_MOBI = "https://app.wallabag.it/api/entries/{}/export.mobi"
    DOWNLOAD_FOLDER = "/.download"
    KINDLE_PATH = "/media/{}/Kindle/documents/".format(getpass.getuser())
    

class Jameson:
    def __init__(self):
        self.auth = Auth()
        self.myToken = self.auth.getAccessToken()
        self.last_update = datetime.datetime(1994, 2, 1)
        self.articles = []
        self.head = {'Authorization': 'token {}'.format(self.myToken)}
        self.path = os.path.dirname(os.path.abspath( __file__ ))
        self.now = datetime.datetime.now()
    
    def __getLastUpdate__(self):
        if os.path.isfile(Constants.LAST_UDATE_FILE) and os.path.getsize(Constants.LAST_UDATE_FILE) > 0:
            with open(Constants.LAST_UDATE_FILE) as f:
                for line in f:
                    pass
                last = line
                self.last_update = datetime.datetime.strptime(last, Constants.DATE_FORMAT)

    def __saveLastUpdate__(self):
         #save last updated timestamp
        f = open(Constants.LAST_UDATE_FILE, "a")
        f.write(Constants.NEWLINE + self.now.strftime(Constants.DATE_FORMAT))
        f.close()

    def __getAllNewEntries__(self):
        self.__getLastUpdate__()
        response = requests.get(Constants.URL_ENTRIES_KINDLE, headers=self.head)
        response_json = response.json()
        for item in response_json["_embedded"]["items"]:
            print(item["title"])
            #get item creation date
            creation_date = datetime.datetime.strptime(item["created_at"], Constants.DATE_FORMAT_WALLABAG)
            if creation_date > self.last_update:
                print("use this article")
                self.articles.append(item["id"])
            else:
                print("discard")
        print(self.articles)

    def __getFilenameFromCd__(self, cd):
        """
        Get filename from content-disposition
        """
        if not cd:
            return None
        fname = re.findall('filename=(.+)', cd)
        if len(fname) == 0:
            return None
        filename = ''.join(e for e in fname[0] if e.isalnum() or e == ".")
        return filename

    def __downloadMobi__(self, entryId, target):
        url = Constants.URL_EXPORT_MOBI.format(entryId)
        response = requests.get(url, headers=self.head)
        filename = self.__getFilenameFromCd__(response.headers.get('content-disposition'))
        filepath = str(target) + "/" + str(filename)
        print(filepath)
        open(filepath, 'wb').write(response.content)
        return filepath

    def __makeFolder__(self):
        download_path = self.path + Constants.DOWNLOAD_FOLDER
        if not os.path.isdir(download_path):
            os.mkdir(download_path)
        foldername = self.now.strftime(Constants.DATE_FORMAT)
        newspaper_folder_path = download_path + "/" + foldername 
        os.mkdir(newspaper_folder_path)
        return newspaper_folder_path

    def __copyToKindle__(self, src):
        filename = src.split("/")[-1]
        copyfile(src, Constants.KINDLE_PATH + filename)


    def makeNewspaper(self):
        self.__getAllNewEntries__()
        target = self.__makeFolder__()
        for entryId in self.articles:
            book_path = self.__downloadMobi__(entryId, target)
            self.__copyToKindle__(book_path)
        self.__saveLastUpdate__()
        #print(json.dumps(response.json(), indent=4, sort_keys=True))


if __name__ == '__main__':
    jameson = Jameson()
    jameson.makeNewspaper()
    
   



