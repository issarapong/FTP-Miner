from socket import timeout
from sys import stderr, exit
import urlparse
import requests
import bs4
#
#
#   Title:  filemare.py
#   Author: Daxda
#   Date:   24.02.1337
#   Desc:   Extracts ftp links of the search results from the online
#           ftp search engine filemare.com, sadly their service is very limited
#           for non-paying users, you can only extract from about 470 pages per
#           hour, thats why I've implemented the proxy (-c/--cloak) feature.


class Filemare(object):
    def __init__(self, args):
        self._args = args
        self._built_url = self._build_url()
        self._session = requests.Session()
        self._get_session()
        self._get_default_headers()
        self._collected = []

    def _filter(self, source):
        """ Searches the passed source for FTP links, adds them to the list of
            gathered links. """
        soup = bs4.BeautifulSoup(source)
        gathered_links = []
        links = soup.find_all("div", attrs={"class": "f"})
        for link in links:
            if not link:
                continue
            elif "ftp://" not in link.get_text():
                continue
            gathered_links.append(link.get_text().encode("utf8", errors="replace"))

        return gathered_links

    def _parse(self, url):
        """ Returns only the root url from the passed url. """
        url_p = urlparse.urlparse(url)
        root = url_p.scheme + "://" + url_p.netloc + "/"
        return root

    def _get_source(self, url):
        """ Gets the source code of the passed url and returns it. """
        try: # Make the get request and return the source code
            if(self._args.cloak):
                request = self._session.get(url, proxies={"http": "http://" + self._args.cloak},
                                            timeout=10)
            else:
                request = self._session.get(url, timeout=10)
        except(requests.exceptions.ConnectionError):
            stderr.write("Failed to connect to filemare.com!\n")
            stderr.flush()
            return
        except(requests.exceptions.Timeout, timeout):
            stderr.write("\nConnection timed out!\n")
            stderr.flush()
            if(self._args.cloak):
                stderr.write("Make sure your proxy is alive")
                stderr.flush()
            return
        else:
            return request.text.encode("utf8", errors="ignore")

    def _build_url(self):
        """ Stittches together the url with the search term the user defined. """
        url = "http://filemare.com/en/search/"
        url += self._args.search
        url += "/128057014/relevance/"
        # Returns http://filemare.com/en/search/<search term>/relevance/
        return url

    def _get_default_headers(self):
        """ Sets the default headers which is used for each request made. """
        self._session.headers.update({"Host": "filemare.com",
                                      "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64;"+\
                                                    " rv:26.0) Gecko/20100101 Firefox/26.0"})

    def _get_session(self):
        """ Gets the session cookie and checks if the search result yields results. """
        try:
            self._session.get(self._built_url)
        except(requests.exceptions.RequestException):
            stderr.write("Failed to establish a connection!\n")
            stderr.flush()
        else:
            return

        exit(1)

    def search(self):
        """ Initialize the search process. """
        # Set the 'start at' variable if it has been passed,
        # otherwise the 'start at' value will default to zero.
        start = 0
        if(self._args.index):
            start = self._args.index

        try: # Extract from the i-th search result page.
            for page_no, i in enumerate(range(start, 99999, 10), start):
                source = self._get_source(self._built_url + str(i) + "/10")
                if not source:
                    break
                elif("About 0 results" in source):
                    raise ValueError("Search query didn't yield any results.")
                elif("You have reached hourly free access limits." in source or
                     "You have reached daily free access limits." in source):
                    if(len(self._collected) > 1):
                        raise ValueError("\nFile limit reached, use a proxy!")
                    else:
                        raise ValueError("\rFile limit reached, use a proxy!")
                elif("<a href='https://filemare.com/en/signup'>Sign up</a>" not in source and
                     self._args.cloak):
                    raise ValueError("\rInvalid proxy configuration, we didn't reach filemare!")
                urls = self._filter(source)
                if not urls:
                    break
                if(self._args.parse):
                    for url in urls:
                        self._collected.append(self._parse(url))
                        self._collected = list(set(self._collected))
                else:
                    self._collected.extend(urls)
                stderr.write("\rGathered links: {0} - Page: {1}".format(len(self._collected), page_no))
                stderr.flush()
        except(ValueError) as e:
            stderr.write(e.message)
            stderr.flush()
        except(requests.exceptions.RequestException):
            pass

        stderr.write("\n")
        stderr.flush()

        # Distinct the search results and print them to stdout
        self._collected = list(set(self._collected))
        for link in self._collected:
            print link

