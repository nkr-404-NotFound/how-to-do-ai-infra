# LLM / AI Infra 学习笔记

## 第 2 章：计算机网络基础
### 2.6 ～ 2.10

> 目标：理解 Linux 如何通过 Routing、ARP、TCP/UDP、Port 和 Socket，把一个网络请求从目标 IP 一路交给正确的 Application Process。
>
> 实验环境：WSL2 + Ubuntu

---

# 2.6 Routing

**Routing（路由）**：

> 根据 Destination IP，决定 IP Packet 下一步应该往哪里发送。

## Routing Table

**Routing Table（路由表）**可以理解成 Kernel 中的：

> “目标网络 → 下一步怎么走”的规则表。

例如：

```text
Destination        Next Hop         Interface
------------------------------------------------
192.168.1.0/24     direct           eth0
10.0.0.0/8         192.168.1.2      eth0
0.0.0.0/0          192.168.1.1      eth0
```

含义：

```text
去 192.168.1.0/24
→ 直接从 eth0 发

去 10.0.0.0/8
→ 先交给 192.168.1.2

其他目标
→ 交给默认网关 192.168.1.1
```

## Route / Next Hop

**Route**：一条路由规则。

**Next Hop（下一跳）**：

> 当前 Host 或 Router 应该先把 Packet 交给谁。

例如：

```text
10.0.0.0/8 via 192.168.1.2 dev eth0
```

表示：

```text
目标属于 10.0.0.0/8
↓
下一跳 192.168.1.2
↓
通过 eth0
```

Next Hop 不是最终 Destination。

## Directly Connected Route

```text
192.168.1.0/24 dev eth0
```

没有 `via`，通常表示：

> 该 Subnet 直接连接在 eth0 上。

## Default Route

```text
default
```

可以理解成：

```text
0.0.0.0/0
```

例如：

```text
default via 192.168.1.1 dev eth0
```

表示：

> 没有更具体 Route 时，交给 192.168.1.1。

所以 Default Gateway 本质上是 Default Route 的 Next Hop。

## WSL 查看 Routing Table

```bash
ip route
```

可能看到：

```text
default via 172.20.48.1 dev eth0
172.20.48.0/20 dev eth0 proto kernel scope link src 172.20.55.10
```

解释：

```text
default
→ 默认路由

via 172.20.48.1
→ Next Hop

dev eth0
→ 从 eth0 发

172.20.48.0/20 dev eth0
→ 该 Subnet 直接连接 eth0

proto kernel
→ Kernel 根据 Interface/IP 配置自动生成

scope link
→ 当前 Link 直接可达

src 172.20.55.10
→ 倾向使用的 Source IP
```

## Longest Prefix Match

**Longest Prefix Match（最长前缀匹配）**：

> 多条 Route 都匹配 Destination IP 时，选择 Prefix 最长、最具体的 Route。

例如：

```text
10.0.0.0/8
10.20.0.0/16
10.20.30.0/24
0.0.0.0/0
```

目标：

```text
10.20.30.40
```

最终选择：

```text
10.20.30.0/24
```

因为 `/24` 最具体。

规律：

```text
/24 比 /16 更具体
/16 比 /8 更具体
/0 最不具体
```

## ip route get

非常实用：

```bash
ip route get 8.8.8.8
```

可能：

```text
8.8.8.8 via 172.20.48.1 dev eth0 src 172.20.55.10
```

可读成：

```text
Destination = 8.8.8.8
Next Hop    = 172.20.48.1
Interface   = eth0
Source IP   = 172.20.55.10
```

## Multi-NIC

AI Infra 中常见：

```text
eth0 → Management Network
eth1 → Storage Network
eth2 → Training Network
```

如果 Routing 配错：

```text
NCCL Traffic
本应走 100G NIC
却走 1G Management NIC
↓
网络慢
↓
GPU 等待
↓
GPU Utilization 降低
```

因此以后常用：

```bash
ip route
ip route get <peer-ip>
```

## IP Forwarding

**IP Forwarding（IP 转发）**：

