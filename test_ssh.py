import paramiko

hosts = ["ssh-nafibo.alwaysdata.net", "nafibo.alwaysdata.net"]
for h in hosts:
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(h, username="nafibo", password="xVQ3576stZ65@5v", timeout=5)
        print(f"SUCCESS CONNECTED TO {h}!")
        ssh.close()
    except Exception as e:
        print(f"FAILED {h}: {e}")
