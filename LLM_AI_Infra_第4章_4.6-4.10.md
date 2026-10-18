# LLM / AI Infra 学习笔记
# 第 4 章：Docker 与 Container Internals
## 4.6 ～ 4.10 离线学习版

> 覆盖范围：  
> 4.6 Docker Engine / containerd / runc / OCI  
> 4.7 Container Network：NetNS / veth / bridge  
> 4.8 Docker Port Mapping / Routing / NAT  
> 4.9 Volume / Bind Mount / Container Storage  
> 4.10 Container PID 1 / Signal / Zombie  

---

# 目录

- 4.6 Docker Engine / containerd / runc / OCI
- 4.7 Container Network：NetNS / veth / bridge
- 4.8 Docker Port Mapping / Routing / NAT
- 4.9 Volume / Bind Mount / Container Storage
- 4.10 Container PID 1 / Signal / Zombie
- 第 4 章进度目录
- 实验安全与回退原则

---

# 4.6 Docker Engine / containerd / runc / OCI

前面已经建立：

```text
Container
≈ Linux Process
+ Namespaces
+ cgroups
+ RootFS
+ Runtime management
```

现在回答：

> `docker run nginx` 到底是谁把 Image、RootFS、Namespace、cgroup 和 Linux Process 组合起来的？

核心链路：

```text
Docker CLI
    ↓
Docker Engine API
    ↓
dockerd
    ↓
containerd
    ↓
containerd-shim
    ↓
runc
    ↓
Linux Kernel
    ↓
Container Main Process
```

## 4.6.1 Docker CLI

`docker` 是客户端：

```bash
docker ps
docker run nginx
docker stop my-container
```

它不会自己实现 Namespace、cgroup、OverlayFS。

典型：

```text
docker CLI
↓
Docker Engine API
↓
dockerd
```

因此：

> 安装 Docker CLI ≠ 本机正在运行 Docker Engine。

CLI 甚至可以连接远程 Docker Engine。

---

## 4.6.2 dockerd

`dockerd` 是 Docker Engine 的核心 daemon。

主要负责：

```text
Container objects
Image management
Network
Volume
Build integration
Docker API
High-level lifecycle
```

例如：

```bash
docker run \
  -d \
  --name my-nginx \
  nginx
```

Docker Engine 需要决定：

```text
Image 是否存在？
Container 名称是否冲突？
要挂什么 Volume？
使用什么 Network？
CPU / Memory Limit 是多少？
要执行什么命令？
```

但它不会自己重新实现所有底层 Linux Runtime 细节。

---

## 4.6.3 containerd

containerd 是更底层的 Container Runtime Daemon。

主要职责：

```text
Image Content
Image Unpack
Snapshot
Container Metadata
Task Lifecycle
Runtime Integration
Events
```

### Content Store

保存：

```text
Manifest
Config
Layer Blob
Digest-addressed content
```

### Snapshotter

负责：

```text
Image layers
↓
unpack
↓
filesystem snapshot
↓
container writable snapshot
↓
RootFS
```

例如：

```text
OverlayFS Snapshotter
```

---

## 4.6.4 runc

`runc` 是低层 OCI Runtime。

它负责：

> 按照 OCI Runtime Configuration，调用 Linux Kernel 能力创建真正的 Linux Container Process。

你前面手工做过：

```text
unshare
mount
chroot
cgroup
namespace
```

runc 做的是更完整、规范和工程化的版本。

逻辑：

```text
OCI runtime config
↓
runc
↓
namespace / cgroup / mount / capabilities / seccomp
↓
Linux Kernel
↓
Container Process
```

runc 通常不是长期驻留 daemon。

---

## 4.6.5 containerd-shim

问题：

```text
runc 创建完容器就退出
```

那么谁负责：

```text
stdout / stderr
exit status
task lifecycle
containerd 重启后的任务管理
```

答案：

```text
containerd-shim
```

典型：

```text
containerd
↓
containerd-shim-runc-v2
↓
runc
↓
Container Process
```

大致分工：

```text
containerd
→ 高层任务管理

shim
→ 长生命周期任务监护与适配

runc
→ 短生命周期创建/启动低层 runtime 操作
```

管理关系不等于 Linux PPID 树必须严格一模一样。

---

## 4.6.6 OCI

OCI：

**Open Container Initiative**

核心标准：

```text
OCI Image Spec
OCI Runtime Spec
OCI Distribution Spec
```

记忆：

```text
Distribution
→ 怎么传

Image
→ 怎么存

Runtime
→ 怎么跑
```

---

## 4.6.7 OCI Image Spec

Image 高层结构：

```text
Image
├─ Manifest
├─ Config
└─ Layers
```

Config 中可能包含：

```text
Entrypoint
Cmd
Env
WorkingDir
User
Architecture
RootFS Diff IDs
History
```

Layer 则表示 Filesystem Diff。

---

## 4.6.8 OCI Distribution Spec

解决：

```text
Registry
↓
Pull / Push
↓
Manifest / Config / Layer Blob
```

它不负责：

```text
如何创建 PID Namespace
如何配置 cgroup
如何执行 nginx
```

---

## 4.6.9 OCI Runtime Spec

解决：

```text
RootFS
+
Runtime Configuration
↓
Container Process
```

OCI Runtime Bundle 常见概念：

```text
bundle/
├─ config.json
└─ rootfs/
```

其中：

```text
rootfs/
→ Container RootFS

config.json
→ 这一次 Container 怎么运行
```

可能描述：

```text
Process args
Environment
cwd
Mounts
Namespaces
Capabilities
Resources
```

---

## 4.6.10 Image Config 与 Runtime config.json 不同

### Image Config

描述 Image 默认行为：

```text
CMD
ENTRYPOINT
ENV
WorkingDir
User
```

### OCI Runtime Config

描述一次具体运行：

```text
实际 command
实际 mounts
实际 namespace
实际 cgroup
实际 rootfs
```

可以理解：

```text
Image Config
+
docker run parameters
+
runtime defaults
+
host environment
↓
Runtime Configuration
```

---

## 4.6.11 Image 不能直接交给 runc

Registry 里是：

```text
Manifest
Config
Compressed Layer Blobs
```

runc 需要：

```text
RootFS
+
OCI Runtime Bundle
```

因此：

```text
OCI Image
↓
Pull
↓
Content Store
↓
Unpack
↓
Snapshot
↓
RootFS
↓
Runtime Config
↓
runc
```

---

## 4.6.12 Content Store vs Snapshotter

### Content Store

回答：

> Image 原始内容在哪里？

```text
compressed layer blob
manifest
config
```

### Snapshotter

回答：

> 怎么把这些内容变成 Container 可以使用的 Filesystem？

```text
unpacked layer
snapshot
active writable snapshot
mount
```

总链：

```text
Registry
↓
Content Store
↓
Unpack
↓
Snapshotter
↓
RootFS
```

---

## 4.6.13 Container 与 Task

