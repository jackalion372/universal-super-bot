import paramiko

hostname = "ssh-nafibo.alwaysdata.net"
username = "nafibo"
password = "xVQ3576stZ65@5v"

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username=username, password=password, timeout=10)
    
    cmd = "cd universal_super_bot && git pull origin main"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8')
    err = stderr.read().decode('utf-8')
    
    print("STDOUT:", out)
    print("STDERR:", err)
    ssh.close()
except Exception as e:
    print("SSH ERROR:", e)
