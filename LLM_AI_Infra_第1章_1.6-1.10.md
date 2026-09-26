# LLM / AI Infra 学习笔记

## 第 1 章：Linux 与计算机系统基础
### 1.6 ～ 1.10

> 目标：从 CPU 调度进入 Linux 内存体系，并理解系统级 OOM。
>
> 本部分重点：
>
> - CPU Core / Logical CPU / SMT
> - Linux Scheduler / Run Queue / Load Average
> - Context Switch
> - Virtual Memory
> - Page Table / MMU / TLB
> - Page Fault / Page Cache
> - Swap / Thrashing
> - OOM / OOM Killer
> - Host RAM OOM / Container OOM / CUDA OOM 的区别
>
> 实验环境：
>
> ```text
> WSL2 + Ubuntu
> ```

---

# 1.6 CPU Core 与 Scheduler

## 1.6.1 CPU Core 是什么

**CPU Core**，中文是 **CPU 核心**。

可以理解成：

> CPU 中能够独立执行指令流的计算核心。

例如：

```text
4 Core CPU
```

大致表示：

```text
Core 0
Core 1
Core 2
Core 3
```

不同 Core 可以并行执行不同 Thread。

---

## 1.6.2 Physical Core 与 Logical CPU

### Physical Core

**Physical Core**，中文是 **物理核心**，就是 CPU 芯片上真实存在的硬件核心。

### Logical CPU

**Logical CPU**，中文是 **逻辑 CPU**，表示：

> 操作系统看到的可调度 CPU 执行单元。

---

## 1.6.3 SMT

**SMT** 全称 **Simultaneous Multithreading**，中文是 **同时多线程**。

Intel 常把自己的实现称为：

**Hyper-Threading（超线程）**。

例如：

```text
4 Physical Cores
```

开启 SMT 后，Linux 可能看到：

```text
8 Logical CPUs
```

大致：

```text
Physical Core 0
 ├─ Logical CPU 0
 └─ Logical CPU 1

Physical Core 1
 ├─ Logical CPU 2
 └─ Logical CPU 3
```

注意：两个 Logical CPU 并不等于两套完全独立的 Physical Core。

---

## 1.6.4 Hardware Thread vs Software Thread

### Hardware Thread

可以粗略等价理解为：

```text
Logical CPU
```

即 CPU 暴露给操作系统的硬件执行上下文。

### Software Thread

例如：

```text
Python Thread
Java Thread
nginx Thread
```

表示 Process 内的一条软件执行流。

关系：

```text
Software Thread
      │
      ↓
Linux Scheduler
      │
      ↓
Logical CPU
      │
      ↓
Physical Core
```

---

## 1.6.5 查看 CPU

WSL 中：

```bash
lscpu
```

常见字段：

```text
CPU(s):
Core(s) per socket:
Thread(s) per core:
Socket(s):
```

### Socket

**Socket**，中文是 **CPU 插槽**。

服务器可能有：

```text
1 socket
2 sockets
4 sockets
```

每个 Socket 可安装一颗 CPU。

---

## 1.6.6 nproc

```bash
nproc
```

表示：

> 当前 Linux 环境可使用多少个 Logical CPU。

---

## 1.6.7 Linux Scheduler 调度什么

Linux Scheduler 实际更接近调度：

> 可运行的 Thread / Task。

例如：

```text
Process A
 ├─ Thread A1
 ├─ Thread A2
 └─ Thread A3

Process B
 ├─ Thread B1
 └─ Thread B2
```

Scheduler 需要安排：

```text
A1
A2
A3
B1
B2
```

到 Logical CPU 上执行。

---

## 1.6.8 Scheduler

**Scheduler**，中文是 **调度器**。

可以理解成：

> Kernel 中决定哪个可运行任务什么时候在哪个 CPU 上运行的组件。

假设：

```text
100 Runnable Threads
8 Logical CPUs
```

则不可能全部同时运行，Scheduler 必须决定谁先执行。

---

## 1.6.9 Runnable

**Runnable**，中文是 **可运行**。

表示：