> Kernel 是否允许把不是发给本机的 IP Packet 根据 Routing Table 继续转发。

查看：

```bash
sysctl net.ipv4.ip_forward
```

常见：

```text
0 → 不转发
1 → 允许转发
```

当前阶段只查看，不修改。

## Router 转发过程

```text
Host A
192.168.1.10/24
    ↓
Router
192.168.1.1 / 10.0.0.1
    ↓
Host B
10.0.0.20/24
```

A 访问 B：

```text
A 判断 10.0.0.20 不属于 192.168.1.0/24
↓
交给 Gateway 192.168.1.1
```

第一段 Ethernet Frame：

```text
Src MAC = Host A MAC
Dst MAC = Router MAC
```

里面：

```text
Src IP = 192.168.1.10
Dst IP = 10.0.0.20
```

Router 收到：

```text
拆当前 Frame
↓
查看 Destination IP
↓
查 Routing Table
↓
从另一 Interface 转发
```

第二段重新生成 Ethernet Frame，但 IP Destination 仍然是：

```text
10.0.0.20
```

所以：

> MAC 每一跳变化，IP 用于跨网络寻址。

## Routing Loop / traceroute

**Routing Loop（路由环路）**：

```text
Router A
→ Router B
→ Router C
→ Router A
```

TTL 每过一跳减 1，最终到 0 后 Packet 被丢弃。

查看路径：

```bash
sudo apt install traceroute
traceroute 8.8.8.8
```

也可以：

```bash
tracepath 8.8.8.8
```

---

# 2.7 ARP / Neighbor

**ARP**

全称：

**Address Resolution Protocol**

中文：

**地址解析协议**

作用：

> 在当前 IPv4 本地链路上，根据 IP Address 找到对应 MAC Address。

```text
IPv4 Address
↓
ARP
↓
MAC Address
```

## 为什么需要 ARP

Routing 得到：

```text
Next Hop IP
```

Ethernet Frame 需要：

```text
Destination MAC
```

所以：

```text
Routing
↓
Next Hop IP
↓
ARP
↓
Next Hop MAC
```

## ARP Request / Reply

假设：

```text
Host:
IP 192.168.1.10
MAC AA:AA:...

Gateway:
IP 192.168.1.1
MAC RR:RR:...
```

Host 不知道 Gateway MAC，于是发：

```text
ARP Request:
Who has 192.168.1.1?
```

因为还不知道目标 MAC，所以 Request 使用：

```text
ff:ff:ff:ff:ff:ff
```

也就是 Broadcast MAC。

拥有该 IP 的设备返回：

```text
ARP Reply:
192.168.1.1 is-at RR:RR:...
```

通常：

```text
ARP Request → Broadcast
ARP Reply   → Unicast
```

## Unicast

**Unicast（单播）**：

> 一对一发送给明确目标。

## Neighbor Table

Linux 会缓存：

```text
IP ↔ MAC
```

现代 Linux 常称：

**Neighbor Table（邻居表）**

查看：

```bash
ip neigh
```

可能：

```text
172.20.48.1 dev eth0 lladdr 00:15:5d:xx:xx:xx STALE
```

其中：

```text
lladdr
→ Link-Layer Address
→ Ethernet 中通常就是 MAC
```

## Neighbor State

常见：

```text
REACHABLE
STALE
INCOMPLETE
FAILED
```

### REACHABLE

最近确认 Neighbor 可达。

### STALE

缓存存在，但近期没有重新确认。

注意：

```text
STALE ≠ 故障
```

### INCOMPLETE

正在解析 Neighbor，还没拿到 MAC。

### FAILED

Neighbor Resolution 失败。

## 同 Subnet 和跨 Subnet

同 Subnet：

```text
192.168.1.10/24
→
192.168.1.20/24
```

ARP：

```text
Who has 192.168.1.20?
```

跨 Subnet：

```text
192.168.1.10/24
→
8.8.8.8
```

Gateway：

```text
192.168.1.1
```

ARP 的不是 8.8.8.8，而是：

```text
Who has 192.168.1.1?
```

所以：

> ARP 的是当前 Next Hop，不一定是最终 Destination。

