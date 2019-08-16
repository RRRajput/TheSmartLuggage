# -*- coding: utf-8 -*-
"""
Created on Thu Dec 14 11:58:24 2017

@author: Rehan Rajput
"""

import cherrypy
import time
import json
import threading
import requests
import os


class Bag(object):
    def __init__(self,bag_id,user_id=[],broker="",thing_ch="",thing_api_w="",thing_api_r="",tel_token="",cat_url="http://localhost:8000",*args,**kwargs):
        self.bag_id=bag_id
        self.user_id = user_id
        self.broker =broker
        self.port = 1883
        self.payload="mode"
        try:
            f = open('config','r')
            j_data = json.load(f)
            self.cat_url = j_data['cat_url']
            f.close()
        except IOError:    
            self.cat_url =cat_url
        self.cam_sub = '/light'+str(self.bag_id)+'/'
        self.cam_pub = '/Image'+str(self.bag_id)+'/'
        self.loc_sub = ['/secure'+str(self.bag_id)+'/','/getloc'+str(self.bag_id)+'/']
        self.thing_url = 'mqtt.thingspeak.com'
        self.thing_port = 1883
        self.thing_ch = thing_ch
        self.thing_api_w = thing_api_w
        self.thing_api_r = thing_api_r
        self.sec_sub = '/secure'+str(self.bag_id)+'/'
        self.sec_pub = ['/light'+str(self.bag_id)+'/','/photo'+str(self.bag_id)+'/']
        self.tel_token = tel_token
        self.tel_sub = '/Image'+str(self.bag_id)+'/'
        self.tel_pub = ['/getloc'+str(self.bag_id)+'/','/secure'+str(self.bag_id)+'/']
    
    def camera(self):
        return {"BROKER": self.broker, "PORT":self.port,"SUB":self.cam_sub,"PUB": self.cam_pub,"PAYLOAD":self.payload}
    
    def location(self):
        return {"BROKER":self.broker,"PORT":self.port,"SUB":self.loc_sub,"PAYLOAD":self.payload,"THING_URL":self.thing_url,"THING_PORT":self.thing_port,"THING_CH":self.thing_ch,"THING_API_W":self.thing_api_w}
    
    def secure(self):
        return {"BROKER":self.broker,"PORT":self.port,"SUB":self.sec_sub,"PUB":self.sec_pub,"PAYLOAD":self.payload}
    
    def telegram(self):
        return {"CAT_URL":self.cat_url,"TOKEN":self.tel_token,"BROKER":self.broker,"PORT":self.port,"SUB":self.tel_sub,"PUB":self.tel_pub,"PAYLOAD":self.payload,"THINGSPEAK_API_R":self.thing_api_r}
    
    def isInsertable(self):
        if(len(self.user_id) ==0 or self.broker =="" or self.thing_ch =="" or self.thing_api_w=="" or self.thing_api_r=="" or self.tel_token==""):
            return False
        return True
        
