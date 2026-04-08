from models import SystemState, Observation

INITIAL_ALERTS = {
    "task1": "ALERT: Nginx web server is DOWN. HTTP requests on port 80 are failing. Investigate and restore the service immediately.",
    "task2": "ALERT: Application cannot bind to port 8080. Deployment pipeline is blocked. A rogue process appears to be holding the port. Investigate and resolve.",
    "task3": "ALERT: CRITICAL — Disk is 100% full on production server. PostgreSQL database has crashed. Multiple services are degraded. Free disk space and restore the database.",
}


class SREEnvironment:
    def __init__(self):
        self.tasks: dict[str, SystemState] = {}

    def reset(self, task_id: str) -> str:
        self.tasks[task_id] = SystemState(task_id=task_id)
        return INITIAL_ALERTS.get(task_id, f"Unknown task: {task_id}")

    def step(self, task_id: str, command: str) -> tuple[Observation, bool]:
        state = self.tasks[task_id]
        state.step_count += 1

        if state.done:
            return Observation(stdout="Task already completed."), True

        obs = self._dispatch(state, command)

        if state.step_count >= state.max_steps:
            state.done = True

        return obs, state.done

    # ------------------------------------------------------------------ #
    #  Command dispatcher                                                  #
    # ------------------------------------------------------------------ #
    def _dispatch(self, state: SystemState, command: str) -> Observation:
        cmd = command.strip()
        # Strip sudo prefix
        if cmd.startswith("sudo "):
            cmd = cmd[5:].strip()

        # Track diagnostics
        state.diagnostic_commands_run.append(cmd)

        # Route to task handler
        handler = {
            "task1": self._handle_task1,
            "task2": self._handle_task2,
            "task3": self._handle_task3,
        }.get(state.task_id)

        if handler:
            result = handler(state, cmd)
            if result is not None:
                return result

        # Common fallback commands
        return self._handle_common(state, cmd)

    # ------------------------------------------------------------------ #
    #  Task 1: Nginx is down                                               #
    # ------------------------------------------------------------------ #
    def _handle_task1(self, state: SystemState, cmd: str) -> Observation | None:
        # systemctl status nginx
        if "systemctl" in cmd and "status" in cmd and "nginx" in cmd:
            if state.nginx_status == "running":
                return Observation(stdout=(
                    "● nginx.service - A high performance web server\n"
                    "     Loaded: loaded (/lib/systemd/system/nginx.service; enabled)\n"
                    "     Active: active (running) since Tue 2026-04-08 10:00:00 UTC\n"
                    "   Main PID: 1234 (nginx)\n"
                    "      Tasks: 2 (limit: 4915)\n"
                    "     Memory: 5.2M\n"
                    "     CGroup: /system.slice/nginx.service"
                ))
            return Observation(stdout=(
                "● nginx.service - A high performance web server\n"
                "     Loaded: loaded (/lib/systemd/system/nginx.service; enabled)\n"
                "     Active: inactive (dead) since Tue 2026-04-08 08:15:33 UTC\n"
                "   Main PID: 1234 (code=exited, status=1/FAILURE)\n"
                "\nApr 08 08:15:33 prod-web-01 systemd[1]: nginx.service: Failed with result 'exit-code'."
            ))

        # systemctl start/restart nginx
        if "systemctl" in cmd and ("start" in cmd or "restart" in cmd) and "nginx" in cmd:
            state.nginx_status = "running"
            state.done = True
            return Observation(stdout="● nginx.service - Starting A high performance web server...\n● nginx.service - Started A high performance web server.")

        # nginx -t (config test)
        if cmd.startswith("nginx") and "-t" in cmd:
            return Observation(stdout="nginx: the configuration file /etc/nginx/nginx.conf syntax is ok\nnginx: configuration file /etc/nginx/nginx.conf test is successful")

        # curl localhost
        if "curl" in cmd and ("localhost" in cmd or "127.0.0.1" in cmd):
            if state.nginx_status == "running":
                return Observation(stdout="<html>\n<head><title>Welcome to nginx!</title></head>\n<body>\n<h1>Welcome to nginx!</h1>\n</body>\n</html>")
            return Observation(stdout="", stderr="curl: (7) Failed to connect to localhost port 80: Connection refused")

        # cat nginx conf
        if "cat" in cmd and "nginx" in cmd:
            return Observation(stdout=(
                "user www-data;\n"
                "worker_processes auto;\n"
                "pid /run/nginx.pid;\n\n"
                "events {\n    worker_connections 768;\n}\n\n"
                "http {\n    sendfile on;\n    tcp_nopush on;\n"
                "    include /etc/nginx/mime.types;\n"
                "    default_type application/octet-stream;\n\n"
                "    server {\n        listen 80 default_server;\n"
                "        root /var/www/html;\n        index index.html;\n    }\n}"
            ))

        return None

    # ------------------------------------------------------------------ #
    #  Task 2: Port 8080 blocked by zombie process                         #
    # ------------------------------------------------------------------ #
    def _handle_task2(self, state: SystemState, cmd: str) -> Observation | None:
        # netstat / ss
        if cmd.startswith("netstat") or cmd.startswith("ss"):
            if state.zombie_pid_alive:
                return Observation(stdout=(
                    "Active Internet connections (only servers)\n"
                    "Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name\n"
                    "tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      512/sshd\n"
                    "tcp        0      0 0.0.0.0:8080            0.0.0.0:*               LISTEN      6789/zombie_proc\n"
                    "tcp        0      0 0.0.0.0:443             0.0.0.0:*               LISTEN      890/nginx"
                ))
            return Observation(stdout=(
                "Active Internet connections (only servers)\n"
                "Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name\n"
                "tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      512/sshd\n"
                "tcp        0      0 0.0.0.0:443             0.0.0.0:*               LISTEN      890/nginx"
            ))

        # lsof -i :8080
        if "lsof" in cmd and "8080" in cmd:
            if state.zombie_pid_alive:
                return Observation(stdout=(
                    "COMMAND       PID   USER   FD   TYPE DEVICE SIZE/OFF NODE NAME\n"
                    "zombie_pr  6789   root    3u  IPv4  12345      0t0  TCP *:8080 (LISTEN)"
                ))
            return Observation(stdout="")

        # ps aux / ps -ef
        if cmd.startswith("ps"):
            if state.zombie_pid_alive:
                return Observation(stdout=(
                    "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
                    "root         1  0.0  0.1 169332 11204 ?        Ss   08:00   0:02 /sbin/init\n"
                    "root       512  0.0  0.0  72304  5576 ?        Ss   08:00   0:00 /usr/sbin/sshd\n"
                    "root      6789  0.0  0.0      0     0 ?        Z    08:05   0:00 [zombie_proc] <defunct>\n"
                    "www-data   890  0.0  0.2 141112  9640 ?        Ss   08:00   0:01 nginx: master process\n"
                    "root      1001  0.0  0.0  21564  4356 pts/0    Ss   09:00   0:00 -bash"
                ))
            return Observation(stdout=(
                "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
                "root         1  0.0  0.1 169332 11204 ?        Ss   08:00   0:02 /sbin/init\n"
                "root       512  0.0  0.0  72304  5576 ?        Ss   08:00   0:00 /usr/sbin/sshd\n"
                "www-data   890  0.0  0.2 141112  9640 ?        Ss   08:00   0:01 nginx: master process\n"
                "root      1001  0.0  0.0  21564  4356 pts/0    Ss   09:00   0:00 -bash"
            ))

        # kill -9 6789  (the correct PID)
        if "kill" in cmd and "6789" in cmd:
            state.zombie_pid_alive = False
            state.port_8080_free = True
            state.done = True
            return Observation(stdout="")

        # kill with wrong PID
        if "kill" in cmd:
            # Extract PID from command
            parts = cmd.split()
            for p in parts:
                if p.isdigit() and p != "9":
                    return Observation(stdout="", stderr=f"bash: kill: ({p}) - No such process")
            return Observation(stdout="", stderr="kill: usage: kill [-s sigspec | -n signum | -sigspec] pid | jobspec ... or kill -l [sigspec]")

        # systemctl status for any service — show them everything is fine
        if "systemctl" in cmd and "status" in cmd:
            service = cmd.split()[-1] if len(cmd.split()) > 2 else "unknown"
            return Observation(stdout=f"● {service}.service\n     Active: active (running)")

        return None

    # ------------------------------------------------------------------ #
    #  Task 3: Disk 100% full + database crashed                           #
    # ------------------------------------------------------------------ #
    def _handle_task3(self, state: SystemState, cmd: str) -> Observation | None:
        # df -h
        if cmd.startswith("df"):
            if state.large_log_exists:
                return Observation(stdout=(
                    "Filesystem      Size  Used Avail Use% Mounted on\n"
                    "/dev/sda1        50G   50G     0 100% /\n"
                    "tmpfs           2.0G     0  2.0G   0% /dev/shm\n"
                    "/dev/sda2       200G   45G  155G  23% /data"
                ))
            return Observation(stdout=(
                "Filesystem      Size  Used Avail Use% Mounted on\n"
                "/dev/sda1        50G   23G   27G  45% /\n"
                "tmpfs           2.0G     0  2.0G   0% /dev/shm\n"
                "/dev/sda2       200G   45G  155G  23% /data"
            ))

        # du -sh /var/log
        if "du" in cmd and "/var/log" in cmd:
            if state.large_log_exists:
                return Observation(stdout=(
                    "15G\t/var/log/app.log\n"
                    "24K\t/var/log/syslog\n"
                    "12K\t/var/log/auth.log\n"
                    "8.0K\t/var/log/kern.log\n"
                    "4.0K\t/var/log/dpkg.log"
                ))
            return Observation(stdout=(
                "24K\t/var/log/syslog\n"
                "12K\t/var/log/auth.log\n"
                "8.0K\t/var/log/kern.log\n"
                "4.0K\t/var/log/dpkg.log"
            ))

        # find large files
        if "find" in cmd and ("size" in cmd or "1G" in cmd):
            if state.large_log_exists:
                return Observation(stdout="/var/log/app.log")
            return Observation(stdout="")

        # ls /var/log
        if "ls" in cmd and "/var/log" in cmd:
            if state.large_log_exists:
                return Observation(stdout=(
                    "total 15G\n"
                    "-rw-r--r-- 1 root root  15G Apr  8 08:00 app.log\n"
                    "-rw-r--r-- 1 root root  24K Apr  8 09:00 syslog\n"
                    "-rw-r--r-- 1 root root  12K Apr  8 09:00 auth.log\n"
                    "-rw-r--r-- 1 root root 8.0K Apr  8 08:30 kern.log"
                ))
            return Observation(stdout=(
                "total 48K\n"
                "-rw-r--r-- 1 root root  24K Apr  8 09:00 syslog\n"
                "-rw-r--r-- 1 root root  12K Apr  8 09:00 auth.log\n"
                "-rw-r--r-- 1 root root 8.0K Apr  8 08:30 kern.log"
            ))

        # rm or truncate the log file
        if ("rm" in cmd or "truncate" in cmd) and "app.log" in cmd:
            if state.large_log_exists:
                state.large_log_exists = False
                state.disk_usage_percent = 45
                # Check if task is fully done
                if state.db_status == "running":
                    state.done = True
                return Observation(stdout="")
            return Observation(stdout="", stderr="rm: cannot remove '/var/log/app.log': No such file or directory")

        # cat /var/log/app.log
        if "cat" in cmd and "app.log" in cmd:
            if state.large_log_exists:
                return Observation(stdout=(
                    "[2026-04-08 00:00:01] ERROR: Connection pool exhausted\n"
                    "[2026-04-08 00:00:01] ERROR: Connection pool exhausted\n"
                    "[2026-04-08 00:00:02] ERROR: Connection pool exhausted\n"
                    "... (repeating, file is 15GB) ..."
                ))
            return Observation(stdout="", stderr="cat: /var/log/app.log: No such file or directory")

        # systemctl start/restart postgresql
        if "systemctl" in cmd and ("start" in cmd or "restart" in cmd) and ("postgresql" in cmd or "postgres" in cmd):
            if state.disk_usage_percent >= 90:
                return Observation(
                    stdout="",
                    stderr="Job for postgresql.service failed because the control process exited with error code.\nSee \"systemctl status postgresql.service\" and \"journalctl -xe\" for details.\nHint: Disk is full — free space before starting the database."
                )
            state.db_status = "running"
            if not state.large_log_exists:
                state.done = True
            return Observation(stdout="● postgresql.service - PostgreSQL RDBMS\n     Active: active (running) since Tue 2026-04-08 10:30:00 UTC\n   Main PID: 2345 (postgres)")

        # systemctl status postgresql
        if "systemctl" in cmd and "status" in cmd and ("postgresql" in cmd or "postgres" in cmd):
            if state.db_status == "running":
                return Observation(stdout=(
                    "● postgresql.service - PostgreSQL RDBMS\n"
                    "     Loaded: loaded (/lib/systemd/system/postgresql.service; enabled)\n"
                    "     Active: active (running) since Tue 2026-04-08 10:30:00 UTC\n"
                    "   Main PID: 2345 (postgres)"
                ))
            return Observation(stdout=(
                "● postgresql.service - PostgreSQL RDBMS\n"
                "     Loaded: loaded (/lib/systemd/system/postgresql.service; enabled)\n"
                "     Active: failed (Result: exit-code) since Tue 2026-04-08 08:00:00 UTC\n"
                "   Main PID: 2345 (code=exited, status=1/FAILURE)\n"
                "\nApr 08 08:00:00 prod-db-01 postgresql[2345]: FATAL: could not write lock file: No space left on device"
            ))

        # journalctl for postgresql
        if "journalctl" in cmd and ("postgresql" in cmd or "postgres" in cmd):
            return Observation(stdout=(
                "-- Logs begin at Tue 2026-04-08 00:00:00 UTC --\n"
                "Apr 08 08:00:00 prod-db-01 postgresql[2345]: FATAL: could not write lock file: No space left on device\n"
                "Apr 08 08:00:00 prod-db-01 systemd[1]: postgresql.service: Main process exited, code=exited, status=1/FAILURE"
            ))

        return None

    # ------------------------------------------------------------------ #
    #  Common commands (fallback for all tasks)                             #
    # ------------------------------------------------------------------ #
    def _handle_common(self, state: SystemState, cmd: str) -> Observation:
        # echo
        if cmd.startswith("echo"):
            text = cmd[5:].strip().strip('"').strip("'")
            return Observation(stdout=text)

        # whoami
        if cmd == "whoami":
            return Observation(stdout="root")

        # hostname
        if cmd == "hostname":
            hosts = {"task1": "prod-web-01", "task2": "prod-app-01", "task3": "prod-db-01"}
            return Observation(stdout=hosts.get(state.task_id, "prod-server"))

        # uname
        if cmd.startswith("uname"):
            return Observation(stdout="Linux prod-server 5.15.0-91-generic #101-Ubuntu SMP x86_64 GNU/Linux")

        # uptime
        if cmd == "uptime":
            return Observation(stdout=" 10:30:00 up 45 days,  3:22,  1 user,  load average: 2.15, 1.89, 1.45")

        # ls (generic)
        if cmd.startswith("ls"):
            return Observation(stdout="bin  boot  dev  etc  home  lib  media  mnt  opt  proc  root  run  sbin  srv  sys  tmp  usr  var")

        # pwd
        if cmd == "pwd":
            return Observation(stdout="/root")

        # id
        if cmd == "id":
            return Observation(stdout="uid=0(root) gid=0(root) groups=0(root)")

        # free -h
        if cmd.startswith("free"):
            return Observation(stdout=(
                "              total        used        free      shared  buff/cache   available\n"
                "Mem:          7.8Gi       3.2Gi       1.1Gi       256Mi       3.5Gi       4.0Gi\n"
                "Swap:         2.0Gi       128Mi       1.9Gi"
            ))

        # top (just header)
        if cmd.startswith("top"):
            return Observation(stdout=(
                "top - 10:30:00 up 45 days,  3:22,  1 user,  load average: 2.15, 1.89, 1.45\n"
                "Tasks: 112 total,   1 running, 110 sleeping,   0 stopped,   1 zombie\n"
                "%Cpu(s):  5.2 us,  1.3 sy,  0.0 ni, 93.1 id,  0.3 wa,  0.0 hi,  0.1 si"
            ))

        # date
        if cmd == "date":
            return Observation(stdout="Tue Apr  8 10:30:00 UTC 2026")

        # Unknown command
        base = cmd.split()[0] if cmd.split() else cmd
        return Observation(stdout="", stderr=f"bash: {base}: command not found")