> Thread 已经准备好执行，只是在等待 CPU。

---

## 1.6.10 Run Queue

**Run Queue**，中文是 **运行队列**。

可以理解成：

> 等待 CPU 的可运行任务集合。

例如：

```text
CPU 只有 2 个

Runnable:
A
B
C
D
E
```

可能：

```text
A → CPU 0
B → CPU 1

C / D / E
→ 等待
```

---

## 1.6.11 CPU Time 与 Wall Time

### CPU Time

表示一个任务真正占用 CPU 执行的时间。

### Wall Time

表示从开始到结束实际经过的时间。

例如：

```python
import time
time.sleep(10)
```

可能：

```text
Wall Time ≈ 10 秒
CPU Time ≈ 很少
```

所以程序运行很久，不等于一直占 CPU。

---

## 1.6.12 CPU-bound

**CPU-bound**，中文是 **CPU 计算受限**。

表示程序主要时间都花在 CPU 计算。

例如：

```text
压缩
加密
编译
大量数学运算
```

---

## 1.6.13 I/O-bound

**I/O** 全称 **Input / Output**，中文是 **输入 / 输出**。

**I/O-bound** 表示：

> 程序主要时间花在等待外部 I/O。

例如：

```text
磁盘
网络
数据库
```

---

## 1.6.14 Time Slice

**Time Slice**，中文是 **时间片**。

可以先理解成：

> Scheduler 一次让某个任务使用 CPU 的一段时间。

现代 Linux 调度远比简单固定时间片复杂，但这个概念便于理解。

---

## 1.6.15 CPU Affinity

**CPU Affinity**，中文是 **CPU 亲和性**。

表示：

> 限制 Process / Thread 只能在哪些 Logical CPU 上运行。

查看当前 Shell：

```bash
taskset -pc $$
```

可能：

```text
pid 1234's current affinity list: 0-7
```

表示当前 Shell 可在 CPU 0～7 上运行。

---

## 1.6.16 固定任务到某个 CPU

```bash
taskset -c 0 yes > /dev/null
```

解释：

```text
taskset -c 0
→ 只允许任务使用 Logical CPU 0

yes
→ 不断输出 y

/dev/null
→ 数据黑洞，写进去的数据直接丢弃
```

另一个终端：

```bash
top
```

可观察 CPU 使用情况。

结束：

```text
Ctrl + C
```

---

## 1.6.17 Load Average

运行：

```bash
uptime
```

可能看到：

```text
load average: 0.20, 0.35, 0.40
```

三个数大致代表最近 1 分钟、5 分钟、15 分钟的系统负载。

### Load Average ≠ CPU Usage

CPU Usage 更接近 CPU 有多少时间在忙。

Load Average 更接近：

> 有多少任务在运行或等待某些不可中断资源。

因此 Load 很高不一定意味着 CPU = 100%。

---

## 1.6.18 AI Infra 中的 Scheduler 问题

例如：

```text
8 × GPU
64 × CPU Core
```

同时有：

```text
DataLoader Threads
NCCL Threads
Python Runtime
Monitoring Agent
Logging Agent
Container Runtime
```

如果 CPU 调度压力太大：

```text
数据准备线程抢不到 CPU
↓
GPU 等数据
↓
GPU Utilization 下降
```

所以 GPU 利用率低，不一定是 GPU 本身的问题。

---

# 1.7 Context Switch

**Context Switch**，中文是 **上下文切换**。

表示：

> CPU 从执行一个 Thread，切换到另一个 Thread。

---

## 1.7.1 Context 是什么

这里的 **Context** 可以理解成：

> 一个 Thread 继续执行所需要的 CPU 状态。

例如：

```text
Program Counter
Registers
Stack Pointer
CPU flags
```

---

## 1.7.2 Context Switch 基本流程

```text
CPU 正执行 Thread A
        ↓
Scheduler 决定切换
        ↓
保存 A 的 CPU 状态
        ↓
加载 B 的 CPU 状态
        ↓
执行 Thread B
```

---

## 1.7.3 Context Switch 有成本