class Catalog(object):
    def __init__(self):
        self.list = []
        self.bags=[]
        if(os.path.isfile('./bags')):
            f = open('bags','r')
            self.bags = json.load(f)
            self.bags = [Bag(**i) for i in self.bags]
            f.close()
    
    def saveAll(self):
        if(len(self.bags) != 0):
            f = open('bags','w')
            json.dump(self.bags,f,default= lambda o:o.__dict__)
            f.close()
        
    def insert(self,ID,bag_id,timestamp):
        for elem in self.list:
            if (elem.get("ID") == ID):
                elem['timestamp'] = timestamp
                return "Device updated"
        obj = {"ID" : ID,"bag_id":bag_id,"timestamp":timestamp}
        self.list.append(obj)
        return "Device added"
    
    def insertBag(self,bag_id,user_id,broker,thing_channel,thing_api_w,thing_api_r,token):
        a = [b for b in self.bags if b.bag_id==bag_id]
        if(len(a)>0):
            if(user_id not in a[0].user_id):
                a[0].user_id.append(int(user_id))
            else:
                return "Bag already exists"
        if(type(user_id) == str or type(user_id) == int):
            user_id = [int(user_id)]
        b = Bag(bag_id,user_id,broker,thing_channel,thing_api_w,thing_api_r,token)
        if(b.isInsertable()):
            self.bags.append(b)
            return "Bag inserted"
        else:
            return "Bag couldn't be inserted"
    
    def getBag(self,bag_id):
        if(bag_id.isdigit()==False):
            return False
        bag_id = int(bag_id)
        x = [i for i in self.bags if i.bag_id==bag_id]
        if(len(x) >0):
            return x[0]
        return False
    
    def DeleteBag(self,ID):
        if(ID.isdigit() == False):
            return "No such bag found"
        ID = int(ID)
        for x in self.bags:
            if (x.bag_id == ID):
                self.bags.remove(x)
                return "Bag Removed"
        return "No such bag found"
    
    def change(self,bag_id,val,ob):
        ans = self.getBag(bag_id)
        if(ans!=False):
            if(ob.upper() == "USER_ID"):
                ans.user_id.append(int(val))
            elif(ob.upper() == "BROKER"):
                ans.broker = str(val)
            elif(ob.upper() == "PORT"):
                ans.port = int(val)
            elif(ob.upper() == "THING_URL"):
                ans.thing_url = str(val)
            elif(ob.upper() == "THING_CH"):
                ans.thing_ch = str(val)
            elif(ob.upper() == "THING_API_W"):
                ans.thing_api_w = str(val)
            elif(ob.upper() == "THING_API_R"):
                ans.thing_api_r = str(val)
            elif(ob.upper() == "TEL_TOKEN"):
                ans.token = str(val)
            else:
                return "No valid arguments given"
            return "%s bag changed" % bag_id
        return "No bag with id %s found" % bag_id
    
    def RetrieveAll(self):
        return self.list
    
    def RetrieveBag(self,bag_id):
        ans = self.getBag(bag_id)
        if(ans!=False):
            return ans
        return "No bag found"
    
    def getUserBag(self,user_id):
        user_id = int(user_id)
        x = [i for i in self.bags if user_id in i.user_id]
        return x

    def getBagUsers(self,bag_id):
        bag_id = int(bag_id)
        x = [i for i in self.bags if i.bag_id==bag_id]
        if(len(x)>0):
            return x[0].user_id
        return "No bag found with such ID"
    
    def RetrieveAllBags(self):
        return self.bags
    
    def RetrieveID(self,ID):
        for elem in self.list:
            if (elem.get("ID")== ID):
                return elem
        return "no device with that ID found"
    
    def RemoveID(self,ID):
        for elem in self.list:
            if (elem.get("ID") == int(ID) or elem.get("ID") == str(ID)):
                self.list.remove(elem)
                return "%s removed" % (ID)
        return "%s not found" % (ID)
    
class User(object):
    def __init__(self):
        self.list = []
        if(os.path.isfile('./users')):
            f = open('users','r')
            self.list = json.load(f)
            f.close()
    
    def insert(self,ID,name,surname,emails,chat_id=-1,bag_id=[],*args,**kwargs):
        for elem in self.list:
            if (elem.get("ID") == ID):
                bid=[int(bag_id)] if type(bag_id) == int or type(bag_id)== str else bag_id
                bag_id = elem.get("bag_id") + bid
                obj = {"ID" : ID,"name":name,"surname":surname,"emails":emails,"chat_id":chat_id,"bag_id":bag_id}
                self.list.remove(elem)
                self.list.append(obj)
                return "User Already Present"
        obj = {"ID" : ID,"name":name,"surname":surname,"emails":emails,"chat_id":chat_id,"bag_id":[int(bag_id)] if type(bag_id) == int or type(bag_id)== str else []}
        self.list.append(obj)
        return "User Added"
    
    def insertBag(self,ID,bag_id):
        for x in self.list:
            if(float(x.get("ID")) == float(ID)):
                if(bag_id not in x.get("bag_id")):
                    x.get("bag_id").append(bag_id)
                print("User %s with bag %d --- arg %s" % (x.get("ID"),bag_id,ID))
                return "Bag associated with user"
        return "Couldn't find the user"
    
    def getChatID(self,chat_id):
        if(chat_id.isdigit() == False):
            return False
        chat_id = int(chat_id)
        for x in self.list:
            if(x.get("chat_id") == chat_id):
                return x
        return False
    
    
    def RetrieveChat(self,chat_id):
        ans = self.getChatID(chat_id)
        if(ans!=False):
            return ans
        return "no such chat ID"
    
    def RetrieveAll(self):
        return self.list
    
    def getID(self,ID):
        if(ID.isdigit() == False):
            return False
        ID = int(ID)
        x = [i for i in self.list if i.get("ID") == ID]
        if (len(x)>0):
            return x[0]
        return False
    
    def change(self,ID,val,ob):
        ans = self.getID(ID)
        if(ans != False):
            if(ob.upper() == "EMAILS"):
                email_list = ans.get("emails")
                email_list.append(str(val))
                ans['emails'] = email_list
            elif(ob.upper() == "CHAT_ID"):
                ans['chat_id'] = int(val)
            elif(ob.upper() == "BAG_ID"):
                bags = ans['bag_id']
                bags.append(int(val))
                ans['bag_id'] = bags
            else:
                return "Unknown Arguments"
            return "User %s updated" % ID
        return "Unknown User"
            
    
    def DeleteUser(self,ID):
        if(ID.isdigit() == False):
            return "No such User found"
        ID = int(ID)
        for x in self.list:
            if (x.get("ID") == ID):
                self.list.remove(x)
                return "Done"
        return "No such User found"
    
    def RetrieveID(self,ID):
        ans = self.getID(ID)
        if(ans== False):
            return "False"
        else:
            return ans
    
    def saveAll(self):
        if(len(self.list) != 0):
            f = open('users','w')
            json.dump(self.list,f)
            f.close()
    