## Routing + ARP

```text
Destination IP
      ↓
Routing Table
      ↓
Next Hop IP
      ↓
Neighbor Table
      ↓
有 MAC？
  │
 ┌┴────┐
有     没有
│       │
│      ARP
│       ↓
│    获得 MAC
│       │
└───┬───┘
    ↓
Ethernet Frame
```

## Broadcast Domain

**Broadcast Domain（广播域）**：

> 一个 Layer 2 Broadcast Frame 可以到达的网络范围。

Router 通常分隔 Broadcast Domain。

## VLAN

**VLAN**

全称：

**Virtual LAN**

中文：

**虚拟局域网**

当前先理解：

> VLAN 可以在交换网络中逻辑划分不同 Layer 2 Broadcast Domain。

## tcpdump 初步

**tcpdump**：

> Linux 命令行抓包工具。

安装：

```bash
sudo apt install tcpdump
```

观察 ARP：

```bash
sudo tcpdump -ni eth0 arp
```

其中：

```text
-n      → 不做名称解析
-i eth0 → 抓 eth0
```

## ARP 故障

如果 Routing 正常，但：

```bash
ip neigh
```

显示：

```text
FAILED
```

可能原因：

```text
目标离线
错误 VLAN
Switch 问题
Interface 问题
二层网络不通
IP 配置错误
虚拟网络故障
```

---

# 2.8 TCP

**TCP**

全称：

**Transmission Control Protocol**

中文：

**传输控制协议**

可以先理解成：

> 在 IP 之上，为两个端点提供可靠、有序、面向连接的 Byte Stream。

关键词：

```text
面向连接
可靠
有序
字节流
```

## TCP 在协议栈中的位置

```text
Application
    ↓
TCP
    ↓
IP
    ↓
Ethernet
    ↓
NIC
```

数据封装：

```text
Ethernet Frame
└─ IP Packet
   └─ TCP Segment
      └─ Application Data
```

## Segment

**Segment（报文段）**：

> TCP 层的数据单元。

## 为什么 IP 上还需要 TCP

IP 不保证：

```text
一定到达
只到一次
按顺序到达
```

TCP 使用：

```text
Sequence Number
ACK
Retransmission
Buffer
Flow Control
Congestion Control
```

帮助 Application 得到可靠、有序的 Byte Stream。

## Connection-Oriented

**Connection-Oriented（面向连接）**：

> 双方传输数据前需要建立 TCP Connection State。

Connection 本质上是两端 Kernel 维护的一组状态，例如：

```text
Sequence Number
ACK 状态
Send Buffer
Receive Buffer
Window
Retransmission 状态
```

## Byte Stream

**Byte Stream（字节流）**

TCP 不保留 Application 的 Message Boundary。

例如：

```python
send(b"hello")
send(b"world")
```

接收端可能看到：

```text
helloworld
```

也可能：

```text
hel
lowor
ld
```

所以应用协议需要自己定义消息边界。

## Three-Way Handshake

**Three-Way Handshake（三次握手）**：

```text
Client                         Server

   -------- SYN ------------>

   <------ SYN + ACK --------

   -------- ACK ------------>
```

之后 Connection Established。

### SYN

请求建立连接并同步初始状态。

### ACK

**Acknowledgment（确认）**：

> 表示已经收到前面的数据或控制信息。

## Sequence Number

**Sequence Number（序列号）**：

> 标记 TCP Byte Stream 中的数据位置。

例如：

```text
Seq = 1000
发送 5 bytes
```

下一步可能期待：

```text
1005
```

## Acknowledgment Number

例如：

```text
ACK = 1005
```

表示：

> 到 1004 为止的连续数据已经收到，下一步期待 1005。

## Packet Loss / Retransmission

**Packet Loss（丢包）**可能来自：

```text
Congestion
Buffer 满
链路错误
设备丢弃
```

**Retransmission（重传）**：

```text
发送
↓
没有收到期望 ACK
↓
判断可能丢失
↓
重新发送
```

## TCP Flags

常见：

