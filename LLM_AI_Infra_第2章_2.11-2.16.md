# LLM / AI Infra 学习笔记

## 第 2 章：计算机网络基础
### 2.11 ～ 2.16（含 2.12A / 2.15A）

> 目标：从 DNS、HTTP、TLS、NAT、Network Namespace 一路建立到 Linux / Docker / Kubernetes / AI API Server 的完整网络心智模型，并掌握基础分层排障方法。
>
> 实验环境建议：WSL2 + Ubuntu + Docker Desktop

---

# 2.11 DNS

## DNS 是什么

**DNS = Domain Name System（域名系统）**。

它解决：

```text
github.com
↓
DNS
↓
IP Address
```

Application 通常先完成名字解析，再建立真正的网络连接：

```text
Application
↓
DNS Resolution
↓
IP Address
↓
TCP / UDP
↓
Routing
↓
Network
```

## Domain Name / Resolution / Resolver

- **Domain Name**：域名，例如 `www.example.com`、`api.openai.com`。
- **Resolution**：解析，即把域名查询成所需 DNS 信息。
- **Resolver**：解析器，帮助 Application 完成 DNS 查询。

典型：

```text
Application
↓
OS Resolver
↓
Configured DNS Server
```

Linux 常见配置：

```bash
cat /etc/resolv.conf
```

可能看到：

```text
nameserver 10.x.x.x
```

或：

```text
nameserver 127.0.0.53
```

WSL 中该文件可能由 WSL / Windows 网络环境自动生成。

## DNS Record

常见记录：

```text
A      → Domain → IPv4
AAAA   → Domain → IPv6
CNAME  → Domain → 另一个 Domain
MX     → Mail Exchange
TXT    → 文本记录
NS     → Name Server
```

### A Record

```text
example.com
↓
A
↓
93.x.x.x
```

### AAAA Record

```text
example.com
↓
AAAA
↓
IPv6 Address
```

### CNAME

```text
api.example.com
↓
CNAME
↓
service.vendor.com
↓
A / AAAA
↓
IP
```

### MX / TXT / NS

- **MX**：指定邮件服务器。
- **TXT**：域名验证、邮件安全配置等文本信息。
- **NS**：指定某个 DNS Zone 的权威 Name Server。

## DNS Zone / Authoritative DNS

**DNS Zone**：由某组 DNS Server 管理的一部分 DNS Namespace。

例如：

```text
example.com
├─ www.example.com
├─ api.example.com
└─ mail.example.com
```

**Authoritative DNS Server（权威 DNS）**：

> 对某个 Zone 提供最终权威答案。

## Recursive Resolver

**Recursive Resolver（递归解析器）**：

> 替 Client 完成多级 DNS 查询。

粗略：

```text
Client
↓
Recursive Resolver
↓
Root DNS
↓
.com TLD Server
↓
example.com Authoritative DNS
↓
Answer
↓
Client
```

## Root / TLD

域名 `www.example.com` 可从右往左理解：

```text
.
↓
com
↓
example
↓
www
```

- `.`：Root
- `.com`：TLD（Top-Level Domain，顶级域）

Root 不保存全世界所有最终 IP，而是知道各 TLD 应该去哪问。

## Iterative Query

**Iterative Query（迭代查询）**：

> 当前 DNS Server 不一定给最终答案，而是告诉查询方下一步该问谁。

例如 Root：

```text
我不知道 www.example.com 的 IP，
但我知道 .com Server 在哪里。
```

## DNS Cache / DNS TTL

DNS 大量使用 Cache。

**DNS TTL** 表示：

> DNS Answer 可缓存多久。

例如：

```text
TTL = 300
```

即缓存 300 秒。

注意：

```text
DNS TTL → 缓存时间
IP TTL  → Packet 最多还能经过多少 Hop
```

因此 DNS 修改不会瞬间全球一致，旧缓存要等 TTL 过期。

## `/etc/hosts` / NSS

Linux 本地静态映射：

```bash
cat /etc/hosts
```

例如：

```text
127.0.0.1 localhost
10.0.0.20 myserver
```

Linux 查询顺序由 **NSS（Name Service Switch）** 等机制控制：

```bash
grep '^hosts:' /etc/nsswitch.conf
```

可能：

```text
hosts: files dns
```

粗略：

```text
先 /etc/hosts
再 DNS
```

系统正常名字解析：

```bash
getent hosts example.com
```

## dig / nslookup

安装：

```bash
sudo apt install dnsutils
```

查询：

```bash
dig example.com
dig +short example.com
dig A example.com
dig AAAA example.com
dig MX example.com
dig NS example.com
dig TXT example.com
```

指定 Resolver：

```bash
dig @8.8.8.8 example.com
```

传统 DNS 常见：

```text
UDP 53
TCP 53
```

DNS 并不是 UDP only。

## DoH / DoT

- **DoH = DNS over HTTPS**
- **DoT = DNS over TLS**

主要用于给 DNS 查询增加加密与完整性保护。

## NXDOMAIN / SERVFAIL

```text
NXDOMAIN
→ 查询的 Domain 不存在

SERVFAIL
→ DNS Server 无法正常完成查询
```

## DNS 故障经典判断

如果：

```bash
ping -c 3 8.8.8.8
```

成功，但：

```bash
curl https://example.com
```

报：

```text
Could not resolve host
```

则优先怀疑 DNS，而不是 Routing。

## Kubernetes 与 DNS

Kubernetes 中常用：

```text
mysql
redis
api
mysql.default.svc.cluster.local
```

通过 DNS 找 Service。

常见组件：**CoreDNS**。

```text
Pod
↓
DNS Query
↓
CoreDNS
↓
Service Address
```

---

# 2.12 HTTP

## HTTP 是什么

