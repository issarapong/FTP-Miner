from sys import stderr
import urlparse
import requests
import bs4
#
#   Title:  mamont.py
#   Author: Daxda
#   Date:   09.03.2014
#   Desc:   This script queries the ftp search engine Mamont for a passed keyword
#           and returns all ftp links from the results.
#
#   Example URL: http://www.mmnt.ru/int/get?in=f&st=HDTV-LOL&cn=&ot=21
#   URL Parameters:
#       Name    Description
#       st      The search term the search engine is queried for.
#       cn      The region option, this can be one of the following options:
#                   ru  =   Russia
#                   us  =   USA
#                   pl  =   Poland
#                   de  =   Germany
#                   ua  =   Ukraine
#                   ca  =   Canada
#
#       ot      The page index, incremented by 21
#
#   The search engine has an option to search inside the search results, this is
#   a very helpful feature to narrow down on files we actually want, the URL
#   parameters are changed when we want to use this method like so:
#
#       Previous URL: http://www.mmnt.ru/int/get?in=f&st=HDTV-LOL
#       New URL:      http://www.mmnt.ru/int/get?in=f&qw=HDTV-LOL&st=.mkv
#
#       As you might notice, the previous URL used the parameter 'st' to search
#       for the keyword, but in the new url it will get replaced with the keyword
#       we want to search for inside the search results, thus the parameter name
#       changes from 'st' to 'qw'. The keyword we want to search for inside the
#       results will become the new 'st'.
#


class Mamont():
    def __init__(self, args):
        self._args = args
        self._links = []

    def search(self):
        """ Initializes the search process. """
        if(not self._args.location):
            self._args.location = "all"
        elif(self._args.location not in ("us", "pl", "de", "ua", "ca")):
            self._args.location = "all"

        url = self._build_url(self._args.search, self._args.location,
                              0, self._args.query)
        try:
            # First execute the query to make sure that the search yields results.
            source = self._get_source(url)
        except(requests.exceptions.RequestException):
            stderr.write("\rCouldn't establish a connection!\n")
            stderr.flush()
            return

        if not source:
            return
        if("Sorry, no results for:" in source):
            stderr.write("Search query didn't yield any results.")
            stderr.flush()
            return

        # Then we enter a for loop to iterate over each search result page
        # and extract the links.
        for page, i in enumerate(range(0, 999999, 21), 1):
            try:
                url = self._build_url(self._args.search, self._args.location,\
                                      i, self._args.query)
                source = self._get_source(url)
                if not source:
                    raise KeyboardInterrupt
                links = self._get_ftp_links(source)
                if len(links) < 1:
                    raise KeyboardInterrupt
                self._links.extend(links)
                stderr.write("\rGathered links: {0} - Page: {1}".format(len(self._links), page))
                stderr.flush()
            except(KeyboardInterrupt, requests.exceptions.Timeout):
                break

        stderr.write("\n")
        stderr.flush()
        if len(self._links) > 1:
            self._print_results()


    def _print_results(self):
        """ Filters out unwanted links and prints out the gathered URLs. """
        self._links = list(set(self._links))
        filters = (".ru", ".fr")
        filtered = []
        for link in self._links:
            try:
                for filter_ in filters:
                    if filter_ in link:
                        raise ValueError
            except ValueError:
                continue
            filtered.append(link)

        # Handle the -p/--parse flag
        if(self._args.parse):
            tmp = []
            for url in filtered:
                u = urlparse.urlparse(url)
                tmp.append("{0}://{1}/".format(u.scheme, u.netloc))
            filtered = list(set(tmp))

        for link in filtered:
            print link

    def _build_url(self, search_term, location, page_no, optional_search_term=None):
        """ Builds the url for our search query. """
        url = "http://www.mmnt.ru/int/get?in=f"

        # Add the search term and the optional search term to the query
        if(optional_search_term):
            url += "&qw={0}&st={1}".format(search_term, optional_search_term)
        else:
            url += "&st={0}".format(search_term)

        # Add the location, as long as it's not set to 'all'
        # in which case it's not needed.
        if(location != "all"):
            url += "&cn={0}".format(location)

        # Add the page number
        url += "&ot={0}".format(page_no)
        return url

    def _get_source(self, url):
        """ This function returns the source code of the passed url. """
        user_agent = "User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64;"+\
                     " rv:27.0) Gecko/20100101 Firefox/27.0"
        try:
            req = requests.get(url, headers={"User-Agent": user_agent,
                                             "Connection": "close"}, timeout=5)
        except(requests.exceptions.ConnectionError):
            stderr.write("Failed to establish a connection!\n")
            stderr.flush()
            return
        except(requests.exceptions.Timeout):
            raise requests.exceptions.Timeout

        return req.text.encode("utf8", errors="ignore")

    def _get_ftp_links(self, source):
        """ This function returns all ftp links of the passed source as a list. """
        soup = bs4.BeautifulSoup(source)
        links = soup.find_all("a", href=True)
        extracted_links = [x["href"].strip() for x in links if "ftp" in x["href"] if x]
        return extracted_links


