# LLM / AI Infra 学习笔记

## 第 1 章：Linux 与计算机系统基础
### 1.11 ～ 1.14

> 目标：完成 Linux 基础章节收尾，把进程、内存、FD、Kernel 接口、systemd 与基础排障串成一套可实际使用的运维心智模型。

---

# 1.11 File Descriptor

**File Descriptor（FD）**，中文是**文件描述符**。

可以理解成：

> Process 内部用于引用 Kernel 中某个已打开资源的整数编号。

例如：

```text
FD 3 → hello.txt
FD 4 → socket
FD 5 → pipe
```

程序执行：

```python
f = open("hello.txt")
```

概念上：

```text
Program
   ↓
open()
   ↓
Kernel
   ↓
返回整数 FD
```

之后程序可以：

```text
read(FD)
write(FD)
close(FD)
```

而不需要每次重新解析完整路径。

## FD 是每个 Process 自己的编号

例如：

```text
Process A
FD 3 → a.txt

Process B
FD 3 → socket
```

不会冲突。

每个 Process 可以粗略理解为有一张：

```text
FD Table

0 → stdin
1 → stdout
2 → stderr
3 → hello.txt
4 → socket
5 → pipe
```

FD 可以理解成这张表的索引。

## stdin / stdout / stderr

```text
0 = stdin
1 = stdout
2 = stderr
```

- stdin：standard input，标准输入
- stdout：standard output，标准输出
- stderr：standard error，标准错误输出

例如：

```bash
echo hello
```

概念上相当于：

```text
write(1, "hello\n", ...)
```

## 查看当前 Shell 的 FD

```bash
ls -l /proc/$$/fd
```

可能看到：

```text
0 -> /dev/pts/0
1 -> /dev/pts/0
2 -> /dev/pts/0
```

## Redirection

```bash
echo hello > out.txt
```

本质上：

```text
FD 1
原来 → Terminal
现在 → out.txt
```

stderr：

```bash
ls /notexist 2> error.txt
```

`2>` 表示把 FD 2 重定向到文件。

常见：

```bash
command > output.log 2>&1
```

表示：

```text
FD 1 → output.log
FD 2 → FD 1 当前指向的位置
```

所以 stdout 和 stderr 最终都进入 output.log。

## FD 可以代表很多资源

FD 不只代表普通文件，还可以代表：

```text
Regular File
Directory
Terminal
Pipe
Socket
Device
eventfd
epoll
...
```

Unix/Linux 常说：

> Everything is a file.

更准确地理解是：

> Linux 尽量为不同资源提供类似文件的统一访问接口。

即：

```text
open
read
write
close
```

## Socket 也是 FD

Web Server 可能：

```text
FD 3 → Listening Socket
FD 4 → Client A
FD 5 → Client B
FD 6 → Client C
```

高并发网络服务会消耗大量 FD。

## Pipe 也是 FD

例如：

```bash
ps aux | grep python
```

概念上：

```text
ps aux
 stdout
   │
   ↓
 Pipe
   │
   ↓
 stdin
grep python
```

## Device 也可以通过 FD 操作

例如：

```text
/dev/null
/dev/zero
/dev/tty
```

这些不是普通磁盘文件，但通过类似文件的接口暴露。

## open / read / write / close

open 大致：

```text
User Space
    │
    │ open syscall
    ↓
Kernel
    ├─ 查找路径
    ├─ 检查权限
    ├─ 找到文件对象
    ├─ 建立打开状态
    └─ 在 FD Table 分配编号
```

read / write：

```text
read(FD)
write(FD)
```

Kernel 根据当前 Process 的 FD Table 找到目标资源。

close：

```text
close(FD)
```

表示 Process 不再需要该 FD。

## FD Leak

**File Descriptor Leak**，即 FD 泄漏。

例如：

```text
每次请求打开一个文件
↓
从不 close
↓
FD 数不断增长
↓
Too many open files
```

注意，Socket、Pipe 等也会占 FD。

## FD Limit

```bash
ulimit -n
```

查看当前打开文件数限制。

Soft Limit：

```bash
ulimit -Sn
```

Hard Limit：

```bash
ulimit -Hn
```

## 查看某 Process 的 FD

```bash
ls /proc/<PID>/fd
ls /proc/<PID>/fd | wc -l
ls -l /proc/<PID>/fd
```

## lsof

**lsof = list open files**

安装：

```bash
sudo apt install lsof
```