每次切换都需要：

```text
保存状态
恢复状态
执行调度逻辑
可能影响 CPU Cache
```

所以 Context Switch 并不是免费的。

---

## 1.7.4 CPU Cache

**CPU Cache**，中文是 **CPU 缓存**。

可以理解成：

> CPU 附近非常快、容量较小的高速存储。

常见层级：

```text
L1 Cache
L2 Cache
L3 Cache
RAM
```

---

## 1.7.5 Thread Migration

**Thread Migration**，中文是 **线程迁移**。

表示：

> 同一个 Thread 从一个 Logical CPU / Core 被调度到另一个。

这可能降低 Cache 局部性。

---

## 1.7.6 Voluntary Context Switch

表示 Thread 因为等待某件事，主动让出 CPU。

例如：

```text
等待网络
等待磁盘
sleep
等待锁
```

---

## 1.7.7 Involuntary Context Switch

表示 Thread 还想继续运行，但 Scheduler 把 CPU 给了别人。

例如：

```text
时间片结束
更高优先级任务出现
重新调度
```

---

## 1.7.8 vmstat

运行：

```bash
vmstat 1
```

常见字段：

```text
r
b
cs
us
sy
id
wa
```

### r

可粗略理解成当前 Runnable / 等待 CPU 的任务数量。

### cs

表示每秒 Context Switch 数量。

### us

**User CPU Time**：CPU 花在 User Space 程序上的时间比例。

### sy

**System CPU Time**：CPU 花在 Kernel Space 上的时间比例。

### id

**Idle**：CPU 空闲时间比例。

### wa

**I/O Wait**：与等待 I/O 完成相关的 CPU 时间。

---

## 1.7.9 查看某 Process 的 Context Switch

```bash
grep ctxt /proc/$$/status
```

可能看到：

```text
voluntary_ctxt_switches:
nonvoluntary_ctxt_switches:
```

---

## 1.7.10 Oversubscription

**Oversubscription** 可以理解成 **过量并发 / 过度超配**。

例如：

```text
8 Logical CPUs
100 Runnable Threads
```

可能造成：

```text
Run Queue 变长
Context Switch 增多
Cache Miss 增多
性能下降
```

### Cache Miss

**Cache Miss**，中文是 **缓存未命中**。

表示 CPU 需要的数据不在 Cache，只能去更慢的内存层级读取。

---

## 1.7.11 AI Infra 常见链路

```text
CPU Oversubscription
        ↓
Context Switch 增多
        ↓
数据准备变慢
        ↓
GPU 等待
        ↓
GPU Utilization 降低
```

---

# 1.8 Virtual Memory

**Virtual Memory**，中文是 **虚拟内存**。

核心思想：

> 给每个 Process 提供自己的虚拟地址空间，并把虚拟地址映射到实际物理内存。

---

## 1.8.1 Physical Memory

**Physical Memory**，中文是 **物理内存**，就是机器真正存在的 RAM。

---

## 1.8.2 Virtual Address

**Virtual Address**，中文是 **虚拟地址**。

表示 Process 自己看到的内存地址。

---

## 1.8.3 Virtual Address Space

每个 Process 都拥有自己的 **Virtual Address Space（虚拟地址空间）**。

例如：

```text
Process A
Virtual 0x1000
      ↓
Physical 0xA000

Process B
Virtual 0x1000
      ↓
Physical 0xF000
```

因此：

```text
同一个 Virtual Address
≠
同一块 Physical RAM
```

---

## 1.8.4 Mapping

**Mapping**，中文是 **映射**。

表示建立 Virtual Address 到 Physical Address 的对应关系。

---

## 1.8.5 Page

**Page**，中文是 **页**。

Linux 通常不是逐 Byte 管理地址映射，而是按固定大小块管理。

常见 Page 大小：

```text
4 KB
```

---

## 1.8.6 Page Frame

**Page Frame** 表示 Physical RAM 中与 Page 对应的固定大小区域。

```text
Virtual Memory 侧 → Page
Physical RAM 侧  → Page Frame
```

---

