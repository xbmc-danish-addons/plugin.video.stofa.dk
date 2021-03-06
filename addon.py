#
#      Copyright (C) 2014 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
import os
import sys
import urlparse
import urllib
import urllib2
import cookielib
import re
from htmlentitydefs import name2codepoint
import simplejson
import buggalo

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin


class StofaWebTv(object):
    LIVE_TV_URL = 'http://webtv.stofa.dk/'
    STREAM_URL = 'http://webtv.stofa.dk/cmd.php?cmd=get_stream_url&sid=%s&datatype=json&segsupport=true&manufacturer=webtv&model=web&uid='
    LOGIN_URL = 'http://webtv.stofa.dk/includes/ajax/login.php?cmd=login_web&'
    CHANNELS_URL = 'http://webtv.stofa.dk/includes/ajax/live.php?cmd=get_sids&inclcn=true'

    COOKIE_JAR = cookielib.LWPCookieJar()

    def __init__(self):
        self.cookieFile = os.path.join(CACHE_PATH, 'cookies.lwp')
        if os.path.isfile(self.cookieFile):
            self.COOKIE_JAR.load(self.cookieFile, ignore_discard=True, ignore_expires=True)
        urllib2.install_opener(urllib2.build_opener(urllib2.HTTPCookieProcessor(self.COOKIE_JAR)))

    def handleLogin(self, html):
        if html.find('<div id="topLogin">Login</div>') >= 0:
            u = urllib2.urlopen('http://webtv.stofa.dk/includes/popup/login.php')
            html = u.read()
            u.close()

            m = re.search('name="(msuser_[^"]+)"', html)
            userParam = m.group(1)
            m = re.search('name="(mspass_[^"]+)"', html)
            passParam = m.group(1)

            data = urllib.urlencode({userParam : ADDON.getSetting('username'), passParam : ADDON.getSetting('password')})

            url = StofaWebTv.LOGIN_URL + data
            u = urllib2.urlopen(url)
            json = simplejson.loads(u.read())
            u.close()

            if json['status'] == 'ok':
                # save cookies
                self.COOKIE_JAR.save(self.cookieFile, ignore_discard=True, ignore_expires=True)
            else:
                self.loginFailed()

    def listTVChannels(self):
        u = urllib2.urlopen(StofaWebTv.LIVE_TV_URL)
        html = u.read()
        u.close()

        self.handleLogin(html)

        u = urllib2.urlopen(StofaWebTv.CHANNELS_URL)
        json = simplejson.loads(u.read())
        u.close()

        for sid in json['sids']:
            name = sid['name']

            if ADDON.getSetting('hide.drm.channels') == 'true' and 'DRM_live' in sid and sid['DRM_live'] == '1':
                continue

            item = xbmcgui.ListItem(name, iconImage=ICON, thumbnailImage=ICON)
            item.setProperty('IsPlayable', 'true')
            item.setProperty('Fanart_Image', FANART)
            url = PATH + '?channel=' + str(sid['channel_id'])
            xbmcplugin.addDirectoryItem(HANDLE, url, item)

        xbmcplugin.endOfDirectory(HANDLE, True)

    def playLiveTVChannel(self, channelId):
        u = urllib2.urlopen(StofaWebTv.STREAM_URL % channelId)
        json_string = u.read()
        u.close()

        json = simplejson.loads(json_string)
        try:
            # check for errors from server
            print json
            self.showError(json['streams'][0]['info'])
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
            return
        except KeyError:
            pass

        u = urllib2.urlopen(json['streams']['stream'])
        u.read()
        u.close()
        # Get the location of the HTTP redirect and pass that to XBMC
        url = u.geturl()

        item = xbmcgui.ListItem(path = url)
        xbmcplugin.setResolvedUrl(HANDLE, True, item)

    def loginFailed(self):
        heading = buggalo.getRandomHeading()
        xbmcgui.Dialog().ok(heading, ADDON.getLocalizedString(200), ADDON.getLocalizedString(201))

    def showError(self, message):
        heading = buggalo.getRandomHeading()
        xbmcgui.Dialog().ok(heading, ADDON.getLocalizedString(202), ADDON.getLocalizedString(203), message)

    def decodeHtmlEntities(self, string):
        """Decodes the HTML entities found in the string and returns the modified string.

        Both decimal (&#000;) and hexadecimal (&x00;) are supported as well as HTML entities,
        such as &aelig;

        Keyword arguments:
        string -- the string with HTML entities

        """
        if type(string) not in [str, unicode]:
            return string

        def substituteEntity(match):
            ent = match.group(3)
            if match.group(1) == "#":
                # decoding by number
                if match.group(2) == '':
                    # number is in decimal
                    return unichr(int(ent))
            elif match.group(2) == 'x':
                # number is in hex
                return unichr(int('0x'+ent, 16))
            else:
                # they were using a name
                cp = name2codepoint.get(ent)
                if cp:
                    return unichr(cp)
                else:
                    return match.group()

        entity_re = re.compile(r'&(#?)(x?)(\w+);')
        return entity_re.subn(substituteEntity, string)[0]


if __name__ == '__main__':
    ADDON = xbmcaddon.Addon()
    PATH = sys.argv[0]
    HANDLE = int(sys.argv[1])
    PARAMS = urlparse.parse_qs(sys.argv[2][1:])

    ICON = os.path.join(ADDON.getAddonInfo('path'), 'icon.png')
    FANART = os.path.join(ADDON.getAddonInfo('path'), 'fanart.jpg')

    CACHE_PATH = xbmc.translatePath(ADDON.getAddonInfo("Profile"))
    if not os.path.exists(CACHE_PATH):
        os.makedirs(CACHE_PATH)

    buggalo.SUBMIT_URL = 'http://tommy.winther.nu/exception/submit.php'
    stv = StofaWebTv()
    try:
        if PARAMS.has_key('channel'):
            stv.playLiveTVChannel(PARAMS['channel'][0])
        else:
            stv.listTVChannels()

    except Exception:
        buggalo.onExceptionRaised()