containerd 中可以粗略区分：

```text
Image
→ 镜像元数据/内容引用

Container
→ Container Metadata Object

Task
→ 真正运行的 Runtime Process
```

因此可以：

```text
Container object exists
Task not running
```

---

## 4.6.14 Docker create / start / run

粗略：

```text
docker run
≈
docker create
+
docker start
```

`create`：

```text
Container object
Writable layer
Config
准备完成
```

但 Main Process 还没跑。

`start`：

```text
真正启动 Container Main Process
```

---

## 4.6.15 Kubernetes 为什么不一定需要 Docker Engine

Kubernetes Node 典型：

```text
Kubelet
↓
CRI
↓
containerd / CRI-O
↓
shim
↓
runc
↓
Linux Kernel
```

CRI：

**Container Runtime Interface**

解决：

```text
Kubelet
↓
Container Runtime
```

之间如何通信。

---

## 4.6.16 CRI ≠ OCI

```text
CRI
→ Kubernetes → runtime 的高层接口

OCI Runtime
→ 低层 Container execution 标准
```

逻辑：

```text
Kubelet
↓ CRI
containerd
↓
shim
↓
runc
↓ OCI runtime model
Linux Container
```

---

## 4.6.17 dockershim

历史：

```text
Kubelet
↓
dockershim
↓
Docker Engine
↓
containerd
↓
runc
```

现代常见：

```text
Kubelet
↓
CRI
↓
containerd
↓
runc
```

---

## 4.6.18 Kubernetes 不用 Docker Engine ≠ 不能跑 Docker Image

必须区分：

```text
Docker Engine
```

和：

```text
Docker-built image
```

例如：

```text
developer machine
↓
docker build
↓
registry
↓
Kubernetes node
↓
containerd pull
↓
runc run
```

完全正常。

---

## 4.6.19 containerd Namespace

containerd 自己也有：

```text
namespace
```

例如：

```text
moby
k8s.io
default
```

但它不是 Linux Namespace。

对比：

```text
Linux Namespace
→ Kernel 隔离机制

containerd Namespace
→ containerd 管理对象的逻辑作用域
```

---

## 4.6.20 docker / ctr / crictl / nerdctl

```text
docker
→ Docker Engine

ctr
→ containerd 原生调试 CLI

crictl
→ Kubernetes CRI

nerdctl
→ Docker 风格 containerd CLI
```

因此：

```bash
docker ps
```

和：

```bash
crictl ps
```

不一定看到同一批 Container。

---

## 4.6.21 WSL + Docker Desktop

典型心智模型：

```text
Windows
│
├─ Ubuntu WSL
│   ├─ bash
│   ├─ python
│   └─ docker CLI
│
└─ Docker Desktop Linux Backend
    ├─ dockerd
    ├─ containerd
    ├─ shim
    ├─ runc
    └─ containers
```

因此在 Ubuntu WSL：

```bash
ps -ef | grep containerd
```

看不到 Docker Desktop 的 containerd：

> 完全可能。

同理：

```bash
ip link
```

看不到 Docker bridge/veth：

> 也完全可能。

---

## 4.6.22 实验：Docker Client / Server 分离

只读：

```bash
command -v docker
docker version
docker context show
docker context inspect "$(docker context show)"
docker info --format \
  'Server={{.Name}} Storage={{.Driver}} Runtime={{.DefaultRuntime}}'
```

理解：

```text
Client
→ 当前 Shell 中的 docker

Server
→ CLI 连接的 Docker Engine
```

### 回退

只读，无需清理。

---

## 4.6.23 实验：Create / Start / Writable Layer

```bash
IMG="busybox:1.36"
LAB="ai-infra-46-$$"

if docker image inspect "$IMG" >/dev/null 2>&1; then
    HAD_IMG=1
else
    HAD_IMG=0
fi
```

创建但不启动：

```bash
docker create \
  --name "$LAB" \
  --network none \
  --memory 64m \
  --pids-limit 32 \
  "$IMG" \
  sleep 600
```

查看：

```bash
docker inspect \
  --format \
  'state={{.State.Status}} pid={{.State.Pid}}' \
  "$LAB"
```

启动：

```bash
docker start "$LAB"
```

Container 内：

```bash
docker exec "$LAB" \
  sh -c '
    echo "PID 1:"
    cat /proc/1/comm

    echo "Kernel:"
    uname -r

    echo "Cgroup:"
    cat /proc/1/cgroup
  '
```

写入 Writable Layer：

```bash
docker exec "$LAB" \
  sh -c \
  'echo hello >/tmp/ai-infra-marker'
```

停止并重启：

```bash
docker stop -t 3 "$LAB"
docker start "$LAB"

docker exec "$LAB" \
  cat /tmp/ai-infra-marker
```

结论：

```text
stop/start same container
→ writable layer remains

rm + recreate
→ new writable layer
```

### 回退

```bash
docker rm -f "$LAB"

if [ "$HAD_IMG" -eq 0 ]; then
    docker image rm "$IMG" || true
fi

unset IMG LAB HAD_IMG
```

不要使用：

```bash
docker container prune
docker system prune
```

---

## 4.6.24 Docker Socket

常见：

```text
/var/run/docker.sock
```

它是 Unix Domain Socket。

逻辑：

```text
docker CLI
↓
Unix Socket
↓
dockerd
```

Docker Socket 权限非常敏感。

传统 Rootful Docker 中：

> 能控制 Docker Engine，通常接近 Host Root-level Control。

---

## 4.6.25 Container Runtime 分层总结

```text
Docker CLI
↓
dockerd
↓
containerd
↓
containerd-shim
↓
runc
↓
Linux Kernel
↓
Container Process
```

记忆：

```text
Docker Engine
→ 高层 Container Platform

containerd
→ image / snapshot / task lifecycle

shim
→ 长期任务监护/适配

runc
→ low-level OCI runtime
```

---

# 4.7 Container Network：NetNS / veth / bridge

核心目标：

> 一个只有 Loopback 的 Network Namespace，怎样获得 eth0、IP、Gateway，并和其他 Container / Host 通信？

最终模型：

```text
Container Process
↓
Container NetNS
↓
eth0
↓
veth
↓
Linux Bridge
↓
Host Network Stack
↓
Routing / NAT
↓
Outer Network
```

---

## 4.7.1 Network Namespace

NetNS 隔离：

```text
Network Interfaces
IP Addresses
Routes
Neighbor Table
Sockets
部分 Netfilter state
```

新 NetNS：

```bash
sudo unshare --net bash
```

里面通常只看到：

```text
lo
```

因此：

> Network Namespace 只提供独立 Network Stack，不自动提供外部 Connectivity。

---

## 4.7.2 veth

veth：

**Virtual Ethernet Pair**

特点：

```text
总是成对
像一根虚拟网线的两个端口
```

例如：

```text
vethA ←→ vethB
```

两个 Endpoint 可以放进不同 NetNS。

---

