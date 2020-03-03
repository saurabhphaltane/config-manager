# config-manager
Chef like simple config-manager to manage packages and files:

### Usage:

Config File
config.yaml (YAML format)
Config file defines the resource definitions eg. package or a file. The format package-1 or file-1 i.e resource-<int> is required to 
keep the YAML valid and recommended best practice to keep the resources numbered.

```
---
package-1:
  package_tool: apt
  action: install
  package_name: php5
package-2:
  package_tool: apt
  action: install
  package_name: libapache2-mod-php5
package-2:
  package_tool: apt
  action: install
  package_name: apache2
  notify: apache2, delayed
file-1:
  location: /var/www/html/index.php
  content_file: contentfile
  owner: root
  group: root
  mode: '774'
  notify: apache2, delayed
file-2:
  location: /etc/apache2/mods-available/dir.conf
  content_file: default_dir.conf
  owner: root
  group: root
  mode: '774'
  notify: apache2, delayed
```

### i) Package Resource
   `package-1`: Package defines a package resource and is appended with -1 (hyphen 1) as a unique identifier.
   - `package-tool`: Presently only supports `apt`.
   
   - `action`: Could be install or remove.
   
   - `package_name`: name of the package to be installed or removed.
   
   - `notify`: notify a service that is to be restarted, provides option to process delayed restarts or immediate restarts using (delayed/immediate) keywords 


### ii) File Resource 
  `file-1`: File defines a package resource and is appended with -1 (hyphen 1) as a unique identifier.
  - `location`: Target location for file that is to be managed by our config-tool. Presently only file are supported , no synlinks or directories 
            for simplicity.
            
  -  `content`: define the content of the file that is to be managed by the config-tool for the desired `location`.
  
  - `mode`: manages mode eg: 770 for the given file at `location`.
  
  - `group`: manages group for the given file at `location`.
  
  - `notify`: if any of the above resource change , the destined service is notified for a restart.
  

### Installation

Execute the `bash bootstrap.sh` file and it should install required dependencies eg: python3 and python3-yaml. 

```sh
bash bootstrap.sh
eg: 
root@ip-172-31-255-45:~/config-manager# bash bootstrap.sh
Reading package lists... Done
Building dependency tree
Reading state information... Done
python3 is already the newest version.
0 upgraded, 0 newly installed, 0 to remove and 193 not upgraded.
Reading package lists... Done
Building dependency tree
Reading state information... Done
python3-yaml is already the newest version.
0 upgraded, 0 newly installed, 0 to remove and 193 not upgraded.
Python 3 is installed
root@ip-172-31-255-45:~/config-manager#
```

Configure your config.yaml file describing the resource that you intend to manage.

eg:
```sh
---
package-1:
  package_tool: apt
  action: install
  package_name: php5
package-2:
  package_tool: apt
  action: install
  package_name: libapache2-mod-php5
package-2:
  package_tool: apt
  action: install
  package_name: apache2
  notify: apache2, delayed
file-1:
  location: /var/www/html/index.php
  content_file: contentfile
  owner: root
  group: root
  mode: '774'
  notify: apache2, delayed
file-2:
  location: /etc/apache2/mods-available/dir.conf
  content_file: default_dir.conf
  owner: root
  group: root
  mode: '774'
  notify: apache2, delayed
```

### Execution:

Sample Run: 

The packages are not installed if they are already installed, the permissions, mode, ownership for file is managed 
by the config-tool and even the services are notified for restart if configured.
The end of the logs show the final status of all the resources. See last 5 lines of the log for stas about updated resources.

```
root@ip-172-31-255-45:~/config-manager# sudo ./config-manager.py
2020-03-03 07:55:52,971 : INFO : Executing config-tool run
2020-03-03 07:55:54,974 : INFO : install ok installed 5.5.9+dfsg-1ubuntu4.29

2020-03-03 07:55:54,974 : INFO : Package php5 already installed and upto date.
2020-03-03 07:55:56,978 : INFO : install ok installed 2.4.7-1ubuntu4.22

2020-03-03 07:55:56,979 : INFO : Package apache2 already installed and upto date.
2020-03-03 07:56:00,987 : INFO : Executing 744 on /etc/apache2/mods-available/dir.conf
2020-03-03 07:56:05,995 : INFO : Restarted Service apache2
2020-03-03 07:56:05,997 : INFO :  * Restarting web server apache2
   ...done.

2020-03-03 07:56:05,998 : INFO : Executed and updated content at: /var/www/html/index.php
2020-03-03 07:56:10,005 : INFO : Executing 744 on /var/www/html/index.php
2020-03-03 07:56:14,011 : INFO : Restarted Service apache2
2020-03-03 07:56:14,012 : INFO :  * Restarting web server apache2
   ...done.

2020-03-03 07:56:14,012 : INFO : Updated 3 resources
2020-03-03 07:56:14,012 : INFO : <resource>        <attribute>       <status>
2020-03-03 07:56:14,012 : INFO : /etc/apache2/mods-available/dir.confmode 744          updated
2020-03-03 07:56:14,013 : INFO : /var/www/html/index.phpcontentfile       updated
2020-03-03 07:56:14,013 : INFO : /var/www/html/index.phpmode 744          updated
root@ip-172-31-255-45:~/config-manager#
```


### Verification
The following boxes are configured using the said config tool and tested for best possible scenerios. 


-[host1]: <http://34.235.117.7/>

-[host2]: <http://54.90.197.91/>
 
  
both should output ```Hello World!```

