# -*- coding: utf-8 -*-

# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING. If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html

import os
import re
import sys
import cookielib
import urllib
import urllib2
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import xbmcvfs
import json

import functools
import ssl

old_init = ssl.SSLSocket.__init__

@functools.wraps(old_init)
def ubuntu_openssl_bug_965371(self, *args, **kwargs):
  kwargs['ssl_version'] = ssl.PROTOCOL_TLSv1
  old_init(self, *args, **kwargs)

ssl.SSLSocket.__init__ = ubuntu_openssl_bug_965371

from urllib import quote_plus, unquote_plus
from traceback import print_exc

try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs
from urlparse import urlparse

from DataManager import DataManager
dataManager = DataManager()

ADDON = xbmcaddon.Addon(id='plugin.video.illicoweb')
ADDON_NAME = ADDON.getAddonInfo( "name" )
ADDON_VERSION = "2.0"
ADDON_CACHE = xbmc.translatePath( ADDON.getAddonInfo( "profile" ).decode('utf-8') )
ADDON_PATH = xbmc.translatePath( ADDON.getAddonInfo( "path" ).decode('utf-8') )

COOKIE = os.path.join(ADDON_CACHE, 'cookie')
COOKIE_JAR = cookielib.LWPCookieJar(COOKIE)

ICON = os.path.join(ADDON_PATH, 'icon.png')
FAVOURITES_XML = os.path.join( ADDON_CACHE, "favourites.xml" )

USERNAME = ADDON.getSetting( "username" )
PASSWORD = ADDON.getSetting( "password" )
DEBUG = ADDON.getSetting('debug')

LANGXBMC = xbmc.getLocalizedString
LANGUAGE = ADDON.getLocalizedString

def addon_log(string):
    if DEBUG == 'true':
        if isinstance(string, unicode):
            string = string.encode('utf-8')
        xbmc.log("[Illicoweb-%s]: %s" %(ADDON_VERSION, string))

def login():
        addon_log('Login to get cookies!')

        if not USERNAME or not PASSWORD:
            xbmcgui.Dialog().ok(ADDON_NAME, LANGUAGE(30004))
            xbmc.executebuiltin("Addon.OpenSettings(plugin.video.illicoweb)")
            exit(0)

        # Set CookieProcessor
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(COOKIE_JAR))
        urllib2.install_opener(opener)
        # Get the cookie first
        url = 'http://illicoweb.videotron.com/accueil'
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0'}

        # Make request and save session cookies
        req = urllib2.Request(url,None,headers)
        response = urllib2.urlopen(req)
        data = response.read()
        COOKIE_JAR.save(COOKIE, ignore_discard=True, ignore_expires=False)
        response.close()


        # now authenticate
        url = 'https://illicoweb.videotron.com/illicoservice/authenticate?localLang=fr'
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil',
                   'X-Requested-With' : 'XMLHttpRequest',
                   'Content-Type' : 'application/json'}

        values = {}
        login = {
             'userId' : USERNAME,
			 'password' : PASSWORD
        }
        req = urllib2.Request(url,urllib.urlencode(values),headers)
        response = urllib2.urlopen(req, json.dumps(login))
        data = response.read()

        COOKIE_JAR.load(COOKIE, ignore_discard=False, ignore_expires=False)
        cookies = {}
        addon_log('These are the cookies we have received from authenticate.do:')
        for i in COOKIE_JAR:
            cookies[i.name] = i.value
            addon_log('%s: %s' %(i.name, i.value))

        if cookies.has_key('iPlanetDirectoryPro'):
            return True
        else:
            return False
        
def getRequest(url, data=None, headers=None):
    data, result = getRequestedUrl(url, data, headers)
    if result == 302:
        addon_log("Unauthenticated.  Logging in.")
        COOKIE_JAR.clear()
        COOKIE_JAR.save(COOKIE, ignore_discard=True, ignore_expires=False)

        login()
        data = getRequestedUrl(url, data, headers)
    
    if data == None:
        addon_log('No response from server')
        
    return data
        