## 1.8.7 Page Table

**Page Table**，中文是 **页表**。

保存：

```text
Virtual Page
→
Physical Page Frame
```

的映射关系。

---

# 1.8A Page Table 存在哪、谁负责维护

## Page Table 存在哪

> Page Table 本身存放在 Physical RAM 中。

Page Table 本身也是 Kernel 使用的一类内存数据结构。

```text
Physical RAM
│
├─ Process A 普通数据
├─ Process B 普通数据
├─ Kernel 数据
├─ Process A Page Table
├─ Process B Page Table
└─ ...
```

---

## PTE

**PTE** 全称 **Page Table Entry**，中文是 **页表项**。

一条 PTE 可能记录：

```text
Physical Frame
Present
Writable
Executable / NX
User / Kernel 权限
Accessed
Dirty
```

---

## 谁负责写 Page Table

主要是：

> Linux Kernel。

普通 User Space 程序不能任意修改 Page Table。

```text
Kernel
→ 创建和修改地址映射

User Space
→ 不能任意修改 Page Table
```

---

## MMU

**MMU** 全称 **Memory Management Unit**，中文是 **内存管理单元**。

是 CPU 内负责 Virtual Address → Physical Address 转换的硬件组件。

```text
CPU
 ↓
Virtual Address
 ↓
MMU
 ↓
Page Table
 ↓
Physical Address
 ↓
RAM
```

---

## CR3

在 x86-64 上，可先把 **CR3** 理解成：

> 保存当前地址空间 Page Table 根位置的特殊 CPU 寄存器。

概念上：

```text
Process A
CR3 → Page Table A

Context Switch

Process B
CR3 → Page Table B
```

---

## Multi-level Page Table

现代 64 位地址空间很大，Page Table 通常是多级结构。

粗略：

```text
Virtual Address
      ↓
Level 1
      ↓
Level 2
      ↓
Level 3
      ↓
Level 4
      ↓
PTE
      ↓
Physical Page
```

---

## Accessed / Dirty Bit

映射关系与权限主要由 Kernel 维护，但 CPU/MMU 可能自动更新某些状态位。

### Accessed

表示页面被访问过。

### Dirty

表示页面被写过。

Kernel 可利用这些信息辅助 Memory Reclaim、Page Cache、Swap 等决策。

---

## TLB

**TLB** 全称 **Translation Lookaside Buffer**。

可以理解成：

> CPU 内部用于缓存常用地址转换结果的高速缓存。

Page Table 在 RAM 中，而 TLB 在 CPU 内部。

一句话：

```text
Kernel：写规则
Page Table：存规则
MMU：执行规则
TLB：缓存规则
```

查看 Page Table 自身占用：

```bash
grep PageTables /proc/meminfo
```

---

## 1.8.8 Virtual Memory ≠ Swap

```text
Virtual Memory
≠
Swap
```

Virtual Memory 的核心是虚拟地址空间、地址映射与隔离。

Swap 只是虚拟内存体系可能使用的一种后备机制。

---

## 1.8.9 Swap

**Swap**，中文是 **交换空间**。

表示 RAM 紧张时，把部分暂时不活跃的数据放到磁盘后备空间。

因为磁盘远慢于 RAM，所以频繁 Swap 会显著拖慢系统。

---

## 1.8.10 Heap 与 Stack

### Heap

主要用于程序运行时动态申请内存，例如 malloc、new、Python 对象。

### Stack

主要用于函数调用、局部变量、返回地址、调用上下文。

每个 Thread 通常有自己的 Stack。

---

## 1.8.11 Process Address Space 简图

```text
高地址
┌──────────────────────┐
│ Thread Stack         │
├──────────────────────┤
│ Shared Libraries     │
├──────────────────────┤
│ mmap regions         │
├──────────────────────┤
│ Heap                 │
├──────────────────────┤
│ Data                 │
├──────────────────────┤
│ Code                 │
└──────────────────────┘
低地址
```

---

## 1.8.12 Shared Memory

**Shared Memory**，中文是 **共享内存**。

