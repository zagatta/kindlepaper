import requests
import json
import os
from lib.auth import Auth
import datetime
import re
from shutil import copyfile
import getpass
import argparse
from PyPDF2 import PdfFileMerger
import subprocess


class Constants:
    DATE_FORMAT_WALLABAG = '%Y-%m-%dT%H:%M:%S+%f'
    DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
    DATE_FORMAT_KINDLE = '%Y-%m-%dT%H_%M_%S'
    NEWLINE = "\n"
    LAST_UDATE_FILE = ".last_update"
    URL_ENTRIES_KINDLE = "https://app.wallabag.it/api/entries.json?tags=kindle"
    URL_EXPORT = "https://app.wallabag.it/api/entries/{}/export.{}"
    DOWNLOAD_FOLDER = "/.download"
    KINDLE_PATH = "/media/{}/Kindle/documents/".format(getpass.getuser())
    KINDLE_CONVERT_FOLDER = "/kindle"
    KINDLE_CONVERT_CMD = "ebook-convert {} {}  --output-profile 'kindle' --base-font-size {} | grep 'error'"
    CMD_GENERATE_TOC = "pdftocgen {}  < recipe.toml > {}"
    CMD_WRITE_TOC = "pdftocio -o {} {} < {}"
    

class Jameson:
    def __init__(self, docFormat, kindle , oldArticles, fontSize):
        self.auth = Auth()
        self.myToken = self.auth.getAccessToken()
        self.last_update = datetime.datetime(1994, 2, 1)
        self.articles = []
        self.head = {'Authorization': 'token {}'.format(self.myToken)}
        self.path = os.path.dirname(os.path.abspath( __file__ ))
        self.now = datetime.datetime.now()
        self.format = docFormat
        self.kindle = kindle
        self.oldArticles = oldArticles
        self.fontSize = fontSize
    
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
            if creation_date > self.last_update or self.oldArticles:
                self.articles.append(item["id"])
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

    def __downloadArticle__(self, entryId, target):
        url = Constants.URL_EXPORT.format(entryId, self.format)
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
        os.mkdir(newspaper_folder_path + Constants.KINDLE_CONVERT_FOLDER)
        return newspaper_folder_path

    def __copyToKindle__(self, src):
        print("src:", src)
        filename = self.__getFilnameFromFilepath__(src)
        print("filename", filename)
        copyfile(src, Constants.KINDLE_PATH + filename)

    def __convert2Kindle__(self, src):
        filename = self.__getFilnameFromFilepath__(src)
        filename = self.__removeFileEnding__(filename)
        #add pdf as file ending
        filename += "pdf"
        srcFolder = src.replace(filename, "")
        destFolder = srcFolder + Constants.KINDLE_CONVERT_FOLDER
        dest = destFolder + "/" + filename
        cmd = Constants.KINDLE_CONVERT_CMD.format(src, dest, self.fontSize)
        self.__runCMD__(cmd)
        return dest

    def __mergePDF__(self, downloadFolder):
        folder = downloadFolder
        pdfs = os.listdir(folder)
        merger = PdfFileMerger()
        for pdf in pdfs:
            if ".pdf" in pdf:
                pdf_path = folder + "/" + pdf
                merger.append(pdf_path)
        title = self.now.strftime(Constants.DATE_FORMAT_KINDLE) + "_jonesnews.pdf"
        result_path = folder + "/" + title
        merger.write(result_path)
        merger.close()
        print(result_path)
        return result_path

    def __getHeadlines__(self, file, folder):
        toc = folder + "/toc"
        cmd = Constants.CMD_GENERATE_TOC.format(file, toc)
        self.__runCMD__(cmd)
        return toc

    def __filterDuplicateHeadlines__(self, tocFile):
        tocFileCleaned = tocFile + "_cleaned"
        f = open(tocFile, "r")
        f2 = open(tocFileCleaned, "a")
        for (i,line) in enumerate(f):
            if i % 2 == 1:
                f2.write(line)
        f.close()
        f2.close()
        return tocFileCleaned
    
    def __writeTocToPDF__(self, pdf, tocFile):
        output = self.__removeFileEnding__(pdf, True) + "_toc.pdf"
        cmd = Constants.CMD_WRITE_TOC.format(output, pdf, tocFile)
        self.__runCMD__(cmd) 
        return output

    def __getFilnameFromFilepath__(self, src):
        #get filename from src file path
        return src.split("/")[-1]
    
    def __removeFileEnding__(self, src, removeDot=False):
        #remove file ending
        text = src.replace(src.split(".")[-1], "")
        if removeDot:
            text = text[0:-1]
        return text

    def __runCMD__(self, cmd):
        print("running command:", cmd)
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        process.wait()
        stdout, stderr = process.communicate()
        print("stdout", stdout)
        print("stderr", stderr)

        



    def makeNewspaper(self):
        self.__getAllNewEntries__()
        downloadTarget = self.__makeFolder__()
        for entryId in self.articles:
            #Download all articles
            bookPath = self.__downloadArticle__(entryId, downloadTarget)
            #convert with calibre to better fit kindle display
            #TODO: change to only merge for kindle after creating pdf
            #converted_bookPath = self.__convert2Kindle__(bookPath)
        #merge all converted pdfs into one document
        mergedPDFPath = self.__mergePDF__(downloadTarget)
        #create table of contents
        tocFile = self.__getHeadlines__(mergedPDFPath, downloadTarget)
        #clean table of contents
        tocFile = self.__filterDuplicateHeadlines__(tocFile)
        #wirte table of contents to the pdf
        mergedPDFPath = self.__writeTocToPDF__(mergedPDFPath, tocFile)
        kindlePDF = self.__convert2Kindle__(mergedPDFPath)
        if self.kindle:
            self.__copyToKindle__(kindlePDF)
        self.__saveLastUpdate__()
        #print(json.dumps(response.json(), indent=4, sort_keys=True))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--format", type=str, default="pdf", help="Which format to donwload from wallabag in? Standard is pdf")
    ap.add_argument("-s", "--font_size", type=int, default=18, help="font-size")
    ap.add_argument("-k", "--kindle", dest='kindle', action='store_true')
    ap.set_defaults(kindle=False)
    ap.add_argument("-o", "--old_articles", dest='old_articles', action='store_true', help="Do you only want to download NEW articles?")
    ap.set_defaults(old_articles=False)

    args = vars(ap.parse_args())

    

    print("chosen format: ", args["format"])
    print("copy to kindle: ", args["kindle"])
    print("also download old articles: ", args["old_articles"])
    jameson = Jameson(args["format"], args["kindle"], args["old_articles"], args["font_size"])
    jameson.makeNewspaper()
    
   