```text
SYN
ACK
FIN
RST
```

### FIN

正常结束一个方向的数据发送。

### RST

立即重置 TCP Connection。

## Full Duplex

**Full Duplex（全双工）**：

> Client 和 Server 可以同时双向发送数据。

因此 TCP 两个方向通常分别关闭。

## Send / Receive Buffer

Kernel 为 TCP Connection 维护：

```text
Send Buffer
Receive Buffer
```

发送：

```text
Application send()
↓
Send Buffer
↓
TCP
↓
Network
```

接收：

```text
NIC
↓
Kernel
↓
TCP Receive Buffer
↓
Application recv()
```

## Flow Control

**Flow Control（流量控制）**：

> 防止 Sender 压垮 Receiver。

主要通过：

**Receive Window（rwnd）**

表示 Receiver 当前还能接多少数据。

## Congestion Control

**Congestion Control（拥塞控制）**：

> 防止 Sender 把 Network 本身压垮。

区别：

```text
Flow Control
→ 保护 Receiver

Congestion Control
→ 保护 Network
```

**Congestion Window（cwnd）**是拥塞控制的重要变量。

概念上可理解：

```text
可发送量
≈
min(rwnd, cwnd)
```

## RTT

**RTT**

全称：

**Round-Trip Time**

中文：

**往返时延**

表示：

> 数据从 A 到 B，再从 B 返回 A 的时间。

高 Bandwidth 不等于低 RTT。

## TCP States

查看：

```bash
ss -tn
```

常见：

```text
LISTEN
ESTAB
SYN-SENT
SYN-RECV
TIME-WAIT
```

### LISTEN

等待新 TCP Connection。

### ESTAB

Connection 已建立。

### TIME-WAIT

连接关闭后暂时保留协议状态。

## tcpdump 看 TCP

```bash
sudo tcpdump -ni any tcp
```

可能看到：

```text
Flags [S]
Flags [S.]
Flags [.]
```

粗略对应：

```text
SYN
SYN+ACK
ACK
```

---

# 2.9 UDP

**UDP**

全称：

**User Datagram Protocol**

中文：

**用户数据报协议**

也是 Transport Layer Protocol。

```text
Application
    ↓
TCP / UDP
    ↓
IP
    ↓
Ethernet
```

## Datagram

**Datagram（数据报）**：

> 有明确边界、独立发送的一条消息。

TCP：

```text
Byte Stream
```

UDP：

```text
Datagram
```

## UDP 保留消息边界

发送：

```text
Datagram A
Datagram B
```

接收端仍按独立 Datagram 处理。

所以：

```text
TCP → Stream-oriented
UDP → Datagram-oriented
```

## Connectionless

**Connectionless（无连接）**：

> UDP 不需要 TCP 式 Three-Way Handshake。

Application 可以直接发送 Datagram。

## UDP 不提供的能力

UDP 本身不保证：

```text
可靠到达
顺序
自动去重
自动重传
Flow Control
Congestion Control
```

如果 Application 需要：

> 自己实现。

## Jitter

**Jitter（抖动）**：

> Packet Delay 的变化程度。

例如：

```text
20 ms
21 ms
150 ms
22 ms
```

实时应用通常同时关心：

```text
Latency
Packet Loss
Jitter
Bandwidth
```

## UDP Header

经典 UDP Header：

```text
8 bytes
```

包含：

```text
Source Port
Destination Port
Length
Checksum
```

UDP Header 比 TCP 更简单。

但：

> UDP 简单 ≠ 一定更快。

## 常见使用场景

```text
DNS
DHCP
NTP
实时音视频
游戏
QUIC 基础
```

## QUIC

**QUIC**：

> 运行在 UDP 之上的现代传输协议，可自行实现可靠性、加密、拥塞控制、多路复用等。

HTTP/3 主要基于：

```text
QUIC
↓
UDP
```

所以：

> UDP 本身不可靠，不代表基于 UDP 的上层协议不能可靠。

## Fragmentation

**Fragmentation（分片）**：

> 太大的 IP Packet 被拆成多个 Fragment。