## 4.7.3 Container eth0

例如：

```text
Host NetNS
veth-host
    │
    │ virtual ethernet pair
    │
Container NetNS
eth0
```

Container 里的：

```text
eth0
```

很多情况下就是被移动并重命名后的 veth Endpoint。

---

## 4.7.4 veth 是 Layer 2

veth 本身负责：

```text
Ethernet Frame
```

不负责：

```text
IPAM
Gateway
Route
NAT
```

---

## 4.7.5 实验：Host ↔ NetNS

```bash
sudo ip netns add ai47ns
```

创建 veth：

```bash
sudo ip link add \
  ai47-host \
  type veth \
  peer name ai47-ns
```

移动一端：

```bash
sudo ip link set \
  ai47-ns \
  netns ai47ns
```

Host：

```bash
sudo ip addr add \
  10.247.1.1/24 \
  dev ai47-host

sudo ip link set \
  ai47-host up
```

NetNS：

```bash
sudo ip netns exec ai47ns \
  ip addr add \
  10.247.1.2/24 \
  dev ai47-ns

sudo ip netns exec ai47ns \
  ip link set ai47-ns up

sudo ip netns exec ai47ns \
  ip link set lo up
```

测试：

```bash
ping -c 2 10.247.1.2

sudo ip netns exec ai47ns \
  ping -c 2 10.247.1.1
```

同网段不需要 Default Gateway。

Neighbor：

```bash
sudo ip netns exec ai47ns \
  ip neigh

ip neigh show dev ai47-host
```

### 回退

```bash
sudo ip netns del ai47ns

if ip link show ai47-host >/dev/null 2>&1; then
    sudo ip link del ai47-host
fi
```

验证：

```bash
ip netns list | grep ai47ns || echo "netns clean"
ip link show ai47-host 2>/dev/null || echo "veth clean"
ip route
```

---

## 4.7.6 Linux Bridge

Linux Bridge：

> Linux Kernel 内的软件 Layer-2 Switch。

```text
Container A
    │
   veth
    │
    ├──── Linux Bridge
    │
   veth
    │
Container B
```

Bridge：

```text
Layer 2
MAC
Ethernet
```

Router：

```text
Layer 3
IP
Routing Table
```

---

## 4.7.7 Bridge Interface 自己可以有 IP

例如：

```text
bridge: ai47br0
IP: 10.247.10.1/24
```

它同时：

```text
L2
→ software switch

L3
→ Host 在该 subnet 上的 IP interface
```

因此：

```text
10.247.10.1
```

可以成为 Container Gateway。

---

## 4.7.8 实验：两个 NetNS + Bridge

```bash
sudo ip netns add ai47n1
sudo ip netns add ai47n2
```

Bridge：

```bash
sudo ip link add \
  ai47br0 \
  type bridge

sudo ip link set ai47br0 up

sudo ip addr add \
  10.247.10.1/24 \
  dev ai47br0
```

第一对：

```bash
sudo ip link add \
  ai47-v1h \
  type veth \
  peer name ai47-v1

sudo ip link set ai47-v1h master ai47br0
sudo ip link set ai47-v1h up
sudo ip link set ai47-v1 netns ai47n1

sudo ip netns exec ai47n1 \
  ip link set lo up

sudo ip netns exec ai47n1 \
  ip link set ai47-v1 up

sudo ip netns exec ai47n1 \
  ip addr add \
  10.247.10.11/24 \
  dev ai47-v1
```

第二对：

```bash
sudo ip link add \
  ai47-v2h \
  type veth \
  peer name ai47-v2

sudo ip link set ai47-v2h master ai47br0
sudo ip link set ai47-v2h up
sudo ip link set ai47-v2 netns ai47n2

sudo ip netns exec ai47n2 \
  ip link set lo up

sudo ip netns exec ai47n2 \
  ip link set ai47-v2 up

sudo ip netns exec ai47n2 \
  ip addr add \
  10.247.10.12/24 \
  dev ai47-v2
```

通信：

```bash
sudo ip netns exec ai47n1 \
  ping -c 2 10.247.10.12
```

---

## 4.7.9 FDB / Broadcast

FDB：

**Forwarding Database**

```text
MAC address
→ Bridge port
```

查看：

```bash
bridge fdb show br ai47br0
```

ARP Broadcast：

```text
Who has 10.247.10.12?
```

Bridge 会 Flood。

目标回复后，Bridge 学习 Source MAC，建立 FDB。

---

## 4.7.10 Default Gateway

```bash
sudo ip netns exec ai47n1 \
  ip route add \
  default via 10.247.10.1

sudo ip netns exec ai47n2 \
  ip route add \
  default via 10.247.10.1
```

但：

> 有 Default Route ≠ 一定能访问 Internet。

还需要：

```text
IP Forwarding
Routing
通常 NAT
```

---

## 4.7.11 Routing vs Bridge

```text
Route Lookup
↓
决定 Interface / Gateway

Neighbor Lookup
↓
得到下一跳 MAC

Ethernet Frame
↓
Interface
↓
Bridge FDB
↓
Bridge Port
```

因此：

```text
Routing
→ L3

Bridge
→ L2
```

---

## 4.7.12 Docker Bridge Network

```text
Container NetNS
│
│ eth0
│
veth
│
Host-side veth
│
Docker Bridge
│
Host Network Stack
```

Docker 还会增加：

```text
IPAM
DNS
Routing
NAT
Firewall
```

---

## 4.7.13 Docker Desktop / WSL

你的环境可能：

```text
Ubuntu WSL
172.26.x.x

Docker container
172.22.0.2

Docker gateway
172.22.0.1
```

重要：

```text
172.22.0.1
```

不要求等于 WSL eth0，更不等于家庭 Router。

它们可能属于不同虚拟 Network / Namespace 层次。

---

## 4.7.14 localhost

Container A：

```text
127.0.0.1
```

是 A 自己。

Container B：

```text
127.0.0.1
```

是 B 自己。

若不共享 NetNS：

```text
A localhost ≠ B localhost
```

---

## 4.7.15 Kubernetes Pod localhost

Pod 内多个 Container 通常共享 Network Namespace。

因此：

```text
A localhost:8080
```

可以被 B 通过：

```text
127.0.0.1:8080
```

访问。

---

## 4.7.16 `--network none` / `--network host`

```text
--network none
→ isolated NetNS，不接普通 Docker network

--network host
→ 使用 Host Network Stack
```

---

## 4.7.17 IPAM / CNI

IPAM：

**IP Address Management**

负责 Subnet 和 IP 分配。

CNI：

**Container Network Interface**

Kubernetes 网络插件规范。

---

## 4.7.18 回退

```bash
sudo ip netns del ai47n1
sudo ip netns del ai47n2

for dev in ai47-v1h ai47-v2h; do
    if ip link show "$dev" >/dev/null 2>&1; then
        sudo ip link del "$dev"
    fi
done

sudo ip link del ai47br0 2>/dev/null || true
```