不同 Process 可以故意让不同 Virtual Address 映射到同一个 Physical Page。

---

## 1.8.13 Copy-on-Write

**Copy-on-Write（COW）**，中文是 **写时复制**。

在 fork 后，Parent 与 Child 可先共享 Physical Pages。

只有某一方要写时，Kernel 才复制对应 Page。

---

## 1.8.14 VSZ 与 RSS

查看：

```bash
ps -o pid,vsz,rss,comm -p $$
```

### VSZ

**Virtual Memory Size**：Process 映射/使用的虚拟地址空间规模。

### RSS

**Resident Set Size**：当前真正驻留在 Physical RAM 中的内存规模。

因此 VSZ 不等于真实 RAM 占用。

---

# 1.9 Page / Page Fault

**Page Fault**，中文是 **缺页异常 / 页错误**。

名字里有 Fault，但 Page Fault 不一定表示程序出错。

---

## 1.9.1 Page Fault 基本流程

```text
Program
 ↓
访问 Virtual Address
 ↓
MMU
 ↓
发现页面当前不可直接访问
 ↓
Page Fault
 ↓
Kernel
 ↓
处理页面
 ↓
建立或修正映射
 ↓
程序继续
```

---

## 1.9.2 First Touch

程序刚申请一大片虚拟内存时，真实 Physical Page 可能尚未分配。

第一次写某一页：

```text
First Touch
↓
Page Fault
↓
Kernel 分配 Physical Page
↓
更新 Page Table
↓
程序继续
```

---

## 1.9.3 Minor Page Fault

**Minor Page Fault**，中文是 **次缺页**。

表示需要 Kernel 修正或建立映射，但不需要从磁盘读取页面数据。

---

## 1.9.4 Major Page Fault

**Major Page Fault**，中文是 **主缺页**。

表示页面数据当前不在 RAM，需要进行磁盘 I/O，例如从文件或 Swap 读取。

---

## 1.9.5 Anonymous Memory

**Anonymous Memory**，中文是 **匿名内存**。

表示没有直接对应普通文件的内存，例如 Heap、malloc、很多程序动态内存。

---

## 1.9.6 File-backed Memory

**File-backed Memory**，中文是 **文件后备内存**。

例如共享库、mmap 文件、模型权重文件。

---

## 1.9.7 Page Cache

**Page Cache**，中文是 **页缓存**。

Linux 会利用空闲 RAM 缓存最近读取的文件数据。

所以 Linux 经常看起来 RAM 被占很多，但其中一部分是可回收 Cache。

查看：

```bash
free -h
```

通常 `available` 比单纯 `free` 更有参考意义。

---

## 1.9.8 查看 Page Fault

```bash
/usr/bin/time -v ls
```

若缺少 GNU time：

```bash
sudo apt install time
```

可观察 Minor / Major Page Fault。

---

## 1.9.9 首次触碰页面实验

```python
import mmap
import time

size = 512 * 1024 * 1024
x = mmap.mmap(-1, size)

print("mapped")

for i in range(0, size, 4096):
    x[i] = 1

print("touched all pages")
time.sleep(1000)
```

另一个终端：

```bash
ps -o pid,vsz,rss,comm -p <PID>
```

通常可观察：刚 mmap 时 VSZ 很大、RSS 较小；触碰大量页面后 RSS 明显增大。

---

## 1.9.10 Cold Start

**Cold Start**，中文是 **冷启动**。

表示服务刚启动、页面和 Cache 尚未准备好时的启动/首请求阶段。

大模型加载可能经历：

```text
SSD
 ↓
Page Fault
 ↓
Page Cache / RAM
 ↓
模型加载
```

大量 Major Page Fault 可能让 Cold Start 变慢。

---

## 1.9.11 内存访问总图

```text
Process
  │
  │ Virtual Address
  ↓
MMU
  │
  ├─ TLB Hit
  │     ↓
  │ Physical Address
  │
  └─ TLB Miss
        ↓
     Page Table
        ↓
     找到有效映射？
        │
    ┌───┴────┐
   是        否
   ↓         ↓
RAM     Page Fault
             ↓
           Kernel
             ↓
     分配页 / 读文件 / Swap
             ↓
         更新 Page Table
             ↓
            RAM
```