**HTTP = Hypertext Transfer Protocol（超文本传输协议）**。

现代 HTTP 大量用于：

```text
JSON API
文件下载
图片
模型 API
Prometheus Metrics
Web Service
```

它属于 Application Layer：

```text
HTTP
↓
TCP
↓
IP
↓
Ethernet
```

HTTP 定义 Request / Response 语义，TCP 负责可靠传输 Bytes。

## Request / Response

```text
Client
↓ HTTP Request
Server
↓ HTTP Response
Client
```

简单 Request：

```http
GET /hello HTTP/1.1
Host: example.com

```

拆解：

```text
GET        → Method
/hello     → Path
HTTP/1.1   → Version
Host: ...  → Header
```

## Method

常见：

```text
GET
POST
PUT
PATCH
DELETE
HEAD
OPTIONS
```

### GET

通常用于获取资源。

### POST

通常用于提交数据给 Server 处理。

例如 LLM API：

```http
POST /v1/chat/completions HTTP/1.1
Content-Type: application/json
```

Body：

```json
{
  "model": "qwen",
  "messages": [
    {"role": "user", "content": "hello"}
  ]
}
```

## URL

例如：

```text
https://api.example.com:8443/v1/models?limit=10
```

拆解：

```text
https             → Scheme
api.example.com   → Host
8443              → Port
/v1/models        → Path
?limit=10         → Query String
```

## Endpoint

例如：

```text
GET  /v1/models
POST /v1/chat/completions
```

都可称 API Endpoint。

## Header / Body

Header 是 HTTP Message 的元数据：

```http
Host: example.com
User-Agent: curl/8.x
Accept: application/json
Content-Type: application/json
```

Body 是真正承载的数据。

## Host Header / Virtual Hosting

HTTP/1.1：

```http
Host: api.example.com
```

同一个 IP 可能承载：

```text
example.com
api.example.com
shop.example.com
```

这叫 **Virtual Hosting**。

## Content-Type

例如：

```http
Content-Type: application/json
```

常见：

```text
application/json
text/html
text/plain
application/octet-stream
image/png
```

## HTTP Message 结构

Request：

```text
Request Line
Headers
空行
Body
```

Response：

```text
Status Line
Headers
空行
Body
```

## Status Code

分类：

```text
1xx → Informational
2xx → Success
3xx → Redirection
4xx → Client Error
5xx → Server Error
```

常见：

```text
200 OK
201 Created
204 No Content
301 / 302 Redirect
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
405 Method Not Allowed
429 Too Many Requests
500 Internal Server Error
502 Bad Gateway
503 Service Unavailable
504 Gateway Timeout
```

## Authentication / Authorization

```text
Authentication
→ 你是谁

Authorization
→ 你能做什么
```

通常：

```text
401 → Authentication 问题
403 → Authorization 问题
```

## 502 / 504

典型：

```text
Client
↓
nginx
↓
vLLM
```

### 502 Bad Gateway

Proxy 收到 Client Request，但访问 Backend 失败或 Backend 返回异常响应。

### 504 Gateway Timeout

Proxy 等 Backend 太久。

LLM TTFT 太高可能直接与 504 相关。

## curl

基础：

```bash
curl http://example.com
```

详细：

```bash
curl -v http://example.com
```

只看 Header：

```bash
curl -I https://example.com
```

POST JSON：

```bash
curl \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"message":"hello"}' \
  http://127.0.0.1:8000/test
```

## Content-Length

例如：

```http
Content-Length: 1234
```

表示 Body 长度。

因为 TCP 是 Byte Stream，不保留 Application Message Boundary，所以 HTTP 需要定义消息边界。

## Chunked Transfer Encoding

HTTP/1.1 可以在不知道完整 Body 长度时分块发送。

## HTTP Streaming / SSE

LLM 可以：

```text
Token 1
Token 2
Token 3
...
```

边生成边通过 HTTP Connection 返回。

**SSE = Server-Sent Events**。

常见：

```text
data: {...}

data: {...}

data: [DONE]
```

## Keep-Alive

一个 TCP Connection 可承载多个 HTTP Request / Response：

```text
TCP Connection
├─ Request 1 / Response 1
├─ Request 2 / Response 2
└─ Request 3 / Response 3
```

减少：

```text
Handshake
TIME_WAIT
Port 压力
CPU 开销
```

## HTTP/1.1 / HTTP/2 / HTTP/3

```text
HTTP/1.1 → TCP
HTTP/2   → TCP + Multiplexing
HTTP/3   → QUIC / UDP
```

## Reverse Proxy / Backend / Load Balancing

```text
Client
↓
Reverse Proxy / Load Balancer
├─ Backend 1
├─ Backend 2
└─ Backend 3
```

Reverse Proxy 常提供：

```text
TLS Termination
Load Balancing
Authentication
Rate Limiting
Logging
Routing
Compression
```

---

# 2.12A HTTP HOL / TCP HOL / QUIC

## HOL Blocking

**HOL = Head-of-Line Blocking（队头阻塞）**。

要分：

```text
HTTP/1.1 Application-Layer HOL
TCP Transport-Layer HOL
```

## HTTP/1.1 HOL

HTTP/1.1 Pipelining：

```text
Request A
Request B
Request C
```

Response 要按顺序：

```text
Response A
Response B
Response C
```

如果 A 很慢：

```text
A 不完成
↓
B 不能先返回
↓
C 也被挡住
```

这就是 HTTP/1.1 Application HOL。

## HTTP/2 Multiplexing

HTTP/2 引入多个 Stream：

```text
TCP Connection
├─ Stream A
├─ Stream B
└─ Stream C
```

数据可以交错：

```text
A1
B1
C1
B2
A2
C2
```

因此基本解决 HTTP 层 HOL。

## TCP HOL

但 HTTP/2 仍基于 TCP。