查看：

```bash
lsof -p <PID>
```

## File Offset

普通文件打开后，Kernel 通常还维护：

```text
当前文件读写位置
打开模式
状态 Flags
```

即 open file state。

## fork 后的 FD

fork 后，Child 通常会继承 Parent 的 FD。

```text
Parent FD 3
      \
       → 同一个底层打开文件状态
      /
Child FD 3
```

## Redirection 与 exec

```bash
python3 app.py > app.log
```

可以粗略理解为：

```text
bash
↓
fork
↓
child
↓
把 FD 1 改到 app.log
↓
exec python3
↓
python3 继承 FD 1
```

所以 Python 仍只需要 write(1, ...)。

---

# 1.12 /proc 与 /sys

结论：

> `/proc` 和 `/sys` 看起来像普通目录，但里面大量内容并不是 SSD 上的普通文件，而是 Kernel 动态暴露给 User Space 的接口。

## Virtual Filesystem

**Virtual Filesystem**，中文：**虚拟文件系统**。

可以理解成：

> 看起来像文件和目录，但数据不一定真正持久存储在磁盘。

例如：

```bash
cat /proc/meminfo
```

其内容由 Kernel 根据当前状态动态提供。

## procfs

`/proc` 对应：

**procfs**

可以理解成：

> Kernel 用于暴露 Process 与系统运行状态的虚拟文件系统。

## /proc/PID

假设：

```text
PID = 1234
```

那么：

```text
/proc/1234/
```

就是该 Process 的 Kernel 状态接口。

常见：

```text
cmdline
cwd
environ
exe
fd
maps
status
stat
task
limits
```

### /proc/PID/cmdline

```bash
tr '\0' ' ' < /proc/<PID>/cmdline
```

查看启动参数。

### /proc/PID/exe

```bash
ls -l /proc/<PID>/exe
```

查看当前执行的程序文件。

### /proc/PID/cwd

```bash
ls -l /proc/<PID>/cwd
```

查看 Current Working Directory。

### /proc/PID/fd

```bash
ls -l /proc/<PID>/fd
```

查看已打开 FD。

### /proc/PID/status

```bash
cat /proc/<PID>/status
```

重点字段：

```text
Name
State
Pid
PPid
Threads
VmSize
VmRSS
voluntary_ctxt_switches
nonvoluntary_ctxt_switches
```

### /proc/PID/maps

```bash
cat /proc/<PID>/maps
```

查看 Process 的 Virtual Address Space Mapping。

可能包含：

```text
程序代码
Shared Libraries
Heap
Stack
mmap 文件
```

### /proc/PID/task

```bash
ls /proc/<PID>/task
```

每个目录对应一个 Thread。

### /proc/PID/limits

```bash
cat /proc/<PID>/limits
```

可查看：

```text
Max open files
Max processes
Max stack size
...
```

### /proc/PID/environ

```bash
tr '\0' '\n' < /proc/<PID>/environ
```

可查看环境变量。

注意：环境变量可能包含 Token、密码、密钥等敏感信息。

## /proc 的系统级信息

```bash
cat /proc/cpuinfo
cat /proc/meminfo
cat /proc/loadavg
cat /proc/uptime
cat /proc/version
```

## /proc/sys

`/proc/sys` 可查看和修改部分 Kernel Runtime Parameters。

例如：

```bash
cat /proc/sys/vm/overcommit_memory
cat /proc/sys/net/ipv4/ip_forward
```

## sysctl

**sysctl** 是查看/设置部分 Kernel 参数的工具。

```bash
sysctl vm.overcommit_memory
sysctl net.ipv4.ip_forward
```

当前阶段以查看为主，不要随意修改 Kernel 参数。

## sysfs

`/sys` 对应：

**sysfs**

可以理解成：

> Kernel 用于暴露设备、驱动、总线及 Kernel Object 关系的虚拟文件系统。

粗略区分：

```text
/proc
→ 更偏 Process / 系统运行状态

/sys
→ 更偏 Device / Driver / Kernel Object
```

## /sys/class

```bash
ls /sys/class
```

可能看到：

```text
net
block
tty
power_supply
...
```

## 网络设备

```bash
ls /sys/class/net
```

可能看到：

```text
eth0
lo
```

查看 MTU：

```bash
cat /sys/class/net/eth0/mtu
```

## Block Device

```bash
ls /sys/block
```

查看 Kernel 识别的块设备。

