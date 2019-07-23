import requests
import time
import threading
import paho.mqtt.client as mqtt
import json

#BROKER = "192.168.1.254"
#PORT = 1883
#SUB='/secure/'
#PAYLOAD = 'mode'
#PUB = ['/light/','/photo/']
#BAG_ID=1
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
        self.pub = []
        self.sub= ""
        self.payload="mode"
        self.broker = ""
        self.port = ""
        
    def setVals(self,JSObject):
        self.sub = JSObject['sec_sub']
        self.pub = JSObject['sec_pub']
        self.payload = JSObject['payload']
        self.broker = JSObject['broker']
        self.port = JSObject['port']
        
class Flags(object):
    def __init__(self,Secure=False,Light=False):
        self.Secure = Secure
        self.Light=Light
    
    def setSec(self,val):
        self.Secure = val
        
    def setLight(self,val):
        self.Light=val
    
    def getSec(self):
        return self.Secure
    
    def getLight(self):
        return self.Light

class LightThread(threading.Thread):
    def __init__(self,threadID,name,Flags):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.ThreadName = name
        self.Flags = Flags
        
    def run(self):
        self.go = True
        while self.go:
            ans = input("Is the light on?")
            if(ans == 'y' or ans == 'Y'):
                self.Flags.setLight(True)
                print("Light turn on")
                time.sleep(4)
                self.Flags.setLight(False)
    
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
        self.mqtt.subscribe(str(self.values.sub))
        print("Subscribed to topic %s with broker %s" % (self.values.sub,self.values.broker))
        
    def stop(self):
        self.mqtt.loop_stop()
        self.mqtt.disconnect()
        
    def S_onConnect(self, paho_mqtt, userdata, flags, rc):
        print ("Connected to message broker with result code: "+str(rc))
    
    def S_onMessage(self, paho_mqtt , userdata, msg):
        if(self.values.sub == str(msg.topic)):
            m = json.loads(msg.payload)
            if(m.get(self.values.payload)):
                self.flags.setSec(True)
            else:
                self.flags.setSec(False)
        print("\nMessage Received by : " + str(self.clientID) + "\n\t")
        print ("Topic:'" + msg.topic+"', QoS: '"+str(msg.qos)+"' Message: '"+str(msg.payload) + "'")
            

class Publisher(object):
    def __init__(self,clientID,values):
        self.clientID = clientID
        self.mqtt = mqtt.Client(self.clientID,clean_session=True)
        self.mqtt.on_connect = self.P_onConnect
        self.values = values
        
    def start(self):
        self.mqtt.connect(self.values.broker,port =self.values.port)
        self.mqtt.loop_start()
        
    def stop(self):
        self.mqtt.loop_stop()
        self.mqtt.disconnect()
    
    def pub(self,topic,message):
        print("\nPublishing message :" + str(message) + " on topic: " + str(topic) + " - " + str(self.clientID))
        self.mqtt.publish(topic,message,0)
        
    def P_onConnect(self, paho_mqtt, userdata, flags, rc):
        print("result code is %s" % (rc))

class Monitor(threading.Thread):
    def __init__(self,threadID,ThreadName,values,flags):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.ThreadName = ThreadName
        self.values = values
        self.publisher = Publisher("LightPub"+str(self.threadID),self.values)
        self.flags = flags
        
    def run(self):
        self.go = True
        self.publisher.start()
        while self.go:
            if (self.flags.getSec() and self.flags.getLight()):
                for i in range(3):
                    self.publisher.pub(self.values.pub[0],json.dumps({self.values.payload:True}))
                    self.publisher.pub(self.values.pub[1],json.dumps({self.values.payload:True}))
                    print("Publish Light and photo")
                time.sleep(10)
        print(self.ThreadName + "ended\n")
            
    def stop(self):
        self.go = False
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
        self.flags = Flags()
        self.registrar = DevRegister(30 + self.values.bag_id*100,"SecurityRegistrar"+str(self.values.bag_id),self.values)
        self.subscriber = Subscriber("SecuritySubscriber"+str(self.values.bag_id),self.values,self.flags)
        self.LightThread = LightThread(self.values.bag_id*100 + 10,"LightThread"+str(self.values.bag_id),self.flags)
        self.Monitor = Monitor(self.values.bag_id*100 + 20 ,"MonitorThread"+str(self.values.bag_id),self.values,self.flags)

    def run(self):
        print("Starting the Main Thread for Bag"+str(self.values.bag_id))
        self.registrar.start()
        self.subscriber.start()
        self.LightThread.start()
        self.Monitor.start()
        self.running = True
        while self.running:
            print("\nBag: %d: Sec %s  Light %s" % (self.values.bag_id,self.flags.getSec(),self.flags.getLight()))
            time.sleep(10)
            
    def stop(self):
       self.LightThread.stop()
       self.Monitor.stop()
       self.subscriber.stop()
       self.registrar.stop() 
       print("Ended the Main Thread for Bag"+str(self.values.bag_id))
       
#class BagChecker(threading.Thread):
#    def __init__(self,cat_url="http://localhost:8000"):
#        threading.Thread.__init__(self)
#        try:
#            f = open('config','r')
#            j_data = json.load(f)
#            self.cat_url = j_data['cat_url']
#            f.close()
#        except IOError:    
#            self.cat_url =cat_url
#        self.list_old =[]
#        self.list_new = []
#        self.allThreads = {}
#    
#    def run(self):
#        self.running = True
#        while self.running:
#            Allbags = requests.get(self.cat_url+"/bag/all")
#            print(Allbags.text)
#            self.list_new = [x['bag_id'] for x in Allbags.json()]
#            new_diff = [x for x in self.list_new if x not in self.list_old]
#            old_diff = [x for x in self.list_old if x not in self.list_new]
#            for x in new_diff:
#                self.allThreads[x] = MainThreadBag(int(x))
#                self.allThreads[x].start()
#            for x in old_diff:
#                self.allThreads[x].stop()
#                self.allThreads.pop(x)
#            self.list_old = [x for x in self.list_new]
#            print("number of running threads %d : %d" % (threading.active_count(),len(self.list_old)))
#            time.sleep(10)
#    
#    def stop(self):
#        self.running = False
#        for x in self.allThreads.values():
#            x.stop()
       
if __name__ == "__main__":
    FatherThread = MainThreadBag()
    FatherThread.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        FatherThread.stop()
        