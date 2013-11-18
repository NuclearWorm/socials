#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  Created by Nuclear Worm
#
#
#  Social bot
#
#  Version 0.1.b.1
#
#
#
import os, sys, time, re, logging,  sqlite3,  urllib,  urllib2,  cookielib
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
VERSION='0.1.b.1'
COOKIEFILE = '/tmp/cookies.lwp'
LOG_FILENAME = '/tmp/dbg.log'
logging.basicConfig(filename=LOG_FILENAME, filemode = 'w', level=logging.DEBUG,)

class PostCommand:
    def __init__(self, url, req = None):
        self.request  = req
        self.headers = ''
        self.url = url
    
    def perform(self):
        cj = cookielib.LWPCookieJar()
        if os.path.isfile(COOKIEFILE): cj.load(COOKIEFILE)
        url_retr = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        self.res =  url_retr.open(self.url,  self.request).read()
        cj.save(COOKIEFILE)
        logging.debug("Got to PostCommand request = %s, url = %s"%(self.request,  self.url))
        #self.res =  urllib.urlopen(self.url,  self.request).read()
        logging.debug("Got result = %s"%self.res)

class GetCommand:
    def __init__(self, url):
        self.headers = ''
        self.url = url
    def perform(self):
        cj = cookielib.LWPCookieJar()
        if os.path.isfile(COOKIEFILE): cj.load(COOKIEFILE)
        url_retr = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        self.res =  url_retr.open(self.url).read()
        cj.save(COOKIEFILE)
        logging.debug("Got to GetCommand url = %s"%(self.url))
        #self.res =  urllib.urlopen(self.url).read()
        logging.debug("Got result = %s"%self.res)
     
class Parse:
    def __init__(self, line, expr):
        self.line = line
        self.expr = expr

    def is_in(self):
        regexp = re.compile(self.expr)
        if regexp.search(self.line):
            return True
        else: return False

class Mirtesenru:
    def __init__(self,  mail,  password):
        self.mail = mail
        self.password = password
        
    def login(self):
        request = 'aa=1auth%5Bbackurl%5D=http%3A%2F%2Fmirtesen.ru%2F&auth%5Blogin%5D=' + self.mail + '&auth%5Bpassword%5D=' + self.password + '&auth%5Bremember%5D=on'
        req = PostCommand('http://mirtesen.ru/login', request)
        req.perform()
        logging.debug("Reply from login:\n" + req.res)
        csrf_find = re.compile('window\.csrf = \'([^\']+)\'')
        for line in req.res.split('\n'):
            if csrf_find.search(line): 
                logging.debug('CSRF = ' + csrf_find.search(line).groups()[0] + '\n')
                return csrf_find.search(line).groups()[0]
        return "Error! CSRF Not found!"
        