## Kernel Module

```bash
ls /sys/module | head
```

Kernel Module 可以动态提供：

```text
Driver
Filesystem
Network Feature
```

## PCIe 初步

PCIe 可以先理解成：

> CPU 与 GPU、NIC、NVMe 等高速设备连接的重要硬件总线。

以后会经常看：

```text
/sys/bus/pci/devices/
```

## AI Infra 中的意义

以后排查 GPU 节点：

```text
Hardware
↓
PCIe Device
↓
Kernel Driver
↓
/sys
↓
Device Node
↓
CUDA
↓
PyTorch
```

---

# 1.13 systemd

**systemd**

可以理解成：

> 现代 Linux 发行版中常见的系统和服务管理器。

## 为什么需要 systemd

Linux 启动后可能要自动运行：

```text
SSH Server
Docker
Database
Monitoring Agent
Web Server
```

需要统一负责：

```text
启动
停止
重启
依赖
自动启动
状态
日志
```

## systemd 与 PID 1

现代 Linux 常见：

```text
PID 1 = systemd
```

查看：

```bash
ps -p 1 -o pid,comm,args
```

概念：

```text
Kernel 启动
↓
systemd
↓
各种 Service
```

## Service

Service 可以理解成：

> 长期运行，为系统或其他应用提供功能的后台程序。

例如：

```text
sshd
docker
nginx
postgresql
```

## Daemon

**Daemon**，中文：**守护进程**。

本质仍然是 Process。

## systemctl

查看：

```bash
systemctl status ssh
```

启动：

```bash
sudo systemctl start nginx
```

停止：

```bash
sudo systemctl stop nginx
```

重启：

```bash
sudo systemctl restart nginx
```

## start 与 enable

```text
start
→ 现在立刻启动

enable
→ 配置以后自动启动
```

常见：

```bash
sudo systemctl enable --now nginx
```

表示 enable + start。

## Unit

systemd 管理对象叫：

**Unit**

常见：

```text
.service
.socket
.target
.timer
.mount
```

## Unit File

示例：

```ini
[Unit]
Description=My Test Service

[Service]
ExecStart=/usr/bin/python3 /opt/app.py

[Install]
WantedBy=multi-user.target
```

### [Unit]

描述 Unit、依赖和启动顺序。

### [Service]

定义 Service 如何运行。

### [Install]

主要用于 enable 时决定启动关系。

## systemd 最终仍然在管理 Process

```text
systemd
↓
创建 Process
↓
nginx / python / docker
↓
Kernel Scheduler
↓
CPU
```

所以 PID、Thread、FD、Memory、Signal 等概念全部继续适用。

## Main PID

```bash
systemctl status <service>
```

可能看到：

```text
Main PID: 1234
```

这个就是普通 Linux PID。

## journalctl

查看 Service 日志：

```bash
journalctl -u ssh
```

最近 50 条：

```bash
journalctl -u ssh -n 50
```

实时跟踪：

```bash
journalctl -u ssh -f
```

## Restart Policy

例如：

```ini
[Service]
Restart=on-failure
```

表示异常失败时自动重新启动。

## Environment

```ini
Environment="PORT=8000"
```

给 Service Process 设置环境变量。

## WorkingDirectory

```ini
WorkingDirectory=/opt/myapp
```

定义 Process 启动后的 Current Working Directory。

## User

```ini
User=myapp
```

让 Service 使用指定用户运行。

## systemd 与 cgroup

现代 systemd 也大量使用 cgroup：

```text
systemd Service
↓
一组 Process
↓
cgroup
↓
CPU / Memory / Process 资源管理
```

## WSL systemd

检查：

```bash
ps -p 1 -o comm=
```

如果输出：

```text
systemd
```

说明当前 WSL 中 systemd 已启用。

---

# 1.14 Linux 基础排障

目标：

> 把前面所有知识变成一套标准 Troubleshooting 顺序。

总框架：

```text
现象
 ↓
系统层？
进程层？
资源层？
服务层？
 ↓
CPU / Memory / I/O / FD / Network
 ↓
找到具体 PID
 ↓
查看 PID 状态
 ↓
继续向 Kernel / Application 定位
```

## 第一轮健康检查

```bash
uptime
free -h
df -h
top
```

分别回答：

```text
uptime
→ Load 高不高？

free -h
→ RAM 紧不紧？

df -h
→ Filesystem 是否满？

top
→ 谁在吃 CPU / Memory？
```

