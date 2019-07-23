# -*- coding: utf-8 -*-
"""
Created on Sat Apr 14 15:19:12 2018

@author: Stefania Titone
"""


#thingspeak + telegram bot request use with python 3.6


import json
import os
import time
import telepot
from urllib import request
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import paho.mqtt.client as mqtt
import requests


class Values(object):
    def __init__(self,cat_url="http://localhost:8000"):
        try:
            f = open('config','r')
            j_data = json.load(f)
            self.cat_url = j_data['cat_url']
            f.close()
        except IOError:    
            self.cat_url =cat_url
        self.token = ""
        self.broker = ""
        self.port = -1
    
#creiamo tutte le funzioni necessarie al funzionamento del bot

#la funzione on_chat_message crea una inline keyboard

class Publisher(object):
    def __init__(self,clientID):
        self.clientID = clientID
        self.mqtt = mqtt.Client(self.clientID,clean_session=True)
        self.mqtt.on_connect = self.P_onConnect
    def start(self,broker,port):
        self.mqtt.connect(broker,port = port)
        self.mqtt.loop_start()
    def stop(self):
        self.mqtt.loop_stop()
        self.mqtt.disconnect()
    def pub(self,topic,message):
        self.mqtt.publish(topic,payload=message,qos=2)
        print("Published Message on topic %s with payload %s" % (topic,str(message)))
    def P_onConnect(self, paho_mqtt, userdata, flags, rc):
        print("result code is %s" % (rc))

class Subscriber(object):
    def __init__(self,clientID,url,port,bot,chat_id):
        self.clientID = clientID
        self.url = url
        self.port = port
        self.mqtt = mqtt.Client(self.clientID,clean_session=True)
        self.mqtt.on_connect = self.S_onConnect
        self.mqtt.on_message = self.S_onMessage
        self.bot = bot
        self.chat_id = chat_id
    
    def start(self):
        self.mqtt.connect(self.url,port=self.port)
        self.mqtt.loop_start()
    
    def changeChat_id(self,chat_id):
        self.chat_id = chat_id
    
    def subscribeTopic(self,topic):
        if(type(topic) is list):
            for i in topic:
                self.mqtt.subscribe(i)
        else:
            self.mqtt.subscribe(topic)
        
    def stop(self):
        self.mqtt.loop_stop()
        self.mqtt.disconnect()
        
    def S_onConnect(self, paho_mqtt, userdata, flags, rc):
        print ("Connected to message broker with result code: "+str(rc))
    
    def S_onMessage(self, paho_mqtt , userdata, msg):
        print("Image Received")
        f = open("received.jpg","wb")
        f.write(msg.payload)
        f.close()
        self.bot.sendPhoto(self.chat_id,open("received.jpg","rb"))

class UserTele(object):
    def __init__(self,user_id,chat_id,JSObject):
        self.user_id = user_id
        self.chat_id = chat_id
        self.bag_id = JSObject['bag_id']
        self.sub = []
        self.pub_loc = []
        self.pub_sec = []
        self.sub.append(JSObject['tel_sub'])
        self.pub_loc.append(JSObject['tel_pub'][0])
        self.pub_sec.append(JSObject['tel_pub'][1])
        self.payload = JSObject['payload']
        self.thing_api_r = JSObject['thing_api_r']
        self.thing_ch = JSObject['thing_ch']
        self.pub_loc = list(set(self.pub_loc))
        self.pub_sec = list(set(self.pub_sec))
        self.sub = list(set(self.sub))
        self.sec_mode = False
        self.pos_mode = False
        self.subscriber = None
        
    def Sec_Text(self):
        return "Turn secure mode off" if self.sec_mode else "Turn secure mode on"
    
    def Pos_Text(self):
        return "Get position"
    
    

#class UserChatDict(object):
#    def __init__(self):
#        self.user = {}
#        self.chat = {}
#    
#    def add(self,user_id,chat_id):
#        self.user[user_id]=chat_id
#        self.chat[chat_id] = user_id
#        
#    def findUser(self,chat_id):
#        if(chat_id in self.chat.keys()):
#            return self.chat[chat_id]
#        return False
#    
#    def findChat(self,user_id):
#        if(user_id in self.user.keys()):
#            return self.user[user_id]
#        return False
#    
#    def Remove(self,user_id,chat_id):
#        if(user_id in self.user and chat_id in self.chat):
#            del self.user[user_id]
#            del self.chat[chat_id]
#            return True
#        return False
        
    
class TheSmartLuggage (object):
    def __init__(self):
        self.values = Values()
        self.getToken()
        self.users = {}
        self.dict = {}
