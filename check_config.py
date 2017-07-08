
#!/usr/bin/env python3
#
# Checking config change on important devices (core/distributions) periodically (using crontab)
# and report to network administrators via email.


from collections import OrderedDict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

import sys
import os
import difflib
import smtplib
import socket

try:
    from netmiko import ConnectHandler, ssh_exception   
except ImportError:
    print("\nNetmiko module needs to be installed on your system.")
    print("Download it from https://pypi.python.org/pypi/netmiko/1.1.0")
    print("\nClosing program...\n")
    sys.exit()


# Edit this dictionary to suit your environment
devices_dict = (("D-SW-01", "192.0.2.1"),
                ("D-SW-02", "192.0.2.2"),
                ("CORE-SW-01", "192.0.2.3"),
                ("CORE-SW-02", "192.0.2.4"))


devices_dict = OrderedDict(devices_dict)
report_path = "/root/DeviceConfigFiles/change.txt"
report_time = datetime.now()  # initialize report_time


def compare_config(device_type, device_name, device_ip, cmd):
   
    """ Compare old config with new config """
   
    global report_time
   
    try:
        net_connect = ConnectHandler(device_type=device_type, ip=device_ip, username="check_config", password="SEc43T$$", global_delay_factor=2)
   
    except ssh_exception.NetMikoAuthenticationException:
        with open("/var/log/check_config.log", "a") as f:
            f.write(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + ": {} ({}): Authentication failed\n".format(device_name, device_ip))
   
    except ssh_exception.NetMikoTimeoutException:
        with open("/var/log/check_config.log", "a") as f:
            f.write(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + ": {} ({}): No response/Connection refused\n".format(device_name, device_ip))
   
    except ValueError as exc:
        with open("/var/log/check_config.log", "a") as f:
            f.write(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + ": {} ({}): {}\n".format(device_name, device_ip, str(exc)))
   
    except OSError as exc:
        with open("/var/log/check_config.log", "a") as f:
            f.write(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + ": {} ({}): {}\n".format(device_name, device_ip, str(exc)))
   
    else:
        try:
            output = net_connect.send_command(cmd)
        except OSError as exc:
            with open("/var/log/check_config.log", "a") as f:
                f.write(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + ": {} ({}): {}\n".format(device_name, device_ip, str(exc)))
        else:
            # Create the old config file if it does not already exist
            old_cfg_path = "/root/DeviceConfigFiles/" + device_name + "_old_cfg.txt"
            if not os.path.isfile(old_cfg_path):
                with open(old_cfg_path, "w") as f:
                    f.write(output)
                return
       
            # Create old config and new config lists
            with open(old_cfg_path, "r+") as f:
                old_cfg = f.read().split("\n")[:-1]
                f.seek(0)
                f.write(output)  # replace old content with new content
                f.truncate()
            new_cfg = output.split("\n")[:-1]
       
            # Do not report "ntp clock-period" as change
            for line in old_cfg:
                if "ntp clock-period" in line:
                    old_cfg.remove(line)
                    break
            for line in new_cfg:
                if "ntp clock-period" in line:
                    new_cfg.remove(line)
                    break
       
            # Compare old config with new config
            diff_obj = difflib.ndiff(old_cfg, new_cfg)
            diff_cfg = [line for line in list(diff_obj) if line.startswith("+") or line.startswith("-") or line.startswith("?")]

            # Writing config change to report file
            if len(diff_cfg) > 4:  # if diff_cfg only has "Current configuration: xxxxx bytes", don't report as change
                with open(report_path, "a") as f:
                    if os.path.getsize(report_path) == 0:
                        report_time = datetime.now()
                        f.write("Report generated at: {}\n\n".format(report_time.strftime("%d/%m/%Y %H:%M:%S")))
                    f.write("{} ({}):\n\n".format(device_name, device_ip))
                    for line in diff_cfg:
                        f.write(line + "\n")
                    f.write("\n####################################################################################\n\n")


def sendmail():
   
    """ Send email alert to network admins about configuration changes """
       
    sender = "check_config@example.com"
    recipients = ["network-admin@example.com"]
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = "Configuration Change Report"
    body = "\nDear Network Team,\n\nConfiguration change has been detected. Please find attached file for detail.\n\nThanks,\n"
    content = MIMEText(body, "plain")
    with open(report_path, "r") as f:
        attachment = MIMEText(f.read())
    attachment.add_header("Content-Disposition", "attachment", filename=report_time.strftime("change_%d%m%Y_%H%M%S.txt"))
    msg.attach(attachment)
    msg.attach(content)
    try:
        server = smtplib.SMTP("192.0.2.99", 25)  # specify the IP address of mail server
        server.sendmail(sender, recipients, msg.as_string())
        server.quit()
    except socket.error:
        with open("/var/log/check_config.log", "a") as f:
            f.write(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + ": Could not connect to SMTP server\n")
    else:
        open(report_path, "w").close()  # erase content in report file if send successfully


def main():
   
    """ Main function """
   
    if os.path.isfile(report_path) and os.path.getsize(report_path) > 0:  # check if report file was previously sent successfully. If not then send it
        try:
            sendmail()
        except OSError as exc:
            with open("/var/log/check_config.log", "a") as f:
                f.write(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + ": {}\n".format(str(exc)))
    else:
        for name, ip in devices_dict.items():
            if (name == "CORE-SW-01") or (name == "CORE-SW-02")
                compare_config("juniper_junos", name, ip, "show configuration")
            else:
                compare_config("cisco_ios", name, ip, "show running-config")
   
        # Only send mail if the report file is not empty
        if os.path.getsize(report_path) > 0:
            try:
                sendmail()
            except OSError as exc:
                with open("/var/log/check_config.log", "a") as f:
                    f.write(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + ": {}\n".format(str(exc)))


if __name__ == "__main__":
    main()