class Services(object):
    exposed = True
    BrokerInfo = json.load(open('broker_info','r'))
    cat = Catalog()
    utente = User()
    with open('dash.json','r') as file:
        dashboard = json.load(file)
    
    def PUT(self,*uri,**params):
        if (len(uri) < 2):
            raise cherrypy.HTTPError(400, message= "not enough arguments")
        if(uri[0] == "user"):
            if("val" in params.keys() or "ob" in params.keys()):
                return json.dumps(self.utente.change(uri[1],params.get("val"),params.get("ob")))
            else:
                return "Unknown arguments"
        elif(uri[0] == "bag"):
            if("val" in params.keys() or "ob" in params.keys()):
                return json.dumps(self.cat.change(uri[1],params.get("val"),params.get("ob")))
            else:
                return "Unknown arguments"
        else:
            return "Unknown command"
                
    def GET(self,*uri,**params):
        if (len(uri) ==0):
            return json.dumps(self.BrokerInfo)
        if(len(uri) == 1 and uri[0] == "saveall"):
            self.cat.saveAll()
            self.utente.saveAll()
            return "Saved Everything"
        if (len(uri) < 2):
            raise cherrypy.HTTPError(400, message= "not enough arguments")
        
        if(uri[0] == "dev"):
            if (uri[1] == "all"):
                return json.dumps(self.cat.RetrieveAll())
            else:
                return json.dumps(self.cat.RetrieveID(uri[1]))
        elif ( uri[0] == "user"):
            if (uri[1] == "all"):
                return json.dumps(self.utente.RetrieveAll())
            else:
                return json.dumps(self.utente.RetrieveID(uri[1]))
        elif (uri[0] == "bag"):
            if(uri[1] == "all"):
                return json.dumps(self.cat.RetrieveAllBags(),default=lambda o : o.__dict__)
            return json.dumps(self.cat.RetrieveBag(uri[1]),default=lambda o : o.__dict__)
        elif (uri[0] == "userbag"):
            return json.dumps(self.cat.getUserBag(uri[1]),default=lambda o:o.__dict__)
        elif (uri[0] == "baguser"):
            return json.dumps(self.cat.getBagUsers(uri[1]),default=lambda o:o.__dict__)
        elif ( uri[0] == "chat_id"):
            return json.dumps(self.utente.RetrieveChat(uri[1]),default=lambda o:o.__dict__)
        return "Unexpected error"
    
    def POST(self,*uri,**params):
        if(len(uri) < 1 ):
            raise cherrypy.HTTPError(450,message = "not enough arguments")
        m = cherrypy.request.body.read()
        j = json.loads(m)
        if(uri[0] == "dev"):
            l = ["ID","bag_id"]
            if ( set(l) != set(j.keys())):
                raise cherrypy.HTTPError(440, message = "not enough keys for the body ")
            self.cat.insert(j.get("ID"),j.get("bag_id"),time.time())
            return "Device inserted/updated"
        elif ( uri[0] == "user"):
            l = ["ID","name","surname","emails"]
            if ( set(l) != set(j.keys())):
                l = ["ID","bag_id"]
                if(set(l) != set(j.keys())):
                    raise cherrypy.HTTPError(440, message = "not enough keys for the body ")
                return self.utente.insertBag(j.get("ID"),j.get("bag_id"))
            return self.utente.insert(j.get("ID"),j.get("name"),j.get("surname"),j.get("emails"),j.get("chat_id"))
        elif ( uri[0] == "bag"):
            l = ["bag_id","user_id","broker","thing_channel","thing_api_w","thing_api_r","token"]
            if ( set(l) != set(j.keys())):
                raise cherrypy.HTTPError(440, message = "not enough keys for the body ")
            if(self.utente.insertBag(j.get("user_id"),j.get("bag_id"))):    
                return self.cat.insertBag(j.get("bag_id"),j.get("user_id"),j.get("broker"),j.get("thing_channel"),j.get("thing_api_w"),j.get("thing_api_r"),j.get("token"))
            return "No user found with corresponding user id"
        else:
            return "Unknown url parameters"
                    
    
    def DELETE(self,*uri,**params):
        if (len(uri) < 1 or "ID" not in params.keys()):
            raise cherrypy.HTTPError(400, message = "Not enough/wrong arguments to delete")
        if (uri[0] == "dev"):
            return self.cat.RemoveID(params.get("ID"))
        elif (uri[0] == "bag"):
            return self.cat.DeleteBag(params.get("ID"))
        elif ( uri[0] == "user"):
            return self.utente.DeleteUser(params.get("ID"))
        else:
            raise cherrypy.HTTPError(400, message = "Unknown URI")
        
            
        