验证：

```bash
ip netns list | grep -E 'ai47n1|ai47n2' || echo "netns clean"
ip link show ai47br0 2>/dev/null || echo "bridge clean"
ip link | grep 'ai47-v' || echo "veth clean"
ip route
```

---

# 4.8 Docker Port Mapping / Routing / NAT

核心问题：

```text
Container 怎么访问 Internet？

Host:8080 怎么进入 Container:80？
```

关键：

```text
Routing
IP Forwarding
SNAT
MASQUERADE
DNAT
PAT
Conntrack
Netfilter
```

---

## 4.8.1 Routing ≠ NAT

Routing：

> 决定 Packet 下一步去哪里。

NAT：

> 修改 Packet 中的 IP / Port。

两者不是一回事。

---

## 4.8.2 Linux Router

只要：

```text
Interface A
Interface B
+
IP forwarding
```

Linux 就可以：

```text
Packet enters A
↓
Route Lookup
↓
Forward
↓
Interface B
```

---

## 4.8.3 `net.ipv4.ip_forward`

只读观察主 WSL：

```bash
sysctl \
  net.ipv4.ip_forward
```

不要随便修改。

实验在专用 Router NetNS 内改。

---

## 4.8.4 实验拓扑

```text
ai48c
10.247.20.2/24
        │
        ▼
10.247.20.1
ai48r
Router
198.18.0.1
        │
        ▼
198.18.0.2
ai48w
External Host
```

---

## 4.8.5 创建 NetNS / veth

```bash
sudo ip netns add ai48c
sudo ip netns add ai48r
sudo ip netns add ai48w
```

Container ↔ Router：

```bash
sudo ip link add \
  ai48-c \
  type veth \
  peer name ai48-rc

sudo ip link set ai48-c netns ai48c
sudo ip link set ai48-rc netns ai48r
```

Router ↔ External：

```bash
sudo ip link add \
  ai48-rw \
  type veth \
  peer name ai48-w

sudo ip link set ai48-rw netns ai48r
sudo ip link set ai48-w netns ai48w
```

---

## 4.8.6 Container 配置

```bash
sudo ip netns exec ai48c \
  ip link set lo up

sudo ip netns exec ai48c \
  ip link set ai48-c up

sudo ip netns exec ai48c \
  ip addr add \
  10.247.20.2/24 \
  dev ai48-c

sudo ip netns exec ai48c \
  ip route add \
  default via 10.247.20.1
```

---

## 4.8.7 Router 配置

```bash
sudo ip netns exec ai48r \
  ip link set lo up

sudo ip netns exec ai48r \
  ip addr add \
  10.247.20.1/24 \
  dev ai48-rc

sudo ip netns exec ai48r \
  ip link set ai48-rc up

sudo ip netns exec ai48r \
  ip addr add \
  198.18.0.1/24 \
  dev ai48-rw

sudo ip netns exec ai48r \
  ip link set ai48-rw up
```

External：

```bash
sudo ip netns exec ai48w \
  ip link set lo up

sudo ip netns exec ai48w \
  ip link set ai48-w up

sudo ip netns exec ai48w \
  ip addr add \
  198.18.0.2/24 \
  dev ai48-w
```

---

## 4.8.8 Forwarding

```bash
sudo ip netns exec ai48r \
  sysctl -w \
  net.ipv4.ip_forward=1
```

只影响实验 Router Namespace。

---

## 4.8.9 Pure Routing

给 External Return Route：

```bash
sudo ip netns exec ai48w \
  ip route add \
  10.247.20.0/24 \
  via 198.18.0.1
```

测试：

```bash
sudo ip netns exec ai48c \
  ping -c 2 \
  198.18.0.2
```

证明：

> Routing 本身不需要 NAT。

删除：

```bash
sudo ip netns exec ai48w \
  ip route del \
  10.247.20.0/24 \
  via 198.18.0.1
```

---

## 4.8.10 SNAT / MASQUERADE

Container：

```text
src 10.247.20.2
dst 198.18.0.2
```

SNAT 后：

```text
src 198.18.0.1
dst 198.18.0.2
```

MASQUERADE：

> 自动使用出口 Interface 当前 IP。

---

## 4.8.11 nftables NAT 实验

```bash
command -v nft
```

如果没有，跳过实际规则。

创建：

```bash
sudo ip netns exec ai48r \
  nft add table ip ai48nat

sudo ip netns exec ai48r \
  nft \
  'add chain ip ai48nat postrouting {
      type nat hook postrouting priority srcnat;
      policy accept;
  }'

sudo ip netns exec ai48r \
  nft add rule \
  ip ai48nat postrouting \
  ip saddr 10.247.20.0/24 \
  oifname '"ai48-rw"' \
  masquerade
```

测试：

```bash
sudo ip netns exec ai48c \
  ping -c 2 \
  198.18.0.2
```

---

## 4.8.12 Conntrack / 5-tuple / PAT

5-tuple：

```text
Source IP
Source Port
Destination IP
Destination Port
Protocol
```

Conntrack：

> 维护 Flow 状态和 NAT Mapping。

PAT：

> 利用 Port Translation，让多个内部 Flow 共用 External IP。

---

## 4.8.13 DNAT / PREROUTING

外部：

```text
198.18.0.1:18080
```

映射：

```text
10.247.20.2:8080
```

通常：

```text
PREROUTING
↓
DNAT
↓
Route Lookup
↓
Container
```

---

## 4.8.14 手工 Port Mapping

启动 Container Namespace Server：

```bash
sudo ip netns exec \
  ai48c \
  python3 -u -c '
import socket

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("10.247.20.2", 8080))
s.listen(1)

print("listening", flush=True)

conn, addr = s.accept()
print("peer:", addr, flush=True)

conn.recv(4096)

conn.sendall(
    b"HTTP/1.1 200 OK\r\n"
    b"Content-Length: 18\r\n"
    b"Connection: close\r\n"
    b"\r\n"
    b"hello from ai48c\n"
)

conn.close()
s.close()
' > /tmp/ai48-server.log 2>&1 &
```

创建 DNAT：

```bash
sudo ip netns exec ai48r \
  nft \
  'add chain ip ai48nat prerouting {
      type nat hook prerouting priority dstnat;
      policy accept;
  }'

sudo ip netns exec ai48r \
  nft add rule \
  ip ai48nat prerouting \
  ip daddr 198.18.0.1 \
  tcp dport 18080 \
  dnat to 10.247.20.2:8080
```

External 访问：

```bash
sudo ip netns exec \
  ai48w \
  python3 -c '
import socket

s = socket.create_connection(
    ("198.18.0.1", 18080),
    timeout=3
)

s.sendall(
    b"GET / HTTP/1.1\r\n"
    b"Host: demo\r\n"
    b"Connection: close\r\n"
    b"\r\n"
)

data = b""

while True:
    chunk = s.recv(4096)
    if not chunk:
        break
    data += chunk

print(data.decode(errors="replace"))
s.close()
'
```