## Load Average

```bash
uptime
```

前三个数字分别约对应：

```text
1 min
5 min
15 min
```

Load 高不一定 CPU 高，也可能有大量任务在等 I/O。

## vmstat

```bash
vmstat 1
```

重点字段：

| 字段 | 含义 |
|---|---|
| r | Runnable，等待 CPU |
| b | Blocked，阻塞等待资源 |
| cs | Context Switch |
| us | User Space CPU |
| sy | Kernel Space CPU |
| id | Idle CPU |
| wa | I/O Wait |
| si | Swap In |
| so | Swap Out |

## CPU 高怎么查

```bash
top
```

或者：

```bash
ps aux --sort=-%cpu | head
```

找到 PID：

```bash
ps -p <PID> -o pid,ppid,stat,%cpu,%mem,nlwp,comm,args
```

看 Thread：

```bash
top -H -p <PID>
ps -T -p <PID>
```

如果：

```text
r 很高
cs 很高
```

要怀疑：

```text
Thread 太多
CPU Contention
Oversubscription
```

## Memory 高怎么查

```bash
free -h
```

重点看：

```text
available
```

找吃内存的 Process：

```bash
ps aux --sort=-%mem | head
```

或：

```bash
ps -eo pid,ppid,%mem,rss,vsz,comm --sort=-rss | head
```

查看详情：

```bash
grep -E "VmSize|VmRSS|VmSwap|Threads" /proc/<PID>/status
```

## Swap 压力

```bash
vmstat 1
```

关注：

```text
si
so
```

持续高可能意味着明显 Memory Pressure。

## 怀疑 OOM

```bash
dmesg | grep -i -E "out of memory|killed process|oom"
```

如果看到：

```text
Killed process <PID>
```

说明 Kernel OOM Killer 杀了该进程。

## Disk Space

```bash
df -h
```

如果 Filesystem 100% 满：

```text
日志写失败
数据库异常
临时文件失败
Container 启动失败
```

## df vs du

```text
df
→ 整个 Filesystem 使用情况

du
→ 具体目录 / 文件占用
```

例如：

```bash
du -sh /var/log
du -h /var/log | sort -h | tail
```

## Deleted-but-open File

文件已经 rm，但 Process 仍持有 FD 时，磁盘空间可能不会释放。

查看：

```bash
lsof +L1
```

或：

```bash
lsof | grep deleted
```

## I/O 问题

```bash
vmstat 1
```

关注：

```text
wa
b
```

进一步：

```bash
sudo apt install sysstat
iostat -xz 1
```

用于观察设备忙碌、延迟、吞吐等。

## FD 问题

典型：

```text
Too many open files
```

查看：

```bash
ulimit -n
cat /proc/<PID>/limits
ls /proc/<PID>/fd | wc -l
ls -l /proc/<PID>/fd
lsof -p <PID>
```

## Service 起不来

```bash
systemctl status <service>
journalctl -u <service> -n 100
```

failed 只是结果，真正原因可能是：

```text
配置错误
权限问题
端口占用
文件不存在
FD Limit
Memory
依赖服务
```

## Process 是否活着

```bash
pgrep -a <name>
```

## 程序“卡住”怎么办

```bash
ps -p <PID> -o pid,stat,%cpu,%mem,comm,args
```

CPU 0% 不代表进程死了。

可能正在：

```text
sleep
wait
I/O
lock
network
```

进一步：

```bash
sudo strace -p <PID>
```

可能看到：

```text
read(...)
futex(...)
poll(...)
epoll_wait(...)
```

## D State

`D` 表示：

**Uninterruptible Sleep**

通常和：

```text
I/O
Device
Filesystem
```

有关。

大量 Process 长时间 D State，同时 Load 高，很值得怀疑底层 I/O。

## Socket / Port 初步排障

```bash
ss -lntp
```

参数：

```text
-l = listening
-n = 直接显示数字
-t = TCP
-p = Process
```

如果端口 8000 被占：

```bash
ss -lntp | grep ':8000'
```

## Kernel 日志

```bash
dmesg | tail -100
```

可能看到：

```text
OOM
Device Error
Filesystem Error
Driver Error
Network Interface Change
```

以后 GPU Driver 排障也会频繁使用。

## “程序突然挂了”标准流程

```text
① Process 还在吗？
```

```bash
pgrep -a <process>
```

