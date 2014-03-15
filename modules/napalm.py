import re
import threading
import Queue
import argparse
import urlparse
from sys import stderr
from base64 import b64decode as b
import requests
import bs4
#
#   Title:    napalmftpindexer.py
#   Author:   Daxda
#   Date:     23.02.2014
#   Desc:     NapalmFTPIndexer is exactly what you think it is, it indexes ftp
#             links. The bad part about their service is that the ftp links are
#             encoded and not easy to access probably to prevent the harvesting
#             of their collected data.
#
#             If you are interessted in the website and want to make a picture fo
#             yourself, visit it under the following link: www.search-ftps.com
#
#             The process looks about like this:
#
#               - Make the search query and store the search results
#               - Visit the search result's links and extract an encrypted string
#               - Decrypt said string and add it to our gathered links
#               - Repeat the above steps until the end of results is reached,
#                 then print the gathered links to stdout
#
#


class Napalm(threading.Thread):
    """ Automates the searching and extracting of search-ftps.com's encoded ftp links. """
    def __init__(self, args):
        threading.Thread.__init__(self)
        self._queue = Queue.Queue()
        self._stop_flag = False
        self._args = args
        self._session = requests.session()
        self._configure_session()
        self._gathered = set()
        self._page_no = 0
        self._lock = threading.Lock()


    def search(self):
        """ Initializes the search process. """
        try:
            self._session.get("http://www.search-ftps.com/submit")
            # First try to search for the passed keyword to make sure the search
            # yields results.
            source = self._get_source({"mode": "Search", "keyword": self._args.search})
            if("No files found." in source):
                stderr.write("Search query didn't yield any results.\n")
                stderr.flush()
                return
            elif("Keyword too generic, try something more specific." in source):
                stderr.write("Keyword too generic, try something more specific.\n")
                stderr.flush()
                return
        except(requests.exceptions.ConnectionError):
            stderr.write("Failed to establish a connection!\n")
            stderr.flush()
            return
        self._start_workers()

        # Iterate over each result page and extract the hashes which point to the
        # page on which the base64 encrypted string resides and put them in the
        # worker queue.
        for page_no, i in enumerate(range(0, 50000, 20), 1):
            self._page_no = page_no
            try: # get the i-th search result
                source = self._get_source({"mode": "Result",
                                           "keyword": self._args.search,
                                           "index": str(i)})
                if not source:
                    raise KeyboardInterrupt
                # extract the hashes, the hashes are used inside a javascript
                # file on the site to navigate from the result page to the correct
                # site which holds the encrypted string we search for.
                search_results = self._extract_search_results(source)
                if(not search_results):
                    raise KeyboardInterrupt
                # Fill the queue with our harvested hashes, the worker threads
                # will take care of the decryption of the encrypted strings which
                # reside on the sites the hashes point to.
                self._fill_queue(search_results)
                while(self._queue.qsize() > 50):
                    pass
            except(requests.exceptions.RequestException):
                stderr.write(e.message+"\n")
                stderr.flush()
                break
            except(KeyboardInterrupt, EOFError):
                self._stop_flag = True
                break

        # Wait until all items inside the queue are processed, without this
        # check the for loop (which iterates over the search result pages)
        # could end before the queue is empty and thus resulting in lost links.
        if(not self._stop_flag and self._queue.qsize() > 0):
            stderr.write("\nAsking all worker threads to finish their work...")
            stderr.flush()
            try:
                while self._queue.qsize() > 0:
                    pass
            except(KeyboardInterrupt, EOFError):
                pass

        stderr.write("\n")
        stderr.flush()

        # Process the (-p/--parse) flag, the search results will be parsed
        # to root urls instead of urls pointing to files, thus the amount of links
        # will be way less than without filtering.
        if(self._args.parse):
            filtered = set()
            for url in self._gathered:
                parse = urlparse.urlparse(url)
                url = parse.scheme + "://" +parse.netloc + "/"
                filtered.add(url)
            self._gathered = filtered

        if(not self._lock.locked()):
            with self._lock:
                for url in self._gathered:
                    print url


    def _fill_queue(self, hashes):
        """ Fills the queue with the passed hashes. """
        hashes = list(set(hashes))
        [self._queue.put(hash_) for hash_ in hashes if hash_]


    def _start_workers(self):
        """ Starts the worker threads. """
        for i in range(10):
            t = threading.Thread(target=self._work)
            t.daemon = True
            t.start()


    def _work(self):
        while self._stop_flag is False:
            # Obtain the source of the hash, and extract the encrypted string.
            # Decrypt it and add it to the results.
            stderr.write("\rGathered links: {0} - Page: {1}".format(len(self._gathered), self._page_no))
            stderr.flush()
            hash_ = self._queue.get()
            if not hash_:
                continue
            source = self._get_source({"mode": "Content", "hash": hash_})
            if not source:
                self._stop_flag = True
            # Decrypt the base64 encrypted string and add it to the result
            link = self._extract_encoded_link(source)
            if not link:
                self._stop_flag = True
            if not self._lock.locked():
                with self._lock:
                    self._gathered.add(link)
            self._queue.task_done()



    def _configure_session(self):
        """ Declares the default header information used for each request. """
        host = "www.search-ftps.com"
        user_agent = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64;"+\
                     " rv:27.0) Gecko/20100101 Firefox/27.0"
        accept = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        accept_language = "en-US,en;q=0.5"
        accept_encoding = "gzip, deflate"
        dnt = "1"
        referer = "http://www.search-ftps.com/"

        headers = {"Host": host, "User-Agent": user_agent, "Accept": accept,
                   "Accept-Language": accept_language,
                   "Accept-Encoding": accept_encoding,
                   "DNT": dnt, "Referer": referer,
                   "Connection": "close"}

        self._session.headers.update(headers)


    def _get_source(self, data):
        """ Returns the source code of the request.
            The arguments for this method are:
                url -  The url we post the passed data to.
                data - The data which will be stitched together with the correct format.
                mode - This argument tells the program what data to add to the
                       post request, possible modes are, Search, Content and Result.
        """
        if(data["mode"] == "Search"):
            data = {"action": "result",
                    "args": "k={0}&t=and&o=none&s=0".format(data["keyword"])}
        elif(data["mode"] == "Content"):
            data = {"action": "content",
                    "args": "type=f&hash={0}".format(data["hash"])}
        else:
            # The arguments for the result requests seem to be:
            #   - k = Keyword
            #   - t = Search mode, either 'and' or 'or'
            #   - o and s = Order and sort
            #   - f = Files, used to let the server know which page to display.
            #         It increments by 20.
            #
            args = "k={0}&t=and&o=none&s=0&f={1}&d=1".format(data["keyword"],
                                                             data["index"])
            data = {"action": "result", "args": args}
        # Post the configured data to the server
        req = self._session.post("http://www.search-ftps.com/", data=data)
        if(req.status_code != requests.codes.ok):
            self._stop_flag = True
            return

        return req.text.encode("utf8", errors="ignore")


    def _extract_search_results(self, source):
        """ Extracts the search results of the passed source, returns them in a list. """
        soup = bs4.BeautifulSoup(source)
        search_results = []

        # Filter out each 'p' tag and for each p tag search for 'a' tags
        # then search the a tags for it's href attribute which contains 'type':'d'.
        # The type 'd' stands for directory, we want to extract the link
        # to later visit it via the _get_source method and process the results.
        for p in soup.find_all("p", class_="filedir"):
            links = p.find_all("a", href=True)
            for link in links:
                if("'content'" in link["href"] and "'type':'f'" in link["href"]):
                    search_results.append(link["href"])

        hashes = []
        # A value of search_results looks like this:
        # javascript:go('content', {'type':'f', 'hash':'qac2gjxawqzh54ygs4wtr'})
        for js_link in search_results:
            js_link = js_link[js_link.rindex(":")+1:] # 'qac2gjxawqzh54ygs4wtr'})
            js_link = js_link.replace("'", "").replace("})", "") # qac2gjxawqzh54ygs4wtr
            hashes.append(js_link)
        return hashes


    def _extract_encoded_link(self, source):
        """ Extracts the encoded link from the passed source, the return value
            of this method is the decoded link, type string. """
        if not source:
            return
        match = re.search("ct1 = ct1_t = decodeURIComponent\(escape\(decode\('.*'", source)
        if not match:
            print("Failed to extract the encoded link")
            return
        match = match.group().replace("ct1 = ct1_t = decodeURIComponent(escape(decode(", "")
        match = match.replace("'", "")
        return b(match).strip()