---

## 4.8.15 `docker -p`

```bash
docker run \
  -p 8080:80 \
  nginx
```

不是：

```text
把 Container 的 80 改成 8080
```

而是：

```text
Host:8080
↓
Published endpoint
↓
DNAT/forwarding
↓
Container:80
```

---

## 4.8.16 EXPOSE ≠ Publish

```dockerfile
EXPOSE 80
```

只是 Image Metadata。

真正 Host Port Publish：

```bash
docker run \
  -p 8080:80 \
  image
```

---

## 4.8.17 Host Bind Address

```bash
-p 8080:80
```

通常对 Host 多个地址暴露。

更严格：

```bash
-p 127.0.0.1:8080:80
```

只绑定 Loopback。

---

## 4.8.18 NAT ≠ Firewall

NAT：

```text
translate
```

Firewall：

```text
allow/drop
```

DNAT 成功后：

```text
FORWARD
```

仍可能 Drop。

---

## 4.8.19 Netfilter Hooks

```text
Packet arrives
↓
PREROUTING
↓
Route Lookup
├─ INPUT
└─ FORWARD
       ↓
  POSTROUTING
       ↓
      Out
```

Local traffic：

```text
Process
↓
OUTPUT
↓
POSTROUTING
```

---

## 4.8.20 Docker Desktop 多层 NAT

```text
Container
172.22.0.2
↓
Docker gateway
172.22.0.1
↓
Docker backend
↓
WSL/virtualization networking
↓
Windows networking
↓
physical NIC
↓
router
↓
Internet
```

可能经历多层 Routing/NAT。

---

## 4.8.21 网络排障

Container 同网通但 Internet 不通：

```text
default route
forwarding
FORWARD firewall
SNAT
outer route
DNS
```

ContainerIP:80 通但 Host:8080 不通：

```text
publish config
DNAT
host firewall
bind address
```

Host:8080 通但其他机器不通：

```text
127.0.0.1 binding?
host firewall?
LAN route?
outer firewall?
```

---

## 4.8.22 回退

```bash
sudo ip netns exec \
  ai48r \
  nft delete table \
  ip ai48nat \
  2>/dev/null \
  || true

sudo ip netns del ai48c 2>/dev/null || true
sudo ip netns del ai48r 2>/dev/null || true
sudo ip netns del ai48w 2>/dev/null || true

rm -f /tmp/ai48-server.log
```

验证：

```bash
ip netns list | grep ai48 || echo "clean"
ip link | grep ai48 || echo "clean"
ip route
sysctl net.ipv4.ip_forward
```

绝对不要：

```bash
sudo nft flush ruleset
sudo iptables -F
```

---

# 4.9 Volume / Bind Mount / Container Storage

核心：

> Container 的数据究竟应该放哪？

四类：

```text
Writable Layer
Bind Mount
Named Volume
tmpfs
```

---

## 4.9.1 Storage 对比

| 类型 | Container 删除后 | 典型用途 |
|---|---|---|
| Writable Layer | 消失 | 临时 runtime file |
| Bind Mount | 保留 | 源码、配置、模型 |
| Named Volume | 保留 | DB、持久数据 |
| tmpfs | 消失 | 临时/敏感数据 |

---

## 4.9.2 Writable Layer

```text
Image lower
+
Container upper
↓
OverlayFS
```

没有额外 Mount 的路径：

```text
/app
/tmp
/var/log
```

通常写进 Writable Layer。

```text
stop/start
→ 数据在

rm/recreate
→ 数据没
```

---

## 4.9.3 Bind Mount

```text
Host path
↕
Container path
```

不是 Copy。

Container 修改：

```text
Host 同一文件立即变化
```

---

## 4.9.4 Bind Mount 实验

```bash
BIND_DIR=$(
  mktemp -d \
    /tmp/ai-infra-bind-lab.XXXXXX
)

echo "hello from host" \
  > "$BIND_DIR/host.txt"
```

```bash
docker run \
  --rm \
  --mount \
  type=bind,src="$BIND_DIR",dst=/data \
  busybox:1.36 \
  sh -c '
    cat /data/host.txt
    echo "hello from container" \
      > /data/container.txt
  '
```

Host：

```bash
cat "$BIND_DIR/container.txt"
```

---

## 4.9.5 Read-only Mount

```bash
docker run \
  --mount \
  type=bind,src="$BIND_DIR",dst=/data,readonly \
  busybox:1.36 \
  sh -c '
    cat /data/host.txt
    echo test >/data/should-fail
  '
```

适合：

```text
models
configs
certificates
```

---

## 4.9.6 Named Volume

```bash
VOL="ai-infra-49-$$"

docker volume create "$VOL"
```

写：

```bash
docker run \
  --rm \
  --mount \
  type=volume,src="$VOL",dst=/data \
  busybox:1.36 \
  sh -c '
    echo persistent \
      > /data/message.txt
  '
```

新 Container 读：

```bash
docker run \
  --rm \
  --mount \
  type=volume,src="$VOL",dst=/data \
  busybox:1.36 \
  cat /data/message.txt
```

证明：

```text
Container lifecycle
≠
Volume lifecycle
```

---

## 4.9.7 Volume Initialization

新的空 Volume 挂到 Image 已有文件的目录时：

Docker 某些场景会：

```text
populate volume
```

这是 Docker Volume 初始化行为。

不是 Linux Bind Mount 固有行为。

---

## 4.9.8 Anonymous Volume

例如：

```bash
docker run \
  -v /data \
  image
```

没有名字。

长期重要数据：

```text
Named Volume 更容易管理
```

---

## 4.9.9 tmpfs

```bash
docker run \
  --rm \
  --mount \
  type=tmpfs,dst=/ram \
  busybox:1.36 \
  sh -c '
    echo hello >/ram/test.txt
    mount | grep /ram
  '
```

特点：

```text
Memory-backed
temporary
not image layer
not persistent
```

---

## 4.9.10 `/tmp` 不一定是 tmpfs

名字不代表 Filesystem 类型。

查看：

```bash
findmnt
mount
df -T
```

---

## 4.9.11 Container Mount Tree

```text
/
→ OverlayFS

/data
→ Volume

/models
→ Bind Mount

/run
→ tmpfs

/proc
→ procfs

/sys
→ sysfs
```

Container Filesystem：

> 多种 Mount 拼起来的一棵树。

---

## 4.9.12 UID/GID Permission

Bind Mount 仍然遵守 Linux 权限。

```text
Host UID/GID
Container Process UID/GID
mode
ACL
```

都可能影响。

不要第一反应：

```bash
chmod -R 777
```

---

## 4.9.13 Bind Mount Security

危险：

```text
/
 /etc
 /var/run/docker.sock
```

特别：

```text
docker.sock writable
```

通常意味着 Container 可控制 Docker Engine，风险极高。

---

## 4.9.14 Immutable RootFS

