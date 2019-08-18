# -*- coding: utf-8 -*-
"""
Created on Tue Mar 27 15:48:43 2018

@author: Rehan Rajput
"""

import random
import time
import threading
import paho.mqtt.client as mqtt
import json
import requests



class Values(object):
    def __init__(self,cat_url="http://localhost:8000"):
        try:
            f = open('config','r')
            j_data = json.load(f)
            self.cat_url = j_data['cat_url']
            self.bag_id = j_data['bag_id']
            f.close()
        except IOError:    
            self.cat_url =cat_url
            self.bag_id = None
            print("Warning! No config file found")
        self.name = "LocationSensor"+str(self.bag_id)
        self.x = 45.0625
        self.y = 7.678889
        self.topics= []
        self.payload=""
        self.thing_url = ""
        self.thing_port = -1
        self.thing_ch = ""
        self.thing_api_w = ""
        self.broker = ""
        self.port = ""
        
    def setVals(self,JSObject):
        self.topics = JSObject['loc_sub']
        self.payload = JSObject['payload']
        self.thing_url = JSObject['thing_url']
        self.thing_port = JSObject['thing_port']
        self.thing_ch = JSObject['thing_ch']
        self.thing_api_w = JSObject['thing_api_w']
        self.broker = JSObject['broker']
        self.port = JSObject['port']
        
                

class GeoCodes(object):
    def __init__(self,values):
        self.lat = values.x;
        self.lng = values.y;
        
    def change(self,x,y):
        self.lat = x;
        self.lng = y;
    
    def giveLat(self):
        return self.lat
    
    def giveLng(self):
        return self.lng;

class Flags(object):
    def __init__(self,Secure=False,CurrPos=False):
        self.Secure = Secure
        self.CurrPos = CurrPos
        
    def setSec(self,val):
        self.Secure = val
    
    def setPos(self,val):
        self.CurrPos = val
        
    def getSec(self):
        return self.Secure
    
    def getPos(self):
        return self.CurrPos
    
class GeoCodeThread(threading.Thread):
    def __init__(self,threadID,name,Geocodes):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.ThreadName = name
        self.Geocodes = Geocodes
        
    def run(self):
        self.go = True
        while self.go:
            time.sleep(2)
            if(random.random()%2 == 0):
                x = self.Geocodes.giveLat() + random.random()/10000
                y = self.Geocodes.giveLng() + random.random()/10000
            else:
                x = self.Geocodes.giveLat() - random.random()/10000
                y = self.Geocodes.giveLng() - random.random()/10000
            self.Geocodes.change(x,y)
        print(self.ThreadName + "ended\n")
    
    def stop(self):
        self.go = False

class Subscriber(object):
    def __init__(self,clientID,values,flags=Flags()):
        self.clientID = clientID
        self.values = values
        self.mqtt = mqtt.Client(self.clientID,clean_session=True)
        self.mqtt.on_connect = self.S_onConnect
        self.mqtt.on_message = self.S_onMessage
        self.flags = flags
    
    def start(self):
        self.mqtt.connect(self.values.broker,port=self.values.port)
        self.mqtt.loop_start()
        for i in self.values.topics:
            self.mqtt.subscribe(i)
        print("Subscribed to topic %s with broker %s" % (self.values.topics,self.values.broker))
    
    def stop(self):
        self.mqtt.loop_stop()
        self.mqtt.disconnect()
        
    def S_onConnect(self, paho_mqtt, userdata, flags, rc):
        print ("Connected to message broker with result code: "+str(rc))
    
    def S_onMessage(self, paho_mqtt , userdata, msg):
        if(self.values.topics[0] == str(msg.topic)):
            m = json.loads(msg.payload)
            if(m.get(self.values.payload)):
                self.flags.setSec(True)
            else:
                self.flags.setSec(False)
        elif (self.values.topics[1] == str(msg.topic)):
            self.flags.setPos(True)
        print("\nMessage Received by : " + str(self.clientID) + "\n\t")
        print ("Topic:'" + msg.topic+"', QoS: '"+str(msg.qos)+"' Message: '"+str(msg.payload) + "'")
            

class Publisher(object):
    def __init__(self,clientID,values):
        self.clientID = clientID
        self.mqtt = mqtt.Client(self.clientID,clean_session=True)
        self.mqtt.on_connect = self.P_onConnect
        self.values = values
        
    def start(self):
        self.mqtt.connect(self.values.thing_url,port =self.values.port)
        self.mqtt.loop_start()
        
    def stop(self):
        self.mqtt.loop_stop()
        self.mqtt.disconnect()
    
    def pub(self,topic,message):
        print("\nPublishing message :" + str(message) + " on topic: " + str(topic) + " - " + str(self.clientID))
        self.mqtt.publish(topic,message,0)
        
    def P_onConnect(self, paho_mqtt, userdata, flags, rc):
        print("result code is %s" % (rc))