UDP Datagram 太大时可能触发 IP Fragmentation。

高性能网络会关注：

```text
MTU
Packet Size
```

## UDP Socket

UDP Socket 也是 Kernel Object，Process 通过 FD 使用。

查看：

```bash
ss -un
ss -lun
sudo ss -lunp
```

Python UDP Server：

```python
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("127.0.0.1", 9999))

data, addr = s.recvfrom(4096)

print(addr)
print(data)
```

Client：

```python
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

s.sendto(
    b"hello udp",
    ("127.0.0.1", 9999)
)
```

---

# 2.10 Port / Socket

## Port

**Port（端口）**：

> Transport Layer 中用来区分一台 Host 内不同网络通信端点的 16-bit 数字编号。

例如：

```text
10.0.0.20:22
```

其中：

```text
10.0.0.20 → Host
22        → Port
```

常见：

```text
22   → SSH
80   → HTTP
443  → HTTPS
5432 → PostgreSQL
3306 → MySQL
```

## Port 范围

```text
0 ～ 65535
```

因为 Port 是：

```text
16 bits
```

TCP Port 和 UDP Port 属于不同协议空间。

例如：

```text
TCP 53
UDP 53
```

可以同时存在。

## Socket

**Socket（套接字）**：

> Kernel 中实际用于网络通信的对象。

Process 通过 FD 使用 Socket：

```text
Process
  ↓
FD
  ↓
Socket
  ↓
TCP / UDP
  ↓
IP
  ↓
Network
```

注意：

```text
Port ≠ Socket
```

Port 是数字，Socket 是 Kernel Object。

## Socket 也是 FD

```python
import socket

s = socket.socket()
print(s.fileno())
```

例如：

```text
3
```

表示：

```text
FD 3
→ Socket
```

## Address Family

常见：

```text
AF_INET  → IPv4
AF_INET6 → IPv6
AF_UNIX  → Unix Domain Socket
```

TCP Socket：

```python
socket.socket(socket.AF_INET, socket.SOCK_STREAM)
```

UDP Socket：

```python
socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
```

## bind

**bind（绑定）**：

> 把 Socket 绑定到 Local IP + Port。

例如：

```python
s.bind(("127.0.0.1", 8000))
```

## 127.0.0.1 vs 0.0.0.0

```text
127.0.0.1:8000
```

通常：

> 只有本机 Loopback 可以访问。

```text
0.0.0.0:8000
```

通常：

> 监听本机所有合适的 IPv4 Interface。

所以：

```text
本机 curl 能通
外部机器连不上
```

时，要检查服务是不是只绑定了 127.0.0.1。

## listen

TCP Server：

```python
s.listen()
```

表示：

> Socket 进入 LISTEN 状态，等待新 TCP Connection。

这个 Socket 叫：

**Listening Socket**

## accept

```python
conn, addr = s.accept()
```

返回：

> 新的 Connected Socket。

例如：

```text
FD 3 → Listening Socket
FD 4 → Client A
FD 5 → Client B
FD 6 → Client C
```

## connect

Client：

```python
s.connect(("10.0.0.20", 8000))
```

发起 TCP Connection。

## Ephemeral Port

**Ephemeral Port（临时端口）**：

> Client 常由 Kernel 自动选择的 Source Port。

例如：

```text
10.0.0.10:53124
→
10.0.0.20:443
```

## TCP 4-tuple

TCP Connection 常由：

```text
Source IP
Source Port
Destination IP
Destination Port
```

标识。

例如：

```text
10.0.0.10:50001
→
10.0.0.20:443
```

同一个 Server Port 可以同时服务很多不同 Client，因为 4-tuple 不同。

## Kernel 如何找到 Socket

收到：

```text
Src IP   = 10.0.0.10
Src Port = 50001
Dst IP   = 10.0.0.20
Dst Port = 443
```

Kernel 大致：

```text
Ethernet
↓
IP
↓
TCP
↓
查看地址和 Port
↓
找到对应 Socket
↓
放入 Receive Buffer
↓
Application 读取
```

## 完整接收链路

