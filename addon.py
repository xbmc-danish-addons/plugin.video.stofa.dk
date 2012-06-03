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
import urllib2
import re

import buggalo

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

class StofaWebTv(object):
    LIVE_TV_URL = 'https://webtv.stofa.dk/live_tv.php'
    STREAM_URL = 'https://webtv.stofa.dk/cmd.php?cmd=get%5Fserver&sid='

    def listTVChannels(self):
        u = urllib2.urlopen(StofaWebTv.LIVE_TV_URL)
        html = u.read()
        u.close()

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

    except Exception:
        buggalo.onExceptionRaised()
