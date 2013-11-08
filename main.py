import os 
from google.appengine.ext.webapp import template
from google.appengine.api import users
import webapp2
from google.appengine.ext import db
import re
from webapp2_extras.routes import PathPrefixRoute


class Remind(db.Model):
    date =            db.DateTimeProperty(auto_now_add = True)
    what =            db.StringProperty(required = True)
    status =          db.StringProperty(choices=['open', 'closed', 'archive'])
    countRelated =    db.IntegerProperty(required = True, default=0)
    tags =            db.ListProperty(db.Key, default=[])
    link =            db.LinkProperty()
    author =          db.UserProperty()
    
    @classmethod
    def createRemind(self, params, author):
        what = params['what']
        generated_key = what[0:18]
        generated_key = re.sub("[\W\d]", "_", generated_key.strip())
        remind = Remind(key_name=generated_key, what=what, author=author)
        remind.status = 'open'
        remind.link = params['link']
        key_tags = []
        for t in params['tags']:
           new = Tag.addTag(t, remind)
           key_tags.append(new)
           
        remind.tags = key_tags
        remind.put()
    
    @classmethod
    def getByTag(self, tag):
        return Remind.all().filter("tags =",tag)
        
class Tag(db.Model):
    tagName =         db.StringProperty(required = True)
    toRemind =        db.ListProperty(db.Key, default=[])
    tagCounter =      db.IntegerProperty(required = True)
    
    @classmethod
    def addTag(self, t, remind):
        if Tag.get_by_key_name(t) is None:
           tag = Tag(key_name=t, tagName=t, toRemind=[remind.key()], tagCounter=1)
           new = tag.put()
           return new
        else:
           tg = Tag.get_by_key_name(t)
           tg.tagCounter = tg.tagCounter + 1
           key_list = tg.toRemind
           key_list.append(remind.key())
           tg.toRemind = key_list
           new = tg.put()
           return new
    
class Related(db.Model):
    date =           db.DateTimeProperty(auto_now_add = True)
    text =           db.StringProperty(required = True, default='Something new here')
    link =           db.LinkProperty()

    @classmethod
    def createRelated(self, remind, params):
        count = remind.countRelated + 1
        what = params['text']
        generated_key = what[0:12]
        generated_key = re.sub("[\W\d]", "_", generated_key.strip())+str(count)
        related = Related(parent=remind, key_name=generated_key)
        related.link = params['link']
        related.text = params['text']
        remind.countRelated = count
        def txn():
          related.put()
          remind.put()
        db.run_in_transaction(txn)
    
class BaseHandler(webapp2.RequestHandler):
   def __init__(self, request, response):
        # Set self.request, self.response and self.app.
        self.initialize(request, response)
        self.user = users.get_current_user()
   def render_template(self, view_filename, params=None):
     if not params:
       params = {}
       
     def GetLoginLinks(callbackURI, pageId=None):
      logStatus = ' <a href="' + users.create_login_url(callbackURI) + '">log on</a>'
      userName = "Benvenuto"
      if self.user:
        logStatus = ' <a href="' + users.create_logout_url(callbackURI) + '">log off</a>'
        userName = self.user.nickname() + " "
      if (users.is_current_user_admin()):
        if pageId == None:   
            logStatus = ' <a href="' + self.request.host_url + '/new">posta</a> |' + logStatus
        else:
            logStatus = ' <a href="' + self.request.host_url + '/new">posta</a> | <a href="' + SITE_URL + '/edit?slug=' + pageId + '">modifica</a> |'  + logStatus
      return userName , logStatus
      
     userName, logStatus = GetLoginLinks(self.request.uri)
     params['user'] = self.user
     params['username'] = userName
     params['logStatus'] = logStatus
     path = os.path.join(os.path.dirname(__file__), 'views', view_filename)
     self.response.out.write(template.render(path, params))
   
class HomeController(BaseHandler):
   def get(self):
       posts = Remind.all()
       params = {}
       reminds = {}
       for p in posts:
          reminds[str(p.key())] = {'what': p.what, 'date' : p.date, 'link' : p.link}
       params['reminds'] = reminds
       tag_list = []
       tags = Tag.all()
       for t in tags:
           tag_list.append(t.tagName)
       params['tags'] = tag_list
       self.render_template('home.html', params)
       
class EditController(BaseHandler):
   def post(self):
       if self.request.get('new') == 'None':
          params = {
            'what' : self.request.get('what'),
            'link' : self.request.get('link')
          }
          tags = self.request.get('tags')
          tags = tags.split()
          params['tags'] = tags
          # new remind
          author = users.get_current_user()
          Remind.createRemind(params, author)
          return self.redirect('/')
          '''resp = self.response
          resp.headers['Content-Type'] = 'application/json'
          resp.body = {'response': 'Done'}
          return resp'''
       else:
          # new related
          key = db.Key(self.request.get('new'))
          remind = db.get(key)
          params = {
              'text' : self.request.get('what'),
              'link' : self.request.get('link')
          }
          Related.createRelated(remind, params)
          return self.redirect('/')
          #return JSON {response: 'Done'}
       if self.request.get('list'):
          listRemindRelated()
          #return JSON {response: list}
          
class NewController(BaseHandler):
    def get(self, id=None):
      if self.user:
         if (not users.is_current_user_admin()):
            return self.redirect("/")
         else:
            params = {}
            tag_list = []
            tags = Tag.all()
            for t in tags:
               tag_list.append(t.tagName)
            params['tags'] = tag_list
            params['key_id'] = id
            return self.render_template('remind.html', params)
      return self.redirect("/")              
            
class RelatedController(BaseHandler):
   def get(self, id):
       params = {
          'key_id' : id
       }
       key = db.Key(id)
       params['key'] = key
       q = Related.all()
       q.ancestor(key)
       q.run()

       reminds = {}
       for r in q:
          reminds[str(r.key())] = {'what': r.text, 'link' : r.link, 'date': r.date}
       params['reminds'] = reminds
       
       self.render_template('related.html', params)     
          
class RssController(BaseHandler):
   def get(self):
       self.render_template('home.html')

app = webapp2.WSGIApplication([
        ('/', HomeController),
        ('/new', NewController),
        ('/new/<id:\/*>', NewController),
        PathPrefixRoute('/new/<id:[a-zA-Z0-9-_]*>', [
         webapp2.Route('/', NewController),
         webapp2.Route('/<id:[a-zA-Z0-9-_]+>/', NewController),
        ]),
        PathPrefixRoute('/related/<id:[a-zA-Z0-9-_]*>', [
         webapp2.Route('/', RelatedController),
         webapp2.Route('/<id:[a-zA-Z0-9-_]+>/', RelatedController),
        ]),
        ('/edit', EditController),
        ('/rss.xml', RssController)
    ], debug=True)