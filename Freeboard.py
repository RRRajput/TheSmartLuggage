# -*- coding: utf-8 -*-
"""
Created on Thu Aug 15 23:24:09 2019

"""
import cherrypy
import time
import json
import threading
import requests
import os

class Values(object):
    def __init__(self,cat_url="http://192.168.1.88:8900"):
        try:
            f = open('config','r')
            j_data = json.load(f)
            self.cat_url = j_data['cat_url']
            f.close()
        except IOError:    
            self.cat_url =cat_url
            print("Warning! No config file found")
        self.name="Freeboard"
        self.bag_id = -1
        self.thing_ch = ""
        self.thing_api_r = ""
        
    def setVals(self,JSObject):
        self.bag_id = JSObject['bag_id']
        self.thing_ch = JSObject['thing_ch']
        self.thing_api_r = JSObject['thing_api_r']
        
class FreeBoard(object):
    exposed = True
    values = Values()
    with open('dash.json','r') as file:
        dashboard = json.load(file)
    
    def GET(self,*uri,**params):
        if(len(uri)> 0 and uri[0].upper() == "FREEBOARD"):
            if( "BID" in params.keys()):
                self.values.bag_id = params.get("BID")
                print(self.values.cat_url+"/bag/"+str(self.values.bag_id))
                bag_data=requests.get(self.values.cat_url+"/bag/"+str(self.values.bag_id))
                print(bag_data.text)
                if(bag_data.text =='"No bag found"'):
                    return "Please, check the bag id.\nNo such bag exists"
                self.values.setVals(bag_data.json())
                channel = self.values.thing_ch
                thing_api_r = self.values.thing_api_r
                print(channel,thing_api_r)
                self.dashboard['datasources'][0]['settings']['url'] = \
                'https://api.thingspeak.com/channels/'+str(channel)+'/fields/1/last.json?api_key='+thing_api_r
                
                self.dashboard['datasources'][1]['settings']['url'] = \
                'https://api.thingspeak.com/channels/'+str(channel)+'/fields/2/last.json?api_key='+thing_api_r
                with open('./dashboard/dashboard.json','w') as jsonFile:
                    json.dump(self.dashboard,jsonFile)
                with open('index.html','r') as file:
                    ret = file.read()
                return ret
            elif("UID" in params.keys() and len(uri) >1 and uri[1].upper() == "USER"):
                user_id = params.get("UID")
                user_data = requests.get(self.values.cat_url+"/user/"+str(user_id))
                if(user_data.text == '"False"'):
                    return "Please check the user id.\nNo user exists with such user id"
                user_data = user_data.json()
                name = user_data.get("name")
                bags = user_data.get("bag_id")
                html_String = "<!DOCTYPE html><html><head><title>Settings for "+name+"</title></head><body>\
                <p> Following are your bags: </b>"
                for bag in bags:
                    html_String += "<br> <a href=/freeboard?BID="+str(bag)+">Bag "+str(bag)+"</a> </br>"
                
                html_String+="</body></html>"
                
                return html_String
            else:
                raise cherrypy.HTTPError(440, message = "Invalid parameters")
        else:
            raise cherrypy.HTTPError(440, message = "Please specify user or bag id")

class DevRegister(threading.Thread):
    def __init__(self,threadID,threadName):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.threadName = threadName
        self.values = Values()
    
    def run(self):
        self.starting = True
        while self.starting:
            body = {"ID":self.values.name,"bag_id":self.values.bag_id}
            resp = requests.post(self.values.cat_url+"/dev/",data=json.dumps(body))
            print(resp.text)
            time.sleep(60)
            
    def stop(self):
        self.starting = False
        print(self.threadName+" ended")

class ServerThread(threading.Thread):
    def __init__(self,ThreadID,name):
        threading.Thread.__init__(self)
        self.ThreadID = ThreadID
        self.name = self.name
        try:
            with open('freeboard_config','r') as file:
                vals = json.load(file)
                self.hostname = vals['free_IP']
                self.port = vals['free_port']
        except:
            print("WARNING! Freeboard config file not present")
            self.hostname ="127.0.0.1"
            self.port = 9999
        
    def run(self):
        conf= {'/': {'request.dispatch': cherrypy.dispatch.MethodDispatcher(),\
                     'tools.sessions.on': True,\
                     'tools.staticdir.root': os.path.abspath(os.getcwd()),\
                     'tools.staticdir.on': True,\
                     'tools.staticdir.dir': './'}
            
    }
        
        cherrypy.tree.mount(FreeBoard(), '/',conf)
        cherrypy.config.update({'server.socket_host': self.hostname})
        cherrypy.config.update({'server.socket_port': self.port})
        cherrypy.engine.start()
        cherrypy.engine.block()
    
    def stop(self):
        print ("Stopping the engine")
        cherrypy.engine.exit()
        return


if __name__=="__main__":
    first = ServerThread(500,"FreeboardServer")
    register = DevRegister(510,"Freeboard")
    
    first.start()
    register.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        first.stop()
        register.stop()