TCP 是可靠、有序 Byte Stream。

```text
Byte 1
Byte 2
Byte 3 ← 丢失
Byte 4
Byte 5
```

即使 4、5 已到，TCP 也要等 Byte 3 重传后再按序交给上层。

因此：

> 一个 TCP 丢包可能让同一 HTTP/2 Connection 上多个 Stream 一起等待。

## QUIC / HTTP3

```text
HTTP/3
↓
QUIC
↓
UDP
```

QUIC 自己实现：

```text
Reliable Delivery
Retransmission
Congestion Control
TLS
Multiple Streams
```

关键：不同 Stream 可独立有序交付。

```text
QUIC Connection
├─ Stream A
├─ Stream B
└─ Stream C
```

A 丢数据，不必阻塞 B/C。

因此 QUIC 改善：

> Cross-Stream Transport HOL。

注意：同一 Stream 内仍然可能 HOL。

## QUIC 为什么用 UDP

UDP 本身很简单：

```text
Datagram
Port
Checksum
```

QUIC 可以在 User Space 快速迭代：

```text
可靠性
重传
Stream
TLS
拥塞控制
```

此外 QUIC 还支持：

```text
更快连接建立
TLS 1.3 集成
0-RTT
Connection Migration
Connection ID
```

三代对比：

| 项目 | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|---|---|---|
| Transport | TCP | TCP | QUIC/UDP |
| Multiplexing | 弱 | 有 | 有 |
| HTTP 层 HOL | 明显 | 基本解决 | 基本解决 |
| TCP 层 HOL | 有 | 有 | 不使用 TCP |
| Cross-Stream Transport HOL | 有 | 有 | 大幅改善 |

---

# 2.13 TLS / HTTPS

## TLS

**TLS = Transport Layer Security（传输层安全协议）**。

三个核心目标：

```text
Confidentiality → 机密性
Integrity       → 完整性
Authentication  → 身份认证
```

## HTTPS

```text
HTTPS = HTTP over TLS
```

经典：

```text
HTTP
↓
TLS
↓
TCP
↓
IP
```

## Encryption / Plaintext / Ciphertext

```text
Plaintext
↓ Encryption
Ciphertext
↓ Decryption
Plaintext
```

**Key（密钥）** 是密码系统的核心输入之一。

## Symmetric Encryption

**对称加密**：双方共享同一把或等价密钥。

优点：快，适合大量数据。

TLS 后续 HTTP 数据主要使用对称加密。

## Asymmetric Cryptography

**非对称密码学**：

```text
Public Key
Private Key
```

用于：

```text
身份认证
数字签名
密钥协商
```

现代 TLS 并不是“拿 Server Public Key 加密所有 HTTP Body”。

更准确：

```text
TLS Handshake
↓
认证 / 密钥协商
↓
Session Keys
↓
后续数据使用对称加密
```

## TLS Handshake

粗略：

```text
Client                     Server

ClientHello
------------------------->

                     ServerHello
                     Certificate
<-------------------------

验证证书
密钥协商
建立 Session Keys

Finished
------------------------->

                     Finished
<-------------------------

Encrypted Application Data
<========================>
```

## Certificate / PKI / CA

**Certificate（数字证书）**：

> 把 Public Key 与 Domain / Server Identity 绑定。

**PKI = Public Key Infrastructure（公钥基础设施）**。

**CA = Certificate Authority（证书颁发机构）**。

典型信任链：

```text
Root CA
↓
Intermediate CA
↓
Server Certificate
```

Client 的 Trust Store 信任 Root CA。

## Digital Signature

**数字签名**主要证明：

```text
是谁签的？
内容有没有被修改？
```

注意：

```text
Signature ≠ Encryption
```

## SAN / Wildcard Certificate

**SAN = Subject Alternative Name**：定义证书对哪些 Hostname 有效。

例如：

```text
DNS:example.com
DNS:www.example.com
DNS:api.example.com
```

Wildcard：

```text
*.example.com
```

可覆盖部分一级子域。

## SNI

**SNI = Server Name Indication**。

作用：

> Client 在 TLS Handshake 阶段告诉 Server 想访问哪个 Hostname。

区别：

```text
SNI
→ TLS 层
→ 用于选 Certificate

Host Header
→ HTTP 层
→ 用于选 Virtual Host
```

## mTLS

**mTLS = Mutual TLS（双向 TLS）**。

```text
Client 验证 Server Certificate
+
Server 验证 Client Certificate
```

常用于 Service-to-Service、Zero Trust、Service Mesh。

## TLS Termination

```text
Client
↓ HTTPS
nginx / Load Balancer
↓ HTTP
vLLM
```

TLS 在 Proxy 处结束。

也可以 Backend 继续 HTTPS，实现更接近 End-to-End Encryption。

## TLS 1.2 / TLS 1.3

TLS 1.3：

```text
握手更简化
移除很多旧算法
通常延迟更低
```

## Session Resumption / 0-RTT

**Session Resumption**：减少重复 TLS Handshake 成本。

**0-RTT**：某些恢复连接可以更早发送 Application Data，但需要注意 Replay Risk。

## HTTPS 完整流程

```text
https://api.example.com/v1/models
↓
DNS
↓
IP
↓
TCP :443
↓
TLS Handshake
├─ ClientHello
├─ SNI
├─ ServerHello
├─ Certificate
├─ Certificate Validation
└─ Session Keys
↓
Encrypted Channel
↓
HTTP Request / Response
```

## HTTPS 隐藏什么

TLS 通常保护：

```text
HTTP Method
Path
Headers
Cookie
Authorization
Body
Prompt
Model Output
```

但网络仍可能看到：

```text
Source IP
Destination IP
Port
Packet Size
Timing
Traffic Volume
```