```text
② Service / Application Log
```

```bash
systemctl status <service>
journalctl -u <service> -n 100
```

```text
③ Kernel 是否杀掉它？
```

```bash
dmesg | grep -i -E "oom|killed process"
```

```text
④ Memory / Disk / FD 是否异常？
```

```bash
free -h
df -h
```

## “服务器很慢”标准流程

```bash
uptime
top
vmstat 1
```

然后根据方向继续：

```text
CPU
→ ps / top -H

Memory
→ free / /proc/PID/status

I/O
→ iostat

FD
→ /proc/PID/fd / lsof

Service
→ systemctl / journalctl
```

## Troubleshooting

**Troubleshooting**

中文：

**故障排查**

不是“会背很多命令”，而是：

> 根据现象提出假设，再用数据验证或排除。

## Observability

**Observability**

中文：

**可观测性**

可以理解成：

> 能否通过系统暴露的数据理解内部正在发生什么。

当前最基础的 Observability 来源：

```text
/proc
/sys
dmesg
ps
vmstat
journalctl
```

以后 Prometheus / Grafana / OpenTelemetry 会把这些能力规模化。

## AI Infra 场景：GPU Utilization 低

如果：

```text
GPU Utilization = 20%
```

不要马上判断 GPU 本身有问题。

还要检查：

```text
CPU 是否忙
Memory 是否 Swap
Disk 是否慢
DataLoader 是否阻塞
Network 是否慢
```

例如：

```text
Disk 慢
↓
DataLoader 等 I/O
↓
数据准备慢
↓
GPU 等数据
↓
GPU Utilization 低
```

或：

```text
CPU Oversubscription
↓
Run Queue 很长
↓
Data preprocessing 慢
↓
GPU 吃不饱
```

## AI 节点初级健康检查

```bash
uptime
nproc
free -h
df -h
vmstat 1
```

再：

```bash
ps aux --sort=-%cpu | head
ps aux --sort=-%mem | head
```

Service：

```bash
systemctl --failed
```

Kernel：

```bash
dmesg | tail -100
```

Network Socket：

```bash
ss -lntp
```

## 为什么不要上来就 restart / reboot

更好的顺序：

```text
先观察
↓
保留证据
↓
定位
↓
再恢复
```

例如先看：

```bash
systemctl status
journalctl
dmesg
ps
free
vmstat
```

然后再决定是否 restart。

---

# 第 1 章最终心智模型

## Process / Thread / FD / CPU

```text
                 Application
                     │
                  Process
                     │
              ┌──────┴──────┐
              ↓             ↓
           Thread           FD
              │             │
              ↓             ├─ File
         Scheduler          ├─ Socket
              │             └─ Pipe
              ↓
         Logical CPU
              │
              ↓
        Physical Core
```

## Memory

```text
Process
  │
  │ Virtual Address
  ↓
 MMU
  │
 TLB
  │
Page Table
  │
Physical RAM
  │
 ├─ Anonymous Memory
 ├─ Page Cache
 └─ Shared Memory
```

## Kernel

```text
              User Space
                  │
             System Call
                  │
────────────────────────────────
                  │
               Kernel
          ┌───────┼────────┐
          ↓       ↓        ↓
       Process  Memory   Filesystem
       Scheduler Network  Device
          │       │        │
────────────────────────────────
          │       │        │
         CPU     NIC      Disk/GPU
```

## Observability

```text
Kernel / Process
      │
      ├─ /proc
      ├─ /sys
      ├─ dmesg
      └─ systemd / journal
```

---

# 第 1 章完成后应该能解释的问题

1. Program 与 Process 有什么区别？
2. Process 与 Thread 有什么区别？
3. Scheduler 为什么存在？
4. Concurrency 与 Parallelism 有什么区别？
5. Context Switch 为什么有成本？
6. Virtual Address 为什么不等于 Physical Address？
7. Page Table 存在哪里，谁负责维护？
8. MMU 与 TLB 分别负责什么？
9. Page Fault 为什么不一定是错误？
10. RSS 与 VSZ 有什么区别？
11. OOM Killer 为什么会杀 Process？
12. Host RAM OOM 与 CUDA OOM 有什么区别？
13. File Descriptor 为什么不只代表普通文件？
14. `/proc` 与 `/sys` 是什么？
15. systemd 最终管理的本质是什么？
16. 服务器变慢为什么不能只看 `top`？

---

# WSL 离线实验清单

