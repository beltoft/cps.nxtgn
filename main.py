# credits goes to https://github.com/TjaLfE/cps.nextgen

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from couchpotato.core.media.movie.providers.base import MovieProvider
import traceback
import cookielib
import urllib2
import time

log = CPLog(__name__)


class nxgn(TorrentProvider, MovieProvider):

   urls = {
      'test' : 'https://nxgn.org/',
      'login_page' : 'https://nxgn.org/login.php',
      'login' : 'https://nxgn.org/takelogin.php',
      'detail' : 'https://nxgn.org/details.php?id=%s',
      'search' : 'https://nxgn.org/browse.php?search=%s&cat=0&incldead=0&modes=%s',
      'download' : 'https://nxgn.org/download.php?id=%s',
   }
   
   cat_ids = [
      ([9, 33, 38, 43, 47], ['720p', '1080p']),
      ([6, 16, 17, 25, 28], ['dvdr']),
      ([5], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr', 'brrip']),
   ]


   https_time_between_calls = 1 #seconds

   cat_backup_id = None

   def _searchOnTitle(self, title, movie, quality, results):

      #correct category search
      categories= ""
      for x in self.getCatId(quality):
         categories+='&c' + str(x) + '=1'

      searchurl = self.urls['search'] % (tryUrlencode('%s %s' % (title.replace(':', ''), movie['info']['year'])), categories)
      data = self.getHTMLData(searchurl).decode('iso-8859-1')
      
      
      if data:
      
         html = BeautifulSoup(data)                      
         try:
            resultsTable = html.find('div', attrs = {'id' : 'torrent-table-wrapper'})
            if not resultsTable:
               return
            
            # Collecting entries
            entries_std = resultsTable.find_all('div' , attrs = {'id' : 'torrent-std'})
            entries_sticky = resultsTable.find_all('div' , attrs = {'id' : 'torrent-sticky'})
            entries = entries_std + entries_sticky
            
            if len(entries) > 0:
               # Extracting results from entries
               for result in entries:
                  
                  torrentId = (((result.find('div', attrs = {'id' :'torrent-download'})).find('a'))['href']).replace('download.php?id=','')
                  torrentName = ((result.find('div', attrs = {'id' :'torrent-udgivelse2-users'})).find('a'))['title']
                  
                  # Name trimming
                  torrentName = torrentName.replace("3D.", "")
                  torrentName = torrentName.replace("DTS7.1.", "")
                  torrentName = torrentName.replace('EXTENDED.CUT.','')
                  torrentName = torrentName.replace('UNRATED.CUT.','')
                  torrentName = torrentName.replace('THEATRICAL.CUT.','')
                  torrentName = torrentName.replace('EXTENDED.','')
                  torrentName = torrentName.replace('UNRATED.','')
                  torrentName = torrentName.replace('THEATRICAL.','')
                  torrentName = torrentName.replace('DIRECTORS.CUT.','')
                  torrentName = torrentName.replace('Extended.Cut.','')
                  torrentName = torrentName.replace('Unrated.Cut.','')
                  torrentName = torrentName.replace('Theatrical.Cut.','')
                  torrentName = torrentName.replace('Extended.','')
                  torrentName = torrentName.replace('Unrated.','')
                  torrentName = torrentName.replace('Theatrical.','')
                  torrentName = torrentName.replace('Directors.Cut.','')
                  
                     
                  results.append({
                     'id': torrentId,
                     'name': torrentName,
                     'url': (self.urls['download'] % torrentId).encode('utf8'),
                     'detail_url': (self.urls['detail'] % torrentId).encode('utf8'),
                     'size': self.parseSize(result.find('div', attrs = {'id' : 'torrent-size'}).text),
                     'seeders': tryInt(result.find('div', attrs = {'id' : 'torrent-seeders'}).text),
                     'leechers': tryInt(result.find('div', attrs = {'id' : 'torrent-leechers'}).text),
               })               

         except:
            log.error('Failed to parsing %s: %s', (self.getName(),traceback.format_exc()))


   def getLoginParams(self):
      return tryUrlencode({
         'username': self.conf('username'),
         'password': self.conf('password'),
      })

   def loginSuccess(self, output):
      if "<title>NextGen - Login</title>" in output:
         return False
      else:
         return True
      

   loginCheckSuccess = loginSuccess

   def login(self):

      # Check if we are still logged in every hour
      now = time.time()
      if self.last_login_check and self.last_login_check < (now - 3600):
         try:
            output = self.urlopen(self.urls['test'])
            if self.loginCheckSuccess(output):
               self.last_login_check = now
               return True
         except: pass
         self.last_login_check = None

      if self.last_login_check:
         return True

      try:
         # Find csrf for login
         data_login = self.getHTMLData(self.urls['login_page'])
         bs = BeautifulSoup(data_login.decode('iso-8859-1'))
         csrfraw = bs.find('form', attrs = {'id': 'login'})['action']
         
         # Create 'login' in self.urls
         self.urls['login'] = (self.urls['test'] + csrfraw).encode('utf8')
         output = self.urlopen(self.urls['login'] + '&' + self.getLoginParams())
         

         if self.loginSuccess(output):
            self.last_login_check = now
            return True

         error = 'unknown'
      except:
         error = traceback.format_exc()

      self.login_opener = None
      log.error('Failed to login %s: %s', (self.getName(), error))
      return False
