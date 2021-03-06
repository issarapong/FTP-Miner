from sys import stderr
import argparse
import urlparse
from modules.napalm import Napalm
from modules.mamont import Mamont
from modules.filewatcher import Filewatcher
from modules.filemare import Filemare
#
#   Title:    FTP-Miner.py
#   Author:   Daxda
#   Date:     10.03.1337
#   Desc:     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# This script wraps multiple FTP search engine scraping scripts, currently the
# following search engines are supported:
#
#   -   Napalm FTP indexer (http://www.search-ftps.com/)
#   -   Mamont (http://www.mmnt.ru/)
#   -   FileWatcher (http://www.filewatcher.com/)
#   -   FileMare (http://filemare.com/)
#
#
# FileMare is a very limited service and requires you to buy "premium" access
# for their resources when you trigger a certain limit, about 470 pages can be
# extracted per hour, thus I've implemented a proxy feature to bypass the
# restrictions. Currently only HTTP proxies are allowed, pass them with the
# -c/--cloak flag when the service limitation was reached. The cloak flag value
# must not begin with 'http://' or any other scheme, only specify a valid
# (and working) proxy IP:Port combination, for example: 192.168.1.1:8080.
#
#
# Arguments for the single scripts:
#
#   Napalm:  -s (search term) -p (parse)
#   Mamont:  -s (search term) -p (parse) -q (optional keyword) -l (location)
#   FMare:   -s (search term) -p (parse) -i (start at index)   -c (proxy)
#   FWatch:  -s (search term) -p (parse)
#
#
#   Special cases for the following scripts:
#
#   Mamont: -q/--query is an optional search term used to search inside the search
#           results.
#
#           -l/--location is also optional, it is used to limit the search engine
#           to server locations, by default this is set to 'all'. Available options
#           are either "us", "pl", "de", "ua", "ca" or "all".
#
#   FMware: -i/--index is an optional integer value, it can be set to a certain
#           number to start from this search result page, it has been implemented
#           to be able to continue a search which has been cut off due to the
#           'free user' limitation of filemare.
#
#           -c/--cloak is optional to use an http proxy while searching, this has
#           been implemented to bypass the 'free user' limit of filemare. Only
#           define the ip and port in this format: 192.168.1.1:8080, do not use
#           leading schemes like http:// or anything the like!
#
#
#
# Custom hoster scraping, you can specify from which hosters you want to extract results,
# set one or more flags from the following list:
#
#   -fw / --filewatcher
#   -ma / --mamont
#   -fm / --filemare
#   -na / --napalm
#


def main(args):
    napalm = {"name": "Napalm", "func": Napalm, "flag_set": args.napalm}
    mamont = {"name": "Mamont", "func": Mamont, "flag_set": args.mamont}
    filewatcher = {"name": "FileWatcher", "func": Filewatcher, "flag_set": args.filewatcher}
    filemare = {"name": "FileMare", "func": Filemare, "flag_set": args.filemare}

    custom_functions = []
    for routine in (napalm, mamont, filewatcher, filemare):
        if(routine["flag_set"]):
            custom_functions.append(routine)

    # Process -fw, -fm, -ma, -na flags if they are set
    if(len(custom_functions) > 0):
        functions = custom_functions
    else:
        functions = (napalm, mamont, filewatcher, filemare)

    # Start the scraping process
    for function in functions:
        try:
            stderr.write("\t-=[ {0} ]=-\n".format(function["name"]))
            stderr.flush()
            function["func"](args).search()
        except(KeyboardInterrupt, EOFError):
            continue

    stderr.write("\n")
    stderr.flush()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", required=True,
                        help="Keyword used to search for various ftp search engines.")
    parser.add_argument("-q", "--query", required=False)
    parser.add_argument("-p", "--parse", required=False,
                        help="Whether or not to parse the results, thus parsing all urls"+\
                             " to root urls to get a more compact list.",
                        action="store_true")
    parser.add_argument("-l", "--location", required=False)
    parser.add_argument("-c", "--cloak", required=False)
    parser.add_argument("-i", "--index", required=False)
    parser.add_argument("-fw", "--filewatcher", action="store_true",
                       help="Search on filewatcher.")
    parser.add_argument("-fm", "--filemare", action="store_true",
                       help="Search on filemare.")
    parser.add_argument("-ma", "--mamont", action="store_true",
                       help="Search on Mamont.")
    parser.add_argument("-na", "--napalm", action="store_true",
                       help="Search on Napalm FTP Indexer.")

    args = parser.parse_args()

    main(args)