```text
NIC
↓
Driver
↓
Kernel Network Stack
↓
Ethernet
↓
IP
↓
TCP / UDP
↓
Destination Port
↓
Socket
↓
FD
↓
Process
```

## Address already in use

如果某 Process 已经：

```text
TCP 0.0.0.0:8000
```

另一普通 Process 再 bind 同一地址/Port，通常：

```text
Address already in use
```

排查：

```bash
ss -ltnp | grep ':8000'
```

或：

```bash
sudo lsof -iTCP:8000
```

## ss

查看 TCP Listener：

```bash
ss -ltn
```

带 Process：

```bash
sudo ss -ltnp
```

可能：

```text
LISTEN 0 4096 0.0.0.0:22 0.0.0.0:* users:(("sshd",pid=123,fd=3))
```

可理解：

```text
LISTEN
→ TCP Listening Socket

0.0.0.0:22
→ 所有 IPv4 Interface 的 Port 22

sshd
→ Process

pid=123
→ PID

fd=3
→ Process 用 FD 3 持有 Socket
```

## Backlog

**Backlog**：

> Server 来不及 accept() 时，Kernel 保存待处理 Connection 的相关队列限制。

例如：

```python
s.listen(128)
```

具体实现以后再深入。

## Port 分类

```text
0–1023
→ Well-Known Ports

1024–49151
→ Registered Ports

49152–65535
→ Dynamic / Private Ports
```

## Port Exhaustion

**Port Exhaustion（端口耗尽）**：

大量 Client 短连接时，Ephemeral Port / 4-tuple 资源可能出现压力。

这和大量：

```text
TIME_WAIT
```

经常一起出现。

## Keep-Alive

**Keep-Alive**：

> 复用已建立 TCP Connection。

可以减少：

```text
Handshake 开销
TIME_WAIT
Port 压力
CPU 开销
```

HTTP 章节会继续讲。

## Python TCP Server

```python
import socket

server = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

server.bind(("127.0.0.1", 9999))
server.listen()

print("listen fd =", server.fileno())

conn, addr = server.accept()

print("client =", addr)
print("connected fd =", conn.fileno())

data = conn.recv(4096)
print("data =", data)

conn.sendall(b"hello client")
```

Client：

```python
import socket

client = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

client.connect(("127.0.0.1", 9999))

print("client fd =", client.fileno())
print("local =", client.getsockname())
print("remote =", client.getpeername())

client.sendall(b"hello server")

print(client.recv(4096))
```

Server 运行时：

```bash
ls -l /proc/<PID>/fd
```

可能：

```text
3 -> socket:[123456]
4 -> socket:[123789]
```

例如：

```text
FD 3 → Listening Socket
FD 4 → Connected Socket
```

---

# 2.6 ～ 2.10 总体心智模型

发送：

```text
Application Process
        │
        │ FD
        ↓
      Socket
        │
        ├─ TCP / UDP
        ├─ Local IP / Port
        ├─ Remote IP / Port
        ├─ Send Buffer
        └─ Receive Buffer
        │
        ↓
Destination IP
        ↓
Routing Table
        ↓
Longest Prefix Match
        ↓
Interface + Next Hop IP
        ↓
Neighbor Table
        ↓
有 Next Hop MAC？
    │
  ┌─┴─┐
  有  无
  │    │
  │   ARP
  │    ↓
  │  获得 MAC
  │    │
  └─┬──┘
    ↓
Ethernet Frame
    ↓
NIC
    ↓
Network
```

接收：

```text
Network
↓
NIC
↓
Driver
↓
Ethernet Frame
↓
IP Packet
↓
TCP / UDP
↓
Destination Port
↓
Socket
↓
FD
↓
Application Process
```

---

# 核心术语表

