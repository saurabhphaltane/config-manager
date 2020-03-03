#!/usr/bin/python3

import yaml
from pprint import pprint
import subprocess
import time
import hashlib
import os, sys
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

# package_tool mapping, can be extended for multiple installers, operations systems etc.(future)
package_tool = {
        "apt": {
                 "installer": "apt-get",
                 }
        }

def shell_exec(params,shell_val=False):
    # shell executable for interacting with OS
    timeout = 0
    try:
        process=subprocess.Popen(params, 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE
                         ) 
        return_code = process.poll()
        # poll process output, keep trying until timeout
        while return_code == None and timeout <operation_timeout :
            return_code = process.poll()
            time.sleep(1)
            timeout = timeout + 1
        if timeout >=operation_timeout:
            raise Exception("Skipping operation Timed out "+' '.join([i for i in params]))
        else:
            std_out = ''.join([i.decode('utf-8') for i in process.stdout.readlines()])
            std_err = ''.join([i.decode('utf-8') for i in process.stderr.readlines()])
    except Exception as e:
        logging.log_error("Exception executing: ", str(e))
        return "", "", 1
    else:
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
    # managing package resource supports :install :remove 
    package_installed = False
    resource_updated = False

    if parameters["action"] not in package_actions:
        logging.log_message("Invalid action on resource ", parameters["action"])

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
            all_updated_resources.append((parameters["package_name"],parameters["action"],resource_updated))
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
            all_updated_resources.append((parameters["package_name"],parameters["action"] ,resource_updated))
            logging.log_error(std_err);logging.log_message(std_out)
            logging.log_message("Executing ",parameters["action"], " on ", parameters["package_name"])

    return return_code

def method_file(parameters):
    # manages file resources supports file, owner , group , file contents 
    resource_updated = False
    def calculate_md5(location):
        try:
            md5 = hashlib.md5(open(location,'rb').read()).hexdigest()
        except IOError as e:
            logging.log_error("IOError ", str(e))
            return "-1"
        return md5

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
        all_updated_resources.append((parameters["location"],parameters["content_file"],resource_updated))
        
        logging.log_message("Executed and updated content at: ",parameters["location"])
        
    # check if file exists
    file_exists = os.path.exists(parameters["location"])

    if file_exists:
        std_out, std_err, return_code = shell_exec(['stat', parameters["location"], '--format="%a %U %G"'])
        if return_code == 0:
            mode, owner, group = eval(std_out).split()
    
    # Manage mode on the file
    if parameters["mode"] and return_code == 0:
        if mode != parameters["mode"]:
            std_out, std_err, return_code = shell_exec(["chmod", parameters["mode"], parameters["location"]])
            resource_updated = resource_updated or  True
            all_updated_resources.append((parameters["location"],"mode "+parameters["mode"], resource_updated))
            logging.log_message("Executing ",parameters["mode"], " on ", parameters["location"])
    
    # Manage  owner on the file
    if parameters["owner"] and return_code == 0:
        if owner != parameters["owner"]:
            resource_updated = resource_updated or  True
            std_out, std_err, return_code = shell_exec(["chown", parameters["owner"], parameters["location"]])
            logging.log_message("Executing ",parameters["owner"], " on ", parameters["location"])
            all_updated_resources.append((parameters["location"],"owner "+parameters["owner"], resource_updated))
    
    # Manage group on the file
    if parameters["group"] and return_code == 0:
        if group != parameters["group"]:
            resource_updated = resource_updated or  True
            std_out, std_err, return_code = shell_exec(["chgrp", parameters["group"], parameters["location"]])
            logging.log_message("Executing ",parameters["group"], " on ", parameters["location"])
            all_updated_resources.append((parameters["location"],"group "+parameters["group"], resource_updated))
    
    if resource_updated and parameters.get("notify"):
        handle_notify(parameters.get("notify"))
    return 0

def process_delayed_queue():
    # delayed queue of service restarts are processed towards end of config-tool run
    for service in set(delayed_queue):
        restart_service(service)

# supported resource types for config-tool and implementation follows
resource_type = {
  "package": method_package,
  "file": method_file
        }
# reads config files and executes on resource types
with open('config.yaml') as f:
    try:
        data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logging.log_error("Invalid Config ", str(e))
        sys.exit()
    else:
        logging.log_message("Executing config-tool run")
        for k,v in data.items():
            try:
              resource = k.split("-")[0]
              output = resource_type[resource]
            except Exception as e:
              logging.log_message("Invalid Reource defination: Should be resource-<int>, eg: package-1")
              continue 
            else:
              output(v)

    # process delayed restarts on services
    process_delayed_queue()

    # prints all final stats
    logging.log_message("Updated ", str(len(all_updated_resources)), " resources")
    if len(all_updated_resources):
        logging.log_message("{:<18}{:<18}{:<18}".format("<resource>","<attribute>","<status>"))
        for element in all_updated_resources:
            resource , attribute, updated = element
            logging.log_message("{:<18}{:<18}{:<18}".format(resource,attribute,"updated"))
