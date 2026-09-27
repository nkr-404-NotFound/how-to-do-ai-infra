# LLM / AI Infra 学习笔记

## 第 2 章：计算机网络基础
### 2.1 ～ 2.5

> 目标：从最底层的 NIC / Network Interface 开始，建立 MAC、IP、Subnet、CIDR、Default Gateway 的完整基础模型。
>
> 实验环境：`WSL2 + Ubuntu`

---

# 2.1 NIC 与 Network Interface

## 2.1.1 NIC 是什么

**NIC** 全称 **Network Interface Card**，中文：**网卡 / 网络接口卡**。

可以理解成：

> 让计算机能够连接网络的硬件设备。

例如服务器可能有：

```text
Ethernet NIC
Wi-Fi NIC
100G NIC
200G NIC
400G NIC
```

AI Infra 中以后还会遇到高速数据网卡、RoCE NIC、InfiniBand HCA。

NIC 属于真实硬件，基本链路：

```text
Application
    ↓
Kernel Network Stack
    ↓
NIC Driver
    ↓
NIC Hardware
    ↓
Cable / Switch / Network
```

## 2.1.2 Driver

**Driver**，中文：**驱动程序**。

作用：

> 让 Kernel 能够控制具体硬件。

```text
Linux Kernel
   ↓
NIC Driver
   ↓
NIC Hardware
```

## 2.1.3 Network Interface

**Network Interface**，中文：**网络接口**。

NIC 更偏物理硬件；Network Interface 更偏：

> Kernel 暴露给 User Space 的网络接口对象。

常见：

```text
eth0
eth1
enp3s0
wlan0
lo
```

NIC 和 Interface 不一定一一对应。Linux 还可以创建 veth、bridge、tun、tap、bond、VLAN interface 等虚拟接口。

所以：

```text
NIC = 物理网络设备
Network Interface = Kernel 中的网络接口对象
```

## 2.1.4 WSL 查看接口

```bash
ip link
```

可能看到：

```text
1: lo: <LOOPBACK,UP,LOWER_UP> ...
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
```

其中 `lo`、`eth0` 都是 Network Interface。

Linux 常用网络命令：

```bash
ip link
ip addr
ip route
ip neigh
```

粗略对应：

```text
link  → Interface / Link Layer
addr  → IP Address
route → Routing
neigh → Neighbor / ARP
```

## 2.1.5 UP / LOWER_UP

```bash
ip link show eth0
```

常见状态：

- `UP`：Interface 在软件层面已启用。
- `LOWER_UP`：底层链路被认为处于可用状态。

## 2.1.6 Loopback

**Loopback Interface**，中文：**回环接口**。

Linux 中常见名称：

```text
lo
```

它不是物理 NIC，而是 Kernel 提供的本机内部通信接口。

常见 IPv4 Loopback Address：

```text
127.0.0.1
```

本机服务通信：

```text
Application A
    ↓
Kernel Network Stack
    ↓
Loopback
    ↓
Application B
```

注意：

```text
lo ≠ localhost
```

`lo` 是 Interface；`localhost` 是 Hostname，通常解析到 `127.0.0.1` 或 IPv6 `::1`。

## 2.1.7 WSL 的 eth0

WSL2 中 `eth0` 通常不是物理网卡，而是虚拟网络接口：

```text
Linux in WSL
   ↓
eth0
   ↓
Virtual Networking
   ↓
Windows Host
   ↓
Physical NIC / Wi-Fi
```

## 2.1.8 /sys/class/net

```bash
ls /sys/class/net
```

可能看到：

```text
eth0
lo
```

查看状态：

```bash
cat /sys/class/net/eth0/operstate
```

查看 MAC：

```bash
cat /sys/class/net/eth0/address
```

查看 MTU：

```bash
cat /sys/class/net/eth0/mtu
```

## 2.1.9 MTU

**MTU** 全称 **Maximum Transmission Unit**，中文：**最大传输单元**。

