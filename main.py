import os 
from google.appengine.ext.webapp import template
from google.appengine.api import users
import webapp2
from google.appengine.ext import db
import re
from webapp2_extras.routes import PathPrefixRoute
import json


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
        generated_key = re.sub("[\W]", "-", what.strip())
        
        remind = Remind(key_name=generated_key, what=what, author=author)
        remind.status = 'open'
        remind.link = params['link']
        key_tags = []
        for t in params['tags']:
           new = Tag.addTag(t, remind)
           key_tags.append(new)
           
        remind.tags = key_tags
        remind.put()
    
    
        
class Tag(db.Model):
    tagName =         db.StringProperty(required = True)
    toRemind =        db.ListProperty(db.Key, default=[])
    tagCounter =      db.IntegerProperty(required = True)
    
    @property
    def remindsTo(self):
        return Remind.all().filter("tags =", self.key())
    
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
        generated_key = re.sub("[\W]", "-", what.strip())+'-'+str(count)
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
      userName = "Welcome "
      if self.user:
        logStatus = ' <a href="' + users.create_logout_url(callbackURI) + '">log off</a>'
        userName = self.user.nickname() + " "
      if (users.is_current_user_admin()):
        logStatus = ' <a href="' + self.request.host_url + '/new">new Remind</a> |' + logStatus
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
       tags = Tag.all()
       aggregates = {'nodes': [], 'links': []} # {'source': 0, 'target': 5, 'value':3}
       params = {}
       reminds = {}
       tag_list = {}
       users_array = []
       for p in posts:
          reminds[str(p.key().name())] = p
          parent = len(aggregates['nodes'])
          aggregates['nodes'].append({'pos': parent, 'name' : p.key().name(), 'group': 'Remind', 'relateds': p.countRelated })
          if p.author not in users_array:
            users_array.append(p.author)
          children = db.query_descendants(p)
          for rel in children:
              child = len(aggregates['nodes'])
              aggregates['nodes'].append({'pos': child, 'name': rel.key().name(), 'group': 'Related'})
              aggregates['links'].append({'source': parent, 'target': child, 'value':1})
          
       for t in tags:
          tag_list[str(t.key().name())] = {'tagName' : t.tagName}
          tag_pos = len(aggregates['nodes'])
          aggregates['nodes'].append({'pos': tag_pos, 'name' : t.tagName, 'group': 'Tag', 'relateds': t.tagCounter })
          for p in t.remindsTo:
                for i in aggregates['nodes']:
                   if i['name'] == p.key().name():
                      aggregates['links'].append({'source': tag_pos, 'target': i['pos'], 'value':1})                  
      
       params['reminds'] = reminds
       params['users_array'] = users_array
       params['tags'] = tag_list
       params['aggregates'] = json.dumps(aggregates)
       self.render_template('home.html', params)
       
class EditController(BaseHandler):
   def post(self):
       if self.request.get('new') == 'None':
          params = {
            'what' : self.request.get('what'),
            'link' : self.request.get('link')
          }
          if len(self.request.get('what')) < 8 or len(self.request.get('what')) > 51:
            params['message'] = 'Title too short/long! (min 8, max 50)'
            return self.redirect('/new')
          
          tags = self.request.get('tags')
          tags = tags.split()
          if len(tags) > 6 or len(tags) < 2:
            params['message'] = 'Too many tags! (max 5)'
            return self.redirect('/new')
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
            if id is not None:
               obj = Remind.get_by_key_name(id)
               params['key_id'] = obj.key()
            else:
               params['key_id'] = 'None'
            return self.render_template('remind.html', params)
      return self.redirect("/")              
            
class RelatedController(BaseHandler):
   def get(self, id):
       params = {
          'key_id' : id
       }
       obj = Remind.get_by_key_name(id)
       key = obj.key()
              
       q = Related.all()
       q.ancestor(key)
       q.run()

       relateds = {}
       for r in q:
          relateds[str(r.key().name())] = r
       params['relateds'] = relateds
       
       remind = obj
       rem_dict = remind
       params['remind'] = rem_dict
       self.render_template('related.html', params)     

class TagController(BaseHandler):
   def get(self, id=None):
   # add related to search results
       obj = Tag.get_by_key_name(id)
       q = db.Query(Related)
       params = {}
       reminds = {}
       for r in obj.remindsTo:
          reminds[str(r.key().name())] = {'what': r.what, 'link' : r.link, 'date': r.date, 'relateds' : []}
          rel = q.ancestor(r.key())
          if rel is not None:
            rel_list = []
            for rel_found in rel:
              rel_list.append({'text': rel_found.text, 'link' : rel_found.link, 'date': rel_found.date}) 
            key_name = str(r.key().name())
            reminds[key_name]['relateds'] = rel_list
       params['reminds'] = reminds
       self.render_template('find.html',params)
       
class RssController(BaseHandler):
   def get(self):
       self.render_template('home.html')

app = webapp2.WSGIApplication([
        ('/', HomeController),
        ('/new', NewController),
        PathPrefixRoute('/new/<id:[a-zA-Z0-9-_]*>', [
         webapp2.Route('/', NewController),
         webapp2.Route('/<id:[a-zA-Z0-9-_]+>/', NewController),
        ]),
        PathPrefixRoute('/related/<id:[a-zA-Z0-9-_]*>', [
         webapp2.Route('/', RelatedController),
         webapp2.Route('/<id:[a-zA-Z0-9-_]+>/', RelatedController),
        ]),
        PathPrefixRoute('/find/<id:[a-zA-Z0-9-]*>', [
         webapp2.Route('/', TagController),
         webapp2.Route('/<id:[a-zA-Z0-9-]+>/', TagController),
        ]),
        ('/edit', EditController),
        ('/rss.xml', RssController)
    ], debug=True)