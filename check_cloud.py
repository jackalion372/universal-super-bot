import paramiko

def test_alwaysdata_ssh():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print("Connecting to ssh-nafibo.alwaysdata.net...")
        ssh.connect(
            hostname="ssh-nafibo.alwaysdata.net",
            port=22,
            username="nafibo",
            password="xVQ3576stZ65@5v",
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        print("SUCCESSFULLY CONNECTED TO ALWAYSDATA SSH!")
        
        # Git pull and run daemon inside universal_super_bot
        stdin, stdout, stderr = ssh.exec_command("cd universal_super_bot && git pull origin main")
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        print("PULL OUTPUT:", out)
        print("PULL ERROR:", err)
        
        ssh.close()
    except Exception as e:
        print("SSH FAILED:", e)

test_alwaysdata_ssh()