可以先理解成：

> 一个 Network Interface 单次网络层传输能承载的数据大小上限之一。

Ethernet 常见：

```text
1500 bytes
```

后面 Jumbo Frame / RDMA 时再深入。

## 2.1.10 Link Layer

**Link Layer**，中文：**链路层**。

先粗略分层：

```text
Application
Transport
Network
Link
Physical
```

Link Layer 主要负责当前链路 / 局部网络上的数据传输。

发送链路：

```text
Process
↓
Socket FD
↓
Kernel Network Stack
↓
Network Interface
↓
NIC Driver
↓
NIC
↓
Network
```

---

# 2.2 MAC Address

## 2.2.1 MAC Address 是什么

**MAC Address** 全称 **Media Access Control Address**，中文：**媒体访问控制地址**。

可以理解成：

> Network Interface 在 Link Layer 使用的地址标识。

常见形式：

```text
00:1A:2B:3C:4D:5E
```

长度：

```text
6 bytes = 48 bits
```

查看：

```bash
ip link show eth0
cat /sys/class/net/eth0/address
```

## 2.2.2 MAC 不是绝对身份

MAC 可以被虚拟化环境生成、管理员修改、软件伪造、容器创建或云平台分配。

所以：

> MAC Address 是 Link Layer 通信用地址，不应当作绝对安全身份。

## 2.2.3 Burned-in Address

**Burned-in Address** 可以理解成 NIC 出厂写入的硬件地址。

但系统当前使用的 MAC 不一定永远等于出厂地址。

## 2.2.4 Ethernet Frame

**Frame**，中文：**帧**。

可以理解成：

> Link Layer 传输的数据单元。

简化结构：

```text
┌──────────────────────┐
│ Destination MAC      │
├──────────────────────┤
│ Source MAC           │
├──────────────────────┤
│ Type                 │
├──────────────────────┤
│ Payload              │
└──────────────────────┘
```

## 2.2.5 Frame 与 Packet

```text
Frame  → Link Layer 数据单元
Packet → Network Layer / IP 层数据单元
```

之后会形成：

```text
Ethernet Frame
  ↓
IP Packet
  ↓
TCP Segment
  ↓
Application Data
```

## 2.2.6 MAC 主要解决局部链路

```text
电脑
↓
家庭 Router
↓
Internet
↓
远程 Server
```

电脑不会直接拿远程 Server 的 MAC 一路穿过 Internet。

MAC 主要解决：

> 当前这一段链路上，Frame 应该交给谁。

跨网络通信主要依赖 IP Address 和 Routing。

## 2.2.7 一个关键例子

Host：

```text
IP: 192.168.1.10
MAC: AA:AA:AA:AA:AA:AA
```

Router：

```text
IP: 192.168.1.1
MAC: RR:RR:RR:RR:RR:RR
```

访问 `8.8.8.8`：

```text
IP Packet:
Source IP      = 192.168.1.10
Destination IP = 8.8.8.8

Ethernet Frame:
Source MAC      = AA:AA:AA:AA:AA:AA
Destination MAC = RR:RR:RR:RR:RR:RR
```

所以：

> IP Destination 可以是远程 Server，但当前 Frame Destination MAC 往往只是下一跳设备的 MAC。

## 2.2.8 Switch

**Switch**，中文：**交换机**。

可以先理解成：

> 在局域网中根据 MAC Address 转发 Ethernet Frame 的设备。

例如：

```text
MAC A → Port 1
MAC B → Port 2
MAC C → Port 3
```

基础模型：

```text
Switch → 主要看 MAC
Router → 主要看 IP
```

## 2.2.9 Broadcast MAC

特殊地址：

```text
ff:ff:ff:ff:ff:ff
```

称为 **Broadcast MAC Address**，中文：**广播 MAC 地址**。

表示：

> 发给当前广播域中的所有相关设备。