```bash
docker run \
  --read-only \
  ...
```

再给必要目录：

```text
/tmp
→ tmpfs

/data
→ volume
```

思想：

```text
program immutable
mutable data explicit
```

---

## 4.9.15 AI Infra：模型权重

不要机械：

```dockerfile
COPY 100GB-model /models
```

问题：

```text
Huge image
Slow pull
Huge registry
App/Model version coupled
Slow startup
```

更合理：

```text
Application Image
+
Model Storage
```

---

## 4.9.16 Model Storage

可来自：

```text
Host NVMe
Bind Mount
Volume
PVC
NFS
CephFS
Lustre
Object Storage cache
```

---

## 4.9.17 Model file vs RAM vs VRAM

```text
Model File
↓
Storage

Page Cache / Tensor
↓
RAM

CUDA Tensor
↓
VRAM
```

三个层次完全不同。

---

## 4.9.18 Checkpoint

Training Checkpoint：

> 不应该只存在 Writable Layer。

更合理：

```text
Persistent Volume
Network Storage
Object Storage
```

---

## 4.9.19 Cache vs Checkpoint

```text
Cache
→ 丢了能重建

Checkpoint
→ 丢了可能造成训练损失
```

因此可靠性要求不同。

---

## 4.9.20 Data Locality

```text
GPU Node
+
Local NVMe model cache
```

通常比：

```text
GPU Node
↓
remote model storage
```

启动快。

以后调度会涉及：

```text
Model Locality
```

---

## 4.9.21 PVC / CSI 伏笔

```text
CRI
→ Runtime

CNI
→ Network

CSI
→ Storage
```

Kubernetes：

```text
hostPath
PV
PVC
StorageClass
CSI
```

---

## 4.9.22 Persistent ≠ Durable ≠ Backup

```text
Persistent
→ Container 重建后还在

Durable
→ Node/Disk 故障后仍可恢复

Backup
→ 有独立恢复副本
```

不要把 Volume 自动理解成 Backup。

---

## 4.9.23 Storage 对照实验

```bash
HOSTDIR=$(
  mktemp -d \
    /tmp/ai-infra-storage-compare.XXXXXX
)

VOL="ai-infra-49-compare-$$"
C="ai49cmp-$$"

docker volume create "$VOL"
```

```bash
docker run \
  --name "$C" \
  --mount \
  type=bind,src="$HOSTDIR",dst=/bind \
  --mount \
  type=volume,src="$VOL",dst=/volume \
  --mount \
  type=tmpfs,dst=/ram \
  busybox:1.36 \
  sh -c '
    echo writable > /writable.txt
    echo bind-data > /bind/bind.txt
    echo volume-data > /volume/volume.txt
    echo ram-data > /ram/ram.txt
  '
```

结论：

```text
Writable Layer
→ container-bound

Bind
→ host-bound

Volume
→ storage object lifecycle

tmpfs
→ memory/mount lifecycle
```

---

## 4.9.24 回退

```bash
docker rm -f "$C" 2>/dev/null || true
docker volume rm "$VOL" 2>/dev/null || true
rm -rf "$HOSTDIR"

unset HOSTDIR VOL C
```

验证：

```bash
docker ps -a \
  --format '{{.Names}}' \
  | grep '^ai49' \
  || echo "container clean"

docker volume ls \
  --format '{{.Name}}' \
  | grep '^ai-infra-49' \
  || echo "volume clean"
```

禁止：

```bash
docker volume prune
docker system prune
```

---

# 4.10 Container PID 1 / Signal / Zombie

核心问题：

```text
为什么 Container Main Process 是 PID1？

为什么 docker stop 有时卡到 timeout？

Shell Form vs Exec Form 为什么影响 Signal？

Zombie / Orphan / tini 是什么？
```

---

## 4.10.1 PID 1

新的 PID Namespace 内：

```text
first process
→ PID1
```

同一个 Task：

```text
Host PID 38291
Container PID 1
```

因此：

> PID 是 Namespace-relative。

---

## 4.10.2 Host PID1 vs Container PID1

```text
Host PID1
→ systemd/init

Container PID1
→ nginx/python/java/go/shell/tini
```

不是同一进程。

---

## 4.10.3 PID1 核心职责

```text
Signal Handling
Child Reaping
Container lifecycle
```

通常：

```text
PID1 exits
↓
Container exits
```

---

## 4.10.4 Signal

常见：

```text
SIGTERM
→ graceful termination request

SIGKILL
→ force kill

SIGINT
→ interactive interrupt

SIGCHLD
→ child status changed
```

---

## 4.10.5 SIGTERM vs SIGKILL

SIGTERM：

```text
can handle
can cleanup
can ignore
```

SIGKILL：

```text
cannot catch
cannot ignore
no cleanup
```

---

## 4.10.6 docker stop

```text
docker stop
↓
Stop Signal
↓
usually SIGTERM
↓
grace period
↓
still alive
↓
SIGKILL
```

因此：

```text
docker stop
≠
kill -9
```

---

## 4.10.7 Graceful Shutdown

理想：

```text
SIGTERM
↓
stop accepting new work
↓
drain inflight requests
↓
flush/checkpoint
↓
close resources
↓
cleanup child
↓
exit
```

AI Training 尤其重要。

---

## 4.10.8 PID1 实验

```bash
IMG="busybox:1.36"

if docker image inspect "$IMG" >/dev/null 2>&1; then
    HAD_IMG=1
else
    HAD_IMG=0
fi

C1="ai-infra-410-pid1-$$"
```

```bash
docker run \
  -d \
  --name "$C1" \
  "$IMG" \
  sleep 600
```

Host-side：

```bash
docker inspect \
  --format \
  'status={{.State.Status}} host-pid={{.State.Pid}}' \
  "$C1"
```

Container：

```bash
docker exec "$C1" \
  sh -c '
    cat /proc/1/comm
    ps
  '
```

Container PID1：

```text
sleep
```

普通 App Container 不自动启动 systemd。

---

## 4.10.9 docker exec

```bash
docker exec my-container sh
```

是在现有：

```text
Namespace
cgroup
RootFS
```

里创建新 Process。

不是替换 PID1。

---

## 4.10.10 Shell Form vs Exec Form

Shell Form：

```dockerfile
CMD python app.py
```

类似：

```text
PID1
/bin/sh -c

PID2
python
```

Exec Form：

```dockerfile
CMD ["python", "app.py"]
```

类似：

```text
PID1
python
```

---

## 4.10.11 为什么推荐 Exec Form

Shell Form：

```text
Docker
↓
TERM
↓
Shell PID1
↓
?
↓
Application
```

Exec：

```text
Docker
↓
TERM
↓
Application PID1
```

Signal Path 更直接。

---

## 4.10.12 Shell Wrapper 实验

```bash
C2="ai-infra-410-shell-$$"

docker run \
  -d \
  --name "$C2" \
  "$IMG" \
  sh -c '
    sleep 600 &
    child=$!
    wait "$child"
  '
```

