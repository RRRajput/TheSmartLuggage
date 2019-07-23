# TheSmartLuggage
A Project by Stefania Titone, Annalisa Pelati, Elena Filipescu and Rehan Razzaque Rajput.

This is a prototype for an anti-theft smart luggage.

The luggage needs to have a sim-card for connectivity and GPS purposes -- in this prototype, simple LAN connection is used.
The raspberry pi needs to contain a camera and a light sensor -- the light sensor here, is simulated.

This is an IoT project, aimed at improving the security of luggages.
There is a Telegram interface which can send the location of the luggage to the owner on-demand. It also allows the 
owner to turn-on the secure mode which makes sure that no one except you can open the luggage. If someone else tries 
to open the luggage in secure mode, the luggage takes the picture and sends it to the owner via the telegram interface. 

# Configuration
The files Catalog.py and Telegram.py are used to turn on the server which hosts all the information and to turn on the 
telegram user-interface, respectively.

Each luggage contains a raspberry pi which needs to run the Secure.py, Location.py and Camera.py files inside of it.

All the files require the 'config' and 'broker_info' files. Although, the Catalog.py and Telegram.py don't necessarily 
require the bag_id field present in the config file, whereas, that field is necessary for the other codes. 
Each luggage needs to have their own thingspeak channel.