def getRequestedUrl(url, data=None, headers=None):
    if not xbmcvfs.exists(COOKIE):
        login()

    if headers is None:
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'http://illicoweb.videotron.com',
                   'Accept' : 'application/json, text/plain, */*;version=1.1'}
    try:
        COOKIE_JAR.load(COOKIE, ignore_discard=True, ignore_expires=False)
    except:
        login()

    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(COOKIE_JAR))
    urllib2.install_opener(opener)
    try:
        req = urllib2.Request(url,data,headers)
        response = urllib2.urlopen(req)
        data = response.read()
        COOKIE_JAR.save(COOKIE, ignore_discard=True, ignore_expires=False)
        response.close()
        addon_log("getRequest : %s" %url)
        return (data, 200)
    except urllib2.URLError, e:
        reason = None
        addon_log('We failed to open "%s".' %url)
        if hasattr(e, 'reason'):
            reason = str(e.reason)
            addon_log('We failed to reach a server.')
            addon_log('Reason: '+ reason)
        if hasattr(e, 'code'):
            reason = str(e.code)
            addon_log( 'We failed with error code - %s.' % reason )
            if (e.code == 401):
                xbmcgui.Dialog().ok(ADDON_NAME, LANGUAGE(30004))
                xbmc.executebuiltin("Addon.OpenSettings(plugin.video.illicoweb)")
                exit(0)
            return (None, e.code)

if re.search( '(GetCarrousel|"carrousel")', sys.argv[ 2 ] ):
    from GuiView import GuiView as viewtype
else:
    from PluginView import PluginView as viewtype 