---

# 1.10 OOM / OOM Killer

**OOM** 全称 **Out Of Memory**，中文是 **内存不足 / 内存耗尽**。

表示程序或系统无法继续满足新的内存需求。

---

## 1.10.1 RAM 紧张时 Linux 不会立刻杀进程

大致：

```text
应用申请更多内存
        ↓
还有空闲 RAM？
        │
    ┌───┴───┐
   有       没有
   ↓         ↓
直接用     尝试 Reclaim
             ↓
        回收 Page Cache
             ↓
         必要时 Swap
             ↓
        还能满足请求？
             │
        ┌────┴────┐
       能         不能
       ↓           ↓
     继续运行      OOM
```

---

## 1.10.2 Memory Reclaim

**Memory Reclaim**，中文是 **内存回收**。

表示 Kernel 尝试释放或回收当前可回收的内存资源。

---

## 1.10.3 Anonymous Memory 与 Swap

匿名内存不能简单丢弃。

如果配置了 Swap，可以把暂时不活跃的匿名页换出到磁盘。

---

## 1.10.4 Thrashing

**Thrashing**，中文可称 **内存抖动 / 颠簸**。

表示系统大量时间都花在 RAM 与 Swap 之间来回搬页面，而不是真正执行工作。

---

## 1.10.5 OOM Killer

**OOM Killer**，中文是 **内存不足杀手**。

当 Linux 判断系统无法正常满足内存需求时，可能选择一个或多个 Process 杀掉以释放内存。

---

## 1.10.6 oom_score / oom_score_adj

查看：

```bash
cat /proc/$$/oom_score
cat /proc/$$/oom_score_adj
```

`oom_score_adj` 通常范围：

```text
-1000 ～ 1000
```

粗略：越高越容易被 OOM Killer 选中；越低越不容易。

---

## 1.10.7 如何判断是否发生过 OOM Kill

```bash
dmesg | grep -i -E "out of memory|killed process"
```

可能看到：

```text
Out of memory: Killed process 12345 (python3) ...
```

---

## 1.10.8 SIGKILL

**SIGKILL** 是一种 Linux Signal（信号）。

可以先理解为：

> 强制立即终止 Process 的控制信号。

进程收到 SIGKILL 通常没有机会优雅退出或写完整日志。

---

## 1.10.9 Allocation Failure ≠ System OOM

例如 Python `MemoryError` 并不一定意味着整台 Linux OOM。

可能只是 Process 自身受限或申请失败。

---

## 1.10.10 安全的 WSL 内存失败实验

新开一个 Shell：

```bash
ulimit -v 300000
```

然后：

```bash
python3
```

输入：

```python
x = bytearray(500 * 1024 * 1024)
```

很可能得到：

```text
MemoryError
```

注意：这不是 OOM Killer，只是 Process 资源限制导致申请失败。

---

## 1.10.11 Memory Overcommit

**Memory Overcommit**，中文是 **内存超额承诺**。

Linux 可能允许 Process 申请比当前真实可用 RAM 更多的 Virtual Memory，因为程序未必真的会全部使用。

风险是所有程序突然都真正触碰这些内存：

```text
Virtual Memory 承诺
↓
真实 RAM 需求
↓
RAM 不够
↓
Swap 不够
↓
OOM
```

查看：

```bash
cat /proc/sys/vm/overcommit_memory
cat /proc/sys/vm/overcommit_ratio
```

当前阶段不要随意修改。

---

## 1.10.12 系统内存压力观察

```bash
free -h
vmstat 1
swapon --show
cat /proc/meminfo
```

`vmstat` 中：

```text
si = Swap In
so = Swap Out
```

如果持续很高，通常说明内存压力明显。

---

# 1.10.13 Linux RAM OOM 与 CUDA OOM

## Host / Linux RAM OOM

```text
CPU / Linux
     ↓
System RAM
```