---

# 2.3 IP Address

## 2.3.1 IP 是什么

**IP** 全称 **Internet Protocol**，中文：**互联网协议 / 网际协议**。

**IP Address** 可以先理解成：

> 用来标识逻辑网络位置，并支持跨网络寻址的地址。

核心区别：

```text
MAC → 更偏局部链路
IP  → 支持跨网络寻址
```

## 2.3.2 IPv4

**IPv4** 全称 **Internet Protocol Version 4**。

长度：

```text
32 bits = 4 bytes
```

例如：

```text
192.168.1.10
```

四段，每段 8 bits，每段范围 `0～255`。

二进制：

```text
192 = 11000000
168 = 10101000
1   = 00000001
10  = 00001010
```

所以：

```text
192.168.1.10
=
11000000.10101000.00000001.00001010
```

## 2.3.3 IP 通常配置在 Network Interface 上

例如：

```text
eth0 → 192.168.1.10
eth1 → 10.0.0.20
```

所以：

```text
一台机器可以有多个 IP
一个 Interface 也可以有多个 IP
```

查看：

```bash
ip addr
ip addr show eth0
```

## 2.3.4 ip link vs ip addr

```text
ip link → Interface / Link Layer
ip addr → Interface 上配置的 IP Address
```

## 2.3.5 Loopback IP

常见：

```text
127.0.0.1
```

表示当前主机自己。

```bash
ping -c 3 127.0.0.1
```

## 2.3.6 Hostname

**Hostname**，中文：**主机名**。

例如：

```text
server01
worker-gpu-01
my-laptop
```

查看：

```bash
hostname
```

注意：

```text
Hostname ≠ IP Address
```

Hostname 可以通过 DNS 或本地配置解析到 IP。

## 2.3.7 Private IP

**Private IP Address**，中文：**私有 IP 地址**。

常见 IPv4 私有范围：

```text
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
```

常用于家庭 LAN、公司内网、云 VPC、Kubernetes 内部网络。

这些地址可以在不同私有网络中重复使用。

## 2.3.8 Public IP

**Public IP Address**，中文：**公网 IP 地址**。

可以粗略理解成：

> 在公共 Internet 中可进行全球路由的地址。

Private IP 不代表自动安全，它只是地址用途和路由范围不同。

## 2.3.9 IP Packet

**Packet**，中文：**数据包**。

这里指 Network Layer 的 IP Packet。

包含：

```text
Source IP
Destination IP
```

例如：

```text
Source IP      = 192.168.1.10
Destination IP = 8.8.8.8
```

## 2.3.10 MAC 与 IP 再串一次

```text
IP Destination  = 最终目标
MAC Destination = 当前这一跳交给谁
```

跨 Router 时，普通情况下最终 Destination IP 保持指向远程目标，而每一跳的 MAC 会变化。

## 2.3.11 Hop

**Hop**，中文：**跳**。

表示 Packet 经过的一次 Router 转发步骤。

## 2.3.12 TTL

**TTL** 全称 **Time To Live**。

可以理解成：

> Packet 最多还能经过多少个 Router Hop。

每经过一个 Router：

```text
TTL -= 1
```

TTL 防止 Routing Loop 导致 Packet 无限循环。

## 2.3.13 ping 与 ICMP

`ping` 使用 **ICMP（Internet Control Message Protocol）**。

```bash
ping -c 3 127.0.0.1
ping -c 3 8.8.8.8
```

它常用于测试 IP 可达性和大致延迟。

注意：

```text
ping 通
≠ HTTP 正常
≠ SSH 正常
≠ Port 开放
≠ Application 正常
≠ TLS 正常
```

---

# 2.4 Subnet / CIDR

## 2.4.1 Subnet

**Subnet** 全称 **Subnetwork**，中文：**子网**。

可以理解成：

> 一个被划分出来的 IP Address Range。

例如：

```text
192.168.1.0/24
```

