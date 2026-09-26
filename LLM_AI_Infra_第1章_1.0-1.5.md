# LLM / AI Infra 学习笔记

## 第 1 章：Linux 与计算机系统基础
### 1.0 ～ 1.5

> 目标：建立 Linux 系统最基础的运行模型。
>
> 本部分重点理解：
> - WSL 中 Ubuntu、Linux Kernel、User Space 的关系
> - Operating System（操作系统）是什么
> - Kernel（内核）是什么
> - User Space / Kernel Space
> - System Call（系统调用）
> - Process（进程）
> - Thread（线程）
> - PID / PPID
> - Program 与 Process 的区别
> - Concurrency 与 Parallelism 的区别

---

# 1.0 WSL 实验环境

如果你使用的是常见的：

```text
Ubuntu on WSL2
```

可以先粗略理解成：

```text
Windows
   │
   └── WSL2
        │
        ├── Linux Kernel
        │
        └── Ubuntu User Space
```

WSL2 中运行的是真正的 Linux Kernel，而 Ubuntu 提供 Shell、软件包、命令、库等用户空间环境。

## 查看 Kernel

```bash
uname -a
uname -r
```

`uname` 用于查看 Unix/Linux 系统核心信息。

## 查看 Linux Distribution

```bash
cat /etc/os-release
```

`/etc/os-release` 描述当前 Linux Distribution（发行版）。

因此：

```text
uname
→ Kernel 信息

/etc/os-release
→ Distribution 信息
```

---

# 1.1 Operating System 是什么

**Operating System**

简称：

**OS**

中文：

**操作系统**

操作系统最重要的职责可以先理解成：

> 管理计算机硬件资源，并为应用程序提供统一的运行环境。

如果完全没有 OS，一个简单程序也要自己解决：

```text
CPU 怎么使用
内存怎么分配
屏幕如何输出
键盘如何读取
文件如何保存
网络如何发送
多个程序如何同时运行
```

所以需要：

```text
Application
    │
    ↓
Operating System
    │
    ↓
Hardware
```

## OS 管理哪些东西

```text
CPU
Memory
Device
Process
Filesystem
Network
Permissions
Scheduling
```

因此：

```text
Operating System
=
硬件资源管理者
+
应用程序运行平台
```

### Scheduler

**Scheduler**

中文：

**调度器**

负责决定：

> 哪个任务何时获得 CPU，以及运行多久。

### 内存管理

OS 还负责：

```text
分配内存
回收内存
隔离不同程序的内存
保护系统
```

---

# 1.2 Kernel 是什么

**Kernel**

中文：

**内核**

Kernel 可以理解为：

> 操作系统中直接管理硬件和核心系统资源的部分。

关系：

```text
应用程序
Python / nginx / bash
        │
        ↓
      Kernel
        │
        ↓
      Hardware
        │
 ┌──────┼──────┐
 CPU   RAM    Disk / NIC / GPU
```

## NIC

**NIC**

全称：

**Network Interface Card**

中文：

**网卡 / 网络接口设备**

---

## Linux 到底是什么

严格来说：

> Linux 最核心指的是 Linux Kernel。

而 Ubuntu 属于：

**Linux Distribution**

简称：

**Distro**

中文：

**Linux 发行版**

Linux 发行版大致可以理解成：

```text
Linux Kernel
+
Shell
+
系统命令
+
软件库
+
包管理器
+
配置文件
+
用户空间工具
```

常见发行版：

```text
Ubuntu
Debian
Fedora
Rocky Linux
Arch Linux
```

因此：

```text
Ubuntu
≠
Linux Kernel
```

而是：

```text
Ubuntu
=
Linux Kernel
+
一套用户空间软件
```

## Kernel 管理的核心资源

```text
Process
Memory
Filesystem
Network
Device
Security
Scheduling
```

---

# 1.3 User Space / Kernel Space

Linux 系统可以先粗略分成：

```text
User Space
Kernel Space
```

## Kernel Space

**Kernel Space**

中文：

**内核空间**

这里主要运行或实现：

```text
Linux Kernel
Memory Manager
Scheduler
Network Stack
Device Driver
```

### Driver

**Device Driver**

中文：

**设备驱动程序**

负责：

> 让操作系统和具体硬件设备交流。

例如：

```text
GPU Driver
NIC Driver
Disk Driver
```

### Network Stack

**Network Stack**

中文：

**网络协议栈**

可以先理解成：

> Kernel 中负责 TCP/IP 等网络通信的一系列功能。

---

## User Space

**User Space**

中文：

**用户空间**

普通应用程序主要运行在这里：

