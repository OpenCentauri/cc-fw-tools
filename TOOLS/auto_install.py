#!/usr/bin/env python3

# Import ssh
from scp import SCPClient
import paramiko
import os
import sys
import time
import getpass
import json

# Create hostname, username, ip struct to save

class PrinterSettings:
    def __init__(self, hostname, username, ip, port):
        self.hostname = hostname
        self.username = username
        self.ip = ip
        self.port = port

    def save_config(self):
        with open('auto_install.cfg', 'w') as file:
            file.write(f'{self.hostname},{self.username},{self.ip},{self.port}')

    def load_config(self):
        with open('auto_install.cfg', 'r') as file:
            data = file.read().split(',')
            self.hostname = data[0]
            self.username = data[1]
            self.ip = data[2]
            self.port = data[3]

def handle_progress(filename: bytes, size: int, sent: int):
    print(f'{filename.decode("utf-8")}: {sent/size*100:.2f}%')

if __name__ == "__main__":
    firmware_path = 'update/update.swu'
    if os.path.exists('update/manifest.json'):
        try:
            with open('update/manifest.json', encoding='utf-8') as file:
                firmware_path = json.load(file)['final_firmware']['path']
        except (KeyError, json.JSONDecodeError):
            print('update/manifest.json does not contain a final firmware path')
            sys.exit(1)

    if not os.path.exists(firmware_path):
        print(f'{firmware_path} not found')
        sys.exit(1)

    # Connect to the printer
    
    # Check if auto_install.cfg exists and load values else ask for input
    if os.path.exists('auto_install.cfg'):
        printer_settings = PrinterSettings('', '', '', '')
        printer_settings.load_config()
    else:
        hostname = input('Enter the pc hostname: ')
        username = input('Enter the username: ')
        ip = input('Enter the ip: ')
        port = input('Enter the port: ')
        printer_settings = PrinterSettings(hostname, username, ip, port)
        printer_settings.save_config()

    # Connect to the printer
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(printer_settings.ip, port=printer_settings.port, username=printer_settings.username, password=getpass.getpass(), timeout=5)

    print('Connected to the printer')

    print(f'Copying {firmware_path} to /mnt/UDISK/update.swu')

    scp = SCPClient(ssh.get_transport(), progress=handle_progress)
    scp.put(firmware_path, remote_path='/mnt/UDISK/update.swu', recursive=True)
    scp.close()

    # Compare the local firmware with /mnt/UDISK/update.swu. If they don't match, try again 3 times.
    for i in range(3):
        # Get md5sum of both files
        stdin, stdout, stderr = ssh.exec_command('md5sum /mnt/UDISK/update.swu')
        md5sum_remote = stdout.read().decode('utf-8').split(' ')[0]
        md5sum_local = os.popen(f'md5sum "{firmware_path}"').read().split(' ')[0]

        print(f'MD5 sum of local:  {md5sum_local}')
        print(f'MD5 sum of remote: {md5sum_remote}')

        # If they match, break and run swupdate
        if md5sum_remote == md5sum_local:
            print('MD5 sums match... Running swupdate')
            # Check fw_printenv boot_partition to see if it's bootA or bootB
            stdin, stdout, stderr = ssh.exec_command('fw_printenv boot_partition')
            current_boot_partition = stdout.read().decode('utf-8').split('=')[1].strip()

            # If current_boot_partition is bootA, run swupdate with bootB. example: now_A_next_B
            boot_partition = "now_A_next_B" if current_boot_partition == "bootA" else "now_B_next_A"
            print(f'Current boot partition: {current_boot_partition}')
            print(f'Running swupdate with boot partition: {boot_partition}')
            ssh.exec_command(f'swupdate_cmd.sh -i /mnt/UDISK/update.swu -e stable,{boot_partition} -k /etc/swupdate_public.pem')
            print("Update started... Please wait for the printer to reboot")
            # wait for the update to complete, the printer to reboot and then close the connection
            # Count down from 60 seconds
            for i in range(60, 0, -1):
                print(f'{i} seconds remaining')
                # Check if we have lost ssh connection
                if ssh.get_transport().is_active() == False:
                    print('Connection lost... Printer is probably rebooting')
                    ssh.close()
                    print('Connection closed')
                    break
                time.sleep(1)
            break
        else:
            # Delete the file and try again
            print(f'MD5 sums do not match... Trying again. Current attempt: {i+1}')
            ssh.exec_command('rm /mnt/UDISK/update.swu')
            scp.put(firmware_path, remote_path='/mnt/UDISK/update.swu', recursive=True)
            scp.close()