## Self-Signed / Trust Store / curl -k

自签名证书默认通常不被 Trust Store 信任。

```bash
curl -k https://...
```

表示跳过证书验证。

生产环境不应把 `-k` 当正常解决方案。

## OpenSSL

```bash
openssl s_client \
  -connect example.com:443 \
  -servername example.com
```

观察：

```text
Certificate Chain
subject
issuer
TLS Version
Cipher
Verify Result
```

---

# 2.14 NAT

## NAT 是什么

**NAT = Network Address Translation（网络地址转换）**。

它会在转发 Packet 时修改：

```text
IP Address
有时还有 Port
```

并维护转换状态。

## Private IPv4

常见：

```text
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
```

多个网络可以重复使用这些地址。

## SNAT

**SNAT = Source Network Address Translation**。

修改 Source：

```text
192.168.1.10
↓
203.0.113.50
```

## PAT / NAPT

为了让多个内部 Host 共用一个 Public IP，常同时转换 Port：

```text
192.168.1.10:50001
→ 8.8.8.8:443

192.168.1.20:50001
→ 8.8.8.8:443
```

转换为：

```text
203.0.113.50:61001
→ 8.8.8.8:443

203.0.113.50:61002
→ 8.8.8.8:443
```

## Stateful NAT

NAT 需要保存：

```text
Internal IP:Port
↔
External IP:Port
```

因此典型 NAT 是 Stateful 的。

## DNAT

**DNAT = Destination Network Address Translation**。

例如：

```text
203.0.113.50:8080
↓
192.168.1.10:80
```

## Port Forwarding

典型：

```text
Public :2222
↓
Private :22
```

本质上经常是 DNAT。

## SNAT vs DNAT

```text
SNAT → 改 Source
DNAT → 改 Destination
```

## MASQUERADE

一种适合动态出口 IP 的 SNAT。

常用于：

```text
家庭宽带
DHCP
PPPoE
```

## NAT 不等于 Firewall

```text
NAT
→ 地址 / Port 转换

Firewall
→ Allow / Deny Traffic
```

家庭 Router 往往同时实现两者，所以容易混淆。

## CGNAT

**CGNAT = Carrier-Grade NAT（运营商级 NAT）**。

常见 Shared Address Space：

```text
100.64.0.0/10
```

如果家庭 Router WAN 得到 `100.64.x.x`，可能还在 ISP NAT 后面。

## Double NAT

```text
Laptop 192.168.1.10
↓
Home Router 100.64.1.20
↓
ISP CGNAT
↓
Public IP
```

即两层 NAT。

CGNAT 下自家 Router 配 Port Forwarding 也可能无法让公网真正访问进来。

## NAT Traversal

用于 NAT 后的 P2P 通信。

常见相关技术：

```text
STUN
TURN
ICE
```

## Hairpin NAT

内部 Host 使用 Public IP 访问同一 LAN 内部 Service：

```text
LAN
→ Public IP
→ NAT
→ 回 LAN
```

## IPv6 与 NAT

IPv6 地址空间大，因此不依赖 IPv4 这种大规模地址共享 NAT。

但：

```text
No NAT ≠ No Firewall
```

## Docker 与 NAT

经典 Linux Docker：

```text
Container
172.17.0.2
↓
docker0
↓
Host
↓
SNAT / MASQUERADE
↓
Internet
```

Docker Port Mapping：

```bash
docker run -p 8080:80 nginx
```

概念：

```text
Host :8080
↓
DNAT / Port Mapping
↓
Container :80
```

## conntrack / 5-tuple

**conntrack = Connection Tracking**。

Linux Kernel 用来追踪 Flow / Connection 状态。

**5-tuple**：

```text
Source IP
Source Port
Destination IP
Destination Port
Protocol
```

## iptables / nftables

传统：

```text
iptables
```

现代：

```text
nftables
```

可用于 Firewall / NAT。

查看：

```bash
sudo nft list ruleset
```

---

# 2.15 Linux Network Namespace

## Namespace

**Namespace（命名空间）**：

> Linux Kernel 提供的资源隔离机制，让不同 Process 看到不同系统资源视图。

常见：

```text
PID Namespace
Network Namespace
Mount Namespace
UTS Namespace
IPC Namespace
User Namespace
Cgroup Namespace
```

## Network Namespace

简称：

```text
netns
```

它提供独立网络栈视图：

```text
Network Interfaces
IP Addresses
Routing Table
Neighbor Table
Sockets
Ports
Firewall Rules
Loopback Interface
```

最关键：

> Network Namespace 隔离的是整个网络栈视图，不只是一张网卡。

## Container 不是 VM

Container 可以理解成：

```text
Linux Process
+
Namespaces
+
Cgroups
+
Filesystem Isolation
```

多个 Container 共用 Host Kernel。

## veth

**veth = Virtual Ethernet**。

总是成对出现：

```text
veth-A
<======= >
veth-B
```

可以理解成 Kernel 内的一根虚拟网线。

## Container veth

```text
Host NetNS
veth-host
   ║
   ║
Container NetNS
eth0
```

Container `eth0` 经常就是 veth pair 的一端。

## Linux Bridge

Linux Bridge：

> Kernel 中的软件 Layer 2 Switch。

主要基于 MAC Address 转发 Ethernet Frame。

## docker0

Docker 默认 bridge 网络常见：

```text
docker0
```

本质通常就是 Linux Bridge。

```text
Container A
172.17.0.2
   │
 veth
   │
docker0
   │
 veth
   │
Container B
172.17.0.3
```

## Container 出网

```text
Container
172.17.0.2
↓
eth0
↓
veth
↓
docker0 / bridge
↓
Host Routing
↓
SNAT / MASQUERADE
↓
Host NIC
↓
Internet
```

## Container Gateway

例如：