不足，可能触发 OOM Killer。

## CUDA OOM

```text
PyTorch
   ↓
CUDA
   ↓
GPU VRAM
```

不足，常见报错：

```text
CUDA out of memory
```

此时 Host RAM 可能仍然很充足。

---

## 1.10.14 Container / Kubernetes OOM

例如：

```text
Physical Host RAM = 128 GB
Container Limit = 4 GB
```

Container 内程序使用超过 4 GB，即使 Host 还有很多 RAM，也可能因为 cgroup Memory Limit 被 Kill。

### cgroup

**cgroup** 全称 **Control Groups**，中文是 **控制组**。

是 Linux Kernel 提供的对一组 Process 进行资源限制、统计和控制的机制。

可限制：

```text
CPU
Memory
I/O
```

Docker / Kubernetes 大量依赖 cgroup。

### Kubernetes OOMKilled

```text
Container 内 Process
       ↓
Memory 使用超过 cgroup Limit
       ↓
Kernel
       ↓
Kill Process
       ↓
Container 退出
       ↓
Kubernetes 记录原因
       ↓
OOMKilled
```

这不等于 Host 一定完全没有 RAM。

---

## 1.10.15 AI Infra 中常见 OOM 场景

### Host RAM 被 DataLoader 吃满

```text
DataLoader Workers
↓
Dataset / Cache
↓
Host RAM 满
↓
OOM Killer
```

### GPU VRAM 不够

```text
Model
↓
加载到 GPU
↓
VRAM 不够
↓
CUDA OOM
```

### KV Cache 太大

```text
Context 太长
Concurrency 太高
↓
KV Cache 增大
↓
GPU VRAM 不够
↓
CUDA OOM
```

### Container Limit 太小

```text
Node RAM 还有很多
↓
Pod / Container Limit = 8 GB
↓
Process 使用 9 GB
↓
cgroup OOM
↓
OOMKilled
```

---

## 1.10.16 OOM 初级排障顺序

1. 应用有没有自身错误日志。
2. Kernel 有没有 OOM 记录：

```bash
dmesg | grep -i -E "out of memory|killed process"
```

3. Host RAM 情况：

```bash
free -h
```

4. Swap 是否频繁工作：

```bash
vmstat 1
swapon --show
```

5. Container / cgroup Limit。
6. 是否是 CUDA OOM。

---

# 1.6 ～ 1.10 核心术语表

| 术语 | 当前理解 |
|---|---|
| Physical Core | CPU 的真实物理核心 |
| Logical CPU | OS 可调度的 CPU 执行单元 |
| SMT | 一个物理核心暴露多个逻辑执行上下文 |
| Scheduler | Kernel 中负责 CPU 调度的组件 |
| Runnable | 已准备执行、正在等待 CPU |
| Run Queue | 等待 CPU 的可运行任务集合 |
| CPU Time | 真正占用 CPU 的时间 |
| Wall Time | 实际经过时间 |
| CPU-bound | 主要受 CPU 计算限制 |
| I/O-bound | 主要时间用于等待 I/O |
| Time Slice | 一次获得 CPU 的时间片 |
| CPU Affinity | 限制任务在哪些 CPU 上执行 |
| Load Average | 系统运行/等待任务的平均负载 |
| Context Switch | CPU 从一个 Thread 切到另一个 |
| CPU Cache | CPU 附近的高速缓存 |
| Thread Migration | Thread 从一个 CPU 移到另一个 |
| Oversubscription | 活跃任务远多于可用资源 |
| Virtual Memory | 虚拟地址空间与地址映射机制 |
| Virtual Address | Process 看到的内存地址 |
| Physical Memory | 真实 RAM |
| Page | 虚拟内存管理的固定大小块 |
| Page Frame | Physical RAM 中对应的固定大小块 |
| Page Table | 保存地址映射关系的数据结构 |
| PTE | Page Table Entry，页表项 |
| MMU | CPU 中负责地址翻译的硬件 |
| TLB | 地址翻译结果缓存 |
| CR3 | x86-64 中指向当前页表根的重要寄存器 |
| Heap | 动态内存区域 |
| Stack | Thread 调用栈等使用的区域 |
| Shared Memory | 多进程共享 Physical Page |
| COW | Copy-on-Write，写时复制 |
| VSZ | 虚拟地址空间规模 |
| RSS | 当前驻留 RAM 的内存规模 |
| Page Fault | 页面访问需要 Kernel 介入 |
| Minor Page Fault | 不需要磁盘 I/O 的缺页 |
| Major Page Fault | 需要磁盘 I/O 的缺页 |
| Anonymous Memory | 不直接对应普通文件的内存 |
| File-backed Memory | 背后对应文件的内存 |
| Page Cache | Linux 用 RAM 缓存文件数据 |
| Cold Start | 尚未预热时的启动/首请求阶段 |
| Swap | RAM 的磁盘后备空间 |
| Thrashing | RAM 与 Swap 之间频繁换页 |
| OOM | Out Of Memory |
| OOM Killer | Linux 内存不足时杀进程的机制 |
| oom_score | OOM 选择 Process 时的相关分值 |
| oom_score_adj | 人工调节 OOM 倾向 |
| SIGKILL | 强制终止 Process 的 Signal |
| Overcommit | 内存超额承诺 |
| cgroup | Control Groups，资源限制与统计机制 |
| OOMKilled | 常见于 Container 超过内存限制 |
| CUDA OOM | GPU VRAM 不足 |