```text
bash
Python
nginx
curl
ssh
Docker CLI
你的程序
```

关系：

```text
             User Space

Python / nginx / bash / curl

────────────────────────────

            Kernel Space

        Linux Kernel

────────────────────────────

             Hardware
```

## 为什么要分开

普通程序不能随便：

```text
访问任意物理内存
修改 Kernel
直接控制所有硬件
读取其他进程的内存
```

因此：

```text
User Space
权限较低

Kernel Space
权限极高
```

这样可以提高：

```text
稳定性
安全性
资源隔离
```

---

## System Call

**System Call**

简称：

**syscall**

中文：

**系统调用**

可以理解成：

> User Space 程序向 Kernel 请求服务的接口。

普通应用程序如果要：

```text
打开文件
读取文件
写文件
申请内存
创建进程
发送网络数据
```

通常都要经过 Kernel。

关系：

```text
Application
User Space
    │
    │ System Call
    ↓
Kernel
    │
    ↓
Hardware
```

例如：

```bash
cat hello.txt
```

概念上可以理解为：

```text
cat
(User Space)
   │
   │ open()
   │ read()
   ↓
Kernel
   │
   ↓
Filesystem / Disk
```

---

## strace

**strace**

可以理解成：

> 用来观察一个 Linux 程序执行了哪些 System Call 的工具。

安装：

```bash
sudo apt update
sudo apt install strace
```

测试：

```bash
strace echo hello
```

可能看到：

```text
openat(...)
mmap(...)
write(...)
close(...)
```

其中：

```text
write(1, "hello\n", 6)
```

可以粗略理解成：

```text
echo
  │
  │ 请求 Kernel 写数据
  ↓
Kernel
  │
  ↓
Terminal
```

---

## /proc 初步

```bash
cat /proc/version
```

`/proc` 可以先理解成：

> Kernel 暴露给用户空间、用于查看系统和进程信息的虚拟文件系统。

---

## PID 1 与当前 Shell

```bash
ps -p 1 -o pid,comm,args
```

**PID**

全称：

**Process ID**

中文：

**进程编号**

再看当前 Shell：

```bash
echo $$
ps -p $$ -o pid,ppid,comm,args
```

**PPID**

全称：

**Parent Process ID**

中文：

**父进程 ID**

---

# 1.4 Process：进程

**Process**

中文：

**进程**

可以理解成：

> 一个正在运行中的程序实例。

## Program vs Process

**Program**

中文：

**程序**

例如：

```text
/usr/bin/python3
/usr/bin/bash
/usr/bin/curl
```

这些是存储在磁盘中的程序文件。

而：

**Process**

表示：

> Program 被运行以后形成的运行实例。

所以：

```text
Program
= 静态程序文件

Process
= 正在运行的程序实例
```

同一个 Program 可以同时产生多个 Process：

```text
/usr/bin/python3
       │
       ├── Process 1201
       ├── Process 1208
       └── Process 1220
```

每个 Process 都有自己的 PID。

---

## Process 中包含什么

Kernel 为一个 Process 维护大量信息：

```text
Process
 │
 ├── PID
 ├── Program Code
 ├── Memory
 ├── CPU State
 ├── Open Files
 ├── Environment Variables
 ├── Current Directory
 ├── Permissions
 └── Threads
```

---

## Address Space

**Address Space**

中文：

**地址空间**

可以理解成：

> 一个 Process 所看到和使用的内存地址范围。

不同 Process 通常拥有相互隔离的地址空间。

后面会通过：

**Virtual Memory**

也就是：

**虚拟内存**

详细解释这种隔离。

---

## Parent / Child Process

一个 Process 可以创建另一个 Process：

```text
Parent Process
      │
      ↓
Child Process
```

其中：

```text
PID
=
当前进程编号

PPID
=
父进程编号
```

实验：

```bash
echo $$
sleep 1000 &
ps -o pid,ppid,comm -C sleep
```

这里：

```text
&
```

表示把程序放到后台运行。

---

## Process Tree

多个 Process 会形成：

**Process Tree**

中文：

**进程树**

查看：

```bash
pstree -p
```

如果没有：

```bash
sudo apt install psmisc
```

可能看到：

```text
systemd(1)
 ├─bash(1000)
 │   ├─sleep(1050)
 │   └─python3(1060)
 └─sshd(1100)
```

---

## Process State

常见状态：

```text
R = Running
S = Sleeping
T = Stopped
Z = Zombie
```

### Running

正在执行，或已准备好等待 CPU。

### Sleeping

正在等待某个事件，例如：

```text
网络
磁盘
锁
定时器
```