#        if(os.path.isfile('./telegram')):
#            print("Reading old data....")
#            f = open('telegram','r')
#            self.dict = json.load(f)
#            f.close()
        
    def getToken(self):
        resp = requests.get(self.values.cat_url)
        print(resp.text)
        resp = resp.json()
        self.values.broker = resp['broker']
        self.values.token = resp['tel_token']
        self.values.port = resp['port']
        
    def start(self):
        self.bot = telepot.Bot(self.values.token)
        self.publisher = Publisher("publisher")
        self.subscriber = None
        
    def run(self):
        self.publisher.start(self.values.broker,self.values.port)
        MessageLoop(self.bot, {'chat': self.on_chat_message,
                      'callback_query': self.on_callback_query}).run_as_thread()
        print('Listening ...')
        try:
            while 1:
                time.sleep(10)
        except KeyboardInterrupt:
            self.publisher.stop()
            f = open('telegram','w')
            json.dump(self.dict,f)
            f.close()
            print("Exiting....")
    
    def WelcomeFunction(self,msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        print(msg)
        chat_requests = requests.get(self.values.cat_url+"/chat_id/"+msg['text'])
        print(chat_requests)
        if(chat_requests.text == '"no such chat ID"'):
            print("Not a chat ID")
            chat_requests = requests.get(self.values.cat_url + "/user/"+msg['text'])
            if(chat_requests.text == '"False"'):
                self.bot.sendMessage(chat_id,"Please Enter a valid ID")
                print("Not a user ID")
            else:
                resp = chat_requests.json()
                self.bot.sendMessage(chat_id,"Welcome " + resp['name'])
                bag_ids = resp['bag_id']
                put_req = requests.put(self.values.cat_url+"/user/"+msg['text']+"?ob=chat_id&val="+str(chat_id))
                print(put_req.text)
                user_id = msg['text']
                self.users[user_id] = []
                self.dict[chat_id] = user_id
                self.bot.sendMessage(chat_id,"Following bags have been added")
                for x in bag_ids:
                    new_request = requests.get(self.values.cat_url + "/bag/" + str(x))
                    if(new_request.text != '"No bag found"'):
                        print(new_request.json())
                        self.users[user_id].append(UserTele(user_id,chat_id,new_request.json()))
                        self.bot.sendMessage(chat_id,"Bag with ID: " + str(x))
                    else:
                        print("Data for Bag with ID: " +str(x) +" missing.")
                self.showBags(chat_id)
       
    def showBags(self,chat_id):
        user_data = self.users[self.dict[chat_id]]
        user_bags = [x.bag_id for x in user_data]
        in_keyboard = []
        for x in user_bags:
            in_keyboard.append([InlineKeyboardButton(text = str(x),callback_data=str(x))])
        self.bot.sendMessage(chat_id,"Choose among the following bags",reply_markup=InlineKeyboardMarkup(inline_keyboard=in_keyboard))
    
    def on_chat_message(self,msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        
        if(chat_id not in self.dict.keys()):
            self.WelcomeFunction(msg)
        else:
            user_data = self.users[self.dict[chat_id]]
            user_bags = [x.bag_id for x in user_data]
            if(msg['text'].isdigit() == False):
                self.showBags(chat_id)
                return
            if(int(msg['text']) in user_bags):
                bag_data = [x for x in user_data if x.bag_id==int(msg['text'])][0]
                self.showBagData(chat_id,bag_data)
            else:
                self.showBags(chat_id)
            
    #la funzione on_callback_query processa i dati da Thingspeak e reagisce a seconda del pulsante premuto
        
    def on_callback_query(self,msg):
       #facciamo reagire alla pressione del pulsante
        
        query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')
        user_data = self.users[self.dict[chat_id]]
        if(query_data.isdigit()):
            bag_data = [x for x in user_data if x.bag_id==int(query_data)][0]
#            self.bot.sendMessage(chat_id,"Showing info for "+query_data+"\n"+str(bag_data))
            self.showBagData(chat_id,bag_data)
        else:
            bag_data = [x for x in user_data if x.bag_id==int(query_data[1:])][0]
            if(bag_data.subscriber == None):
                bag_data.subscriber = Subscriber("subscriber:"+str(chat_id),self.values.broker,self.values.port,self.bot,chat_id)
                bag_data.subscriber.start()
                bag_data.subscriber.subscribeTopic(bag_data.sub)
            else:
                bag_data.subscriber.changeChat_id(chat_id)
            print('Callback Query:',query_id,chat_id,query_data)
            if(query_data[0] == 'p'):
#                bag_data.pos_mode = not bag_data.pos_mode
                for i in bag_data.pub_loc:
                    self.publisher.pub(i,json.dumps({"mode":True}))
                    print("trying to publish data for",str(i))
                print("sleeping...")
                time.sleep(5)  
                print("Taking data from thingspeak")
                response = request.urlopen('https://api.thingspeak.com/channels/' + str(bag_data.thing_ch) + '/feeds.json?api_key='+bag_data.thing_api_r+'&results=2')
#            # preleva i dati json dalla richiesta        
                data = response.read().decode('utf-8')
#            # convertiamo la stringa in dizionario
                data_dict = json.loads(data)
#            #separiamo i valori che ci interessano
                feeds = data_dict['feeds']
                self.bot.sendLocation(chat_id, feeds[-1]['field1'], feeds[-1]['field2'])
                print("Location sent")
                self.showBagData(chat_id,bag_data)
            elif(query_data[0] == 's'):
                bag_data.sec_mode = not bag_data.sec_mode
                for i in bag_data.pub_sec:
                    self.publisher.pub(i,json.dumps({"mode":bag_data.sec_mode}))
                self.showBagData(chat_id,bag_data)
            else:
                self.showBags(chat_id)
                
    def showBagData(self,chat_id,bag_data):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                       [InlineKeyboardButton(text=bag_data.Pos_Text(), callback_data='p'+str(bag_data.bag_id))],
                       [InlineKeyboardButton(text=bag_data.Sec_Text(), callback_data='s'+str(bag_data.bag_id))],
                       [InlineKeyboardButton(text="Back to all bags", callback_data='e'+str(bag_data.bag_id))]
                   ])
        self.bot.sendMessage(chat_id,"Settings for the bag :" + str(bag_data.bag_id),reply_markup=keyboard)
#inizializziamo le funzioni

if __name__ == '__main__':
    Luggage=TheSmartLuggage()
    Luggage.start()
    Luggage.run()