class Friend:
    def __init__(self, csrf=None):
        self.csrf = csrf
        
    def find(self,  limit=None,  datafile='/tmp/fems',  sex=None,  start_age=None,  end_age=None,  city=None,  online = ''):
        self.sex = sex
        self.start_age = str(start_age)
        self.end_age = str(end_age)
        self.city = urllib.quote(city)
        self.datafile = datafile
        if online: self.online = '&wf=on'
        else: self.online = ''
        if limit: self.limit = limit
        else: self.limit = 20000000
        ind = 0
        fp = GetCommand('http://mirtesen.ru/people?json=&n=&ln=&q=&city='+ self.city + '&sex='+ self.sex + '&agf=' + self.start_age + '&agt=' + self.end_age + self.online)
        fp.perform()
        logging.debug("Search result:\n" + fp.res)
        all_r = re.compile('Люди с \d+ по \d+ \| всего: (\d+)')
        for line in fp.res.split('\n'):
            if all_r.search(line):
                all_of_this = all_r.search(line).groups()[0]
                logging.debug("Sum of all results:\n" +all_of_this + '\n' )
        results = extract_ids(fp.res)
        ind = (len(results.split('\n')) - 1)
        logging.debug("From page 0\n" + results)
        add_to_file(self.datafile, results)
        for i in range(2, int(all_of_this)/3):
            fp = GetCommand('http://mirtesen.ru/people?json=&n=&ln=&q=&city='+ self.city + '&sex='+ self.sex + '&agf=' + str(self.start_age) + '&agt=' + str(self.end_age)+'&page=' + str(i))
            fp.perform()
            results = extract_ids(fp.res)
            ind += (len(results.split('\n')) - 1)
            logging.debug("From page " + str(i) + "\n" + results + '\nNow have ind=' + str(ind) + ' results\n')
            if ind > self.limit:
                    rr = ind - self.limit
                    results = '\n'.join(results.split('\n')[:-(rr)])
            add_to_file(self.datafile, results)
            if ind >= self.limit or  ind >=  int(all_of_this) or 'Нет результатов' in fp.res or 'Запрошено слишком много' in fp.res: 
                logging.debug("Search has ended:\nind=%d, limit=%d, all_of_this=%s\n%s"%(ind, self.limit, all_of_this, fp.res))
                break
        return all_of_this
    
    def invite(self,  id_fr=None, datafile=None,  message=None,  limit=None):
        ### Send "Davaj druzhit' without any message"  
        self.datafile = datafile
        if limit: self.limit = limit
        else: self.limit = 20000000
        if message: self.message = urllib.quote(message)
        else: self.message = ''
        if id_fr:
            fp = PostCommand('http://mirtesen.ru/messages/' + id_fr + '/json/', req = 'csrf=' + self.csrf + '&message%5Btext%5D=' + self.message + '&invite%5Binvite%5D=1')
            fp.perform()
            if '"ok":true' in fp.res: 
                logging.debug("Human " + id_fr + ':' + extract_name(id_fr) + " was invited successfully :)")
                return 1
            else: 
                logging.debug("Something wrong with user %s:%s - %s, not invited" % (id_fr, extract_name(id_fr), fp.res))
                return 0
        ind = 0     
        df = open(self.datafile, 'r')
        number = re.compile('http://mirtesen.ru/people/([0-9]+)')
        for line in df.readlines():
            idcl = number.search(line).groups()[0]
            fp = PostCommand('http://mirtesen.ru/messages/' + idcl + '/json/', req = 'csrf=' + self.csrf + '&message%5Btext%5D=&invite%5Binvite%5D=1')
            fp.perform()
            logging.debug('++++++++++++++++++++ ID:' + idcl + ' Name:' + extract_name(idcl) + ' +++++++++++++++++++\n' + fp.res)
            ind += 1
            time.sleep(1)
            if ind >= self.limit or 'QuotaException' in fp.res: break
        df.close()
        return ind
        
    def send_msg(self, id_fr=None, datafile=None,  message=None,  limit = None):
        self.datafile = datafile
        if limit: self.limit = limit
        else: self.limit = 20000000
        if message: self.message =urllib.quote(message)
        else: 
            print "Give the fucking message!"
            logging.debug("Function 'send message' can NOT work without message!")
            return 0
        if id_fr:
            fp = PostCommand('http://mirtesen.ru/messages/' + id_fr + '/json/', req = 'csrf=' + self.csrf + '&message%5Btext%5D=' + self.message)
            fp.perform()
            if '"ok":true' in fp.res: 
                logging.debug("Message " + self.message + " human " + id_fr + ':' + extract_name(id_fr) +" was sent successfully :)")
                return 1
            else: 
                logging.debug("Something wrong with user %s:%s - %s, message %s was NOT sent!" % (id_fr, extract_name(id_fr),  fp.res,  self.message))
                return 0
        ind = 0     
        df = open(self.datafile, 'r')
        number = re.compile('http://mirtesen.ru/people/([0-9]+)')
        for line in df.readlines():
            idcl = number.search(line).groups()[0]
            fp = PostCommand('http://mirtesen.ru/messages/' + idcl + '/json/', req = 'csrf=' + self.csrf + '&message%5Btext%5D=' + self.message)
            fp.perform()
            logging.debug('++++++++++++++ ID:' + idcl + ' Name:' + extract_name(idcl) +  ' +++++++++++++++++\n' + fp.res + '\n')
            ind += 1
            time.sleep(1)
            if ind >= self.limit or 'QuotaException' in fp.res: break
        df.close()
        
        
        
        
    def oblit(self, id_fr=None, message=None, limit=None, datafile=None):
         ## Send "Davaj druzhit' when "oblit' vodoj" " 
        if message: self.message = urllib.quote(message)
        if limit: self.limit = limit
        else: self.limit = 20000000
        if id_fr:
            fp = PostCommand('http://mirtesen.ru/people/' + id_fr + '/presents/snowball', req = 'csrf=' + self.csrf + '&buy%5Btext%5D=' + self.message + '&buy%5Banonymous%5D=on')
            fp.perform()
            if '<li class="notice gainlayout" title="Уведомление">' in fp.res: 
                logging.debug("Human " + id_fr + ':' + extract_name(id_fr) +" was oblit successfully :)")
                return 1
            else: 
                logging.debug("Something wrong with user %s:%s - %s, not oblit" % (id_fr, extract_name(id_fr),  fp.res))
                return 0
        ind = 0     
        self.datafile = datafile
        df = open(self.datafile, 'r')
        number = re.compile('http://mirtesen.ru/people/([0-9]+)')
        for line in df.readlines():
            idcl = number.search(line).groups()[0]
            fp = PostCommand('http://mirtesen.ru/people/' + idcl + '/presents/snowball', req = 'csrf=' + self.csrf + '&buy%5Btext%5D=' + self.message + '&buy%5Banonymous%5D=on')
            fp.perform()
            logging.debug('++++++++++++++ ID:' + idcl + ' Name:' + extract_name(idcl) +  ' +++++++++++++++++\n' + fp.res + '\n')
            ind += 1
            time.sleep(1)
            if ind >= self.limit or 'QuotaException' in fp.res: break
        df.close()
        
        
        