## 2.4.2 CIDR

**CIDR** 全称 **Classless Inter-Domain Routing**。

当前最重要的是理解：

```text
192.168.1.10/24
```

中的 `/24`：

> IPv4 前 24 bits 是 Network Prefix。

IPv4 共 32 bits，所以剩余 8 bits 属于 Host 部分。

## 2.4.3 Network Prefix

对于：

```text
192.168.1.10/24
```

前 24 bits：

```text
192.168.1
```

属于 Network 部分。

最后 8 bits 属于 Host 部分。

## 2.4.4 Network Address

对于：

```text
192.168.1.10/24
```

把 Host bits 全部置 0：

```text
192.168.1.0
```

因此整个网络：

```text
192.168.1.0/24
```

## 2.4.5 /24 有多少地址

Host bits = 8，所以：

```text
2^8 = 256
```

范围：

```text
192.168.1.0
～
192.168.1.255
```

传统 IPv4 子网中：

```text
192.168.1.0   → Network Address
192.168.1.255 → Broadcast Address
```

常见可用 Host：

```text
192.168.1.1 ～ 192.168.1.254
```

## 2.4.6 Broadcast Address

**Broadcast Address**，中文：**广播地址**。

对于 `192.168.1.0/24`：

```text
192.168.1.255
```

注意它和 Ethernet Broadcast MAC：

```text
ff:ff:ff:ff:ff:ff
```

不是同一种地址。

## 2.4.7 Subnet Mask

例如：

```text
255.255.255.0
```

叫 **Subnet Mask（子网掩码）**。

它和 `/24` 表达相同的核心 Prefix 信息。

```text
/24
=
11111111.11111111.11111111.00000000
=
255.255.255.0
```

## 2.4.8 /16 与 /8

```text
10.20.30.40/16
→ Network = 10.20.0.0/16
→ 65536 个地址
```

```text
10.20.30.40/8
→ Network = 10.0.0.0/8
→ 16,777,216 个地址
```

## 2.4.9 Prefix 越大，Subnet 越小

```text
/8  → Subnet 很大
/24 → 较小
/30 → 很小
```

所以：

> Prefix 数字越大，地址范围越小。

## 2.4.10 常见 CIDR 表

| CIDR | Subnet Mask | 地址数量 |
|---|---|---:|
| `/8` | `255.0.0.0` | 16,777,216 |
| `/16` | `255.255.0.0` | 65,536 |
| `/24` | `255.255.255.0` | 256 |
| `/25` | `255.255.255.128` | 128 |
| `/26` | `255.255.255.192` | 64 |
| `/27` | `255.255.255.224` | 32 |
| `/28` | `255.255.255.240` | 16 |
| `/29` | `255.255.255.248` | 8 |
| `/30` | `255.255.255.252` | 4 |
| `/32` | `255.255.255.255` | 1 |

不要求现在全部背下来。

## 2.4.11 判断是否同 Subnet

```text
A: 192.168.1.10/24
B: 192.168.1.20/24
```

两者 Network 都是：

```text
192.168.1.0/24
```

所以同 Subnet。

而：

```text
A: 192.168.1.10/24
B: 192.168.2.20/24
```

Network 不同，所以不同 Subnet。

## 2.4.12 IP 必须和 Prefix 一起看

```text
192.168.1.10/24
→ Network = 192.168.1.0

192.168.1.10/16
→ Network = 192.168.0.0
```

所以单独一个 IP 不足以判断属于哪个 Subnet。

## 2.4.13 同 Subnet vs 不同 Subnet

同 Subnet：

```text
通常直接通过本地链路通信
```

不同 Subnet：

```text
通常需要 Router / Default Gateway
```

## 2.4.14 Bitwise AND

**Bitwise AND**，中文：**按位与**。

规则：

```text
1 AND 1 = 1
其他情况 = 0
```

IP 与 Subnet Mask 做 AND，可以得到 Network Address。