```text
Container IP 172.17.0.2/16
Gateway      172.17.0.1
```

Gateway 常是 Host 上 docker0 或 user-defined bridge 的 IP。

## 每个 NetNS 有自己的 lo

```text
Container A localhost
≠
Container B localhost
≠
Host localhost
```

同样：

```text
0.0.0.0
```

也只代表当前 Network Namespace 的所有合适 IPv4 Interface。

## Port 隔离

不同 NetNS 可以同时监听同一个 Port：

```text
Container A :80
Container B :80
```

完全可以。

## ip netns 实验

```bash
sudo ip netns add ns1
sudo ip netns add ns2
```

创建 veth：

```bash
sudo ip link add veth1 type veth peer name veth2
```

移入：

```bash
sudo ip link set veth1 netns ns1
sudo ip link set veth2 netns ns2
```

配置：

```bash
sudo ip netns exec ns1 \
  ip addr add 10.10.0.1/24 dev veth1

sudo ip netns exec ns2 \
  ip addr add 10.10.0.2/24 dev veth2
```

启用：

```bash
sudo ip netns exec ns1 ip link set veth1 up
sudo ip netns exec ns2 ip link set veth2 up
sudo ip netns exec ns1 ip link set lo up
sudo ip netns exec ns2 ip link set lo up
```

测试：

```bash
sudo ip netns exec ns1 ping -c 3 10.10.0.2
```

观察：

```bash
sudo ip netns exec ns1 ip addr
sudo ip netns exec ns1 ip route
sudo ip netns exec ns1 ip neigh
```

删除：

```bash
sudo ip netns del ns1
sudo ip netns del ns2
```

## Kubernetes Pod NetNS

一个 Pod 内多个 Container 通常共享同一个 Network Namespace。

因此：

```text
同一个 Pod IP
同一个 lo
同一个 Port Space
```

同 Pod Container 可以：

```text
127.0.0.1
```

互相通信。

**Pause Container** 可先理解成：用于维持 Pod Namespace 生命周期的轻量基础 Container。

---

# 2.15A Docker Desktop / WSL2 网络架构

## 示例环境

Ubuntu WSL：

```text
eth0 = 172.26.65.141
```

Docker Container：

```text
IP      = 172.22.0.2/16
Gateway = 172.22.0.1
```

在 Ubuntu WSL 中看不到：

```text
172.22.0.1
Docker Bridge
Container veth
```

是正常现象。

## 原因

Docker Desktop 的 Docker Engine 并不运行在 Ubuntu WSL 的 Network Namespace 中。

更接近：

```text
Windows
├─ Ubuntu WSL
│   ├─ eth0 = 172.26.65.141
│   └─ docker CLI
│
└─ Docker Desktop Linux Environment
    ├─ Docker Engine
    ├─ Docker Bridge
    ├─ Container veth
    └─ Container NetNS
```

WSL Integration：

> 让 Ubuntu 中的 docker CLI 能连接 Docker Desktop Engine。

它不代表 Docker Engine 位于 Ubuntu WSL。

## `172.22.0.1` 是什么

如果 Container：

```text
172.22.0.2/16
Gateway 172.22.0.1
```

那么 `172.22.0.1` 通常是 Docker user-defined bridge network 的 Gateway IP。

查看：

```bash
docker inspect <container> \
  --format '{{json .NetworkSettings.Networks}}'
```

以及：

```bash
docker network inspect <network>
```

## 为什么 Ubuntu 看不到 veth / bridge

因为：

```bash
ip addr
ip link
```

只显示当前 Ubuntu WSL 自己的 Linux 网络视图。

Docker Bridge / Container veth 属于 Docker Desktop 自己的 Linux environment。

## Container 是否通过 Ubuntu eth0 出网

通常不是。

不要理解成：

```text
Container
↓
Docker Bridge
↓
Ubuntu eth0 172.26.65.141
↓
Internet
```

更接近：

```text
Container
172.22.0.2
↓
veth
↓
Docker Bridge
172.22.0.1
↓
Docker Desktop Linux Networking
↓
NAT / Desktop Backend
↓
Windows TCP/IP Stack
↓
Physical NIC
↓
Internet
```

所以 Ubuntu WSL `172.26.65.141` 通常不是 Container 主出网链路的一部分。

## docker CLI ≠ dockerd 所在环境

你可以：

```bash
docker ps
```

正常工作，但：

```bash
ps aux | grep dockerd
```

不一定能在 Ubuntu 找到真正管理 Container 的 daemon。

逻辑：

```text
docker CLI
↓
Docker API / WSL Integration
↓
Docker Desktop Engine
```

## `ip netns list` 为什么可能看不到 Container

Linux Network Namespace 不要求必须通过 `ip netns add` 创建。

`ip netns list` 并不是 Kernel 中所有 NetNS 的完整数据库。

Container runtime 可以直接通过 Namespace API 管理 NetNS。

所以：

```text
Container 确实有 NetNS
```

同时：

```text
ip netns list
→ 可能看不到
```

并不矛盾。

## 原生 Linux vs Docker Desktop

原生 Linux Docker：

```text
Container
↓
veth
↓
docker0 / br-xxx
↓
Linux Host Routing / NAT
↓
Linux Host eth0
↓
Internet
```

Docker Desktop + WSL2：

```text
Container
↓
veth
↓
Docker Bridge
↓
Docker Desktop Linux Environment
↓
Desktop Backend Networking
↓
Windows TCP/IP
↓
Physical NIC
↓
Internet
```

---

# 2.16 网络基础排障

## 第一原则：先分层

“网络不通”不是一个单独故障。

可能是：

```text
DNS
Routing
ARP
TCP
Port / Listener
TLS
HTTP
Application
```

排障顺序建议：