## FD

```bash
ls -l /proc/$$/fd
ulimit -n
ulimit -Sn
ulimit -Hn
cat /proc/$$/limits
```

## /proc

```bash
ls /proc/$$
grep -E "Name|State|Pid|PPid|Threads|VmSize|VmRSS" /proc/$$/status
ls -l /proc/$$/fd
ls -l /proc/$$/cwd
ls -l /proc/$$/exe
cat /proc/loadavg
head /proc/cpuinfo
head -20 /proc/meminfo
```

## /sys

```bash
ls /sys
ls /sys/class
ls /sys/class/net
ls /sys/block
ls /sys/module | head
```

## Kernel Parameters

```bash
sysctl vm.overcommit_memory
sysctl net.ipv4.ip_forward
```

## systemd

```bash
ps -p 1 -o pid,comm,args
systemctl list-units --type=service --state=running
systemctl --failed
journalctl -n 50
```

## CPU / Scheduler

```bash
lscpu
nproc
uptime
top
vmstat 1
```

## Process / Thread

```bash
ps aux
pstree -p
ps -T -p <PID>
```

## Memory

```bash
free -h
grep -E "VmSize|VmRSS|VmSwap" /proc/<PID>/status
cat /proc/meminfo
```

## Disk

```bash
df -h
du -sh <directory>
```

## I/O

```bash
vmstat 1
iostat -xz 1
```

## Network Socket

```bash
ss -lntp
```

## Kernel Log

```bash
dmesg | tail -100
```

---

# 核心术语表

| 术语 | 当前理解 |
|---|---|
| FD | Process 用整数引用 Kernel 资源 |
| FD Table | Process 的 FD 映射表 |
| stdin | FD 0，标准输入 |
| stdout | FD 1，标准输出 |
| stderr | FD 2，标准错误输出 |
| Handle | 代表系统资源的引用 |
| Pipe | Process 间的数据管道 |
| Socket | 网络通信的 Kernel 对象 |
| FD Leak | FD 未释放导致数量持续增长 |
| procfs | `/proc` 对应的虚拟文件系统 |
| sysfs | `/sys` 对应的虚拟文件系统 |
| sysctl | Kernel Runtime Parameter 工具 |
| Kernel Module | 可动态加载的 Kernel 模块 |
| systemd | 系统与 Service 管理器 |
| Service | 长期运行的后台服务 |
| Daemon | 守护进程 |
| systemctl | 管理 systemd Unit |
| Unit | systemd 管理对象 |
| Unit File | systemd 配置文件 |
| Main PID | Service 的主要 PID |
| journalctl | 查询 systemd 日志 |
| Troubleshooting | 基于现象、假设和证据逐步定位故障 |
| Observability | 通过系统暴露的数据理解内部状态 |
| iostat | 查看 Block I/O 状态 |
| ss | 查看 Socket 状态 |
| dmesg | 查看 Kernel 日志 |

---

# 第 1 章最终学习进度

```text
第 0 章：AI Infra 心智模型
✅ 完成

第 1 章：Linux 与计算机系统基础
✅ 完成

✅ 1.0 WSL 实验环境
✅ 1.1 Operating System
✅ 1.2 Kernel
✅ 1.3 User Space / Kernel Space
✅ 1.4 Process
✅ 1.5 Thread
✅ 1.6 CPU Core 与 Scheduler
✅ 1.7 Context Switch
✅ 1.8 Virtual Memory
✅ 1.8A Page Table
✅ 1.9 Page / Page Fault
✅ 1.10 OOM / OOM Killer
✅ 1.11 File Descriptor
✅ 1.12 /proc 与 /sys
✅ 1.13 systemd
✅ 1.14 Linux 基础排障

下一章：

第 2 章：计算机网络基础

⬜ 2.1 NIC 与 Network Interface
⬜ 2.2 MAC Address
⬜ 2.3 IP Address
⬜ 2.4 Subnet / CIDR
⬜ 2.5 Default Gateway
⬜ 2.6 Routing
⬜ 2.7 ARP / Neighbor
⬜ 2.8 TCP
⬜ 2.9 UDP
⬜ 2.10 Port / Socket
⬜ 2.11 DNS
⬜ 2.12 HTTP
⬜ 2.13 TLS / HTTPS
⬜ 2.14 NAT
⬜ 2.15 Linux Network Namespace 初步
⬜ 2.16 网络基础排障
```
