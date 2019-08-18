# -*- coding: utf-8 -*-
"""
Created on Mon Apr 16 20:28:47 2018

@author: Rehan Rajput
"""
import time
import paho.mqtt.client as mqtt
import json
import picamera
import requests
import threading

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
        self.name = "Camera"+str(self.bag_id)
        self.pub = ""
        self.sub= ""
        self.payload=""
        self.broker = ""
        self.port = ""
        
    def setVals(self,JSObject):
        self.sub = JSObject['cam_sub']
        self.pub = JSObject['cam_pub']
        self.payload = JSObject['payload']
        self.broker = JSObject['broker']
        self.port = JSObject['port']

class Publisher(object):
    def __init__(self,clientID,values):
        self.clientID = clientID
        self.mqtt = mqtt.Client(self.clientID,clean_session=False)
        self.mqtt.on_connect = self.P_onConnect
        self.values = values
        
    def start(self):
        self.mqtt.connect(self.values.broker,port =self.values.port)
        self.mqtt.loop_start()
    def stop(self):
        self.mqtt.loop_stop()
        self.mqtt.disconnect()
    def pub(self,topic,message):
        self.mqtt.publish(topic,payload=message,qos=2)
        print("Published Message with topic " + str(topic))
    def P_onConnect(self, paho_mqtt, userdata, flags, rc):
        print("result code is %s" % (rc))
        

class Subscriber(object):
    def __init__(self,clientID,values,cam):
        self.clientID = clientID
        self.values = values
        self.mqtt = mqtt.Client(self.clientID,clean_session=True)
        self.mqtt.on_connect = self.S_onConnect
        self.mqtt.on_message = self.S_onMessage
        self.cam = cam
    
    def start(self):
        self.mqtt.connect(self.values.broker,port=self.values.port)
        self.mqtt.loop_start()
        self.mqtt.subscribe(self.values.sub)
        print("Subscribed")
    
    def stop(self):
        self.mqtt.loop_stop()
        self.mqtt.disconnect()
        print("unsubscribed " + self.topic)
        
    def S_onConnect(self, paho_mqtt, userdata, flags, rc):
        print ("Connected to message broker with result code: "+str(rc))
    
    def S_onMessage(self, paho_mqtt , userdata, msg):
        print ("Topic:'" + msg.topic+"', QoS: '"+str(msg.qos)+"' Message: '"+str(msg.payload) + "'")
        m = json.loads(msg.payload)
        print("Camera coso has payload %s",m.get("mode"))
        if(m.get(self.values.payload)):
            print("Making the foootooo")
            self.cam.capturePic()
        
        
class Cam(object):
    def __init__(self,values):
        self.publisher = Publisher("Pic Publisher",values)
        self.publisher.start()
        self.i = 1
        self.values = values
    
    def capturePic(self):
        with picamera.PiCamera() as camera:
            camera.start_preview()
            time.sleep(2)
            camera.capture(str(self.i) + "Image.jpg")
            f=open(str(self.i) + "Image.jpg", "rb") 
            fileContent = f.read()
            byteArr = bytearray(fileContent)
            f.close()
            self.publisher.pub(self.values.pub,byteArr)
            self.i = self.i + 1
    
    def end(self):
        self.publisher.stop()

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
        self.cam = Cam(self.values)
        self.registrar = DevRegister(90 + 100*self.values.bag_id,"CameraRegistrar"+str(self.values.bag_id),self.values)
        self.sub = Subscriber("Subscriber" + str(self.values.bag_id),self.values,self.cam)

    def run(self):
        self.registrar.start()
        self.sub.start()
        self.running = True
        while self.running:
            pass
    
    def stop(self):
        self.running = False
        self.registrar.stop()
        self.sub.stop()
        self.cam.end()
    

if __name__ == "__main__":
    FatherThread = MainThreadBag()
    FatherThread.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        FatherThread.stop()
        