---

# WSL 实验清单

## CPU 与调度

```bash
lscpu
nproc
taskset -pc $$
uptime
top
vmstat 1
```

制造 CPU 负载：

```bash
yes > /dev/null &
```

停止：

```bash
pkill yes
```

## Context Switch

```bash
grep ctxt /proc/$$/status
vmstat 1
```

## Virtual Memory

```bash
free -h
ps -o pid,vsz,rss,comm -p $$
cat /proc/$$/maps
cat /proc/$$/status
grep PageTables /proc/meminfo
```

## Page Fault

```bash
/usr/bin/time -v ls
```

## Swap / Memory Pressure

```bash
free -h
vmstat 1
swapon --show
cat /proc/meminfo
```

## OOM 相关

```bash
cat /proc/$$/oom_score
cat /proc/$$/oom_score_adj
cat /proc/sys/vm/overcommit_memory
cat /proc/sys/vm/overcommit_ratio
dmesg | grep -i -E "out of memory|killed process"
```

---

# 1.6 ～ 1.10 核心心智模型

## CPU

```text
很多 Process
      ↓
很多 Thread
      ↓
Runnable Threads
      ↓
Run Queue
      ↓
Linux Scheduler
      ↓
Logical CPU
      ↓
Physical Core
```

## Context Switch

```text
Thread A
   ↓
保存 Context
   ↓
Scheduler
   ↓
恢复 Thread B Context
   ↓
Thread B
```

## Virtual Memory

```text
Process
   │
   │ Virtual Address
   ↓
  MMU
   │
   ├─ TLB
   │
   └─ Page Table in RAM
           │
           ↓
    Physical Address
           ↓
          RAM
```

## Page Fault

```text
Virtual Address
      ↓
MMU
      ↓
没有有效映射
      ↓
Page Fault
      ↓
Kernel
      ↓
分配 / 读取 Page
      ↓
更新 Page Table
      ↓
程序继续
```

## OOM

```text
Memory Pressure
      ↓
Memory Reclaim
      ↓
Page Cache 回收
      ↓
Swap
      ↓
仍无法满足
      ↓
OOM
      ↓
OOM Killer
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
✅ 1.5 Thread
✅ 1.6 CPU Core 与 Scheduler
✅ 1.7 Context Switch
✅ 1.8 Virtual Memory
✅ 1.8A Page Table 存储与维护
✅ 1.9 Page / Page Fault
✅ 1.10 OOM / OOM Killer

下一节：

⬜ 1.11 File Descriptor
⬜ 1.12 /proc 与 /sys
⬜ 1.13 systemd
⬜ 1.14 Linux 基础排障
```
