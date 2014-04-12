from socket import timeout
from sys import stderr
import urlparse
import requests
import bs4
#
#   Title:  filewatcher.py
#   Author: Daxda
#   Date:   23.02.2014
#   Desc:   Extracts ftp links of the search results from the online
#           ftp search engine filewatcher.com.
#

class Filewatcher(object):
    def __init__(self, args):
        self._args = args
        self._built_url = self._build_url()
        self._headers = self._get_default_headers()
        self.collected = []

    def _filter(self, source):
        """ Searches the passed source for FTP links, adds them to the list of
            gathered links. """
        soup = bs4.BeautifulSoup(source)
        gathered_links = []
        for element in soup.find_all("div", attrs={"class": "listing"}):
            links = element.find_all("a", href=True)
            # Add the urls to the collection
            for link in links:
                if not link:
                    continue
                elif "ftp://" not in link["href"]:
                    continue
                gathered_links.append(link["href"].encode("utf8", errors="replace"))

        return gathered_links

    def _parse(self, url):
        """ Returns only the root url from the passed url. """
        url_p = urlparse.urlparse(url)
        root = url_p.scheme + "://" + url_p.netloc + "/"
        return root

    def _get_source(self, url):
        """ Gets the source code of the passed url and returns it. """
        try: # Make the get request and return the source code
            request = requests.get(url, headers=self._headers, timeout=5)
        except(requests.exceptions.Timeout, timeout, requests.exceptions.ConnectionError):
            stderr.write("Failed to establish a connection!\n")
            stderr.flush()
        else:
            return request.text.encode("utf8", errors="ignore")

    def _build_url(self):
        """ Stittches together the url with the search term the user defined. """
        # The parameters of the URL are straight forward, here is a short list:
        #   q = query
        #   p = page
        url = "http://filewatcher.com/_/?q="
        url += self._args.search
        url += "&p="
        # returns http://www.filewatcher.com/_/?q=QUERY&q=
        return url

    def _get_default_headers(self):
        """ Returns the default headers which will be used for each request. """
        return {"Host": "www.filewatcher.com",
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64;"+\
                              " rv:26.0) Gecko/20100101 Firefox/26.0",
                "Connection": "close"}

    def search(self):
        """ Initialize the search process. """
        try: # Extract from the i-th search result page.
            for page_no, i in enumerate(range(0, 99999), 1):
                source = self._get_source(self._built_url + str(i))
                if not source:
                    break
                elif("No results." in source and len(self.collected) < 1):
                    raise ValueError("Search query didn't yield any results.")
                urls = self._filter(source)
                if not urls:
                    break
                if(self._args.parse):
                    for url in urls:
                        if url:
                            self.collected.append(self._parse(url))
                            self.collected = list(set(self.collected))
                else:
                    self.collected.extend(urls)
                stderr.write("\rGathered links: {0} - Page: {1}".format(len(self.collected), page_no))
                stderr.flush()
        except(ValueError) as e:
            stderr.write(e.message)
            stderr.flush()
        except(KeyboardInterrupt, EOFError):
            pass
        finally:
            stderr.write("\n")
            stderr.flush()



        # Distinct the search results and print them to stdout
        self.collected = set(self.collected)
        for link in self.collected:
            print link