class first(threading.Thread):
    def __init__(self,ThreadID,name):
        threading.Thread.__init__(self)
        self.ThreadID = ThreadID
        self.name = self.name
        self.cat_url = ""
        
    def run(self):
        try:
            f = open('config','r')
            j_data = json.load(f)
            host = j_data['cat_IP']
            port = j_data['cat_port']
            self.cat_url = j_data['cat_url']
            f.close()
        except IOError:    
            host ='0.0.0.0'
            port = 8000
            self.cat_url = "http://localhost:8000"
            print("Warning! No config file found")
        conf= {
                '/': {'request.dispatch': cherrypy.dispatch.MethodDispatcher(),\
                     'tools.sessions.on': True}
                }
        cherrypy.tree.mount(Services(), '/',conf)
        cherrypy.config.update({'server.socket_host': host})
        cherrypy.config.update({'server.socket_port': port})
        cherrypy.engine.start()
        cherrypy.engine.block()
    
    def stop(self):
        r = requests.get(self.cat_url + "/saveall/")
        print(r.text)
        print ("Stopping the engine")
        cherrypy.engine.exit()
        return
        
class second(threading.Thread):
    def __init__(self,threadid,name):
        threading.Thread.__init__(self)
        self.threadid = threadid
        self.name = name
        self.running = True
        try:
            f = open('config','r')
            j_data = json.load(f)
            self.cat_url = j_data['cat_url']
            f.close()
        except IOError:    
            self.cat_url = "http://localhost:8000"
        
    def run(self):
        
        while self.running:
            l = requests.get(self.cat_url+ "/dev/all").json()
            IDlist = [x.get("ID") for x in l if (time.time() - x.get("timestamp") > 120.0)]
            for i in IDlist:
                print("Here")
                r = requests.delete("%s/dev/?ID=%s" % (self.cat_url,str(i)))
                print (r.text)
            time.sleep(60)
        print("Second thread ended")
        
    def stop(self):
        self.running = False
        
        
if __name__ == "__main__":
    thread1 = first(1,"Main")
    thread2 = second(2,"Remover")
    
    thread1.start()
    thread2.start()
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        thread2.stop()
        thread1.stop()
    
        
        
        