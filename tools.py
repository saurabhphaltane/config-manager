import yaml
from pprint import pprint
import subprocess
import time
import hashlib
import os
from collections import Counter
from lib import logging

# valid actions for pacakge resource 
package_actions = [ "install", "remove", "update"]

# Config location for storing content_files
FILE_CONFIG = "files"
delayed_queue = []
run_status = []
operation_timeout = 60
all_updated_resources = []

package_tool = {
        "apt": {
                 "installer": "apt-get",
                 }
        }

def shell_exec(params,shell_val=False):
    timeout = 0
    process=subprocess.Popen(params, 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE
                         ) 
    return_code = process.poll()
    # pprint(params)
    while return_code == None and timeout <operation_timeout :
        return_code = process.poll()
        time.sleep(1)
        timeout = timeout + 1

    if timeout >=operation_timeout:
        std_err = "Skipping operation Timed out: "+' '.join([i for i in params])
        return_code = 1
        std_out = ""
    else:
         std_out = ''.join([i.decode('utf-8') for i in process.stdout.readlines()])
         std_err = ''.join([i.decode('utf-8') for i in process.stderr.readlines()])

    return std_out, std_err, return_code


def handle_notify(notify):
    if notify:
        if "delayed" in notify.split(","):
            delayed_queue.append(notify.split(",")[0])
        else:
            restart_service(notify.split(",")[0])
    return True



def restart_service(package):
    # Restaring a service 
    std_out, std_err, return_code = shell_exec(["/etc/init.d/"+package,"restart"])
    if return_code == 0:
        logging.log_message("Restarted Service ", package)
    logging.log_error(std_err);logging.log_message(std_out)
    return return_code

def method_package(parameters):
    package_installed = False
    resource_updated = False

    if parameters["action"] not in package_actions:
        logging.log_message("Invalid action on resource ", parameters["action"])
        #raise Exception("Invalid actionn on Reource", parameters["action"])

    # if package is already installed
    std_out, std_err, _ = shell_exec([ "dpkg-query", "-f", "${Status} ${Version}\n", "-W", parameters["package_name"] ],shell_val=True)
    logging.log_message(std_out); logging.log_message(std_err)
    if "install ok installed" in std_out:
        package_installed = True

    return_code = 0
    # action == install
    if parameters["action"] == "install":
        version = "="+parameters["version"] if parameters.get("version") else ""
        # if package_installed == False install the package
        if package_installed == False:
            std_out, std_err, return_code = shell_exec([package_tool[parameters["package_tool"]]["installer"], parameters["action"], parameters["package_name"]+version, "-y"])
            resource_updated = True if return_code == 0 else False
            all_updated_resources.append((parameters["package_name"],resource_updated))
            logging.log_error(std_err);logging.log_message(std_out)
            logging.log_message("Executing ",parameters["action"], " on ", parameters["package_name"])
            if resource_updated and parameters.get("notify"):
                handle_notify(parameters.get("notify"))
        else:
            logging.log_message("Package ", parameters["package_name"]," already installed and upto date.")
            
            
    
    # action == remove
    if parameters["action"] == "remove":
        if package_installed == False:
            logging.log_message("No Action ",parameters["action"], " on ", parameters["package_name"])
        else:
            std_out, std_err, return_code = shell_exec([package_tool[parameters["package_tool"]]["installer"], parameters["action"], parameters["package_name"], "-y"])
            resource_updated = True
            all_updated_resources.append((parameters["package_name"], resource_updated))
            logging.log_error(std_err);logging.log_message(std_out)
            logging.log_message("Executing ",parameters["action"], " on ", parameters["package_name"])

    return return_code

def method_file(parameters):

    resource_updated = False
    
    def calculate_md5(location):
        md5 = hashlib.md5(open(location,'rb').read()).hexdigest()
        return md5
    
    file_exists = os.path.exists(parameters["location"])
    print(file_exists)
    if file_exists:
        std_out, std_err, return_code = shell_exec(['stat', parameters["location"], '--format="%a %U %G"'])
        if return_code == 0:
            mode, owner, group = eval(std_out).split()
            print(eval(std_out), mode, owner, group)

    # calculate md5 for target, "-1" if target missing
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
          f1.close();f2.close()

    post_location_md5 = calculate_md5(os.path.abspath(parameters["location"]))

    # Compute if Target resource was updated
    if pre_location_md5 != post_location_md5:
        resource_updated = resource_updated or  True
        all_updated_resources.append((parameters["location"], resource_updated))
        logging.log_message("Executed and updated content at: ",parameters["location"])

    # Update  mode on the file
    print(parameters["mode"])
    print(str(mode))
    if parameters["mode"]:
        if mode != parameters["mode"]:
            std_out, std_err, return_code = shell_exec(["chmod", parameters["mode"], parameters["location"]])
            resource_updated = resource_updated or  True
            logging.log_message("Executing ",parameters["mode"], " on ", parameters["location"])
            
    if parameters["owner"]:
        if owner != parameters["owner"]:
            resource_updated = resource_updated or  True
            std_out, std_err, return_code = shell_exec(["chown", parameters["owner"], parameters["location"]])
            logging.log_message("Executing ",parameters["owner"], " on ", parameters["location"])
    
    if parameters["group"]:
        if group != parameters["group"]:
            resource_updated = resource_updated or  True
            std_out, std_err, return_code = shell_exec(["chgrp", parameters["group"], parameters["location"]])
            logging.log_message("Executing ",parameters["owner"], " on ", parameters["location"])
    
    if resource_updated and parameters.get("notify"):
        handle_notify(parameters.get("notify"))
    return 0

def process_delayed_queue():
    for service in set(delayed_queue):
        restart_service(service)

resource_type = {
  "package": method_package,
  "file": method_file
        }

with open('config.yaml') as f:
    data = yaml.load(f)
    tool_run = True
    logging.log_message("Executing config-tool run")
    for k,v in data.items():
        output = resource_type.get(k, lambda: "undefined resource")
        run_status.append(output(v))
    
    process_delayed_queue()
    stats = dict(Counter(run_status))
    logging.log_message("Config-tool run successful:",str(stats.get(0))," and Failed:", str(stats.get(1))," for  total ",str(len(run_status))," resources") 
