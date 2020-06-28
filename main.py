from pprint import pprint
import requests
import json
from xml.dom import minidom
import sys

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

    def create(self, mapping):
        response = self.__setter(122, {
            "action": "add",
            "instance": "",
            "local_IP": mapping.ip,
            "start_port": mapping.port_start_local,
            "end_port": mapping.port_end_local,
            "start_portIn": mapping.port_start_global,
            "end_portIn": mapping.port_end_global,
            "protocol": 3,
            "enable": 1,
            "delete": 0,
            "idd": ""
        })
    
    def delete(self, id):
        ids = None
        if type(id) is list:
            ids = id
        elif type(id) is int:
            ids = [id]
        else:
            return

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
            "delete": "*".join([("1" if int(x["id"]) in ids else "0") for x in entries]),
            "idd": "*".join(["" for x in entries])
        })

############################ Mappings ##########################

class Mapping:
    def __init__(self, ip, port_range_local, port_range_global):
        (port_start_local, port_end_local) = port_range_local
        (port_start_global, port_end_global) = port_range_global
        self.id = None
        self.ip = ip
        self.port_start_local = port_start_local
        self.port_end_local = port_end_local
        self.port_start_global = port_start_global
        self.port_end_global = port_end_global
    
    def __eq__(self, b):
        return (
            type(b) is Mapping and
            self.ip == b.ip and
            int(self.port_start_local) == int(b.port_start_local) and            
            int(self.port_end_local) == int(b.port_end_local) and            
            int(self.port_start_global) == int(b.port_start_global) and            
            int(self.port_end_global) == int(b.port_end_global)
        )

    def __str__(self):
        return "(%sIP: %s, local: (%d-%d), global: (%d-%d))" % (
            ("#%d " % int(self.id)) if self.id is not None else "",
            self.ip,
            int(self.port_start_local),
            int(self.port_end_local),
            int(self.port_start_global),
            int(self.port_end_global)
        )

def check_entry(entry):
    return str(entry["enable"]) == '1' and str(entry["protocol"]) == '3'

def config_to_mappings(config):
    if "ip" not in config:
        return None
    ip = config["ip"]
    if "port" in config:
        ports = None
        if type(config["port"]) is list:
            ports = config["port"]
        elif type(config["port"]) is int:
            ports = [config["port"]]
        else:
            return None
        
        return [Mapping(ip, (port, port), (port, port)) for port in ports]

    if "port_local" in config and "port_global" in config:
        p_local = config["port_local"]
        p_global = config["port_global"]
        ports_local = None
        ports_global = None

        if type(p_local) is list and type(p_global) is list and len(p_local) == len(p_global):
            ports_local = p_local
            ports_global = p_global
        elif type(p_local) is int and type(p_global) is int:
            ports_local = [p_local]
            ports_global = [p_global]
        else:
            return None

        mappings = []
        for i in range(len(ports_local)):
            mappings.append(Mapping(ip, (ports_local[i], ports_local[i]), (ports_global[i], ports_global[i])))
        return mappings
    
    if "port_range" in config:
        port_range = config["port_range"]

        if type(port_range) is list and len(port_range) == 2:
            return [Mapping(ip, 
                (port_range[0], port_range[1]),
                (port_range[0], port_range[1])
            )]
        else:
            return None

    if "port_range_local" in config and "port_range_global" in config:
        port_range_local = config["port_range_local"]
        port_range_global = config["port_range_global"]

        if type(port_range_local) is list and type(port_range_global) is list and len(port_range_local) == 2 and len(port_range_global) == 2:
            return [Mapping(ip, 
                (port_range_local[0], port_range_local[1]),
                (port_range_global[0], port_range_global[1])
            )]
        else:
            return None
    return None

def entry_to_mapping(entry):
    mapping = Mapping(entry["local_IP"],
        (entry["start_port"], entry["end_port"]),
        (entry["start_portIn"], entry["end_portIn"])
    )
    mapping.id = int(entry["id"])
    return mapping

######################## difference #####################

class Difference:
    def __init__(self, current_structures, maintained_identifiers, identify_structure_method, update_predicate):
        self.to_create_identifiers = maintained_identifiers[:]
        self.to_delete = []
        self.to_update = []
        self.to_do_nothing = []

        for item in current_structures:
            identifier = identify_structure_method(item)
            if identifier in maintained_identifiers:
                self.to_create_identifiers.remove(identifier)

                if update_predicate(item):
                    self.to_update.append(item)
                else:
                    self.to_do_nothing.append(item)
            else:
                self.to_delete.append(item)

##################### main ##########################
host = None
password = None
managed_hosts = []
required_mappings = []

def read_config(config):
    global host
    global password
    global managed_hosts
    global required_mappings
    
    if "host" in config and host is None:
        host = config["host"]
    if "password" in config and password is None:
        password = config["password"]

    if "port_forwards" in config:
        for port_forward in config["port_forwards"]:
            required_mappings.extend(config_to_mappings(port_forward))
    
    if "managed_hosts" in config:
        managed_hosts.extend(config["managed_hosts"])

    if "parent" in config:
        read_config(read_json(config["parent"]))

config_file = "config.json"
if len(sys.argv) > 1:
    config_file = sys.argv[1]

read_config(read_json(config_file))

api = PortForwardsAPI(host, password)

all_entries = api.get_all()

managed_mappings = []
invalid_mappings = []

for entry in all_entries:
    if entry["local_IP"] not in managed_hosts:
        continue

    mapping = entry_to_mapping(entry)
    if not check_entry(entry):
        invalid_mappings.append(mapping)
        continue
    managed_mappings.append(mapping)

difference = Difference(
    managed_mappings,
    required_mappings,
    lambda x: x,
    lambda x: x not in required_mappings
)

to_delete_ids = [x.id for x in invalid_mappings]
to_delete_ids.extend([x.id for x in difference.to_delete])
to_delete_ids.extend([x.id for x in difference.to_update])

for mapping in difference.to_do_nothing:
    print("OK: %s" % str(mapping))

for mapping in invalid_mappings:
    print("Invalid: %s" % str(mapping))

for mapping in difference.to_delete:
    print("Delete: %s" % str(mapping))

for mapping in difference.to_update:
    print("Update: %s" % str(mapping))

for mapping in difference.to_create_identifiers:
    print("Create: %s" % str(mapping))

api.delete(to_delete_ids)

for mapping in difference.to_update:
    api.create(mapping)

for mapping in difference.to_create_identifiers:
    api.create(mapping)