```text
1. Name
2. Route
3. Neighbor
4. TCP
5. TLS
6. HTTP
7. Application
```

## 常见错误与层次

```text
Could not resolve host
→ DNS

Network is unreachable
→ Routing / Interface

Connection refused
→ Port / Listener

Connection timed out
→ Firewall / Routing / Host / Loss

TLS certificate error
→ TLS / PKI

HTTP 404
→ HTTP Path

HTTP 500
→ Application

HTTP 502
→ Proxy → Backend

HTTP 504
→ Backend Timeout
```

## Refused vs Timeout

### Connection refused

典型：

```text
Client
↓ SYN
Server
↓ RST
Client
↓
Connection refused
```

说明目标网络栈大概率已经收到 SYN，但没有正常 Listener。

### Timeout

```text
Client
↓ SYN
...
无回应
...
重试
...
Timeout
```

可能：

```text
Firewall Drop
Routing
Host Offline
Return Path
Packet Loss
```

## 第一轮五个命令

```bash
ip link
ip addr
ip route
ip neigh
ss -lntup
```

分别回答：

```text
ip link  → Interface 活着吗？
ip addr  → IP 配了吗？
ip route → Packet 往哪走？
ip neigh → Next Hop MAC 能解析吗？
ss       → Port / Socket 有没有 Listener？
```

## Interface / IP

推荐：

```bash
ip -br link
ip -br addr
```

确认：

```text
UP / LOWER_UP
IP
Prefix
```

## Routing

```bash
ip route
```

更推荐：

```bash
ip route get <target-ip>
```

Kernel 会告诉你：

```text
Next Hop
Interface
Source IP
```

Multi-NIC AI Server 上尤其重要。

## Neighbor / ARP

```bash
ip neigh
```

重点：

```text
REACHABLE
STALE
INCOMPLETE
FAILED
```

`FAILED` 表示 Neighbor Resolution 失败。

优先检查：

```text
ARP
Layer 2
veth
bridge
VLAN
Gateway
```

`STALE` 通常不是故障。

## Ping / ICMP

```bash
ping -c 3 <target>
```

主要观察：

```text
IP Reachability
RTT
Packet Loss
```

但：

```text
Ping OK ≠ Application OK
Ping Fail ≠ Server 一定挂了
```

因为 ICMP 可能被过滤。

## Port / Listener

```bash
ss -ltnp
ss -lunp
```

特定：

```bash
ss -ltnp | grep ':8000'
```

如果：

```text
127.0.0.1:8000
```

通常只允许当前 NetNS 本地访问。

如果：

```text
0.0.0.0:8000
```

表示当前 NetNS 所有合适 IPv4 Interface 都监听。

## netcat / nc

```bash
nc -vz 10.0.0.20 8000
```

区别：

```text
nc   → 测 TCP Connection
curl → 测 HTTP / HTTPS Application
```

## DNS 排障

```bash
getent hosts api.example.com
dig api.example.com
dig @8.8.8.8 api.example.com
```

如果 IP 可达但域名失败，优先怀疑 DNS。

## TLS 排障

```bash
curl -v https://api.example.com
```

更底层：

```bash
openssl s_client \
  -connect api.example.com:443 \
  -servername api.example.com
```

## HTTP 排障

```bash
curl -v https://api.example.com/v1/models
```

状态码：

```text
404 → Path
401 → Authentication
403 → Authorization
429 → Rate Limit
500 → Application
502 → Proxy → Backend
503 → Service Unavailable
504 → Backend Timeout
```

## tcpdump

```bash
sudo tcpdump -ni eth0 host 10.0.0.20
```

特定 TCP：

```bash
sudo tcpdump -ni eth0 'tcp port 8000'
```

正常握手：

```text
SYN
SYN+ACK
ACK
```

只看到：

```text
SYN
SYN
SYN
```

说明 Client 一直发，但没有得到有效回答。

看到：

```text
SYN
RST
```

通常对应 `Connection refused`。

## MTU / PMTUD

**Path MTU**：整条路径实际可安全通过的最大 Packet Size 上限。

**PMTUD = Path MTU Discovery**。

典型问题：

```text
小包正常
TCP Handshake 正常
小 HTTP 正常
大数据开始卡
```

可能与：

```text
MTU
Fragmentation
PMTUD
ICMP Filtering
```

有关。

初步测试：

```bash
ping -M do -s 1472 8.8.8.8
```

IPv4 粗略：

```text
1472 Payload
+20 IPv4 Header
+8 ICMP Header
=1500
```

## TCP Retransmission

网络能通但很慢时：

```text
Packet Loss
↓
TCP Retransmission
↓
Latency 上升
```

可初步：

```bash
ss -ti
```

观察 RTT / cwnd / retrans 等信息。

## Docker Container 排障

Container 内：

```bash
ip addr
ip route
ip neigh
```

Docker 侧：

```bash
docker inspect <container>
docker network inspect <network>
```

确认：

```text
Subnet
Gateway
Container IP
Network Driver
```

先测试 Gateway，再测试公网 IP，再测试 DNS。

例如：

```text
Container 172.22.0.2
Gateway   172.22.0.1
```

```bash
ping 172.22.0.1
ping 8.8.8.8
getent hosts example.com
```

## Docker Port Mapping 排障

```bash
docker ps
```

确认：

```text
0.0.0.0:8080->80/tcp
```

Container 内：

```bash
ss -ltn
```

确认 `:80` 有 Listener。

然后 Host：

```bash
curl http://localhost:8080
```

如果 Container 自己 `curl 127.0.0.1:80` 都失败，问题在 Application，而不是 Port Mapping。

## WSL / Docker Desktop 排障特别注意

可能同时存在：

```text
Windows
Ubuntu WSL
Docker Desktop Linux Environment
Container NetNS
```

每次运行 `ip addr` 前，先问：