| 术语 | 当前理解 |
|---|---|
| Routing | 根据 Destination IP 决定下一步路径 |
| Routing Table | Kernel 保存的 Route 集合 |
| Route | 一条网络转发规则 |
| Next Hop | 当前下一跳 Router |
| Default Route | `0.0.0.0/0` 的兜底 Route |
| Longest Prefix Match | 多条 Route 匹配时选最具体的 |
| IP Forwarding | Linux 转发非本机 Packet |
| ARP | IPv4 → 当前链路 MAC |
| Neighbor Table | Kernel 的 IP ↔ MAC 缓存 |
| REACHABLE | Neighbor 最近确认可达 |
| STALE | 缓存存在但近期未重新确认 |
| INCOMPLETE | 正在解析 Neighbor |
| FAILED | Neighbor Resolution 失败 |
| TCP | 可靠、有序、面向连接的 Byte Stream |
| Segment | TCP 数据单元 |
| Sequence Number | TCP Byte Stream 的位置编号 |
| ACK | 确认 |
| Retransmission | 重传 |
| Flow Control | 保护 Receiver |
| Congestion Control | 保护 Network |
| RTT | 往返时延 |
| UDP | User Datagram Protocol |
| Datagram | 保留消息边界的数据报 |
| Jitter | 网络延迟波动 |
| Port | Transport Layer 的 16-bit 端点编号 |
| Socket | Kernel 网络通信对象 |
| bind | 绑定 Local IP + Port |
| listen | TCP Socket 开始监听 |
| accept | 获取新的 Connected Socket |
| connect | Client 发起连接 |
| Ephemeral Port | Client 临时 Source Port |
| 4-tuple | Src IP + Src Port + Dst IP + Dst Port |
| Backlog | 待处理连接队列相关限制 |
| Port Exhaustion | 临时 Port / Connection 资源耗尽 |
| Keep-Alive | 复用已建立连接 |

---

# WSL 离线实验清单

## Routing

```bash
ip route
ip route | grep default
ip route get 8.8.8.8
sysctl net.ipv4.ip_forward
```

## Neighbor / ARP

```bash
ip neigh
ping -c 1 <gateway-ip>
ip neigh
```

可选：

```bash
sudo tcpdump -ni eth0 arp
```

## TCP

```bash
ss -tn
ss -ltn
sudo ss -ltnp
```

抓包：

```bash
sudo tcpdump -ni any tcp
```

## UDP

```bash
ss -un
ss -lun
sudo ss -lunp
```

## Port / Socket

```bash
ss -ltnp
ss -lunp
sudo lsof -iTCP
sudo lsof -iUDP
```

查看 Process FD：

```bash
ls -l /proc/<PID>/fd
```

---

# 本部分最重要的十句话

1. Routing 根据 Destination IP 决定 Packet 下一步往哪里走。
2. 多条 Route 同时匹配时，选择 Longest Prefix Match。
3. 跨 Subnet 时，Next Hop 往往是 Gateway，而不是最终 Destination。
4. Routing 先决定 Next Hop IP，ARP 再把它解析为 MAC。
5. TCP 提供可靠、有序、面向连接的 Byte Stream。
6. Sequence Number + ACK + Retransmission 是 TCP 可靠传输的重要基础。
7. UDP 是 Datagram-oriented，本身不提供 TCP 式可靠、有序、自动重传。
8. IP 找到 Host，Port 帮 Kernel 找到网络端点。
9. Socket 是 Kernel Object，Process 通过 FD 持有 Socket。
10. 网络到应用的最后一段是：TCP/UDP → Port → Socket → FD → Process。

---

# 当前学习进度

```text
第 0 章：AI Infra 心智模型
✅ 完成

第 1 章：Linux 与计算机系统基础
✅ 完成

第 2 章：计算机网络基础

✅ 2.1 NIC 与 Network Interface
✅ 2.2 MAC Address
✅ 2.3 IP Address
✅ 2.4 Subnet / CIDR
✅ 2.5 Default Gateway
✅ 2.6 Routing
✅ 2.7 ARP / Neighbor
✅ 2.8 TCP
✅ 2.9 UDP
✅ 2.10 Port / Socket

下一节：

⬜ 2.11 DNS
⬜ 2.12 HTTP
⬜ 2.13 TLS / HTTPS
⬜ 2.14 NAT
⬜ 2.15 Linux Network Namespace 初步
⬜ 2.16 网络基础排障
```