class GeoCodePublisherThread(threading.Thread):
    def __init__(self,threadid,name,Geocode,values,sleeptime):
        threading.Thread.__init__(self)
        self.threadID = threadid
        self.ThreadName = name
        self.Geocode = Geocode
        self.values= values
        self.publisher = Publisher("GCPub_Periodic"+str(self.threadID),self.values)
        self.sleeptime = sleeptime
        self.topic = "channels/"+str(self.values.thing_ch)+"/publish/"+str(self.values.thing_api_w)
        
    def run(self):
        self.go = True
        self.publisher.start()
        while self.go:
            message = "field1="+str(self.Geocode.giveLat())+"&field2="+str(self.Geocode.giveLng())
            self.publisher.pub(self.topic,message)
            print("\nPublished Geocodes")
            time.sleep(self.sleeptime)
        self.publisher.stop()
        print(self.ThreadName + "ended\n")
    
    def stop(self):
        self.go = False
        
class Monitor(threading.Thread):
    def __init__(self,threadID,ThreadName,flags,GC,values):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.ThreadName = ThreadName
        self.flags = flags
        self.GC = GC
        self.values = values
        
    def run(self):
        self.go = True
        self.isOn = False
        while self.go:
            if (self.flags.getSec() and self.isOn == False):
                self.GCThread = GeoCodeThread(10,"GeoCodeThread",self.GC)
                self.GCPubThread = GeoCodePublisherThread(20,"GCPub",self.GC,self.values,4)
                self.GCThread.start() ### fa andare thread1.run
                self.GCPubThread.start()
                self.isOn = True
            elif(self.flags.getSec() == False and self.isOn):
                self.isOn = False
                self.GCThread.stop()
                self.GCPubThread.stop()
            
    def stop(self):
        self.go = False
        if(self.isOn):
            self.GCThread.stop()
            self.GCPubThread.stop()

class GetLocationThread(threading.Thread):
    def __init__(self,threadID,ThreadName,flags,GC,values):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.ThreadName = ThreadName
        self.flags = flags
        self.GC = GC
        self.values = values
        
    def run(self):
        self.go = True
        while self.go:
            if (self.flags.getPos()):
                self.GCPubThread = GeoCodePublisherThread(30,"GCPub",self.GC,self.values,0)
                self.GCPubThread.start()
                time.sleep(20)
                self.flags.setPos(False)
                self.GCPubThread.stop()
            
    def stop(self):
        self.go = False
        if(self.flags.getPos()):
            self.GCPubThread.stop()
        
        
class DevRegister(threading.Thread):
    def __init__(self,threadID,threadName,values):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.threadName = threadName
        self.values = values
    
    def run(self):
        self.starting = True
        while self.starting:
            body = {"ID":self.values.name,"bag_id":self.values.bag_id}
            resp = requests.post(self.values.cat_url+"/dev/",data=json.dumps(body))
            print(resp.text)
            time.sleep(60)
            self.values.setVals(requests.get(self.values.cat_url+"/bag/"+str(self.values.bag_id)).json())
            time.sleep(30)
            
    def stop(self):
        self.starting = False
        print(self.threadName+" ended")

class MainThreadBag(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.values = Values()
        resp = requests.get(self.values.cat_url+"/bag/"+str(self.values.bag_id))
        print(resp.text)
        self.values.setVals(resp.json())
        self.flags = Flags()
        self.registrar = DevRegister(3+ self.values.bag_id*100,"LocationRegistrar"+str(self.values.bag_id),self.values)
        self.subscriber = Subscriber("LocationSubscriber"+str(self.values.bag_id),self.values,self.flags)
        self.GC = GeoCodes(self.values)
        self.GCThread = GeoCodeThread(0+ self.values.bag_id*100,"GCThread"+str(self.values.bag_id),self.GC) 
        self.Monitor = Monitor(1+ self.values.bag_id*100,"Monitor"+str(self.values.bag_id),self.flags,self.GC,self.values)
        self.GLThread = GetLocationThread(2+ self.values.bag_id*100,"GLThread"+str(self.values.bag_id),self.flags,self.GC,self.values)
    
    def run(self):
        print("Starting the Main Thread for Bag"+str(self.values.bag_id))
        self.registrar.start()
        self.subscriber.start()
        self.GCThread.start()
        self.Monitor.start()
        self.GLThread.start()
        self.running = True
        while self.running:
            print("\nBag:%d " % self.values.bag_id)
            print("\n\tLatitude %f Longitude %f" % (self.GC.giveLat(),self.GC.giveLng()))
            print("\n\tSecure: %s Live Pos : %s" % (self.flags.getSec(),self.flags.getPos()))
            time.sleep(3)
            
    def stop(self):
        self.running = False
        self.GCThread.stop()
        self.Monitor.stop()
        self.GLThread.stop()
        self.subscriber.stop()
        self.registrar.stop()
        print("End of Main thread for Bag"+str(self.values.bag_id))
        
if __name__ == "__main__":
    FatherThread = MainThreadBag()
    FatherThread.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        FatherThread.stop()
        