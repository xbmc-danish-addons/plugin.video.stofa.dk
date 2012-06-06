#
#      Copyright (C) 2012 Tommy Winther
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

import buggalo

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

class LoginFailedException(Exception):
    pass

class AccessBlockedException(Exception):
    pass

class StofaWebTv(object):
    LIVE_TV_URL = 'https://webtv.stofa.dk/live_tv.php'
    STREAM_URL = 'https://webtv.stofa.dk/cmd.php?cmd=get%5Fserver&sid='
    LOGIN_URL = 'https://webtv.stofa.dk/ajax_ms_login.php'

    COOKIE_JAR = cookielib.LWPCookieJar()

    def __init__(self):
        self.cookieFile = os.path.join(CACHE_PATH, 'cookies.lwp')
        if os.path.isfile(self.cookieFile):
            self.COOKIE_JAR.load(self.cookieFile, ignore_discard=True, ignore_expires=True)
        urllib2.install_opener(urllib2.build_opener(urllib2.HTTPCookieProcessor(self.COOKIE_JAR)))


    def handleLogin(self, html):
        if html.find('notloggedin') >= 0:
            print 'logging in'

            m = re.search('name="(msuser_[^"]+")', html)
            userParam = m.group(1)
            m = re.search('name="(mspass_[^"]+")', html)
            passParam = m.group(1)

            data = urllib.urlencode({userParam : ADDON.getSetting('username'), passParam : ADDON.getSetting('password')})
            print data

            try:
                r = urllib2.Request(StofaWebTv.LOGIN_URL)
                r.add_data(data)
                u = urllib2.urlopen(r)
                u.read()
                u.close()

                # save cookies
                self.COOKIE_JAR.save(self.cookieFile, ignore_discard=True, ignore_expires=True)

            except urllib2.HTTPError, ex:
                if ex.code == 503:
                    raise AccessBlockedException()
                else:
                    raise LoginFailedException()


    def listTVChannels(self):
        u = urllib2.urlopen(StofaWebTv.LIVE_TV_URL)
        html = u.read()
        u.close()

        self.handleLogin(html)

        for m in re.finditer('channel_change_live_tv\(([0-9]+),.*?<img src="([^"]+)".*?<span>([^<]+)<', html, re.DOTALL):
            id = m.group(1)
            image = m.group(2)
            title = m.group(3)

            item = xbmcgui.ListItem(title, iconImage = image)
            item.setProperty('IsPlayable', 'true')
            url = PATH + '?channel=' + id
            xbmcplugin.addDirectoryItem(HANDLE, url, item)

        xbmcplugin.endOfDirectory(HANDLE, True)

    def playLiveTVChannel(self, channelId):
        u = urllib2.urlopen(StofaWebTv.STREAM_URL + channelId)
        params_string = u.read()
        u.close()

        params = urlparse.parse_qs(params_string)
        url = params['servers'][0] + params['filename'][0] + ' live=1 swfUrl=http://webtv.stofa.dk/videoplayer.swf swfVfy=true'
        print url

        item = xbmcgui.ListItem(path = url)
        xbmcplugin.setResolvedUrl(HANDLE, True, item)

    def loginFailed(self):
        heading = buggalo.getRandomHeading()
        xbmcgui.Dialog().ok(heading, ADDON.getLocalizedString(200), ADDON.getLocalizedString(201))

    def accessBlocked(self):
        heading = buggalo.getRandomHeading()
        xbmcgui.Dialog().ok(heading, ADDON.getLocalizedString(210))

if __name__ == '__main__':
    ADDON = xbmcaddon.Addon()
    PATH = sys.argv[0]
    HANDLE = int(sys.argv[1])
    PARAMS = urlparse.parse_qs(sys.argv[2][1:])

    ICON = os.path.join(ADDON.getAddonInfo('path'), 'icon.png')

    CACHE_PATH = xbmc.translatePath(ADDON.getAddonInfo("Profile"))
    if not os.path.exists(CACHE_PATH):
        os.makedirs(CACHE_PATH)

    stv = StofaWebTv()
    try:
        if PARAMS.has_key('channel'):
            stv.playLiveTVChannel(PARAMS['channel'][0])
        else:
            stv.listTVChannels()

    except LoginFailedException:
        stv.loginFailed()
    except AccessBlockedException:
        stv.accessBlocked()
    except Exception:
        buggalo.onExceptionRaised()