def write_file(file, string):
    file1 = open(file, 'w')
    file1.write(string)
    file1.close()

def add_to_file(file, data):
    file1 = open(file, 'a')
    file1.write(data)
    file1.close()

def extract_ids(data):
    result = ''
    link = re.compile('(http://mirtesen.ru/people/[0-9]+)" class="name nopopup"><em class="display_name')
    for line in StringIO(data).readlines():
        if link.search(line):
            result += link.search(line).groups()[0] + '\n'
    return result    

def extract_name(id):
    id_f = re.compile('<foaf:name>([^<]+)</foaf:name>')
    #id_l = re.compile('<foaf:surname>([^<]+)</foaf:surname>')
    get_it = GetCommand('http://mirtesen.ru/people/'+ id +'/foaf')
    get_it.perform()
    for line in get_it.res.split('\n'):
        if id_f.search(line): 
            f_name = id_f.search(line).groups()[0]
            break
        #if id_l.search(line): l_name = id_l.search(line).groups()[0]
    try:
        if f_name: return f_name
        else: return "Unknown"
    except:
        return "Name was not found!"

def main(*args):
    mail,  password = sys.argv[1:]
    #mail = "mymail@mail.ru"
    #password = "mypass"
    mail = mail.replace("@","%40")
        
    mycsrf = Mirtesenru(mail,  password).login()
    if mycsrf ==  "Error! CSRF Not found!":
        print "Something changed! Can't get CSRF and go on! Exiting...."
        sys.exit(1)
    
    #####   Usage examples  #####
    st = Friend(csrf = mycsrf)
    ####  Invite human to be a your friend, send ID as a parameter. 
    ####  ID is extracted from homepage of human - http://mirtesen.ru/people/875956200, where 875956200 is ID
    #if not st.invite(id_fr ='672935701'): print "Failed!"
    #else: print "Success!"
    ####  "Oblit'" human, send ID as a parameter.  Send with this message  'Давай дружить с червем! :))'
    #if not st.oblit(id_fr = '331102859',  message = 'Давай дружить с червем! :))'): print "Failed!"
    #else: print "Success!"
    ####   Find female humans from Moscow from age 21 to 22, find 50 humans. Write results to file /tmp/fems_50
    #st.find(50,  datafile='/tmp/fems_50',  sex='female',  start_age=21,  end_age=22,  city='Москва')
    ####  Invite 10 females from previous search (/tmp/fems_50) to be a friend
    #friends = st.invite(datafile='/tmp/fems_50', limit=10)
    #print "Invited ",  friends,  " people"
    ####  Send message "Какая классная фотка!" to user ID 14279333
    #st.send_msg(id_fr = '14279333', message = "Какая классная фотка!")
    
    ####  Massive example  ####
    ### Find ALL females from Kiev 22 age old
    #st.find(datafile='/tmp/hohlushki',  sex='female',  start_age=22,  end_age=22,  city='Киев')
    ####  Send to all of them message "Какая вы красивая..Вы модель?"  ####
    #st.send_msg(datafile='/tmp/hohlushki', message = "Какая вы красивая..Вы модель?")
    
    ####  Find all females from Moscow 25 age old, write them to /tmp/mos_24 file
    #st.find(datafile='/tmp/mos_25',  sex='female',  start_age=25,  end_age=25,  city='Москва', online='yes')
    ####  Send to ALL them message "Привет! Хочешь сходить в кино на Ларса фон Триера "Антихрист"? :) Обещаю, будет прикольно ))"
    ####  or  "Я изменил жене с ее лучшей подругой.. Как вы думаете, она скажет ей???" or something else that выносит моск
    #st.send_msg(datafile='/tmp/mos_25', message = "Привет! Хочешь сходить в кино на Ларса фон Триера 'Антихрист'? :) Обещаю, будет прикольно ))")
    ####  Oblit' vodoj all found females in previous search (/tmp/mos_25), with message "Давай дружить! :) Дружба с червем полезна для здоровья!"
    #st.oblit(datafile='/tmp/mos_25', message = "Давай дружить! :) Дружба с червем полезна для здоровья!")
    
if __name__ == '__main__': main(sys.argv)