class Main( viewtype ):
    def __init__( self ):
        viewtype.__init__( self )
        self.args = Info()

        
        if self.args.isempty():
            login()
            self._add_directory_root()

        elif self.args.addtofavourites or self.args.removefromfavourites:
            #turn dict back into url, decode it and format it in xml
            f = self.args.addtofavourites or self.args.removefromfavourites
            addon_log(f.decode('utf-8'))
            f = parse_qs(urlparse('?' + f.replace( ", ", "&" ).replace('"','%22').replace('+','%2B')).query)

            remove = True if self.args.removefromfavourites else False
            self._addToFavourites(unquote_plus(f['label'][0]), f['category'][0], f['url'][0], remove)
                
        
        elif self.args.favoris:
            try:
                self._add_directory_favourites()                    
            except:
                print_exc
                    
        elif self.args.live:
            self._playLive(unquote_plus(self.args.live).replace( " ", "+" ))

        elif self.args.episode:
            self._checkCookies()
            self._playEpisode(unquote_plus(self.args.episode).replace( " ", "+" ))

        elif self.args.channel:
            url = unquote_plus(self.args.channel).replace( " ", "+" )

            shows, fanart, livelist = self._getShows(url)
            
            listitems = []
            if 'channels' in shows:
                for channel in shows['channels']:
                    self._addChannelToStingray(channel, listitems, fanart)
            else:
                for i in shows:
                    if 'submenus' in i:
                        for show in i['submenus']:
                            self._addShowToChannel(show, listitems, fanart)
                    else:
                        self._addShowToChannel(i, listitems, fanart)
            
            if listitems:
                # Sort list by ListItem Label
                listitems = self.natural_sort(listitems, False) 

            if len(listitems) == 0:
                live = livelist[0][0]
                self._playLive(live[live.find('"'):].replace('"',""))
                return
                
            listitems = livelist + listitems
            addon_log("Adding Shows to Channel")
            OK = self._add_directory_items( listitems )
            self._set_content( OK, "episodes", False )

        elif self.args.show:
            try:
                OK = False
                listitems = self._getSeasons(unquote_plus(self.args.show).replace( " ", "+" ))
            
                if listitems:
                    from operator import itemgetter
                    listitems = self.natural_sort(listitems, False)
                    OK = self._add_directory_items( listitems )
                self._set_content( OK, "episodes", False )
            except:
                print_exc()
        elif self.args.season:
            url = unquote_plus(self.args.season).replace( " ", "+" )
            season = url[url.rfind(',') + 1:]
            url = url[:url.rfind(',')]

            data = self._getShowJSON(url)
            self._addEpisodesToSeason(data, season)

    def _addToFavourites(self, label, category, url, remove=False):
        if os.path.exists( FAVOURITES_XML ):
            favourites = open( FAVOURITES_XML, "r" ).read()
        else:
            favourites = u'<favourites>\n</favourites>\n'
        if isinstance(favourites, str):
            favourites = favourites.decode('utf-8')
        
        label = label.replace("/plus/","+")
        
        favourite = ('<favourite label="%s" category="%s" url="%s" />' % (label.replace(" -- En Direct --", " - Live").replace(" -- Live --", "-Live"), category, url))
        addon_log("----" + favourite)
        if remove or favourite not in favourites:
            if remove:
                addon_log('Removing %s from favourites' % favourite)
                favourites = favourites.replace( '  %s\n' % favourite, '' )
                refresh = True
            else:
                favourites = favourites.replace( '</favourites>', '  %s\n</favourites>' % (favourite))
                refresh = False
            if isinstance(favourites, unicode):
                favourites = favourites.encode('utf-8')
            file( FAVOURITES_XML, "w" ).write( favourites )
            if refresh:
                if favourites == '<favourites>\n</favourites>\n':
                    try: os.remove( FAVOURITES_XML )
                    except: pass
                    xbmc.executebuiltin( 'Action(ParentDir)' )
                    xbmc.sleep( 1000 )
                WINDOW.setProperty("force_data_reload", "true")
                xbmc.executebuiltin( 'Container.Refresh' )    
            
    def _addChannel(self, listitems, i, url):
        OK = False                
        try:
            label = i['name']
            episodeUrl = i['link']['uri']

            uri = sys.argv[ 0 ]
            #item = ( label, '', 'https://static-illicoweb.videotron.com/media/public/images/providers_logos/common/' + i['image'], 'https://static-illicoweb.videotron.com/media/public/images/providers_logos/common/' + i['image'])
            item = ( label, '', 'https://static-illicoweb.videotron.com/media/public/images/providers_logos/common/' + i['image'], 'https://static-illicoweb.videotron.com/media/public/images/providers_logos/common/' + i['image'])
            url = url %( uri, episodeUrl  )
            
            infoLabels = {
                "tvshowtitle": label,
                "title":       label,
                #"genre":       genreTitle,
                "plot":        i[ 'description' ] or ""
                #"season":      int(season) or -1
                #"episode":     episode[ "EpisodeNumber" ] or -1,
                #"year":        int( episode[ "Year" ] or "0" ),
                #"Aired":       episode[ "AirDateLongString" ] or "",
                #"mpaa":        episode[ "Rating" ] or "",
                #"duration":    episode[ "LengthString" ] or "",
                #"studio":      episode[ "Copyright" ] or "",
                #"castandrole": scraper.setCastAndRole( episode ) or [],
                #"writer":      episode[ "PeopleWriter" ] or episode[ "PeopleAuthor" ] or "",
                #"director":    episode[ "PeopleDirector" ] or "",
            }
            
            
            listitem = xbmcgui.ListItem( *item )
            listitem.setInfo( "Video", infoLabels )

            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/media/public/images/providers_logos/common/' + i['image'] )
            listitem.setProperty( "fanart_image", 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/custom/presse1.jpg') #'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/channels/' + ep['largeLogo'])
            
            if '?live=' in url:
                category = 'live'
            else: category = 'channel'
            self._add_context_menu( label, episodeUrl, category, listitem )
            listitems.append( ( url, listitem, True ) )
        except:
            print_exc()


        
    def _addLiveChannel(self, listitems, i, url, fanart):
        OK = False                
        try:
            label = LANGUAGE(30003) #'-- En Direct / Live TV --'
            episodeUrl = i['orderURI'] 
            uri = sys.argv[ 0 ]
            item = ( label, '', 'https://static-illicoweb.videotron.com/media/public/images/providers_logos/common/' + i['image'])
            url = url %( uri, episodeUrl  )
            
            listitem = xbmcgui.ListItem( *item )
            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/media/public/images/providers_logos/common/' + i['image'] )
            listitem.setProperty( "fanart_image", fanart)
            
            self._add_context_menu( i['name'] + ' - Live', episodeUrl, 'live', listitem )
            listitems.append( ( url, listitem, True ) )
        except:
            print_exc()
            
    def _addEpisodesToSeason(self, data, season):
        addon_log("-- Adding Episodes to Season")
        OK = False
        listitems = self._getEpisodes(data, season)

        if listitems:
            listitems = self.natural_sort(listitems, True)
            OK = self._add_directory_items( listitems )
        self._set_content( OK, "episodes", False )
    
    
    def _addEpisode(self, ep, listitems):
        addon_log("-- Adding Episode")
        label = ep['title']
        if not 'orderURI' in ep:
            return
        seasonUrl = ep['orderURI']
        OK = False
        try:
            uri = sys.argv[ 0 ]
            item = ( label, '', "DefaultTVShows.png", 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/player/'  + ep['image']) #'DefaultAddonSubtitles.png')
            url = '%s?episode="%s"' %( uri, unquote_plus(seasonUrl.replace( " ", "+" ) ) )
            
            
            infoLabels = {
                "tvshowtitle": label,
                "title":       label,
                #"genre":       genreTitle,
                "plot":        ep[ 'description' ] or "",
                "season":      int(ep['seasonNo'] if 'seasonNo' in ep else "-1") or -1,
                "episode":     int(ep[ 'episodeNo' ] if 'episodeNo' in ep else "-1") or -1,
                "year":        int( ep[ "released" ] or "0" ),
                #"Aired":       episode[ "AirDateLongString" ] or "",
                "mpaa":        ep[ 'rating' ] or "",
                "duration":    str(ep[ 'lengthInMinutes' ]) or "",
                #"studio":      episode[ "Copyright" ] or "",
                #"castandrole": scraper.setCastAndRole( episode ) or [],
                #"writer":      episode[ "PeopleWriter" ] or episode[ "PeopleAuthor" ] or "",
                #"director":    episode[ "PeopleDirector" ] or "",
            }
            
            listitem = xbmcgui.ListItem( *item )
            listitem.setInfo( "Video", infoLabels )
            
            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/player/' + ep['image'] )
            listitem.setProperty( "fanart_image", xbmc.getInfoLabel( "ListItem.Property(fanart_image)" )) #'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/thumb/' + ep['image'])
            
            listitem.setProperty( "IsPlayable", "true" )
            
            self._add_context_menu(  label, unquote_plus(seasonUrl.replace( " ", "+" ) ), 'episode', listitem )
            listitems.append( ( url, listitem, False ) )
        except:
            print_exc()

    def _addSeasonsToShow(self, i, listitems, title=False):
        addon_log("-- Adding Seasons to Show")
        seasonNo = i['seasonNo'] if 'seasonNo' in i else 0
        label = i['title'] + " - " + (LANGUAGE(30018) + " " + str(seasonNo)) if i['objectType'] == "SEASON" else i['title'] 

        if title and not i['title'] in label: label = '%s - %s' % (i['title'], label)
        seasonUrl = i['link']['uri'] + ',' + str(seasonNo)

        OK = False
        try:
            uri = sys.argv[ 0 ]
            thumb = 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/player/' + i['image']
            item = ( label,     '',  thumb)
            url = '%s?season="%s"' %( uri, seasonUrl )
            
            listitem = xbmcgui.ListItem( *item )
            description = ''
            if 'description' in i: description = i['description']
            infoLabels = {
                "tvshowtitle": label,
                "title":       label,
                "genre":       i['genre'] if 'genre' in i else '',
                "year":        int( i['released'] ),
                #"tagline":     ( STRING_FOR_ALL, "" )[ bool( GeoTargeting ) ],
                "duration":    i['lengthInMinutes'] if 'lengthInMinutes' in i else '0',
                #"episode":     NombreEpisodes,
                "season":      int(seasonNo) or -1,
                "plot":        description,
                #"premiered":   emission.get( "premiered" ) or "",
                }
            
            listitem.setInfo( "Video", infoLabels )

            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/thumb/' + i['image'] )
            listitem.setProperty( "fanart_image", xbmc.getInfoLabel( "ListItem.Property(fanart_image)" )) #'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/thumb/' + i['image'])

            self._add_context_menu( i['title'], seasonUrl, 'season', listitem )
            listitems.append( ( url, listitem, True ) )
        except:
            print_exc()
    
    def _addChannelToStingray(self, channel, listitems, fanart, url=None):
        addon_log("-- Adding Channel to Stingray")
        label = channel['name']
        OK = False
        try:
            channelUrl = url or channel['orderURI']
            uri = sys.argv[ 0 ]
            item = ( label, '' , 'https://static-illicoweb.videotron.com/media/public/images/providers_logos/common/' + channel['image'])
            url = '%s?live="%s"' %( uri, channelUrl  )
            
            infoLabels = {
                "title":       label,
                "artist":      label,
                "album":       label
            }
            
            listitem = xbmcgui.ListItem( *item )
            listitem.setInfo( "Music", infoLabels )

            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/media/public/images/providers_logos/common/' + channel['image'] )
            listitem.setProperty( "fanart_image", fanart)

            self._add_context_menu( label, channelUrl, 'stingray', listitem )
            listitems.append( ( url, listitem, False ) )
        except:
            print_exc()
            
    
    
    def _addShowToChannel(self, season, listitems, fanart, url=None):
        addon_log("-- Adding Show to Channel")
        label = season['label'] if 'label' in season else season['name']
        if label=='Home':
            return
        OK = False                
        try:
            showUrl = url or season['link']['uri']
            uri = sys.argv[ 0 ]
            item = ( label,     '')
            url = '%s?show="%s"' %( uri, showUrl  )
            listitem = xbmcgui.ListItem( *item )

            listitem.setProperty( 'playLabel', label )
            #listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/media/public/images/providers_logos/common/' + i['image'] )
            listitem.setProperty( "fanart_image", fanart)
            self._add_context_menu( label, showUrl, 'show', listitem )
            listitems.append( ( url, listitem, True ) )
        except:
            print_exc()
    

    # --------------------------------------------------------------------------------------------
    # [ Start of scrappers -------------------------------------------------------------------------
    # --------------------------------------------------------------------------------------------
    
    def _getShowJSON(self, url):
        self._checkCookies()

        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}

        # url format: http://illicoweb.videotron.com/illicoservice/url?logicalUrl=/channels/<channelName>/<showID>/<showName>
        url = 'http://illicoweb.videotron.com/illicoservice/url?logicalUrl=' +url
        data = dataManager.GetContent(url)

        sections = data['body']['main']['sections']
        # url format: https://illicoweb.videotron.com/illicoservice/page/section/0000
        url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(sections[1]['contentDownloadURL'].replace( " ", "+" ))
        return dataManager.GetContent(url)

        
    # Returns json of Channel labeled <label>
    def _getChannel(self, label):
        self._checkCookies()

        url = 'https://illicoweb.videotron.com/illicoservice/channels/user?localeLang='
        if xbmc.getLanguage() == "English":
            url = url + 'en'
        else: url = url + 'fr'
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = getRequest(url,urllib.urlencode(values),headers)

        jsonList = json.loads(data)['body']['main']

        for i in jsonList:
            if i['name'] == label:
                return i

                
    # Returns json of Seasons from a specific Show's URL
    # Can return a specific season number json if seasonNo arg is non-0
    def _getSeasons(self, url, seasonNo=0):
        self._checkCookies()
        
        # url format: http://illicoweb.videotron.com/illicoservice/url?logicalUrl=/chaines/ChannelName
        url = 'http://illicoweb.videotron.com/illicoservice/url?logicalUrl=' + url
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}

        # get Channel sections to get URL for JSON shows
        data = getRequest(url,urllib.urlencode(values),headers)
        sections = json.loads(data)['body']['main']['sections']

        if (len(sections) == 1):
            # play show directly
            self._playEpisode(json.loads(data)['body']['main']['provider']['orderURI'], True)
            return           
        
        # url format: https://illicoweb.videotron.com/illicoservice/page/section/0000
        url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(sections[1]['contentDownloadURL'].replace( " ", "+" ))
        data = dataManager.GetContent(url)
        
        listitems = []
        seasons = data['body']
        if 'SeasonHierarchy' in seasons:
            seasons = data['body']['SeasonHierarchy']['seasons']
            for i in seasons:
                # [body][SeasonHierarchy][seasons] seasons
                if seasonNo > 0:
                    if int(i['seasonNo']) == seasonNo:
                        # found specified season, return json
                        return i
                else: self._addSeasonsToShow(i,listitems)
        i = data['body']['main']
        if type(i) is list:
            # sub category, loop through shows / episodes
            for y in i:
                if 'seasonNo' in y and y['objectType'] != "EPISODE":
                    self._addSeasonsToShow(y,listitems)
                else:
                    self._addEpisode(y, listitems)
            
        if len(listitems) == 1 and seasonNo == 0 and 'seasonNo' in i:
            # only one season for this show, go straight to episode list
            return self._getEpisodes(data, str(i['seasonNo']))

        if len(listitems) == 0 and not 'seasonNo' in i:
            # no season information, play show directly
            self._playEpisode(i[0]['orderURI'] if type(i) is list else i['orderURI'], True)
            return
            
        return listitems

    # Returns json of Season from a specific Show's URL
    def _getSeasonJSON(self, id):
        self._checkCookies()

        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}

        # url format: https://illicoweb.videotron.com/illicoservice/page/section/0000
        url = 'https://illicoweb.videotron.com/illicoservice/content/'+id
        return dataManager.GetContent(url)
        

    def _getShows(self, url):
        self._checkCookies()

        url = 'http://illicoweb.videotron.com/illicoservice/url?logicalUrl=' +unquote_plus(url).replace( " ", "+" )
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = getRequest(url,urllib.urlencode(values),headers)
      
        # url format: http://illicoweb.videotron.com/illicoservice/url?logicalUrl=chaines/ChannelName
        addon_log("Getting fanart from URL: " + url)
        fanart = self._getChannelFanartImg(data)

        i = json.loads(data)['body']['main']['provider']
        
        livelist = []
        if 'Stingray Mus' in i['name']:
            shows = i
        else:
            # Add LiveTV to top of show list
            try:
                self._addLiveChannel(livelist, i, '%s?live="%s"', fanart) 
            except:
                print_exc() 
        
            data = self._getChannelShowsJSON(data)
            # No onDemand content? do nothing
            if data is None:
                return "", fanart, livelist
            
            shows = data['body']['main']['submenus']
        
        return shows, fanart, livelist

    def _getStingray(self, url, label):
        self._checkCookies()

        url = 'http://illicoweb.videotron.com/illicoservice/url?logicalUrl=/chaines/Stingray' #+unquote_plus(url).replace( " ", "+" )
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = getRequest(url,urllib.urlencode(values),headers)
        #data = self._getChannelShowsJSON(data)
        
        channels = json.loads(data)['body']['main']['provider']['channels']   

        for i in channels:
            if i['name'] == label:
                return i
        
    def _getShow(self, url, label):
        self._checkCookies()

        url = 'http://illicoweb.videotron.com/illicoservice/url?logicalUrl='+unquote_plus(url).replace( " ", "+" )
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = getRequest(url,urllib.urlencode(values),headers)
        data = self._getChannelShowsJSON(data) or data

        shows = data['body']['main']
        if not 'submenus' in shows:
            shows = shows['provider']
            if shows['name'] == label:
                return shows
        else:
            shows = shows['submenus']

        for i in shows:
            if 'submenus' in i:
                for show in i['submenus']:
                    if show['label'] == label:
                        return show
            else:
                if ('label' in i):
                    if i['label'] == label:
                        return i
    
    def _getEpisodes(self, data, season, title=None):
        seasons = data['body']['SeasonHierarchy']['seasons']
        listitems = []

        # [body][SeasonHierarchy][seasons] seasons
        for i in seasons:
            if(str(i['seasonNo']) == season):
                season = self._getSeasonJSON(str(i['id']))
                for ep in season['body']['main']['episodes']:
                    if title:
                        if title == ep['title']:
                            self._addEpisode(ep, listitems)
                    else: self._addEpisode(ep, listitems)
        # [body][main] seasons
        i = data['body']['main']
        if(str(i['seasonNo']) == season):
            for ep in i['episodes']:
                if title:
                    if title == ep['title']:
                        self._addEpisode(ep, listitems)
                else: self._addEpisode(ep, listitems)

        return listitems    

    def _getEpisodesAlt(self, data):
        listitems = []
        i = json.loads(data)['body']
        for ep in i['main']:
            self._addEpisode(ep, listitems)

        return listitems   
        
    def _getChannelShowsJSON(self, data):
        sections = json.loads(data)['body']['main']['sections']
        onDemand = False
        for i in sections:
            if 'widgetType' in i:
                if i['widgetType'] == 'MENU':
                    onDemand = True
                    url = i['contentDownloadURL']
        if (onDemand == False):
            return
        # url format: https://illicoweb.videotron.com/illicoservice/page/section/0000
        url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(url.replace( " ", "+" ))
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
            'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        return dataManager.GetContent(url)
    
    def _getChannelFanartImg(self, data):
        sections = json.loads(data)['body']['main']['sections']
        onDemand = False
        for i in sections:
            if 'widgetType' in i:
                if i['widgetType'] == 'PLAYER':
                    url = i['contentDownloadURL']
        try:
            # url format: https://illicoweb.videotron.com/illicoservice/page/section/0000
            url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(url.replace( " ", "+" ))
            
            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                'Referer' : 'https://illicoweb.videotron.com/accueil'}
            values = {}
            data = getRequest(url,urllib.urlencode(values),headers)
            img = json.loads(data)['body']['main'][0]
            return 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/custom/' + img['image']    
        except:
            return ''
         
    # --------------------------------------------------------------------------------------------
    # [ End of scrappers -------------------------------------------------------------------------
    # --------------------------------------------------------------------------------------------
    
    def _playLive(self, pid):
        self._checkCookies()
        url = 'https://illicoweb.videotron.com/illicoservice'+pid
        addon_log("Live show at: %s" %url)
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = getRequest(url,urllib.urlencode(values),headers)
        options = {'live': '1'}

        if not (self._play(data, pid, options, True), True):
            addon_log("episode error")
    
    
    def _playEpisode(self, pid, direct=False):
        url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(pid).replace( " ", "+" )
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = getRequest(url,urllib.urlencode(values),headers)

        if not (self._play(data, pid, {}, direct)):
            addon_log("episode error")
    
    def _play(self, data, pid, options={}, direct=False):
        info = json.loads(data)
        path = info['body']['main']['mainToken']
        encrypted = info['body']['main']['mediaEncryption']
        connected = info['head']['userInfo']['clubIllicoStatus']
        
        if connected == 'NOT_CONNECTED':
            if not login():
                xbmcgui.Dialog().ok(ADDON_NAME, '%s\n%s' % (LANGUAGE(30004),LANGUAGE(30041)))
                xbmc.executebuiltin("Addon.OpenSettings(plugin.video.illicoweb)")
                exit(0)                
        
        if encrypted:
            xbmcgui.Dialog().ok(ADDON_NAME, '%s' % (LANGUAGE(30017)))
            return False
        
        rtmp = path[:path.rfind('/')]
        playpath = ' Playpath=' + path[path.rfind('/')+1:]
        pageurl = ' pageUrl=' + unquote_plus(self.args.episode).replace( " ", "+" )
        swfurl = ' swfUrl=https://illicoweb.videotron.com/swf/vplayer_v1-5_219_prd.swf swfVfy=1'
        
        win = xbmcgui.Window(10000)
        win.setProperty('illico.playing.title', xbmc.getInfoLabel( "ListItem.Property(playLabel)" ))
        win.setProperty('illico.playing.pid', unquote_plus(pid).replace( " ", "+" ))

        
        if 'live' in options.keys() and options['live']:
            live = ' live=1'
            win.setProperty('illico.playing.live', 'true')
        else:
            live = ''
            win.setProperty('illico.playing.live', 'false')
        
        final_url = rtmp+playpath+pageurl+swfurl+live
        addon_log('Attempting to play url: %s' % final_url)
    
        item = xbmcgui.ListItem(xbmc.getInfoLabel( "ListItem.Property(playLabel)" ), '', xbmc.getInfoLabel( "ListItem.Property(playThumb)" ), xbmc.getInfoLabel( "ListItem.Property(playThumb)" ))
        item.setPath(final_url)
        
        if direct:
            addon_log('Direct playback with DVDPlayer')
            player = xbmc.Player( xbmc.PLAYER_CORE_DVDPLAYER )
            player.play(final_url, item)
        else:
            addon_log('Indirect playback with setResolvedUrl')
            xbmcplugin.setResolvedUrl(int( sys.argv[ 1 ] ), True, item)

        return True

    def _checkCookies(self):
        # Check if cookies have expired.
        COOKIE_JAR.load(COOKIE, ignore_discard=False, ignore_expires=False)
        cookies = {}
        addon_log('These are the cookies we have in the cookie file:')
        for i in COOKIE_JAR:
            cookies[i.name] = i.value
            addon_log('%s: %s' %(i.name, i.value))
        if cookies.has_key('iPlanetDirectoryPro') or cookies.has_key('session-illico-profile'):
            addon_log('We have valid cookies')
            login_ = 'old'
        else:
            login_ = login()

        if not login_:
            xbmcgui.Dialog().ok(ADDON_NAME, '%s\n%s' % (LANGUAGE(30004),LANGUAGE(30041)))
            xbmc.executebuiltin("Addon.OpenSettings(plugin.video.illicoweb)")
            exit(0)

        COOKIE_JAR.load(COOKIE, ignore_discard=False, ignore_expires=False)
        cookies = {}
    def _add_directory_favourites( self ):
        OK = False
        listitems = []
        try:
            from xml.dom.minidom import parseString

            xmlFav = open( FAVOURITES_XML, "r" ).read()
            if isinstance(xmlFav, unicode):
                xmlFav = xmlFav.encode('utf-8')
            favourites = parseString( xmlFav).getElementsByTagName( "favourite" )
            
            for favourite in favourites:
                try:
                    label = favourite.getAttribute( "label" )
                    category  = favourite.getAttribute( "category" )
                    url = favourite.getAttribute( "url" )

                    if category == 'channel':
                        i = self._getChannel(label)
                        if i:
                            self._addChannel(listitems, i, '%s?channel="%s"')

                    elif category == 'live':
                        i = self._getChannel(label.replace(' - Live', ''))
                        if i:
                            i['name'] = label.replace(' - Live', " " + LANGUAGE(30003))
                            i['link']['uri'] = url 
                            self._addChannel(listitems, i, '%s?live="%s"')
                    
                    elif category == 'stingray':
                        i = self._getStingray(url, label)
                        if i:
                            self._addChannelToStingray(i, listitems, "", url)
                            
                    elif category == 'show':
                        i = self._getShow(url, label)
                        if i:
                            self._addShowToChannel(i,listitems, "", url)
                            
                    elif category == 'season':
                        # split the url to show url and seasonNo
                        seasonNo = int(url[url.rfind(',')+1:])
                        url = url[:url.rfind(',')]
                        i = self._getSeasons(url, seasonNo)
                        if i:
                            self._addSeasonsToShow(i, listitems, True)
                except:
                    print_exc()
                    addon_log("-- Favourite no longer exists")
                    question = label + LANGUAGE(30019)
                    remove = xbmcgui.Dialog()
                    remove = remove.yesno(ADDON_NAME, question)
                    if remove:
                        self._addToFavourites(label, category, url, True)
                        
        except:
            print_exc()

        if listitems:
            addon_log("Adding Favourites")
            OK = self._add_directory_items( listitems )   
        else:
            xbmc.executebuiltin("XBMC.Notification("+ADDON_NAME+", "+LANGUAGE(30020)+",10000,"+ICON+")")
            
        self._set_content( OK, "episodes", False )  
                
    def _add_directory_root( self ):
        self._checkCookies()

        url = 'https://illicoweb.videotron.com/illicoservice/channels/user?localeLang='
        if xbmc.getLanguage() == "English":
            url = url + 'en'
        else: url = url + 'fr'
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = getRequest(url,urllib.urlencode(values),headers)

        try:
            jsonList = json.loads(data)['body']['main']
            listitems = []
            
            if os.path.exists( FAVOURITES_XML ):
                uri = sys.argv[ 0 ]
                item = (LANGUAGE(30007), '', 'DefaultAddonScreensaver.png')
                listitem = xbmcgui.ListItem( *item )
                listitem.setProperty( "fanart_image", 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/custom/presse1.jpg')
                url = '%s?favoris="root"' %uri 
                listitem.addContextMenuItems( [( LANGXBMC(184), "Container.Refresh")], False )
                listitems.append(( url, listitem, True ))
            
            OK = False
            for i in jsonList:
                self._addChannel(listitems, i, '%s?channel="%s"')
        except:
            xbmcgui.Dialog().ok(ADDON_NAME, LANGUAGE(30016))
    
        if listitems:
            addon_log("Adding Channels to Root")
            OK = self._add_directory_items( listitems )
        self._set_content( OK, "episodes", False )

    '''
    ' Section de gestion des menus
    '''
    def _add_context_menu( self, label, url, category, listitem ):
        try:
            c_items = [] #[ ( LANGXBMC( 20351 ), "Action(Info)" ) ]
    
            #add to my favourites
            if category is not 'episode':
                # all strings must be unicode but encoded, if necessary, as utf-8 to be passed on to urlencode!!
                if isinstance(label, unicode):
                    labelUri = label.encode('utf-8')
                addon_log("--- " + labelUri)
                f = { 'label' : labelUri, 'category' : category, 'url' : url}
                uri = '%s?addtofavourites=%s%s%s' % ( sys.argv[ 0 ], "%22", urllib.urlencode(f), "%22" ) #urlencode(f) )
                
                if self.args.favoris == "root":
                    c_items += [ ( LANGUAGE(30005), "RunPlugin(%s)" % uri.replace( "addto", "removefrom" ) ) ]
                else:
                    c_items += [ ( LANGUAGE(30006), "RunPlugin(%s)" % uri ) ]
            c_items += [ ( LANGXBMC(184), "Container.Refresh") ]
                
            self._add_context_menu_items( c_items, listitem )
        except:
            print_exc()

    def _add_context_menu_items( self, c_items, listitem, replaceItems=True ):
        c_items += [ ( LANGXBMC( 1045 ), "Addon.OpenSettings(plugin.video.illicoweb)" ) ]
        listitem.addContextMenuItems( c_items, replaceItems )        

    '''
    ' Section de sort order
    ' e.g. 1, 2, 3, ... 10, 11, 12, ... 100, 101, 102, etc...
    '''
    def natsort_key(self, item):
        chunks = re.split('(\d+(?:\.\d+)?)', item[1].getLabel())
        for ii in range(len(chunks)):
            if chunks[ii] and chunks[ii][0] in '0123456789':
                if '.' in chunks[ii]: numtype = float
                else: numtype = int
                chunks[ii] = (0, numtype(chunks[ii]))
            else:
                chunks[ii] = (1, chunks[ii])
        return (chunks, item)

    def natural_sort(self, seq, reverseBool):
        sortlist = [item for item in seq]
        sortlist.sort(key=self.natsort_key, reverse = reverseBool)
        return sortlist
            
class Info:
    def __init__( self, *args, **kwargs ):
        # update dict with our formatted argv
        addon_log('__init__ addon received: %s' % sys.argv[ 2 ][ 1: ].replace( "&", ", " ).replace("%22",'"').replace("%2B","/plus/"))
        try: exec "self.__dict__.update(%s)" % ( sys.argv[ 2 ][ 1: ].replace( "&", ", " ).replace("%22",'"').replace("%2B","/plus/"))
        except: print_exc()
        # update dict with custom kwargs
        self.__dict__.update( kwargs )

    def __getattr__( self, namespace ):
        return self[ namespace ]

    def __getitem__( self, namespace ):
        return self.get( namespace )

    def __setitem__( self, key, default="" ):
        self.__dict__[ key ] = default

    def get( self, key, default="" ):
        return self.__dict__.get( key, default )#.lower()

    def isempty( self ):
        return not bool( self.__dict__ )

    def IsTrue( self, key, default="false" ):
        return ( self.get( key, default ).lower() == "true" )

if ( __name__ == "__main__" ):
    Main()

dataManager.canRefreshNow = True