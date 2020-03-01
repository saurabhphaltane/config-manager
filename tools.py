import yaml
import shlex
from pprint import pprint
import subprocess
import time, logging
import hashlib
import os

# valid actions for pacakge resource 
package_actions = [ "install", "remove", "update"]

# Config location for storing content_files
FILE_CONFIG = "files"

delayed_queue = []

# logging_configurations
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='tool.log',
                    filemode='a+')
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')
console.setFormatter(formatter)
#logging.getLogger("").addHandler(console)

package_tool = {
        "apt": {
                 "installer": "apt-get",
                 }
        }

def log_message( *log ):
    """Logs the given message"""
    logging.info( ''.join([i for i in log ]))

def log_error( *log ):
    """Logs the given error message"""
    logging.error( ''.join([i for i in log ]))

def shell_exec(params,shell_val=False):

    timeout = 0
    process=subprocess.Popen(params, 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE
                         ) 

    return_code = process.poll()
    # pprint(params)
    while return_code == None and timeout <60 :
        return_code = process.poll()
        time.sleep(0.5)
        timeout = timeout + 1

    if timeout >=60:
        std_err = "Skipping operation Timed out: "+' '.join([i for i in params])
        return_code = 1
        std_out = ""
    else:
         std_out = ''.join([i.decode('utf-8') for i in process.stdout.readlines()])
         std_err = ''.join([i.decode('utf-8') for i in process.stderr.readlines()])

    return std_out, std_err, return_code


def restart_service(package):
    # Restaring a service 
    std_out, std_err, return_code = shell_exec(["/etc/init.d/"+package,"restart"])
    if return_code == 0:
        log_message("Restarted Service ", package)
    log_error(std_err);log_message(std_out)

def method_package(parameters):
    installed_flag = False
    installation_update = False
    if parameters["action"] not in package_actions:
        log_message("Invalid action on resource ", parameters["action"])

    # if package is already installed
    std_out, std_err, return_code = shell_exec([ "dpkg-query", "-f", "${Status} ${Version}\n", "-W", parameters["package_name"] ],shell_val=True)
    log_message(std_out); log_message(std_err)
    if "install ok installed" in std_out:
        installed_flag = True
    # action == install
    if parameters["action"] == "install":
        version = "="+parameters["version"] if parameters.get("version") else ""
        if installed_flag == False:
            std_out, std_err, return_code = shell_exec([package_tool[parameters["package_tool"]]["installer"], parameters["action"], parameters["package_name"]+version, "-y"])
            if return_code == 0 and parameters["notify"]:
                if "delayed" in parameters["notify"]:
                    installation_update = True
                    delayed_queue.append(parameters["notify"].split(",")[0])
                else:
                    restart_service(parameters["notify"].split(",")[0])

            log_error(std_err);log_message(std_out)
            log_message("Executing ",parameters["action"], " on ", parameters["package_name"])
    
    # action == remove
    if parameters["action"] == "remove":
        if installed_flag == False:
            log_message("No Action ",parameters["action"], " on ", parameters["package_name"])
        else:
            std_out, std_err, return_code = shell_exec([package_tool[parameters["package_tool"]]["installer"], parameters["action"], parameters["package_name"], "-y"])
            log_error(std_err);log_message(std_out)
            log_message("Executing ",parameters["action"], " on ", parameters["package_name"])

    return 0

def method_file(parameters):
    std_out, std_err, return_code = shell_exec(["test", "-e", parameters["location"], "&&", "$?" ])
    
    def calculate_md5(location):
        md5 = hashlib.md5(open(location,'rb').read()).hexdigest()
        return md5
    
    # calculate md5 of file else return -1 for non-existent file in target location
    pre_location_md5 = calculate_md5(os.path.abspath(parameters["location"])) if os.path.isfile(os.path.abspath(parameters["location"])) else "-1"

    # calculate md5 of the content file 
    content_md5 = calculate_md5(os.path.join(FILE_CONFIG, parameters["content_file"]))
   
    # if the md5 hashes differ copy over the contents from content_file to location file(target)
    if pre_location_md5 != content_md5:
        f2 = open(os.path.abspath(parameters["location"]), "w+")
        with open(os.path.join(FILE_CONFIG, parameters["content_file"]), "r") as f1:
          line = f1.readline()
          while line != '':
            f2.write(line)
            line = f1.readline()            
          f1.close()
          f2.close()

    post_location_md5 = calculate_md5(os.path.abspath(parameters["location"]))

    if pre_location_md5 != post_location_md5:
        log_message("Executed and updated content at: ",parameters["location"])


    if return_code == 0:
        print("File Exists")
    # Update  mode on the file
    if parameters["mode"]:
        std_out, std_err, return_code = shell_exec(["chmod", parameters["mode"], parameters["location"]])
        log_message("Executing ",parameters["mode"], " on ", parameters["location"])
    if parameters["owner"]:
        std_out, std_err, return_code = shell_exec(["chown", parameters["owner"], parameters["location"]])
        log_message("Executing ",parameters["mode"], " on ", parameters["location"])
    if parameters["group"]:
        std_out, std_err, return_code = shell_exec(["chgrp", parameters["group"], parameters["location"]])
        log_message("Executing ",parameters["mode"], " on ", parameters["location"])
    
    return True

def process_delayed_queue():
    for service in set(delayed_queue):
        restart_service(service)




resource_type = {
  "package": method_package,
  "file": method_file
        }


with open('config.yaml') as f:
    data = yaml.load(f)
    
    for k,v in data.items():
        output = resource_type.get(k, lambda: "undefined resource")
        pprint(output(v))
        process_delayed_queue()
        for i in set(delayed_queue):
            restart_service(i)

