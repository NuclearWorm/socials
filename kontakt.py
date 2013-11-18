#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  Created by Nuclear Worm
#
#
#  Vkontakte friends adder  #
#  Version 0.1.a.1
#

import os, sys, time, re, logging,  sqlite3,  urllib,  urllib2,  cookielib
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
VERSION='0.1.a.1'
COOKIEFILE = '/tmp/cookies1.lwp'
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
        
class Vkontakte:
    def __init__(self,  mail,  password):
        self.mail = mail
        self.password = password
        
    def login(self):
        request = 'op=a_login_attempt&email=' + self.mail + '&pass=' + self.password +'&expire=0'
        req = PostCommand('http://vkontakte.ru/login.php', request)
        req.perform()
        my_id = re.compile('good(\d+)')
        logging.debug("Reply from login:\n" + req.res)
        if "failed" in req.res: return "Error! Check your login/pass!"
        else: 
            myid = my_id.search(req.res).groups()[0]
            return myid

class Group:
    def __init__(self, group_id):
        self.group_id = group_id
        
    def find(self,  datafile = None):
        if datafile: self.datafile = datafile
        else: 
            print "No datafile to store your friends"
            sys.exit(1)
        gp = GetCommand('http://vkontakte.ru/search.php?group=' + self.group_id)
        gp.perform()
        logging.debug("Reply from login:\n" + gp.res)
        sum = re.compile('<strong>.* (\d+) .*\.</strong>')
        all_those = sum.search(gp.res).groups()[0]
        logging.debug("Sum of all users in group:\n" + all_those)
        friends = extract_id(gp.res)
        add_to_file(self.datafile, friends)
        time.sleep(1)
        for i in range(1, int(all_those)/10 + 1):
            gp = GetCommand('http://vkontakte.ru/search.php?&group=' + self.group_id + '&o=0&st=' + str(i*10))
            gp.perform()
            friends = extract_id(gp.res)
            add_to_file(self.datafile, friends)
            time.sleep(1)
        return sum


class Friend:
    def __init__(self):
        pass
    def add(self,  datafile = None,  limit = None,  message = None):
        if datafile: self.datafile = datafile
        else: pass
        if limit: self.limit = limit
        else: self.limit = 20000000
        if message: self.message = message
        else: self.message=''
        df = open(self.datafile, 'r')
        ind = 0
        hash_find = re.compile('id="hash" value="([^"]+)"')
        for line in df.readlines():
            id = line.strip(' \n')
            fp = PostCommand('http://vkontakte.ru/friends_ajax.php', req = 'act=request_form&fid=' + id)
            fp.perform()
            #print fp.res
            for line1 in fp.res.split('\\n'):
                if  hash_find.search(line1.replace('\\',  '')):
                    hash = hash_find.search(line1.replace('\\',  '')).groups()[0]
                    break
            try: hash
            except:
                print "Hash not found"
                logging.debug("Hash for user %s not found!"%id)
                continue
            fp = PostCommand('http://vkontakte.ru/friends_ajax.php',  req = 'act=accept_friend&fid=' + id + '&hash=' + hash +'&verbose=1&message=' + self.message)
            fp.perform()
            ind +=1
            if ind >= self.limit: break
        return ind
    

def extract_id(data):
    result = ''
    link = re.compile('<div class="info" id="row2(\d+)">')
    for line in StringIO(data).readlines():
        if link.search(line):
            result += link.search(line).groups()[0] + '\n'
    return result  


def write_file(file, string):
    file1 = open(file, 'w')
    file1.write(string)
    file1.close()

def add_to_file(file, data):
    file1 = open(file, 'a')
    file1.write(data)
    file1.close()

def main(*args):
    mail,  password = sys.argv[1:]
    #mail = "mymail@mail.ru"
    #password = "mypass"
    ###  For Windows change to your path
    tmp_file = '/tmp/group_mems'
    mail = mail.replace("@","%40")
    mylogin = Vkontakte(mail,  password).login()
    #print "Your ID = ", mylogin
    link = raw_input("Give link of group: ")
    group_id = re.search('http://vkontakte.ru/club(\d+)',  link).groups()[0]
    gr = Group(group_id)
    gr.find(datafile = tmp_file)
    
    fr = Friend()
    print "Added ", fr.add(datafile = tmp_file),  " friends"
    ###  Limit fo adding 30 friends, example:
    #print "Added ", fr.add(datafile = '/tmp/group_mems',  limit = 30),  " friends"
    ###  Add friends with message "Куку", example
    #message_to_send = urllib.quote("Куку")
    #print "Added ", fr.add(datafile = '/tmp/group_mems',  message = message_to_send),  " friends"

if __name__ == '__main__': main(sys.argv)