查看：

```bash
docker exec "$C2" ps
```

测试：

```bash
time docker stop \
  -t 2 \
  "$C2"
```

重点：

> Shell Wrapper 会增加 Signal Propagation 复杂度。

---

## 4.10.13 Entrypoint Script

错误：

```sh
#!/bin/sh

prepare_config
python app.py
```

更好：

```sh
#!/bin/sh
set -e

prepare_config
exec "$@"
```

Dockerfile：

```dockerfile
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "app.py"]
```

---

## 4.10.14 exec

```sh
exec python app.py
```

表示：

> Python 替换当前 Shell Process Image。

因此：

```text
PID1 shell
↓ exec
PID1 python
```

PID 不变。

---

## 4.10.15 STOPSIGNAL / docker kill

Dockerfile：

```dockerfile
STOPSIGNAL SIGTERM
```

`docker kill` 默认更接近强制 SIGKILL。

也可以：

```bash
docker kill \
  --signal SIGTERM \
  container
```

---

## 4.10.16 Python / Go Signal

Python：

```python
import signal

def shutdown(signum, frame):
    raise SystemExit(0)

signal.signal(
    signal.SIGTERM,
    shutdown,
)
```

Go：

```go
ctx, stop := signal.NotifyContext(
    context.Background(),
    syscall.SIGTERM,
    syscall.SIGINT,
)

defer stop()
```

Container：

```text
TERM
↓
app runtime
↓
graceful shutdown
```

---

## 4.10.17 Zombie

Zombie：

> Child 已经退出，但 Parent 还没 wait/waitpid 读取 Exit Status。

```text
Child
↓
exit
↓
Zombie
↓
Parent wait()
↓
Reaped
```

Zombie：

```text
不再执行代码
CPU ≈ 0
```

但保留少量 Kernel Process Metadata。

大量 Zombie 会消耗 PID / Task 资源。

---

## 4.10.18 Zombie ≠ Orphan

Zombie：

```text
Child dead
Parent alive
Parent no wait
```

Orphan：

```text
Parent dead
Child alive
```

---

## 4.10.19 Reparenting

Orphan：

```text
parent exits
↓
child still alive
↓
reparent
↓
subreaper / PID1
```

所以 PID1 需要具备 Child Reaping 能力。

---

## 4.10.20 Zombie 隔离实验

```bash
sudo unshare \
  --pid \
  --fork \
  --mount \
  --mount-proc \
  --propagation private \
  bash
```

里面：

```bash
echo $$
```

应为 1。

运行：

```bash
python3 - <<'PY' &
import os
import time

child = os.fork()

if child == 0:
    os._exit(42)

print(
    f"parent={os.getpid()} child={child}",
    flush=True,
)

time.sleep(60)
PY
```

查看：

```bash
ps \
  -o pid,ppid,stat,comm,args
```

看到：

```text
STAT Z
```

就是 Zombie。

### 回退

```bash
exit
```

整个临时 PID Namespace 销毁。

---

## 4.10.21 Orphan 实验

重新：

```bash
sudo unshare \
  --pid \
  --fork \
  --mount \
  --mount-proc \
  --propagation private \
  bash
```

执行：

```bash
python3 - <<'PY'
import os
import time

child = os.fork()

if child == 0:
    print(
        f"child pid={os.getpid()} ppid={os.getppid()}",
        flush=True,
    )
    time.sleep(30)
    print(
        f"child later ppid={os.getppid()}",
        flush=True,
    )
    os._exit(0)

print(
    f"parent exiting pid={os.getpid()} child={child}",
    flush=True,
)

os._exit(0)
PY
```

查看：

```bash
ps \
  -o pid,ppid,stat,comm,args
```

Child 可能被 reparent 给 PID1。

### 回退

```bash
exit
```

---

## 4.10.22 Subreaper

Process 可以：

```text
prctl(PR_SET_CHILD_SUBREAPER)
```

成为：

```text
Child Subreaper
```

用于更近一级接收 Orphan Descendant。

常用于：

```text
Service Manager
Container Init
Process Supervisor
```

---

## 4.10.23 Tiny Init

典型：

```text
tini
dumb-init
```

主要解决：

```text
Signal Forwarding
Child Reaping
```

不是完整 systemd。

---

## 4.10.24 Docker `--init`

```bash
docker run \
  --init \
  image
```

典型：

```text
PID1
tini/docker-init
│
└─ Application
```

---

## 4.10.25 `--init` 实验

```bash
C4="ai-infra-410-init-$$"

docker run \
  -d \
  --init \
  --name "$C4" \
  "$IMG" \
  sh -c '
    sleep 600 &
    wait
  '
```

查看：

```bash
docker exec "$C4" \
  sh -c '
    cat /proc/1/comm
    ps
  '
```

PID1 通常会类似：

```text
docker-init
```

---

## 4.10.26 Tiny Init 能做什么 / 不能做什么

能：

```text
forward signals
reap children
```

不能：

```text
save checkpoint
drain HTTP request
flush DB
```

Graceful Logic 必须 Application 自己实现。

---

## 4.10.27 Foreground Process

错误：

```sh
python app.py &
```

Shell PID1 退出：

```text
Container exits
```

所以 Container Service 通常：

```text
foreground
```

运行。

例如 nginx：

```text
daemon off
```

---

## 4.10.28 多进程 Container

Container 不限制只能一个 Process。

可以：

```text
PID1
├─ worker
├─ helper
└─ subprocess
```

工程惯例是：

> 一个 Container 通常一个主要生命周期责任。

---

## 4.10.29 AI Training Process Tree

```text
PID1
entrypoint
↓
torchrun
├─ rank0
├─ rank1
├─ rank2
└─ rank3
```

Signal 错误可能导致：

```text
TERM lost
worker orphan
shutdown timeout
```

AI Workload 很依赖正确的 Process Lifecycle。

---

## 4.10.30 Exit Code 137 / 143

常见 Unix 约定：

```text
128 + signal
```

SIGKILL 9：

```text
137
```

SIGTERM 15：

```text
143
```

137 可能来自：

```text
OOM
stop timeout
kill -9
```

不能仅凭 Exit Code 定根因。

查看：

```bash
docker inspect \
  --format \
  'OOMKilled={{.State.OOMKilled}} ExitCode={{.State.ExitCode}}' \
  container
```

---

## 4.10.31 Kubernetes Graceful Termination 伏笔

```text
Pod termination
↓
termination signal
↓
grace period
↓
still alive
↓
SIGKILL
```

还会涉及：

```text
preStop
terminationGracePeriodSeconds
request draining
```

本质仍建立在 Linux Signal / PID1 之上。

---

## 4.10.32 回退

检查：

```bash
docker ps -a \
  --format '{{.Names}}' \
  | grep '^ai-infra-410-' \
  || echo "clean"
```

逐个确认后：

```bash
docker rm -f <experiment-container>
```

