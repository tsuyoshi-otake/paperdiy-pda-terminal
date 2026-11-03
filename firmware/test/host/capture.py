# Record raw terminal output of interactive programs in an 80x24 pty with scripted keystrokes.
# Run from fixtures/ (`make fixtures`); the files are replayed by compare_pyte.py.

import os, pty, sys, time, select, struct, fcntl, termios
def capture(argv, keys, out, env_extra=None, wait=0.6):
    pid, fd = pty.fork()
    if pid == 0:
        env = dict(os.environ, TERM="xterm", LANG="C.UTF-8", LC_ALL="C.UTF-8", COLUMNS="80", LINES="24")
        if env_extra: env.update(env_extra)
        os.execvpe(argv[0], argv, env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    data = b""
    def drain(t):
        nonlocal data
        end = time.time() + t
        while time.time() < end:
            r,_,_ = select.select([fd],[],[],0.05)
            if r:
                try: chunk = os.read(fd, 65536)
                except OSError: return
                if not chunk: return
                data += chunk
    drain(wait)
    for k in keys:
        os.write(fd, k.encode()); drain(0.3)
    drain(0.5)
    try: os.kill(pid, 9)
    except: pass
    open(out,"wb").write(data)
    return len(data)
txt = "\n".join(f"{i:03d} 日本語の行 line {i} " + "x"*(i%50) for i in range(60))
open("sample.txt","w").write(txt)
print(capture(["vim","-u","NONE","-N","sample.txt"], ["jjjjj", ":set number\r", "\x06", "Gkkk", "ddp", "u", "/line 30\r", "ihello 漢字\x1b", ":q!\r"], "vim.raw"))
print(capture(["less","sample.txt"], [" ", " ", "b", "q"], "less.raw"))
print(capture(["top","-d","0.5"], ["", "q"], "top.raw", wait=1.2))
print(capture(["nano","sample.txt"], ["\x0e\x0e\x0e", "abc", "\x16", "\x18", "n"], "nano.raw"))
print(capture(["bash","--norc","-i"], ["ls -la / | head -30\r", "printf '\\e[1mbold\\e[0m \\e[44mbluebg\\e[0m \\e[4munder\\e[0m\\n'\r", "seq 1 40\r", "exit\r"], "bash.raw"))
print(capture(["tmux","-f","/dev/null","new","-x","80","-y","24"], ["\x02%", "echo left-right\r", "\x02\"", "echo bottom\r", "\x02d"], "tmux.raw", wait=1.0))
