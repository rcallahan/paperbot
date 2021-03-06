"""
Integration with http://sci-hub.org/
"""

import requests
from urlparse import urlparse
import itertools
from lxml import etree
from StringIO import StringIO
import urllib
import os

scihub_cookie = os.environ.get("SCIHUB_PASSWORD", None)
if scihub_cookie:
    shcookie = {scihub_cookie: ""}
else:
    raise Exception("need SCIHUB_PASSWORD set")


def cookie(fn):
    def _fn(*ar, **kw):
        if "cookies" not in kw: kw["cookies"] = shcookie
        elif scihub_cookie not in kw["cookies"]: kw["cookies"].update(shcookie)
        return fn(*ar, **kw)
    return _fn

def libgen(pdfstr, doi, **kwargs):
    auth_ = requests.auth.HTTPBasicAuth("genesis", "upload")
    re = requests.post("http://libgen.org/scimag/librarian/form.php", auth = auth_,
       files = {"uploadedfile":("derp.pdf", pdfstr)}, data = {"doi": doi})
    shu = etree.parse(StringIO(re.text), etree.HTMLParser())
    formp = dict(map(lambda x: (x.get("name"), x.get("value")), shu.xpath("//input[@name]")))
    re = requests.get("http://libgen.org/scimag/librarian/register.php", data = formp, auth = auth_)
    return "http://libgen.org/scimag/get.php?doi=" + urllib.quote_plus(doi)

@cookie
def scihub_dl(url, **kwargs):
    re = requests.get(url, **kwargs)
    return re.content

@cookie
def scihubber(url, **kwargs):
    """
    Takes user url and traverses sci-hub proxy system until pdf is found.
    When successful, returns either sci-hub pdfcache or libgen pdf url
    """
    a = urlparse(url)
    geturl = "http://%s.sci-hub.org/%s?%s" % (a.hostname, a.path, a.query)
    def _go(_url, _doi = None):
        re = requests.get(_url, **kwargs).text.encode("utf8")
        shu = etree.parse(StringIO(re),etree.HTMLParser())
        if not _doi:
            metas = map(lambda x:x.get("content"), shu.xpath("//meta[contains(@name,'doi')]"))
            _as = map(lambda x:urllib.unquote(x.get("href")), shu.xpath("//a[contains(@href,'doi')]"))
            maybedoi = filter(lambda x:str.find(x, "10.") != -1, metas + _as)
            if maybedoi:
                ix = str.find(maybedoi[0],"10.")
                _doi = maybedoi[0][ix:]
        just = map(lambda x:x.get("src"), shu.xpath("//frame[@name='_pdf']"))
        if just: return (just[0], _doi)
        derp = map(lambda x:x.get("src"), shu.xpath("(//frame | //iframe)[contains(@src,'pdf')]"))
        derp += map(lambda x:x.get("href"), shu.xpath("//a[contains(@href,'pdf')]"))
        it = itertools.ifilter(None,
            itertools.imap(lambda x: _go("http://%s.sci-hub.org/%s" % (a.hostname, x), _doi), derp))
        try: return it.next()
        except StopIteration: return None
    ret = _go(geturl)
    if ret: return ret
    else: return (None, None)
