# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
from bs4 import BeautifulSoup
import logging
from logging import DEBUG

INTERACT = '../interact/'

logging.basicConfig()
logging.getLogger().setLevel(DEBUG)
logger = logging.getLogger('legacy.html_redirector')


class SubmitRedirector:
    def __init__(self, hostname=None):
        self.hostname = hostname

    def get_maxes(self, html):
        max_x = 0
        max_y = 0
        seeker = BeautifulSoup(html, features="html.parser")
        top_tbl = seeker.find('table')
        height = top_tbl.attrs.get('height','0')
        width = top_tbl.attrs.get('width','0')
        style = top_tbl.attrs.get('style',None)
        if height != '0' and 'px' in height:
            height = int(height.replace('px',''))
            if height > max_y:
                max_y = height
        if width != '0' and 'px' in width:
            width = int(width.replace('px',''))
            if width > max_x:
                max_x = width
        if style:
            style = style.replace(' ','')
            height = 0
            width = 0
            splitter = style.split(';')
            for el in splitter:
                if el.startswith('height:'):
                    try:
                        height_str = el.replace('height:','')
                        if 'px' in height_str:
                            height = int(height_str.replace('px',''))
                            if height > max_y:
                                max_y = height
                    except:
                        logger.warning("Could not find plugin html top "
                                       "table's height value in style "
                                       "attribute")
                if el.startswith('width:'):
                    try:
                        width_str = el.replace('width:','') 
                        if 'px' in width_str:
                            width = int(width_str.replace('px',''))
                            if width > max_x:
                                max_x = width
                    except:
                        logger.warning("Could not find plugin html top "
                                       "table's width value in style "
                                       "attribute")
        return max_x, max_y

    def redirect_submits(self, html: str, job_id: str):
        # Find the largest pixel width and pixel height
        max_x, max_y = self.get_maxes(html)
            
        script = BeautifulSoup("", features="html.parser").new_tag("script")
        script['type'] = 'text/javascript'
        terminator = '''function terminate() {
        navigator.sendBeacon("../terminate/", "%s");
    }
    window.addEventListener("unload", terminate);
    const all = document.getElementsByTagName("*");
    const max = all.length;
    for (let i = 0; i < max; i++) {
        const elem = all[i];
        if (elem.name === "result") {
            elem.addEventListener("click", function () {
                window.removeEventListener("unload", terminate);
            })
        }
    }
    function resize_me(){
        var max_x = Number("%s");
        var max_y = Number("%s");
        var screen_width = Number(window.screen.width);
        var screen_height = Number(window.screen.height);
        if (max_x == 0 || max_x > screen_width) {
            max_x = screen_width;
        }
        if (max_y == 0 || max_y > screen_height) {
            max_y = screen_height;
        }
        if (window.outerWidth) {
            window.resizeTo(
                max_x + (window.outerWidth - window.innerWidth) + 50, 
                max_y + (window.outerHeight - window.innerHeight) + 50
            );
        } else {
            window.resizeTo(500, 500);
            window.resizeTo(
                max_x + (500 - document.body.offsetWidth),
                max_y + (500 - document.body.offsetHeight)
            );
        }
    }
    window.onload = resize_me;
    ''' % (job_id, max_x, max_y) # TODO: Update - Currently adding 50, 150 because window height and width are not same as content's height and width 
        script.string = terminator
        hider = BeautifulSoup("", features="html.parser").new_tag("input")
        hider['type'] = "hidden"
        hider['id'] = "job_id"
        hider['name'] = "job_id"
        hider['value'] = job_id
        bs = BeautifulSoup(html, features="html.parser")
        try:
            bs.find('html').append(script)
        except:
            logger.warning("No HTML tag found in html: %s" % html)
            pass 
        for form in bs.findAll('form'):
            if form.attrs['action'] == 'submit_action':
                form.attrs['action'] = INTERACT
            form.append(hider)
        return str(bs)
