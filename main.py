from pprint import pprint
import requests
import json
from xml.dom import minidom

##################### utilities #####################

def read_all_text(file):
    try:
        with open(file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def write_all_text(file, text):
    with open(file, "w") as f:
        f.write(text)

def read_json(file):
    text = read_all_text(file);
    if text is None:
        return None
    return json.loads(text)

config = read_json("config.json")

###################### Router ######################

class PortForwardsAPI:
    def __init__(self, host, password):
        self.base_url = "http://%s" % host
        self.sess = requests.Session()
        self.sess.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.116 Safari/537.36"
        })

        self.sess.get(self.base_url + "/common_page/login.html")
        self.sess.headers.update({
            "Referer": self.base_url + "/common_page/login.html"
        })

        self.__getter(1)
        self.__getter(3)
        self.__getter(3)
        self.__getter(1)

        login_response = self.__setter(15, data={
            "Username": "NULL",
            "Password": password
        })

        response_data = login_response.text
        if not response_data.startswith("successful"):
            print("Wrong password")
            exit()

        sid = response_data[len("successful;SID="):]
        self.sess.cookies.update({
            "SID": sid
        })

    def __getter(self, fun, data = {}):
        d = {}
        d["token"] = self.sess.cookies.get("sessionToken")
        d["fun"] = fun
        for key in data.keys():
            d[key] = data[key]
        return self.sess.post(self.base_url + "/xml/getter.xml", data=d)

    def __setter(self, fun, data = {}):
        d = {}
        d["token"] = self.sess.cookies.get("sessionToken")
        d["fun"] = fun
        for key in data.keys():
            d[key] = data[key]
        return self.sess.post(self.base_url + "/xml/setter.xml", data=d)
    
    def get_all(self):
        response = self.__getter(121)
        doc = minidom.parseString(response.text)
        instances = doc.getElementsByTagName("instance")

        entries = []
        for instance in instances:
            entry = {}
            for node in instance.childNodes:
                entry[node.nodeName] = node.firstChild.nodeValue
            entries.append(entry)

        return entries
    
    def create(self, ip, port):
        response = self.__setter(122, {
            "action": "add",
            "instance": "",
            "local_IP": ip,
            "start_port": port,
            "end_port": port,
            "start_portIn": port,
            "end_portIn": port,
            "protocol": 3,
            "enable": 1,
            "delete": 0,
            "idd": ""
        })
    
    def delete(self, id):
        entries = self.get_all()
        response = self.__setter(122, {
            "action": "apply",
            "instance": "*".join([x["id"] for x in entries]),
            "local_IP": "",
            "start_port": "",
            "end_port": "",
            "start_portIn": "*".join(["" for x in entries]),
            "end_portIn": "",
            "protocol": "*".join([x["protocol"] for x in entries]),
            "enable": "*".join([x["enable"] for x in entries]),
            "delete": "*".join([("1" if int(x["id"]) == id else "0") for x in entries]),
            "idd": "*".join(["" for x in entries])
        })
        
api = PortForwardsAPI(config["host"], config["password"])

# api.create("192.168.0.210", 8080)

api.delete(3)

pprint(api.get_all())