### Stopped

被暂停，但尚未退出。

### Zombie

**Zombie**

中文：

**僵尸进程**

可以先理解成：

> 子进程已经结束，但父进程还没有处理完它的退出状态。

查看：

```bash
ps aux
```

其中 `STAT` 列显示 Process State。

---

## fork / exec

### fork

**fork**

可以先理解成：

> 当前 Process 创建一个新的子 Process。

```text
bash
 │
 │ fork
 ↓
child process
```

### exec

**exec**

可以先理解成：

> 用新的 Program 替换当前 Process 正在执行的程序。

例如 Bash 执行：

```bash
python3 app.py
```

可以粗略理解成：

```text
bash
 │
 │ 创建 child
 ↓
child process
 │
 │ exec python3
 ↓
python3 process
```

`exec` 通常不是再产生一个新 PID，而是改变当前 Process 正在运行的 Program。

---

## /proc/PID

假设：

```text
PID = 2300
```

那么：

```text
/proc/2300/
```

包含 Kernel 暴露出来的这个 Process 的大量信息。

例如：

```bash
ls /proc/2300
ls -l /proc/2300/exe
```

可能看到：

```text
/proc/2300/exe -> /usr/bin/sleep
```

表示：

```text
Process 2300
     │
     ↓
正在运行
     │
/usr/bin/sleep
```

---

# 1.5 Thread：线程

**Thread**

中文：

**线程**

可以理解成：

> Process 内部的一条执行流。

例如：

```text
Process
 │
 ├── Thread 1
 ├── Thread 2
 └── Thread 3
```

一个 Process 可以有一个或多个 Thread。

---

## Process 与 Thread 的核心区别

不同 Process：

```text
Process A
Memory A

Process B
Memory B
```

通常拥有相互隔离的地址空间。

同一个 Process 内的多个 Thread：

```text
          Process
             │
      Shared Memory
             │
   ┌─────────┼─────────┐
   ↓         ↓         ↓
Thread 1  Thread 2  Thread 3
```

通常共享这个 Process 的大部分内存和资源。

---

## Thread 自己保存哪些东西

每个 Thread 也需要自己的执行状态：

```text
Program Counter
Registers
Stack
```

### Program Counter

**Program Counter**

简称：

```text
PC
```

可以理解成：

> 当前 Thread 执行到哪条 CPU 指令。

### Register

**Register**

中文：

**寄存器**

是 CPU 内部极快、容量很小的存储位置。

### Stack

**Stack**

中文：

**栈**

可以先理解成：

> Thread 用来保存函数调用、局部变量等执行信息的一块内存。

---

## Process 与 Thread 对比

| Process | Thread |
|---|---|
| 进程 | 线程 |
| 正在运行的程序实例 | Process 内的一条执行流 |
| 通常拥有独立地址空间 | 同 Process 的 Thread 共享大部分内存 |
| 隔离更强 | 共享资源更多 |
| 创建与切换成本通常更高 | 通常更轻量 |
| 一个 Process 可包含多个 Thread | Thread 必须属于某个 Process |

---

## Single-threaded

**Single-threaded**

中文：

**单线程**

```text
Process
  │
  └── Thread 1
```

## Multi-threaded

**Multi-threaded**

中文：

**多线程**

```text
Process
 │
 ├── Thread 1
 ├── Thread 2
 ├── Thread 3
 └── Thread 4
```

---

## Concurrency

**Concurrency**

中文：

**并发**

表示：

> 多个任务在一段时间内共同推进。

例如单核 CPU：

```text
A → B → A → C → B → A
```

多个任务不断切换。

---

## Parallelism

**Parallelism**

中文：

**并行**

表示：

> 多个任务在同一个时刻真正执行。

例如：

```text
CPU Core 1 → Thread A
CPU Core 2 → Thread B
CPU Core 3 → Thread C
```

因此：

```text
Concurrency
≠
Parallelism
```

多线程不等于一定并行。

如果：

```text
4 Threads
1 CPU Core
```

可能只是不断切换：

```text
Thread 1
↓
Thread 2
↓
Thread 3
↓
Thread 4
↓
Thread 1
...
```

---

## 查看 Thread 数量

```bash
ps -p $$ -o pid,comm,nlwp
```

**NLWP**

表示：

```text
Number of Light Weight Processes
```

Linux 工具中常用于表示一个 Process 中的 Thread 数量。

---

## Python 多线程实验

运行：

```bash
python3
```

然后：

```python
import threading
import time

def worker():
    time.sleep(1000)

for i in range(5):
    threading.Thread(target=worker).start()

time.sleep(1000)
```