> 我现在到底在哪个 Linux environment / Network Namespace 中？

## AI API Server 排障示例

架构：

```text
Client
↓
api.example.com
↓
Reverse Proxy
↓
vLLM :8000
```

建议：

```bash
getent hosts api.example.com
```

↓

```bash
ip route get <resolved-ip>
```

↓

```bash
nc -vz <resolved-ip> 443
```

↓

```bash
curl -v https://api.example.com/v1/models
```

如果返回：

```text
502 Bad Gateway
```

则 Client → Proxy 大概率正常，继续检查 Proxy → vLLM：

```bash
ss -ltnp | grep ':8000'
curl http://127.0.0.1:8000/v1/models
```

如果 Backend 自己 500，再查：

```text
vLLM
Model
GPU
Memory
Disk
Dependencies
```

## 不要第一步就抓包 / 重启

推荐：

```text
Observe
↓
Classify
↓
Narrow Down
↓
Fix
```

Restart / Reboot 可能破坏现场证据：

```text
Socket State
Neighbor State
Connection State
Logs
Process State
```

---

# 第 2 章完整网络心智模型

```text
Application
    ↓
HTTP / API
    ↓
TLS
    ↓
DNS Resolution
    ↓
IP Address
    ↓
Socket / Port
    ↓
TCP / UDP
    ↓
Routing Table
    ↓
Next Hop
    ↓
Neighbor / ARP
    ↓
MAC Address
    ↓
Network Interface
    ↓
NIC / veth
    ↓
Bridge / Switch
    ↓
Router / NAT
    ↓
Network
```

Container：

```text
Process
↓
Socket
↓
Container NetNS
↓
eth0
↓
veth
↓
Linux Bridge
↓
Host Routing
↓
conntrack
↓
NAT
↓
Host / Docker Desktop Networking
↓
Internet
```

---

# 核心术语表

| 术语 | 当前理解 |
|---|---|
| DNS | Domain Name System |
| Resolver | DNS 解析器 |
| Authoritative DNS | 对某个 Zone 提供权威答案 |
| Recursive Resolver | 替 Client 完成多级查询 |
| A | Domain → IPv4 |
| AAAA | Domain → IPv6 |
| CNAME | Domain → Domain |
| DNS TTL | DNS Cache 时间 |
| HTTP | Application Layer Request / Response Protocol |
| URL | Scheme + Host + Port + Path + Query |
| Header | HTTP 元数据 |
| Body | HTTP 数据主体 |
| Status Code | HTTP 处理结果 |
| HOL Blocking | 队头阻塞 |
| Multiplexing | 多路复用 |
| QUIC | 基于 UDP 的现代传输协议 |
| TLS | Transport Layer Security |
| Certificate | 数字证书 |
| PKI | Public Key Infrastructure |
| CA | Certificate Authority |
| SNI | TLS Handshake 中携带目标 Hostname |
| mTLS | 双向 TLS |
| NAT | Network Address Translation |
| SNAT | 修改 Source |
| DNAT | 修改 Destination |
| PAT / NAPT | IP + Port Translation |
| conntrack | Linux Connection Tracking |
| Network Namespace | 独立网络栈视图 |
| veth | Virtual Ethernet |
| Linux Bridge | 软件 Layer 2 Switch |
| docker0 | Docker 默认常见 Bridge |
| netcat / nc | TCP/UDP 测试工具 |
| tcpdump | Packet Capture |
| Path MTU | 整条路径有效 MTU |
| PMTUD | Path MTU Discovery |

---

# 离线实验清单

## DNS

```bash
cat /etc/resolv.conf
cat /etc/hosts
grep '^hosts:' /etc/nsswitch.conf
getent hosts example.com

sudo apt install dnsutils
dig example.com
dig +short example.com
dig A example.com
dig AAAA example.com
dig NS example.com
dig @8.8.8.8 example.com
```

## HTTP

```bash
mkdir -p /tmp/http-demo
cd /tmp/http-demo
echo "hello http" > index.html
python3 -m http.server 8000
```

另一个 Terminal：

```bash
ss -ltnp | grep ':8000'
curl http://127.0.0.1:8000
curl -v http://127.0.0.1:8000
curl -I http://127.0.0.1:8000
sudo tcpdump -A -ni lo tcp port 8000
```

## TLS

```bash
curl -v https://example.com
curl -I https://example.com

openssl s_client \
  -connect example.com:443 \
  -servername example.com
```

## Network Namespace

```bash
sudo ip netns add ns1
sudo ip netns add ns2
sudo ip link add veth1 type veth peer name veth2
sudo ip link set veth1 netns ns1
sudo ip link set veth2 netns ns2
sudo ip netns exec ns1 ip addr add 10.10.0.1/24 dev veth1
sudo ip netns exec ns2 ip addr add 10.10.0.2/24 dev veth2
sudo ip netns exec ns1 ip link set veth1 up
sudo ip netns exec ns2 ip link set veth2 up
sudo ip netns exec ns1 ip link set lo up
sudo ip netns exec ns2 ip link set lo up
sudo ip netns exec ns1 ping -c 3 10.10.0.2
sudo ip netns exec ns1 ip addr
sudo ip netns exec ns1 ip route
sudo ip netns exec ns1 ip neigh
sudo ip netns del ns1
sudo ip netns del ns2
```

## Docker

```bash
docker network ls
docker network inspect <network>
docker inspect <container> \
  --format '{{json .NetworkSettings.Networks}}'
```

Container 内：

```bash
ip addr
ip route
ip neigh
```

## 基础排障

```bash
ip -br link
ip -br addr
ip route
ip route get <target-ip>
ip neigh
getent hosts <hostname>
nc -vz <host> <port>
curl -v http://<host>:<port>
curl -v https://<hostname>
openssl s_client -connect <host>:443 -servername <hostname>
sudo tcpdump -ni <interface> host <target-ip>
sudo tcpdump -ni <interface> 'tcp port <port>'
```

