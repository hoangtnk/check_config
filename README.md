# Description
This tool is used to report any configuration changes on network devices to administrators via email. It will point out the differences of the configuration before and after change, so we can easily track who is doing what on which device.

# Installation
Install the following python modules:
```
pip3 install cryptography
pip3 install paramiko
pip3 install netmiko
```

# Usage
We should schedule this script to run periodically every day. Below is an crontab example of scheduling it to run every 15 minutes:
```
*/15 * * * * /root/scripts/check_config.py
```