另一个 Terminal：

```bash
pgrep -n python3
```

假设得到：

```text
3000
```

查看：

```bash
ps -p 3000 -o pid,nlwp,comm
```

可能看到：

```text
PID   NLWP   COMMAND
3000  6      python3
```

因为：

```text
1 个主线程
+
5 个创建出来的 Thread
=
6 Threads
```

进一步：

```bash
ps -T -p 3000
ls /proc/3000/task
```

可以观察这个 Process 内的各个 Thread。

---

# 1.0 ～ 1.5 核心关系图

## User Space / Kernel

```text
                      Hardware
                         ↑
                         │
                    Linux Kernel
                         ↑
                   System Call
                         ↑
                      User Space
                         ↑
                   Application
```

## Process / Thread

```text
                     Linux Kernel
                          │
                   管理 Process
                          │
              ┌───────────┴───────────┐
              ↓                       ↓
          Process A                Process B
       Address Space A          Address Space B
              │                       │
       ┌──────┼──────┐          ┌─────┴─────┐
       ↓      ↓      ↓          ↓           ↓
    Thread  Thread  Thread    Thread      Thread
```

Process 之间通常有较强隔离。

同 Process 的 Thread 共享大部分资源。

每个 Thread 保存自己的执行状态。

---

# 核心术语表

| 术语 | 当前理解 |
|---|---|
| Operating System | 管理硬件资源并给应用提供运行环境 |
| Kernel | OS 中直接管理核心资源和硬件的部分 |
| Distribution | Kernel + 用户空间软件组成的发行版 |
| User Space | 普通应用程序主要运行的区域 |
| Kernel Space | Kernel 工作的高权限区域 |
| System Call | User Space 向 Kernel 请求服务的接口 |
| Driver | Kernel 与硬件交流的软件 |
| Program | 磁盘上的程序文件 |
| Process | 正在运行的程序实例 |
| PID | Process ID，进程编号 |
| PPID | Parent Process ID，父进程编号 |
| Address Space | Process 所看到的内存地址范围 |
| fork | 创建子 Process |
| exec | 用新 Program 替换当前 Process 的执行内容 |
| Thread | Process 内的一条执行流 |
| Program Counter | Thread 当前执行到的位置 |
| Register | CPU 内部极快的小型存储单元 |
| Stack | Thread 保存函数调用等执行信息的内存区域 |
| Concurrency | 多任务在一段时间内共同推进 |
| Parallelism | 多任务真正同时执行 |
| NLWP | Process 中的 Thread 数量 |
| strace | 观察程序 System Call 的工具 |
| /proc | 查看 Kernel 和 Process 状态的虚拟文件系统 |

---

# WSL 实验清单

## 系统与 Kernel

```bash
uname -a
uname -r
cat /etc/os-release
cat /proc/version
```

## PID 1 与当前 Shell

```bash
ps -p 1 -o pid,comm,args
echo $$
ps -p $$ -o pid,ppid,comm,args
```

## System Call

```bash
strace echo hello
```

## Process

```bash
sleep 1000 &
pgrep sleep
ps -o pid,ppid,comm -C sleep
pstree -p
```

## /proc/PID

```bash
ls /proc/<PID>
ls -l /proc/<PID>/exe
```

## Thread

```bash
ps -p $$ -o pid,comm,nlwp
ps -T -p <PID>
ls /proc/<PID>/task
```

---

# 学习进度

```text
第 0 章：AI Infra 心智模型
✅ 完成

第 1 章：Linux 与计算机系统基础

✅ 1.0 WSL 实验环境
✅ 1.1 Operating System
✅ 1.2 Kernel
✅ 1.3 User Space / Kernel Space

✅ 1.4 Process
    ├─ Program vs Process
    ├─ PID / PPID
    ├─ Address Space
    ├─ Parent / Child
    ├─ Process Tree
    ├─ Process State
    ├─ fork / exec
    └─ /proc/PID 初步

✅ 1.5 Thread
    ├─ Process vs Thread
    ├─ Thread Stack
    ├─ Register / Program Counter
    ├─ Single-thread / Multi-thread
    ├─ Concurrency
    ├─ Parallelism
    └─ /proc/PID/task

下一节：

⬜ 1.6 CPU Core 与 Scheduler
⬜ 1.7 Context Switch
⬜ 1.8 Virtual Memory
⬜ 1.9 Page / Page Fault
⬜ 1.10 OOM / OOM Killer
⬜ 1.11 File Descriptor
⬜ 1.12 /proc 与 /sys
⬜ 1.13 systemd
⬜ 1.14 Linux 基础排障
```