---

# 第 2 章最终排障速查表

| 症状 | 优先检查 |
|---|---|
| `Could not resolve host` | DNS |
| `Network is unreachable` | Route / Interface |
| Gateway 不通 | Local Link / ARP / Interface |
| `ip neigh FAILED` | Neighbor / L2 |
| `Connection refused` | TCP Port / Listener |
| TCP timeout | Firewall / Routing / Host |
| TLS certificate error | TLS / PKI |
| HTTP 404 | HTTP Path / Routing |
| HTTP 401 | Authentication |
| HTTP 403 | Authorization |
| HTTP 429 | Rate Limit |
| HTTP 500 | Application |
| HTTP 502 | Proxy → Backend |
| HTTP 503 | Service Unavailable |
| HTTP 504 | Backend Timeout |
| Ping OK 但 HTTP 不通 | TCP / Port / TLS / Application |
| IP 可达但域名失败 | DNS |
| 小包正常大包异常 | MTU / PMTUD |
| 本机通远程不通 | Bind Address / Firewall |
| Container 内通 Host 不通 | Port Mapping / NAT |
| Container Gateway 通但不能出网 | NAT / Forwarding / Docker Desktop Networking |

---

# 本部分最重要的十二句话

1. **DNS 把 Domain Name 解析成网络通信真正使用的地址信息。**
2. **HTTP 定义 Request / Response 语义，TCP 只负责可靠 Byte Stream。**
3. **HTTP/1.1 有应用层 HOL，HTTP/2 解决 HTTP 层 HOL，但仍受 TCP HOL 影响。**
4. **HTTP/3 使用 QUIC，让不同 Stream 不再因为同一 TCP Byte Stream 的丢包一起等待。**
5. **HTTPS = HTTP over TLS。**
6. **TLS 的核心目标是 Confidentiality、Integrity、Authentication。**
7. **NAT 会修改 IP / Port，并依赖 Connection Tracking 保存映射。**
8. **SNAT 改 Source，DNAT 改 Destination。**
9. **Network Namespace 隔离的是整个网络栈视图，不只是 Interface。**
10. **veth pair 可以理解成 Linux Kernel 内的一根虚拟 Ethernet Cable。**
11. **Docker Desktop + WSL2 中，Container 网络不一定位于 Ubuntu WSL 的 Network Namespace。**
12. **网络排障要固定按 DNS → Route → Neighbor → TCP → TLS → HTTP → Application 缩小范围。**

---

# 当前课程进度

```text
第 0 章：AI Infra 心智模型
✅ 完成

第 1 章：Linux 与计算机系统基础
✅ 完成

第 2 章：计算机网络基础
✅ 完成

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
✅ 2.11 DNS

✅ 2.12 HTTP
    ├─ Request / Response
    ├─ Method / Path / URL
    ├─ Header / Body
    ├─ Status Code
    ├─ Keep-Alive
    ├─ Streaming / SSE
    ├─ HTTP/1.1 / HTTP/2 / HTTP/3
    ├─ Reverse Proxy
    └─ Load Balancing 初步

✅ 2.12A HTTP HOL / TCP HOL / QUIC
    ├─ HTTP/1.1 Application HOL
    ├─ HTTP Pipelining
    ├─ HTTP/2 Multiplexing
    ├─ TCP HOL
    ├─ QUIC Independent Streams
    ├─ Cross-Stream HOL
    ├─ Connection Migration
    └─ HTTP/3

✅ 2.13 TLS / HTTPS
    ├─ Confidentiality / Integrity / Authentication
    ├─ Symmetric / Asymmetric Cryptography
    ├─ TLS Handshake
    ├─ Certificate / PKI / CA
    ├─ Certificate Chain
    ├─ SNI
    ├─ mTLS
    ├─ TLS Termination
    ├─ Trust Store
    └─ OpenSSL

✅ 2.14 NAT
    ├─ SNAT / DNAT
    ├─ PAT / NAPT
    ├─ Port Forwarding
    ├─ MASQUERADE
    ├─ CGNAT
    ├─ conntrack
    ├─ 5-tuple
    └─ Docker NAT 初步

✅ 2.15 Linux Network Namespace 初步
    ├─ Namespace
    ├─ Network Namespace / netns
    ├─ veth pair
    ├─ Linux Bridge
    ├─ docker0
    ├─ Loopback / Port Isolation
    ├─ ip netns
    └─ Kubernetes Pod NetNS 初步

✅ 2.15A Docker Desktop / WSL2 网络架构
    ├─ WSL Integration ≠ Docker Engine 位于 Ubuntu
    ├─ Docker Desktop Linux environment
    ├─ Docker Bridge 位于 Docker Desktop 网络环境
    ├─ 为什么 Ubuntu 看不到 docker0 / veth
    ├─ Container → Bridge → NAT
    ├─ Ubuntu WSL eth0 不在 Container 主出网链路
    ├─ docker network inspect
    └─ NetNS 不一定出现在 ip netns list

✅ 2.16 网络基础排障
    ├─ Layered Troubleshooting
    ├─ Interface / IP
    ├─ Routing / ip route get
    ├─ Neighbor / ARP
    ├─ Ping / ICMP
    ├─ Port / Listener
    ├─ nc
    ├─ DNS
    ├─ TLS
    ├─ HTTP
    ├─ tcpdump
    ├─ MTU / PMTUD 初步
    ├─ TCP Retransmission 初步
    ├─ Docker 网络排障
    ├─ Network Namespace 排障
    └─ AI API Server 分层排障

下一章：

⬜ 第 3 章：Python + Go
```