例如：

```text
192.168.1.10
AND
255.255.255.0
=
192.168.1.0
```

## 2.4.15 /26 示例

```text
192.168.1.70/26
```

Mask：

```text
255.255.255.192
```

最后一个 Byte：

```text
70  = 01000110
192 = 11000000
```

AND：

```text
01000110
11000000
--------
01000000
```

`01000000 = 64`

所以 Network：

```text
192.168.1.64/26
```

地址范围：

```text
192.168.1.64 ～ 192.168.1.127
```

传统情况下：

```text
Network   = 192.168.1.64
Broadcast = 192.168.1.127
Usable    = 192.168.1.65 ～ 192.168.1.126
```

## 2.4.16 AI Infra / Cloud 为什么关心 CIDR

以后会大量看到：

```text
VPC CIDR
Node Subnet
Pod CIDR
Service CIDR
```

例如：

```text
Node Network:    10.0.0.0/24
Pod Network:     10.244.0.0/16
Service Network: 10.96.0.0/12
```

---

# 2.5 Default Gateway

## 2.5.1 Gateway

**Gateway**，中文：**网关**。

可以理解成：

> 帮你把 Packet 从当前网络转发到其他网络的设备。

家庭网络中通常由 Router 承担。

## 2.5.2 Default Gateway

**Default Gateway**，中文：**默认网关**。

表示：

> 当系统不知道目标 IP 应该通过哪条更具体路径发送时，默认把 Packet 交给这个下一跳设备。

例如：

```text
Host IP: 192.168.1.10/24
Gateway: 192.168.1.1
Target:  8.8.8.8
```

因为 `8.8.8.8` 不属于 `192.168.1.0/24`，所以先交给 `192.168.1.1`。

## 2.5.3 Gateway 不是最终目标

Packet 仍然是：

```text
Source IP      = 192.168.1.10
Destination IP = 8.8.8.8
```

不会因为先交给 Gateway 就把 Destination IP 改成 `192.168.1.1`。

Gateway 只是：

> 下一跳。

## 2.5.4 当前 Frame 的 MAC 会指向 Gateway

当前这一跳：

```text
Host → Gateway
```

所以 Ethernet Frame：

```text
Source MAC      = Host MAC
Destination MAC = Gateway MAC
```

但里面 IP Packet：

```text
Source IP      = Host IP
Destination IP = 最终目标 IP
```

## 2.5.5 完整例子

Host：

```text
IP:      192.168.1.10/24
MAC:     AA:AA:AA:AA:AA:AA
Gateway: 192.168.1.1
```

Router：

```text
IP:  192.168.1.1
MAC: RR:RR:RR:RR:RR:RR
```

访问 `8.8.8.8`：

```text
IP Packet:
Src IP = 192.168.1.10
Dst IP = 8.8.8.8

Ethernet Frame:
Src MAC = AA:AA:AA:AA:AA:AA
Dst MAC = RR:RR:RR:RR:RR:RR
```

## 2.5.6 为什么 Gateway 通常要本地可达

Host：

```text
192.168.1.10/24
```

Gateway：

```text
192.168.1.1
```

两者同属：

```text
192.168.1.0/24
```

所以 Host 能先在本地链路上到达 Gateway。

## 2.5.7 WSL 查看 Default Gateway

```bash
ip route
```

可能看到：

```text
default via 172.20.48.1 dev eth0
172.20.48.0/20 dev eth0 ...
```

解释：

```text
default
→ 默认路由

via 172.20.48.1
→ 下一跳 Gateway

dev eth0
→ 从 eth0 发出去
```

## 2.5.8 default = 0.0.0.0/0

`default` 可以理解成：

```text
0.0.0.0/0
```

`/0` 没有固定任何 Network Prefix bit，因此能匹配所有 IPv4 Destination。

它是没有更具体匹配时的兜底 Route。