如果实验前没有 Image：

```bash
if [ "${HAD_IMG:-1}" -eq 0 ]; then
    docker image rm "$IMG" \
      2>/dev/null \
      || true
fi
```

然后：

```bash
unset IMG HAD_IMG
```

禁止：

```text
docker container prune
pkill python
pkill sleep
pkill bash
```

---

# 4.6 ～ 4.10 总体心智模型

Runtime：

```text
User
↓
docker CLI
↓
dockerd
↓
containerd
↓
shim
↓
runc
↓
Linux Kernel
↓
Container Process
```

Filesystem：

```text
Image Layers
+
Writable Layer
+
Bind Mount
+
Volume
+
tmpfs
↓
Container Mount Tree
```

Network：

```text
Application
↓
Socket
↓
Container Route
↓
eth0
↓
veth
↓
Bridge
↓
Host Routing
↓
NAT
↓
Outer Network
```

Lifecycle：

```text
docker stop
↓
SIGTERM
↓
PID1
↓
graceful shutdown
↓
child cleanup
↓
exit
```

AI Infra：

```text
Application
→ Image

Model
→ Model Storage / Cache

Checkpoint
→ Durable Persistent Storage

Container Network
→ NetNS / veth / bridge / route / NAT

Container Runtime
→ containerd / shim / runc

Container Lifecycle
→ PID1 / signal / reaping
```

---

# 第 4 章进度目录

```text
第 0 章：AI Infra 心智模型
✅ 完成

第 1 章：Linux 与计算机系统基础
✅ 完成

第 2 章：计算机网络基础
✅ 完成

第 3 章：Python + Go
✅ 完成


第 4 章：Docker 与 Container Internals
🟨 进行中


✅ 4.1 Container 到底是什么

✅ 4.2 Linux Namespace 深入

✅ 4.3 cgroup：CPU / Memory / PID

✅ 4.4 Container RootFS / Mount / chroot / pivot_root

✅ 4.5 Docker Image / Layer / OverlayFS


✅ 4.6 Docker Engine / containerd / runc / OCI
    ├─ Docker CLI
    ├─ Docker Engine API
    ├─ dockerd
    ├─ containerd
    ├─ containerd-shim
    ├─ runc
    ├─ OCI Image Spec
    ├─ OCI Runtime Spec
    ├─ OCI Distribution Spec
    ├─ Runtime Bundle
    ├─ Content Store
    ├─ Snapshotter
    ├─ Image / Container / Task
    ├─ CRI
    ├─ Kubelet
    ├─ dockershim
    ├─ containerd Namespace
    ├─ Docker Context
    ├─ Docker Socket
    ├─ Docker Desktop / WSL Runtime
    └─ Rollback


✅ 4.7 Container Network：NetNS / veth / bridge
    ├─ Network Namespace
    ├─ veth Pair
    ├─ Linux Bridge
    ├─ FDB
    ├─ ARP / Neighbor
    ├─ Default Gateway
    ├─ Routing vs Bridge
    ├─ Docker Bridge
    ├─ Container eth0
    ├─ IPAM
    ├─ localhost
    ├─ --network none
    ├─ --network host
    ├─ Docker Desktop / WSL Network Layers
    ├─ CNI 伏笔
    └─ Rollback


✅ 4.8 Docker Port Mapping / Routing / NAT
    ├─ Routing vs NAT
    ├─ Linux Router
    ├─ IP Forwarding
    ├─ Forward / Return Path
    ├─ Pure Routing
    ├─ SNAT
    ├─ MASQUERADE
    ├─ PAT
    ├─ Conntrack
    ├─ 5-tuple
    ├─ DNAT
    ├─ PREROUTING
    ├─ POSTROUTING
    ├─ Netfilter
    ├─ Firewall vs NAT
    ├─ Port Publishing
    ├─ EXPOSE vs -p
    ├─ Host Bind Address
    ├─ Docker Desktop Port Forwarding
    ├─ Multi-layer NAT
    ├─ Network Troubleshooting
    └─ Rollback


✅ 4.9 Volume / Bind Mount / Container Storage
    ├─ Writable Layer
    ├─ Bind Mount
    ├─ Read-only Mount
    ├─ Named Volume
    ├─ Anonymous Volume
    ├─ tmpfs
    ├─ Storage Lifecycle
    ├─ Persistence
    ├─ Durability
    ├─ Backup
    ├─ UID / GID
    ├─ Bind Mount Security
    ├─ Immutable RootFS
    ├─ Model Weight Storage
    ├─ Model Cache
    ├─ Checkpoint
    ├─ Scratch Storage
    ├─ Data Locality
    ├─ PVC / CSI 伏笔
    └─ Rollback


✅ 4.10 Container PID 1 / Signal / Zombie
    ├─ PID 1
    ├─ Namespace PID
    ├─ SIGTERM
    ├─ SIGKILL
    ├─ SIGINT
    ├─ SIGCHLD
    ├─ docker stop
    ├─ Graceful Shutdown
    ├─ Shell Form vs Exec Form
    ├─ EntryPoint Script
    ├─ exec "$@"
    ├─ STOPSIGNAL
    ├─ docker kill
    ├─ Zombie
    ├─ Orphan
    ├─ wait / waitpid
    ├─ Reaping
    ├─ Reparenting
    ├─ Subreaper
    ├─ tini / dumb-init
    ├─ Docker --init
    ├─ Exit Code 137 / 143
    ├─ OOMKilled
    ├─ Go signal.NotifyContext
    ├─ AI Training Process Tree
    ├─ Kubernetes Graceful Termination 伏笔
    └─ Rollback


⬜ 4.11 Container Security 基础

⬜ 4.12 Dockerfile / Build Context / Build Cache

⬜ 4.13 Multi-stage Build

⬜ 4.14 Docker 基础排障

⬜ 4.15 Container 综合实验
```

---

# 实验安全与回退原则

本文件所有实验遵循：

```text
优先临时目录
优先独立 Namespace
优先专用 Container 名称
优先专用 Volume 名称
只删除自己创建的资源
```

不要使用宽泛清理：

```bash
docker system prune -a
docker container prune
docker volume prune
sudo nft flush ruleset
sudo iptables -F
pkill python
pkill sleep
pkill bash
```

因为它们可能破坏：

```text
已有 Container
已有 Volume
Docker 网络
VPN
WSL 网络
其他实验
开发服务
```

每一组实验都应：

```text
创建明确命名的资源
↓
完成验证
↓
只删除对应资源
↓
再次验证无残留
```

---

# 下一节

```text
4.11 Container Security 基础
```

将进入：

```text
Container Root vs Host Root
Linux Capabilities
--cap-drop / --cap-add
--privileged
seccomp
no-new-privileges
AppArmor
SELinux
Docker Socket Security
Read-only RootFS
Non-root Container
User Namespace
```

核心问题：

> Namespace 提供隔离，但为什么 Container 并不天然等于完整安全边界？