Routing Table 的完整工作方式将在 2.6 正式学习。

---

# 2.1 ～ 2.5 核心关系图

## 从 Application 到 NIC

```text
Application
    ↓
Socket FD
    ↓
Kernel Network Stack
    ↓
Network Interface
    ↓
NIC Driver
    ↓
NIC Hardware
    ↓
Network
```

## Frame 与 Packet

```text
Ethernet Frame
┌────────────────────────────┐
│ Source MAC                 │
│ Destination MAC            │
│                            │
│   IP Packet                │
│   ┌────────────────────┐   │
│   │ Source IP          │   │
│   │ Destination IP     │   │
│   │ Payload            │   │
│   └────────────────────┘   │
└────────────────────────────┘
```

记忆：

```text
MAC → 当前链路 / 下一跳
IP  → 最终网络目标
```

## Local vs Remote Subnet

```text
Destination IP
      ↓
与自己同 Subnet？
      │
   ┌──┴──┐
  是     否
  ↓       ↓
本地发送  Default Gateway
```

---

# 核心术语表

| 术语 | 当前理解 |
|---|---|
| NIC | 实际网络硬件设备 |
| Network Interface | Kernel 暴露的网络接口对象 |
| Driver | Kernel 控制 NIC 的软件 |
| Loopback | 本机内部通信的虚拟接口 |
| `lo` | Linux 常见 Loopback Interface |
| `eth0` | 常见 Ethernet Interface 名称 |
| MTU | Maximum Transmission Unit |
| Link Layer | 当前链路 / 局部网络传输层次 |
| MAC Address | Link Layer 地址 |
| Ethernet Frame | Link Layer 数据单元 |
| Switch | 根据 MAC 转发 Frame |
| Broadcast | 向当前广播域发送 |
| IP | Internet Protocol |
| IPv4 | 32-bit IP Address |
| Private IP | 私有网络地址 |
| Public IP | 公网可路由地址 |
| IP Packet | Network Layer 数据单元 |
| Hop | 一次网络转发步骤 |
| TTL | 限制 Packet 可经过的 Router 数量 |
| ICMP | 网络控制消息协议 |
| Subnet | IP 网络中的一个地址范围 |
| CIDR | `/数字` 表示 Prefix 长度 |
| Network Prefix | IP 中标识网络的 bits |
| Host Part | IP 中用于 Host 的 bits |
| Network Address | Host bits 全 0 的地址 |
| Broadcast Address | IPv4 子网广播地址 |
| Subnet Mask | Prefix 的另一种表达 |
| Bitwise AND | 计算 Network Address 的按位运算 |
| Gateway | 将 Packet 转发到其他网络的设备 |
| Default Gateway | 没有更具体 Route 时使用的下一跳 |

---

# WSL 离线实验清单

## Interface

```bash
ip link
ip link show eth0
ip link show lo
```

## sysfs

```bash
ls /sys/class/net
cat /sys/class/net/eth0/address
cat /sys/class/net/eth0/mtu
cat /sys/class/net/eth0/operstate
```

## IP

```bash
ip addr
ip addr show eth0
ip addr show lo
hostname
```

## Loopback

```bash
ping -c 3 127.0.0.1
```

## Default Gateway

```bash
ip route
ip route | grep default
```

---

# 2.1 ～ 2.5 最重要的六句话

1. **NIC 是硬件，Network Interface 是 Kernel 暴露的网络接口对象。**
2. **Process 通过 Socket FD 进入 Kernel Network Stack，再通过 Interface / NIC 发送数据。**
3. **MAC Address 主要解决当前链路上的 Frame 交给谁。**
4. **IP Address 用于逻辑网络寻址，并支持跨网络通信。**
5. **IP Address 必须和 Prefix 一起看，才能判断 Subnet。**
6. **目标不在本地 Subnet 时，通常先把 Packet 交给 Default Gateway。**

---

# 学习进度

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

下一节：

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
