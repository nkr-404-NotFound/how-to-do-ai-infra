# LLM / AI Infrastructure 学习课程
# 第 4 章：Docker 与 Container Internals（4.1～4.5 离线完整版）

> **覆盖范围**：4.1 Container 本质；4.2 Linux Namespace；4.3 cgroup v2；4.4 RootFS / chroot / pivot_root；4.5 Image / Layer / OverlayFS。  
> **实验环境**：Ubuntu WSL2（首选），具备可用的 Linux 工具；有 Docker Desktop 则可选做 Docker 对照实验。  
> **学习方式**：先定义术语，再建立模型，再做可复现实验；每个实验系列都有 **回退 / 清理 / 验证**。  
> **当前进度**：第 0～3 章已完成；第 4 章已学完 4.5；下一节 4.6 Docker Engine / containerd / runc / OCI。

---

## 阅读导航

- [实验安全与回退总规则](#实验安全与回退总规则)
- [4.1 Container 到底是什么](#41-container-到底是什么)
- [4.2 Linux Namespace 深入](#42-linux-namespace-深入)
- [4.3 cgroup：CPU / Memory / PIDs](#43-cgroupcpu--memory--pids)
- [4.4 Container RootFS / Mount / chroot / pivot_root](#44-container-rootfs--mount--chroot--pivot_root)
- [4.5 Docker Image / Layer / OverlayFS](#45-docker-image--layer--overlayfs)
- [综合复盘：从 Dockerfile 到 Linux Process](#综合复盘从-dockerfile-到-linux-process)
- [完整术语表](#完整术语表)
- [课程目录](#课程目录)

---

# 实验安全与回退总规则

这一规则是本课程 **所有 WSL 实验的固定约定**。

**实验顺序：**

```text
检查前提和初始状态
       ↓
记录使用的临时目录、进程或 Unit 名称
       ↓
进入隔离实验环境
       ↓
执行与观察
       ↓
退出实验 Process / 停止服务
       ↓
Unmount（如果挂载过）
       ↓
删除专用临时资源
       ↓
验证实验资源不再存在、宿主状态未变
```

1. 默认只使用 `/tmp/ai-infra-*` 下通过 `mktemp -d` 建立的**专用临时目录**；不覆盖已有目录。
2. Mount 实验尽量在 `unshare --mount --propagation private` 的隔离环境里做；在正常 WSL Shell 只做只读检查。
3. **不要为成功完成实验而关闭 WSL 安全限制**、更改 sysctl、修改 `/etc/wsl.conf` 或干预 systemd 的 cgroup 根树。
4. 实验中的 PID 用变量记录，用**准确 PID / 专用 systemd Unit / 专用 cgroup**清理。不要使用 `pkill python`、`pkill sleep` 等可能误伤原有进程的通配命令。
5. 以 `exit` 退出 Namespace Shell 前，先退出其中开启的后台任务；对 Mount 明确 `umount`。若某一步报错，**先清理，不继续叠加实验**。
6. `sudo` 只授予当前实验所需的最低权限。`rm -rf` 只用于本次 `mktemp` 创建且已确认的专用目录；不在 `ROOTFS` 等变量为空时执行删除。
7. 实验回退可使**本课程创建的资源**恢复到实验前状态，但不声称自动撤销原本已有的外部系统变化。原有的 Docker Image / 容器 / 服务一律保留。

### 快速环境预检（只读）

```bash
uname -a
cat /etc/os-release
printf 'Shell PID=%s\n' "$$"
stat -fc '%T' /sys/fs/cgroup
command -v unshare; command -v nsenter
command -v findmnt; command -v ip
```

某个工具缺失、出现 `Operation not permitted` / `Read-only file system` 时：先跳过相应动手实验，阅读原理即可；**不要求修改 WSL 设置**。

---

# 4.1 Container 到底是什么

## 4.1.1 首要结论：Container 仍然是 Linux Process

> **Container 不是缩小版的 VM，而是运行在某个 Linux Kernel 上、具有隔离视图和资源约束的一组 Linux Process。**

基本模型：

```text
Container ≈ Linux Process(es)
          + Namespaces
          + cgroups
          + RootFS / Mount View
          + Security Policy
          + Container Runtime 管理
```

运行普通程序：

```bash
python3 app.py
```

Linux 会建立一个进程，拥有 PID、虚拟内存、线程、FD 表、凭据以及调度状态。

运行：

```bash
docker run nginx
```

最后也会创建真正的 Linux Process；不是在一个“容器专属 Kernel”里再模拟 Process。

### Process vs Container vs Virtual Machine

```text
                     VM 方案
┌──────────────────────────────────┐
│ Hypervisor                       │
│   ├─ Guest A: Kernel + Userland  │
│   └─ Guest B: Kernel + Userland  │
└──────────────────────────────────┘

                 Linux Container 方案
┌──────────────────────────────────┐
│ Host Linux Kernel                │
│  ├─ Host Process                 │
│  ├─ Isolated Process Group A     │
│  └─ Isolated Process Group B     │
└──────────────────────────────────┘
```

VM 有自己的 Guest Kernel；普通 Linux Container 使用 **Host Linux Kernel**。因此 Container 启动一般更快、密度通常更高，但共享 Kernel 也是需要额外安全加固的原因。

## 4.1.2 为什么 Container 看起来“像自己的 Linux”？

程序在 Container 内常看到：

```bash
ps -ef       # 可能只看到当前容器的进程
ip addr      # 看见自己的 eth0 和 IP
hostname     # 看见容器 hostname
mount        # 看见自己的 mount tree
ls /         # 看见自己的 RootFS
```

这是因为内核给它分配了**局部系统视图（Namespace）**，并不是另起一个 Linux Kernel。

## 4.1.3 Linux Namespace：决定“你看见什么”

**Namespace**：Linux Kernel 提供的一类隔离机制，使不同 Process 可以处于不同的系统视图。

| Namespace | 主要隔离内容 | Container 里的直观表现 |
|---|---|---|
| PID | 进程 ID、进程可见性 | 容器内主进程可能是 PID 1 |
| Network | 网络接口、地址、路由、Socket 所在的网络栈等 | 独立 `eth0` / Route |
| Mount | Mount Tree / Mount Table | `/` 和 Host 的 `/` 不同 |
| UTS | hostname、NIS domain name | 容器自己的 hostname |
| IPC | System V IPC、部分 POSIX 消息队列 | 隔离共享内存、信号量等 |
| User | UID/GID、与身份相关的权限上下文 | 容器内 root 可映射为 Host 非 root |
| Cgroup | cgroup 文件系统的可见根 | 更局部的 cgroup 视图 |
| Time | 部分时钟视图 | 可隔离特定时钟偏移（了解即可） |

**注意：** Namespace 既不是 Docker 发明的，也不是默认绝对安全的隔离边界。

## 4.1.4 cgroup：决定“你可以使用多少”

**cgroup = Control Group**，管理一组 Linux Process/Task 的资源使用、统计与限制。

```text
Namespace：隔离可见性
cgroup：管理 CPU / Memory / PIDs / I/O 等资源
```

例子：

```bash
docker run --cpus=1 --memory=512m nginx
```

Docker Runtime 大致为容器进程配置 CPU / Memory Controller，真正执行资源控制的是 Kernel。

## 4.1.5 Image ≠ Container

- **Image**：创建 Container RootFS 和启动配置的模板；主要包含只读 Filesystem Layers + Metadata。
- **Container**：以 Image 为基础创建的运行实例，具有自身可写状态、Process 生命周期、隔离与资源约束。

类比：

```text
程序文件       → 运行中的 Process
Container Image → Container 实例
```

一个 Image 可以创建多个 Container。镜像里的“发行版”主要对应 **Userland / RootFS**，不是独立 Guest Kernel；详见 4.4。

## 4.1.6 `docker run` 背后做了什么

简化的因果链：

```text
docker run IMAGE
↓
解析 Image 与配置
↓
准备 Image Layers 对应的 RootFS
↓
创建/加入 Namespaces
↓
配置 cgroups、Capabilities、Seccomp 等
↓
准备网络、Mount、Volume
↓
执行容器主 Process
↓
Kernel 调度普通 Linux Threads
```

Docker 不是内核；它将 Process、Namespace、cgroup、Mount 和网络等内核能力包装成易用的工具。

## 4.1.7 Container 并不限定“只有一个 Process”

容器可以包含多个 Process；但通常存在一个承担容器生命周期的**主进程**：

```text
Container PID 1
├── worker
└── helper
```

主进程结束，容器通常停止。`docker exec` 不是新建容器，而是在已有容器的隔离与管理环境里再运行一个命令（新 Process）。

**PID 1** 还有信号默认处理、Child Reaping 等特殊语义；后面 4.10 深入。

## 4.1.8 Docker Desktop / WSL2 的特殊性

Container 必须依靠真正的 Linux Kernel 特性。Windows/macOS 的 Docker Desktop 通常在专用 Linux 环境/VM 里运行 Linux Container：

```text
Windows / macOS
    ↓
Docker Desktop 管理层
    ↓
Linux Kernel（WSL2 / VM 等）
    ↓
Docker Containers
```

**重要：** Ubuntu WSL Distribution 与 Docker Desktop 自己的 Linux 环境不一定是同一个 Root Network Namespace。你可能在 Ubuntu WSL 看到 `172.26.x.x`，而 Docker Container 看到 `172.22.x.x`、网关 `172.22.0.1`，并不意味着 Docker Bridge 必须出现在 Ubuntu WSL 的 `ip addr` 里。

## 4.1.9 Container 安全机制：先定义

| 机制 | 要回答的问题 |
|---|---|
| Namespace | 允许看见什么？ |
| cgroup | 允许消耗多少资源？ |
| Linux Capabilities | 允许使用哪些细分的特权能力？ |
| seccomp | 允许发起哪些系统调用？ |
| User Namespace | Container 内外的 UID/GID 如何映射？ |
| LSM（AppArmor/SELinux） | 还允许访问哪些对象或执行哪些操作？ |

单靠 Namespace + cgroup 不足以构成完整的安全边界。

## 4.1 WSL 实验：Container 是 Process

**前提：** Docker CLI 可以正常连接 Docker Engine；否则跳过。

先检查是否已有实验名字，避免覆盖：

```bash
docker ps -a --filter 'name=^/ai-infra-ch41-demo$'
```

只有确认没有同名容器时才执行：

```bash
docker run --name ai-infra-ch41-demo -d alpine:3.20 sleep 600
docker ps --filter 'name=^/ai-infra-ch41-demo$'
docker top ai-infra-ch41-demo
docker exec ai-infra-ch41-demo ps
```

最后一个 `ps` 可能需要对应镜像的工具集；Alpine 自带 BusyBox，通常可执行。观察 `sleep` 在容器内部的 PID（通常是 1）。

在**原生 Linux Docker Host** 上：

```bash
docker inspect -f '{{.State.Pid}}' ai-infra-ch41-demo
```

这个 Host-side PID 可能与容器内部 PID 1 不同。在 Docker Desktop 下，它属于 Engine 所在 Linux 环境，不一定能在你的 Ubuntu WSL `/proc` 中直接找到。

### 实验回退 / 清理

只针对本实验专用名字：

```bash
docker rm -f ai-infra-ch41-demo
```

如果 `alpine:3.20` 原本不存在且你希望完全清除**本实验新下载的镜像**，可在确认它没有被其他容器使用后 `docker image rm alpine:3.20`。如果它原本已经存在，则不要删除。

**回退验证：**

```bash
docker ps -a --filter 'name=^/ai-infra-ch41-demo$'
# 结果应为空
```

## 4.1 十句话

1. Container 不是轻量 VM，它本质仍是 Linux Process / Process Group。
2. Linux Container 使用承载它的 Host Linux Kernel。
3. Namespace 决定 Process 看到什么。
4. cgroup 决定一组 Process 能用多少资源。
5. PID Namespace 允许同一 Process 在内外看到不同 PID。
6. Mount Namespace 隔离的是 Mount Tree，不自动生成新 RootFS。
7. Image 是模板，Container 是运行实例。
8. `docker exec` 本质仍是启动新 Linux Process。
9. Windows/macOS Docker Desktop 的 Linux Container 通常运行在专用 Linux VM/环境内。
10. Docker 将多个 Kernel Primitive 组合并管理成 Container。

---

# 4.2 Linux Namespace 深入

> 本节目标：**不用 Docker，直接利用 Linux Kernel 建立一个简陋的“Container-like Shell”。**

## 4.2.1 三个关键工具

**`unshare`**：创建/脱离某些 Namespace，让后续 Process 不再与原 Process 共享该视图。

**`nsenter`**：参照目标 Process 的 Namespace，启动一个新 Process 进入指定 Namespace；它不是“接管”目标进程。

**`lsns`**：从系统 Process 的 Namespace 信息整理当前可观察到的 Namespace 列表。

辅助接口：

```text
/proc/<PID>/ns/{pid,mnt,net,uts,ipc,user,cgroup,...}
```

这些是 Kernel 暴露的 Namespace Handle：

```bash
readlink /proc/$$/ns/net
# 例如 net:[4026531840]
```

两个 Process 的 `net:[...]` 相同，通常说明它们共享同一个 Network Namespace。

### `$$` 是什么？

`$$` 是当前 Bash/Shell 的 PID。`/proc/$$/ns/*` 因此可以直接观察当前 Shell 的 Namespace。

## 4.2.2 Namespace 是 Kernel Object

Namespace 并不是一个写在 `/etc/namespaces` 里的文本配置，而是 Linux Kernel 维护、由 Process 及 Namespace FD 等对象引用的 Kernel Object。它们可以独立组合：

```text
Process A                         Process B
├─ PID NS ─────→ PID Namespace 1 ←── PID NS
├─ NET NS ─────→ Net Namespace 2     NET NS ──→ Net Namespace 3
├─ UTS NS ─────→ UTS Namespace 4 ←── UTS NS
└─ MNT NS ─────→ Mount NS 5          MNT NS ──→ Mount NS 6
```

一个 Namespace 在所有持有它的进程/文件描述符/挂载引用消失后通常会被内核回收。**仅退出某个 Shell 不一定足够**：如果你在里面启动了仍存活的后台任务或保留 Namespace FD，它还可能存在。因此每个实验都先清理任务再退出。

## 实验 4.2-A：读取当前 WSL Namespace（只读）

```bash
printf 'PID=%s\n' "$$"
hostname
for ns in pid mnt net uts ipc user cgroup; do
  printf '%-8s ' "$ns"
  readlink "/proc/$$/ns/$ns"
done
```

观察：`pid`、`mnt`、`net` 等有不同的 Namespace Identity。

**回退**：只读，无需清理。

---

## 4.2.3 UTS Namespace：独立 Hostname

**UTS Namespace** 隔离 hostname 等信息。进入新 UTS Namespace 后，初始 hostname 与外层相同，但修改只作用于新 UTS Namespace。

### 实验 4.2-B：只改隔离环境里的 hostname

**Terminal A：**

```bash
ORIGINAL_HOSTNAME=$(hostname)
printf 'outer hostname: %s\n' "$ORIGINAL_HOSTNAME"
sudo unshare --uts bash
```

在新 Bash 中：

```bash
hostname                 # 初始与外层一样
hostname ai-infra-uts
hostname                 # ai-infra-uts
readlink /proc/$$/ns/uts
```

**Terminal B（正常 WSL Shell）：**

```bash
hostname
# 应仍为原 hostname
readlink /proc/$$/ns/uts
```

**原理：** `hostname` 修改的是当前 Process 所属 UTS Namespace 的 Kernel 状态；不是改 `/etc/hostname` 文件。

### 实验 4.2-B 回退 / 验证

Terminal A：

```bash
exit
```

Terminal B：

```bash
hostname
# 与实验前相同
```

没有写入持久系统配置。若你仍在一个被隔离的 Bash 里，不要继续运行其他章节的命令，先 `exit`。

---

## 4.2.4 PID Namespace：同一 Process 有不同 PID

**PID Namespace** 隔离进程 ID 的可见性，是层级结构：父 PID Namespace 可以看到子 Namespace 中的 Process，子 Namespace 看不到父 Namespace 的其他进程。

### 为什么需要 `--fork`？

```text
unshare 创建新 PID Namespace
↓
新 Namespace 作用于以后创建的 Child
↓
--fork 创建 Child
↓
Child 成为新 PID Namespace 中的 PID 1
```

`unshare --pid bash` 不足以让原本的那个 Process 自己变成新 PID Namespace 的 PID 1。通常用 `--pid --fork`。

### 为什么需要 `--mount-proc`？

`ps` 通常读取 `/proc`。如果换了 PID Namespace 却保留原来的 procfs Mount，就可能看到与内层 PID Namespace 不一致的进程视图。因此配合新 Mount Namespace 和对应的 procfs。

### 实验 4.2-C：创建 PID 1

```bash
sudo unshare \
  --pid --fork \
  --mount --mount-proc \
  --propagation private \
  --uts \
  bash
```

**新 Shell：**

```bash
echo "inner PID=$$"        # 常见为 1
ps -ef                    # 应只看到很少进程
hostname ai-infra-pid
sleep 180 &
CHILD_PID=$!
echo "child inner PID=$CHILD_PID"
ps -ef
```

**Terminal B（同一个 WSL Linux 进程视图的外部 Shell）：**

```bash
ps -ef | grep '[s]leep 180'
```

如看到一个 `sleep 180` 对应较大的 PID：它与内层较小的 PID 指向同一 Kernel Task，不是两份独立 Process。

> Windows 宿主进程列表和 Ubuntu WSL 的 Process 视图不等价；这里比较的是同一 WSL Linux 环境内外 PID Namespace。

### PID Namespace 中 PID 1 的特殊性

Inner PID 1 是此 PID Namespace 的 Init Process。它退出时，这个 PID Namespace 内的其他进程通常会被 Kernel 结束。不要因此省略主动清理：显式终止实验子进程有助于识别是否存在泄漏。

### 实验 4.2-C 回退 / 验证

新 Shell 内：

```bash
kill "$CHILD_PID" 2>/dev/null || true
wait "$CHILD_PID" 2>/dev/null || true
exit
```

外部 Shell：

```bash
hostname
readlink /proc/$$/ns/pid
```

确认外部 hostname / PID Namespace 与实验前一致。不要对 WSL 全局执行 `pkill sleep`。

---

## 4.2.5 Mount Namespace：独立的 Mount Tree

**Mount**：将某个 Filesystem 挂到某个路径。**Mount Namespace**：决定一个 Process 可以看到什么 Mount 结构。

```text
同一个路径 /tmp/demo：

外层 Mount Namespace → 普通目录
内层 Mount Namespace → tmpfs 挂载点
```

### `tmpfs`

**tmpfs** 是一种基于内存（并可能涉及 swap）的临时 Filesystem。它不是把一个真实物理磁盘直接格式化或挂载进来。

### Mount Propagation

Mount Event 是否跨 Mount Namespace 传播，由 `shared/slave/private` 等 Propagation 机制决定。实验使用：

```bash
--propagation private
```

避免实验性 Mount 向外传播。`--mount` 本身并不自动意味着“所有挂载事件绝不会传播”，所以显式声明很重要。

### 实验 4.2-D：相同路径看到不同内容

**外层 WSL Shell：**

```bash
LAB_MNT=$(mktemp -d /tmp/ai-infra-mnt.XXXXXX)
mkdir -p "$LAB_MNT/demo"
printf 'LAB_MNT=%s\n' "$LAB_MNT"
```

启动新 Mount Namespace（让变量通过环境传入）：

```bash
sudo env LAB_MNT="$LAB_MNT" \
  unshare --mount --propagation private bash
```

**在新 Shell 内：**

```bash
mount -t tmpfs tmpfs "$LAB_MNT/demo"
printf 'inside namespace\n' > "$LAB_MNT/demo/hello.txt"
findmnt --mountpoint "$LAB_MNT/demo"
cat "$LAB_MNT/demo/hello.txt"
```

**外部 Terminal B：**

```bash
ls -la "$LAB_MNT/demo"
# 不应看到内层 tmpfs 的 hello.txt
```

可以把这个实验理解成：同名路径是 Mount Tree 中的一个位置，但不同 Namespace 可以将它映射到不同 Filesystem。

### 实验 4.2-D 回退 / 验证

先在新 Shell：

```bash
umount "$LAB_MNT/demo"
exit
```

外部 Shell：

```bash
# 只删除本次 mktemp 创建的已知路径
[ -n "${LAB_MNT:-}" ] && [ -d "$LAB_MNT" ] && rm -rf -- "$LAB_MNT"
unset LAB_MNT
```

回退验证：

```bash
findmnt | grep 'ai-infra-mnt' || echo 'no lab mounts'
find /tmp -maxdepth 1 -name 'ai-infra-mnt.*' -print
```

第二条若系统有其他同名模式的目录应人工判断；不要直接通配 `rm -rf /tmp/ai-infra-mnt.*`。

---

## 4.2.6 Network Namespace：一套独立网络栈

新 NetNS 默认通常只有 `lo`（一般为 DOWN）。它并不会自动把 WSL 的 `eth0` 或 Host Route 拿进来。

### 实验 4.2-E：观察只剩 loopback

外层：

```bash
ip addr
ip route
readlink /proc/$$/ns/net
```

进入：

```bash
sudo unshare --net bash
```

新 Shell：

```bash
ip addr                  # 通常只有 lo，最初 DOWN
ip route                 # 通常无默认路由
ip link set lo up
ip addr show lo
ping -c 2 127.0.0.1      # 若 ping 工具可用
```

为什么没有互联网？

```text
New NetNS
  └─ lo

没有 veth
没有网关
没有 default route
没有 Host Bridge / NAT
```

Docker 以后会创建 NetNS 侧的 `eth0`、veth pair、Host Bridge 或其他网络连接。

### 实验 4.2-E 回退 / 验证

新 Shell：

```bash
exit
```

外部：

```bash
ip addr
ip route
readlink /proc/$$/ns/net
```

**没有创建 veth、bridge，也没有改 Host NAT/Route**。原 WSL `eth0` 和 default route 应保持不变。

---

## 4.2.7 User Namespace：容器内 UID 0 不一定是 Host root

**User Namespace**：为 User ID / Group ID 提供隔离与映射。例如：

```text
Outer UID 1000  ←→  Inner UID 0
```

因此“在 Container 里是 root”不能自动推导为“在宿主 initial user namespace 中有完整 root 权限”。这是 Rootless Container 的重要基础。

### 实验 4.2-F（可选，权限取决于 WSL 配置）

直接在普通用户 Shell 试：

```bash
id
unshare --user --map-root-user bash
```

成功进入后：

```bash
id
cat /proc/self/uid_map
cat /proc/self/gid_map
```

`id` 可能显示 UID 0，但映射文件显示其与外层 UID/GID 的关系。不要用修改 `/root` 或访问敏感目录的方式试探权限；观察 `uid_map` 已足够说明机制。

如果 `Operation not permitted`，**跳过即可，不要更改系统 sysctl**。

**回退：** `exit`。外部 `id` 应仍显示原用户身份。

---

## 4.2.8 IPC Namespace 与 Cgroup Namespace

**IPC = Inter-Process Communication**：传统 System V Shared Memory、Semaphore、Message Queue 等。IPC Namespace 让不同 Process Groups 看不到/访问不到彼此的某些 IPC 对象。

**Cgroup Namespace**：隔离 cgroup hierarchy 的视图；它本身不是 CPU / Memory Limit 的执行机制。真正资源限制来自 4.3 的 cgroup Controllers。

本节只解释概念，不创建复杂 IPC 对象，以降低实验残留风险。

---

## 4.2.9 `nsenter`：进入已有 Namespace

### 实验 4.2-G：从外部读取隔离 hostname

**Terminal A：**

```bash
sudo unshare --uts bash
hostname ai-infra-nsenter
echo "TARGET_PID=$$"
```

让 Terminal A 的 Shell 保持运行。因为只创建了 UTS Namespace，`$$` 可用作外部同一 WSL 环境中的 PID。假设得到 `TARGET_PID=5234`。

**Terminal B：**

```bash
sudo nsenter -t 5234 -u hostname
# 输出应为 ai-infra-nsenter
```

这里：

- `-t 5234`：使用目标 Process 的 Namespace 信息；
- `-u`：进入它的 UTS Namespace；
- `hostname`：启动一个新的进程，执行这个命令。

这不是直接进入 5234 的 Bash，也不是修改 5234 的运行逻辑。

**回退：** Terminal B 命令自己已结束；Terminal A `exit`。最后 `ps -p 5234` 应不再找到此实验 Shell（注意不要在新实验中复用旧 PID）。

---

## 4.2.10 最终实验：不依赖 Docker 的 Container-like Shell

```bash
sudo unshare \
  --uts --pid --fork \
  --mount --mount-proc --propagation private \
  --net --ipc \
  bash
```

Inside：

```bash
hostname ai-infra-mini
ip link set lo up
echo "my inner PID=$$"
ps -ef
ip addr
ip route
ls /
cat /etc/os-release
```

你已经拥有：

```text
PID Namespace    ✓
UTS Namespace    ✓
Mount Namespace  ✓
Network Namespace ✓
IPC Namespace    ✓
RootFS           ✗  仍指向 WSL 的原 RootFS 视图
cgroup Resource Limit ✗
Capabilities / seccomp Hardening ✗
Image Layer      ✗
```

**最重要的观察：** Namespace 并不会自动生成新 `/`。`ls /` 还很像外部 WSL。换 RootFS 是 4.4 的工作。

### 最终实验回退 / 验证

```bash
exit
```

新 PID Namespace 的 PID 1 退出后，内部剩余 Task 通常也会被结束；不要在 Namespace Shell 里留下后台服务。

外部：

```bash
hostname
ip addr
ip route
for ns in pid mnt net uts ipc user cgroup; do
  printf '%-8s ' "$ns"
  readlink "/proc/$$/ns/$ns"
done
```

应与最初的外部 Namespace/hostname/网络记录一致。本节未永久修改 `/etc`、WSL 配置、Docker 网络、Host Route、sysctl。

## 4.2 与 Kubernetes Pod 的联系

Container 不必独占每一种 Namespace。Kubernetes Pod 中不同容器通常**共享一个 Pod Network Namespace**，所以同 Pod 的 App Container 与 Sidecar 可以通过 `localhost` 相互访问。

```text
Pod Network Namespace
├─ App Container      :8080
└─ Sidecar Container  → http://127.0.0.1:8080
```

但两者可具有不同 Image RootFS、Process 生命周期等。`docker run --network host`、`--pid host` 也反映 Namespace Sharing 是可配置的。

## 4.2 关键复盘

1. `unshare` 建立隔离；`nsenter` 用已有 Namespace 启动新 Process。
2. `/proc/PID/ns` 可帮助识别 Namespace Identity。
3. PID Namespace 有层级，内外看到的 PID 可以不同。
4. PID Namespace 实验应同时正确处理 procfs / Mount Namespace。
5. Mount Namespace 隔离 Mount Tree，但不自动切换 RootFS。
6. 新 NetNS 默认没有外部网络；需要 veth、IP、Route 等配置。
7. User Namespace 可以把内层 root 映射为外层非 root。
8. Namespace 是 Kernel Object，可按需求组合与共享。
9. Docker exec 与 nsenter 都体现“新 Process 加入已有隔离视图”的思想。
10. 实验结束，清理专用任务并退出临时 Namespace，宿主 WSL 的基础配置保持不变。

---

# 4.3 cgroup：CPU / Memory / PIDs

> 核心问题：已经通过 Namespace 隔离可见性后，如何阻止某个 Container 把全部 CPU、内存或 Task 数耗尽？

## 4.3.1 基本定义

**cgroup = Control Group**：Linux Kernel 对一组 Process/Task 进行**资源统计、限制与分配控制**的机制。

```text
Namespace → Visibility / Isolation
cgroup    → Resource Accounting / Control
```

例如：

```text
cgroup: inference-service
├─ Process A
├─ Worker Thread B
└─ Helper Process C

CPU   → 1 CPU 的配额
Memory → 512 MiB 上限
Tasks → 最多 100 个
```

cgroup 不是进程树。父子进程关系来自 Process Parent/Child 机制；cgroup Membership 是另外一套管理维度。

## 4.3.2 cgroup v1 vs v2

- **v1**：不同资源 Controller 曾可以有不同 Hierarchy。
- **v2**：Unified Hierarchy（统一层级），CPU、Memory、PIDs、I/O 等在一棵 cgroup Tree 中共同组织。

现代 systemd、Docker、Kubernetes 环境常见 cgroup v2。但不是所有 WSL 环境均允许普通用户或 root 任意创建/编辑 cgroup。**有 systemd 时优先让 systemd 创建临时 Unit，不强行写根 cgroup。**

### 实验 4.3-A：只读检查当前环境

```bash
stat -fc %T /sys/fs/cgroup
# 预期：cgroup2fs

cat /proc/$$/cgroup
cat /sys/fs/cgroup/cgroup.controllers
cat /sys/fs/cgroup/cgroup.subtree_control
mount | grep cgroup
```

常见 v2 路径：

```text
/proc/PID/cgroup:
  0::/user.slice/...

/sys/fs/cgroup:
  cgroup.procs
  cgroup.controllers
  cgroup.subtree_control
  cpu.max
  cpu.stat
  memory.current
  memory.max
  memory.events
  pids.current
  pids.max
```

`0::/path` 中 `path` 是当前进程所属 cgroup 的路径（可能受 Cgroup Namespace 视图影响）。

**回退**：只读；无清理。若 `stat` 不是 `cgroup2fs`，不要把后续 v2 文件操作直接套用到 v1。

## 4.3.3 cgroup Hierarchy 和 Controller

```text
/
├─ system.slice
│  ├─ service-A.service
│  └─ service-B.service
└─ user.slice
   └─ user-1000.slice
```

**Controller**：负责一种资源的 Kernel 子系统，如 `cpu`、`memory`、`pids`、`io`。

**Hierarchical Resource Control**：子 cgroup 不可能绕过父 cgroup 的总资源约束。例如：

```text
Parent memory.max = 1GiB
Child memory.max = 4GiB
实际仍受 Parent 1GiB 约束
```

### 重要的 cgroup v2 委派细节

在 v2 中：

- 父 cgroup 的 `cgroup.controllers` 表示可向下分配的 Controller；
- 父 cgroup 的 `cgroup.subtree_control` 决定哪些 Controller 对子层启用；
- domain controller 有 no-internal-process 等约束；
- systemd 管理的 cgroup Tree 不能随意插入自己建的目录并开启 Controller。

因此 **“`sudo mkdir /sys/fs/cgroup/my-test` 成功”并不保证新目录已经有可写 `cpu.max` 或 `memory.max`**。直接在根层写 `cgroup.subtree_control` 可能影响整套 WSL 服务管理；本讲义不要求这样做。

---

## 4.3.4 CPU Controller

### `cpu.max`

v2 格式：

```text
QUOTA PERIOD
```

单位：微秒（µs）。例如：

```text
50000 100000  → 约 0.5 个 CPU 的计算配额
100000 100000 → 约 1 个 CPU
200000 100000 → 约 2 个 CPU
max 100000    → 不施加该级别的硬配额
```

**特别注意：** `50000 100000` 不是“8 核机器的一半（4 核）”，而是约 0.5 个 CPU 的总周期预算。

### CPU Throttling

**Throttling = 节流 / 暂缓执行。** 如果 cgroup 用完当前 CPU 周期预算：

```text
CPU 配额已用完
↓
Task 仍是想运行的
↓
Kernel 暂时限制它继续获得 CPU
↓
新配额周期开始后恢复
```

对应统计：

```text
cpu.stat:
usage_usec
user_usec
system_usec
nr_periods
nr_throttled
throttled_usec
```

### `cpu.weight`

`cpu.weight` 是多个组存在 CPU 竞争时的**相对权重**，并不等同于 Hard Ceiling。

```text
cpu.max    → 最多使用多少 CPU 配额
cpu.weight → 竞争时获得多少相对份额
```

例如 A weight=100、B weight=200，二者高度竞争时 B 倾向得到更高份额；没有竞争时 A 不一定被人为卡住。

---

## 实验 4.3-B：CPU 限额与 Throttling（systemd 安全路径）

**前提：** WSL 已运行 systemd 且 `/sys/fs/cgroup` 是 cgroup v2。否则跳过此组，不要改 `/etc/wsl.conf` 只是为了实验。

确认：

```bash
ps -p 1 -o comm=
systemctl is-system-running || true
command -v systemd-run
```

本实验通过 systemd 创建一个**临时、唯一名字的 Unit**，避免直接管理根 cgroup：

```bash
UNIT=ai-infra-lab-cpu.service
sudo systemctl status "$UNIT" --no-pager 2>/dev/null || true
```

如果同名 Unit 已存在且不是这次实验创建的，**不要覆盖或停止它**，改一个不同名字再试。

启动专用 CPU-heavy Process：

```bash
sudo systemd-run \
  --unit=ai-infra-lab-cpu \
  --property=CPUQuota=50% \
  /bin/sh -c 'exec yes >/dev/null'
```

查进程与 cgroup：

```bash
UNIT=ai-infra-lab-cpu.service
sudo systemctl show "$UNIT" -p MainPID -p ControlGroup -p CPUQuotaPerSecUSec
CG=$(sudo systemctl show -p ControlGroup --value "$UNIT")
PID=$(sudo systemctl show -p MainPID --value "$UNIT")
[ -n "$CG" ] && cat "/sys/fs/cgroup${CG}/cpu.max"
[ -n "$CG" ] && cat "/sys/fs/cgroup${CG}/cpu.stat"
ps -p "$PID" -o pid,pcpu,comm
```

等待几秒再看 `cpu.stat`：

```bash
sleep 4
[ -n "$CG" ] && cat "/sys/fs/cgroup${CG}/cpu.stat"
```

关注 `nr_throttled`、`throttled_usec`。`ps %CPU` 的显示取决于采样窗口，不必精确等于 50.0%。

### 实验 4.3-B 回退 / 验证

```bash
sudo systemctl stop ai-infra-lab-cpu.service
sudo systemctl reset-failed ai-infra-lab-cpu.service 2>/dev/null || true
```

专用服务不再运行，临时 Unit/cgroup 由 systemd 管理回收。验证：

```bash
sudo systemctl is-active ai-infra-lab-cpu.service || true
# 预期：inactive / unknown
[ -n "${PID:-}" ] && ps -p "$PID" -o pid,comm || true
unset PID CG UNIT
```

不要使用 `pkill yes`，否则可能杀掉 WSL 原有的其他测试程序。

---

## 4.3.5 Memory Controller

CPU 超额主要是 Throttle；Memory Hard Limit 超额可能触发 Reclaim / cgroup OOM / Kill。

关键文件：

| 文件 | 含义 |
|---|---|
| `memory.current` | 当前计入该 cgroup 的内存（Bytes） |
| `memory.max` | Memory Hard Limit，`max` 表示本层无限制 |
| `memory.high` | 产生内存压力/回收的阈值，不等于同样的硬上限 |
| `memory.events` | low/high/max/oom/oom_kill 等事件计数 |
| `memory.swap.max` | Swap 用量上限相关配置 |

### Memory 不是简单“bytearray 大小”

Python：

```python
x = bytearray(60 * 1024 * 1024)
```

真实 `memory.current` 不一定恰好是 60 MiB，还可能计入解释器 Heap、Stack、Page Cache、文件页等；取决于 Controller Accounting 规则。

### cgroup OOM ≠ 整台 WSL RAM 耗尽

即使 Host 还有大量 Free RAM，如果一个 cgroup 的 `memory.max` 为 96MiB，而 Process 需要更多的不可回收内存，也可能发生 **memcg OOM**。Kubernetes 里的 Container `OOMKilled` 经常与这条链有关。

---

## 实验 4.3-C：Memory Limit + cgroup OOM（可选）

为了降低风险，这里用 `systemd-run` 设置 96MiB 的**强约束**，而不是直接在 WSL 环境中无限分配内存。被启动的 Python 程序最多尝试申请 160MiB 并写入页面。

**前提：** 与 CPU 实验相同：systemd + cgroup v2 可用。若机器正处于内存紧张状态或 WSL 内存特别小，跳过此组。

先确认同名 Unit 不存在：

```bash
sudo systemctl status ai-infra-lab-mem.service --no-pager 2>/dev/null || true
```

启动：

```bash
sudo systemd-run \
  --unit=ai-infra-lab-mem \
  --property=MemoryMax=96M \
  /usr/bin/python3 -c '
import time
print("allocating up to 160 MiB", flush=True)
x = bytearray(160 * 1024 * 1024)
for offset in range(0, len(x), 4096):
    x[offset] = 1
print("allocation completed", flush=True)
time.sleep(15)
'
```

检查：

```bash
sudo systemctl show ai-infra-lab-mem.service -p Result -p ExecMainStatus -p ControlGroup
sudo journalctl -u ai-infra-lab-mem.service --no-pager -n 30
```

如果 Unit 还在运行，可实时观察它的 cgroup：

```bash
CG=$(sudo systemctl show -p ControlGroup --value ai-infra-lab-mem.service)
if [ -n "$CG" ] && [ -d "/sys/fs/cgroup${CG}" ]; then
  cat "/sys/fs/cgroup${CG}/memory.max"
  cat "/sys/fs/cgroup${CG}/memory.current"
  cat "/sys/fs/cgroup${CG}/memory.events"
fi
```

由于 OOM 可能很快结束进程，事件文件所在 Unit cgroup 也可能被 systemd 清理。若已看不到，不代表 Kernel 没做内存控制；结合 `journalctl` 和 `systemctl show ... Result` 判断。

### 实验 4.3-C 回退 / 验证

```bash
sudo systemctl stop ai-infra-lab-mem.service 2>/dev/null || true
sudo systemctl reset-failed ai-infra-lab-mem.service 2>/dev/null || true
sudo systemctl is-active ai-infra-lab-mem.service || true
unset CG
```

没有修改系统范围内的 `memory.max`；只创建了临时 Unit。

---

## 4.3.6 PIDs Controller：防 Process / Thread 爆炸

关键文件：

```text
pids.current → 当前 Tasks 数量
pids.max     → 最大允许的 Tasks 数量
pids.events  → 超过限制导致拒绝创建的事件
```

**Task** 既可能是 Process，也可能是 Thread。某程序只有一个 PID，但如果创建大量 OS Threads，也可能触发 `pids.max`。

CPU 超限、Memory 超限、PIDs 超限表现完全不同：

| 超限类型 | 常见结果 |
|---|---|
| CPU Quota | Throttling，Task 还活着但获得 CPU 时间减少 |
| Memory Hard Limit | Reclaim 失败后 cgroup OOM，可能 Kill |
| PIDs Limit | `fork()` / `clone()` / 创建 OS Thread 失败 |

### 实验 4.3-D：限制最多的 Tasks（可选）

**绝对不运行 Fork Bomb。** 仅尝试有限次数（例如 25 次），并限制每个 Child 的寿命，使用独立 systemd Unit 清理：

```bash
sudo systemctl status ai-infra-lab-pids.service --no-pager 2>/dev/null || true
sudo systemd-run \
  --unit=ai-infra-lab-pids \
  --property=TasksMax=12 \
  /bin/bash -c '
    for ((i=0; i<25; i++)); do
      sleep 25 &
    done
    wait
  '
```

查看：

```bash
CG=$(sudo systemctl show -p ControlGroup --value ai-infra-lab-pids.service)
if [ -n "$CG" ] && [ -d "/sys/fs/cgroup${CG}" ]; then
  cat "/sys/fs/cgroup${CG}/pids.max"
  cat "/sys/fs/cgroup${CG}/pids.current"
  cat "/sys/fs/cgroup${CG}/pids.events"
fi
sudo journalctl -u ai-infra-lab-pids.service --no-pager -n 30
```

可能看到 `fork: Resource temporarily unavailable` 以及 `pids.events:max` 计数上升。实际 TasksMax 可能与其他父 cgroup 约束、线程数共同作用。

### 实验 4.3-D 回退 / 验证

```bash
sudo systemctl stop ai-infra-lab-pids.service 2>/dev/null || true
sudo systemctl reset-failed ai-infra-lab-pids.service 2>/dev/null || true
sudo systemctl is-active ai-infra-lab-pids.service || true
unset CG
```

systemd 会按该 Unit 的 cgroup 管理和结束属于它的任务；不对整台 WSL 执行 `pkill sleep`。

---

## 4.3.7 进阶：直接写 `cgroup.procs`（原理演示，非默认实验）

在合法委派给你的、已经启用 Controller 的 cgroup 子树里，操作大致如下：

```text
mkdir <delegated-parent>/test
↓
echo '<quota> <period>' > test/cpu.max
↓
echo <PID> > test/cgroup.procs
↓
该进程及其 Task Membership 开始受配置限制
```

这里不提供直接修改 `/sys/fs/cgroup` 根目录的默认指令，因为 WSL/systemd 的委派、no-internal-process 和权限状态可能不符合条件。**正确的工程能力是理解 Kernel API，并知道何时交给 systemd、containerd 或 kubelet 管理它。**

当 `cgroup.kill` 可用时，写入 `1` 可以结束该 cgroup 中的所有进程（涉及其子树，需确认作用范围），比按命令名猜进程安全；但绝对不可对自己不了解的 cgroup 使用。cgroup 目录中仍有任务时，直接 `rmdir` 往往会失败。

## 4.3.8 Kubernetes Resource Request / Limit 的伏笔

```yaml
resources:
  requests:
    cpu: "500m"
  limits:
    cpu: "1"
    memory: 512Mi
```

- `500m` 表示 **0.5 CPU**。
- CPU **Limit** 典型通过 CPU cgroup Quota 等机制实现；低 Limit 可能导致服务延迟高、Throttling。
- Memory **Limit** 典型受 `memory.max` 等机制约束；低 Limit 可能 OOMKilled。
- CPU Request 参与调度及 CPU 权重等机制，不是与 `cpu.max` 完全同一个东西。

### Go/Python 程序并不知道什么叫“Docker CPU”

```text
Go Goroutine
↓
Go GMP Scheduler
↓
OS Thread / Process
↓
cgroup CPU/Memory/PIDs Control
↓
Linux Kernel Scheduler / MM
↓
CPU / RAM
```

cgroup 不直接调度 Goroutine，它主要作用于 Linux Tasks 和资源 Accounting。对于 Python、Go、Java、C++、vLLM 都适用。

## 4.3.9 Docker Stats 与 cgroup Accounting

Docker 看到的 CPU / Memory 等容器指标通常依赖内核资源统计，例如：

```text
cpu.stat
memory.current
pids.current
```

经 Runtime / cAdvisor / kubelet / Metrics Pipeline 处理后，变成 `docker stats`、Container Metrics、Prometheus 指标等。

### GPU 为什么不同？

标准的 CPU/Memory/PIDs cgroup Controller 不等于直接存在一个通用 `gpu.max`。GPU 分配还涉及 Device Nodes、Host GPU Driver、NVIDIA Container Toolkit、Device Plugin、MIG、Kubernetes DRA 等；后续章节再展开。

## 4.3 最终回退核对

```bash
for unit in ai-infra-lab-cpu ai-infra-lab-mem ai-infra-lab-pids; do
  sudo systemctl is-active "${unit}.service" 2>/dev/null || true
done

cat /proc/$$/cgroup
hostname
ip route
```

只要这些专用 Unit 已停止 / 释放、未动系统根 cgroup，那么本节未持久修改 WSL 配置。

## 4.3 十五句话

1. cgroup 管理一组 Process/Task 的资源，不是单个代码段。
2. Namespace 解决 Visibility，cgroup 解决 Resource Control。
3. cgroup v2 使用 Unified Hierarchy。
4. `cgroup.procs` 表示 Process Membership。
5. `cpu.max` 是硬配额，`cpu.weight` 是竞争权重。
6. `50000 100000` 约等于 0.5 CPU，而不是物理机器所有 CPU 的 50%。
7. CPU Limit 过低常导致 Throttling。
8. `cpu.stat` 可以观察实际用量和 Throttling。
9. `memory.current` 用于 Memory Accounting。
10. `memory.max` 是硬上限。
11. 即使 Host 内存充足，子 cgroup 也可能触发 OOM。
12. PIDs Controller 限制 Task 数量，包括 Threads。
13. PIDs Limit 达到后，新 Process/Thread 创建可能失败。
14. 子组受父组资源限制约束。
15. systemd、Docker、containerd、kubelet 都可使用 cgroup 管理 Workload；不要为了实验随意改它们的根 Hierarchy。

---

# 4.4 Container RootFS / Mount / chroot / pivot_root

> 核心问题：**为什么 Dockerfile 必须经常 `FROM ubuntu` / `FROM python`，但实际运行用的是 Host Linux Kernel？它们到底有什么关系？**

## 4.4.1 先把 Linux 系统分为 Kernel Space 和 User Space

平时说“Ubuntu 操作系统”，通常包含：

```text
完整传统 Linux 系统
├─ Linux Kernel
│  ├─ Process / Scheduler
│  ├─ Virtual Memory
│  ├─ Network Stack / Filesystem Drivers
│  └─ System Call Implementation
│
└─ User Space
   ├─ /bin/bash、coreutils
   ├─ libc（如 glibc 或 musl）
   ├─ Dynamic Loader 和 .so Libraries
   ├─ Package Manager（apt/apk/...）
   ├─ /etc 配置
   └─ Application / Runtime
```

但普通 **Linux Container 只带 Image 提供的 User-space 文件/元数据，不带能独立启动的 Guest Kernel**。

```text
Container A：Ubuntu User Space ──┐
Container B：Alpine User Space ───┼──→ 同一个 Host Linux Kernel
Container C：Rocky User Space ───┘
```

因此：

```dockerfile
FROM ubuntu:24.04
```

**不是**启动 Ubuntu Kernel，而是使用 Ubuntu 风格的 **User-space RootFS** 及 Image Metadata 作为基础。

## 4.4.2 `/etc/os-release` vs `uname -r`

这两个命令看起来都在回答“Linux 什么版本”，但实际答案来自不同来源。

```bash
cat /etc/os-release
```

- `/etc/os-release` 是当前 RootFS 里的一个文件，通常告诉你发行版 Userland 信息。

```bash
uname -r
```

- `uname` 是一个 User-space 程序；它向运行中的 Kernel 查询信息，因此报告的是承载 Container Process 的 Kernel 版本。

例如：

```text
/etc/os-release → Alpine Linux
uname -r       → Docker Desktop Linux Kernel X.Y
```

**它们不矛盾。**

### 实验 4.4-A：Docker 里的 Userland / Kernel（可选）

有 Docker 时，先检查 `alpine:3.20` 是否已有，以便清理镜像缓存：

```bash
if docker image inspect alpine:3.20 >/dev/null 2>&1; then
  HAD_ALPINE=1
else
  HAD_ALPINE=0
fi

docker run --rm alpine:3.20 sh -c '
  echo "=== userland ==="
  cat /etc/os-release
  echo "=== running kernel ==="
  uname -r
'
```

此实验使用 `--rm`，退出就删除 Container。

**回退 / 验证：**

```bash
# 只有确定原来没有镜像、且当前没有其他容器依赖它时才移除
if [ "${HAD_ALPINE:-1}" -eq 0 ]; then
  docker image rm alpine:3.20
fi
unset HAD_ALPINE
```

不删除原来已存在的 Image。

---

## 4.4.3 `FROM` 提供了什么

**Base Image**：新 Image 构建所依据的初始 Filesystem Layers 与相应 Metadata。

例如：

```dockerfile
FROM python:3.13-slim
```

初始环境通常有：

```text
/bin、/lib、/usr、/etc
Python Interpreter
Python Standard Library
User-space Shared Libraries
CA Certificates 等基础运行文件
```

假如 Image RootFS 为空，`app.py` 本身没有 Python Interpreter 就不能执行。

### `FROM scratch`

`scratch` 是逻辑上的空基础镜像：

```dockerfile
FROM scratch
COPY my-agent /my-agent
ENTRYPOINT ["/my-agent"]
```

如果 `my-agent` 是兼容目标 CPU/OS 的**真正自包含静态 Binary**，有时可以这样运行。Go 常适合这种场景，但：

- 若 Go 程序使用 CGO/动态链接库，RootFS 仍需配套 Loader/Shared Libraries。
- HTTPS 验证可能需要 CA Certificates。
- 时区、用户名映射、模板、配置和 DNS 等可能需要额外文件。

**Static Binary ≠ 永远不需要 RootFS 文件。**

## 4.4.4 为什么 Ubuntu Binary 不一定能在 Alpine 运行？

核心经常与 User Space C Library 有关：

- Ubuntu/Debian 常以 **glibc** 为基础；
- Alpine 常以 **musl libc** 为基础。

两者都属于 User Space。Linux Kernel 是共享的，但**动态链接 Binary 的 Loader / Shared Library 环境**可能不兼容。

```text
Application Binary
↓
ELF Interpreter / Dynamic Loader
↓
libc、libssl、libstdc++ 等 .so
↓
System Call ABI
↓
Host Linux Kernel
```

某个 ELF Binary 文件明明存在，但执行时显示 `No such file or directory`，可能是指定的 **ELF Interpreter 缺失**，而不是程序文件本身丢失。

查看：

```bash
file /usr/bin/bash
ldd /usr/bin/bash
```

可能出现：

```text
libc.so.6
libtinfo.so...
/lib64/ld-linux-x86-64.so.2
```

**安全提示：** 只对系统可信的 Binary 使用 `ldd`；不对来源不可信的 ELF 随意运行它。

## 4.4.5 System Call ABI：Base Image 如何调用 Host Kernel

**ABI = Application Binary Interface**。在本节重点指：User-space 程序与 Library / Kernel 之间遵循的二进制接口约定。

```text
Python / Bash / nginx / Go Binary
↓
libc 或 Runtime
↓
open / read / write / socket / connect / mmap / clone 等 syscall
↓
Host Linux Kernel
↓
设备 / CPU / RAM / Disk / NIC
```

因此 Image 和 Kernel **并非完全无关**：如果程序需要较新的 syscall / Kernel Feature，而 Host Kernel 太旧或被安全策略拦截，仍可能失败。只是 Image 本身**不会为普通 Container 启动独立 Kernel**。

---

## 4.4.6 Filesystem、RootFS、Mount、Image 的区别

| 名称 | 含义 | 举例 |
|---|---|---|
| Filesystem（FS） | 存储/组织文件及目录的机制或格式 | ext4、xfs、tmpfs、procfs、OverlayFS |
| Mount | 把某个 Filesystem 挂到指定路径 | 把 procfs 挂到 `/proc` |
| Mount Namespace | 一个 Process 所看见的 Mount Tree | 不同进程可以有不同的 `/` 和挂载点 |
| RootFS | 某个 Process 使用的根目录 `/` 对应的文件系统树 | `/bin`、`/etc`、`/usr`、`/app` |
| Container Image | 构造 RootFS 的 Filesystem Layers + 运行时 Metadata | `ubuntu:24.04` |

**RootFS 不是一个必须独立格式化出来的新磁盘分区**。它更多表示“这个 Process 看见的根目录树”。

```text
Image Layer Chain
↓
Unpack / Snapshot / Overlay Mount
↓
RootFS
↓
Mount Namespace 里的 /
↓
Container Process 的路径解析
```

---

## 4.4.7 `chroot`：改变 Process 的 `/`

**chroot = change root**。让 Process / Child Process 在 Path Resolution 时把某个目录当成根 `/`。

但它：

- 不会自动创建 PID Namespace；
- 不会自动创建 Network Namespace；
- 不会自动限制 CPU / Memory；
- 不会提供健全的 Container Security Boundary；
- 不一定让旧 Mount Tree 被真正断开。

所以 **chroot ≠ 完整 Container**。

## 实验 4.4-B：在 `/tmp` 手工制作最小 RootFS

### B-1 创建唯一实验目录

```bash
ROOTFS=$(mktemp -d /tmp/ai-infra-rootfs.XXXXXX)
printf 'ROOTFS=%s\n' "$ROOTFS"
mkdir -p "$ROOTFS"/{usr/bin,etc,proc,sys,dev,tmp}
```

**本实验只复制可信的系统 Binary 与其直接动态依赖；不是独立完整 Linux 发行版。**

### B-2 定义复制命令（适用于常见 Ubuntu WSL ELF 布局）

```bash
copy_elf() {
  local bin="$1"
  [ -x "$bin" ] || { echo "missing binary: $bin" >&2; return 1; }

  sudo mkdir -p "$ROOTFS$(dirname "$bin")"
  sudo cp -L -- "$bin" "$ROOTFS$bin"

  ldd "$bin" | awk '
    /=> \/\// {print $3}
    /^\// {print $1}
  ' | while IFS= read -r lib; do
    [ -n "$lib" ] || continue
    sudo mkdir -p "$ROOTFS$(dirname "$lib")"
    sudo cp -L -- "$lib" "$ROOTFS$lib"
  done
}
```

准备最少工具：

```bash
for command in bash ls cat uname id head; do
  copy_elf "$(command -v "$command")"
done

sudo mkdir -p "$ROOTFS/etc"
sudo cp -L /etc/os-release "$ROOTFS/etc/os-release"
```

> 若你的 WSL 二进制路径、Loader 路径或其他依赖不匹配，`chroot` 可能报 `No such file or directory`。优先重新检查 `ldd` 的 Interpreter / `.so` 是否复制完整；不为此更改 WSL 环境。不同架构（amd64/arm64）的 Loader 路径自然不同。

查看：

```bash
find "$ROOTFS" -maxdepth 3 -type f | head -30
```

### B-3 进入这个 RootFS

Ubuntu/WSL 常见 `bash` 的路径可能是 `/usr/bin/bash`（`/bin` 有时只是指向 `/usr/bin` 的 Symlink），因此从真实 `command -v` 路径启动：

```bash
BASH_PATH=$(command -v bash)
sudo chroot "$ROOTFS" "$BASH_PATH" --noprofile --norc
```

在 `chroot` 里：

```bash
pwd
ls /
cat /etc/os-release
uname -r
ls /proc
```

观察：

- `ls /`：只看到刚才准备的实验 RootFS 文件；
- `/etc/os-release`：来自本实验复制的静态文件；
- `uname -r`：仍然是 WSL 当前 Linux Kernel；
- `/proc`：只是一个空目录，因为还没有挂载 procfs。

**这是“User Space 是文件，Kernel 是实际运行中的内核”最直观的证据。**

### 实验 4.4-B 中途回退

在 chroot 里：

```bash
exit
```

外部 RootFS 目录暂时保留，用于后续 procfs / PID 实验；`chroot` 本身不会留下 Mount。

---

## 4.4.8 `/proc`、`/sys`、`/dev` 为什么不是简单的 Image 文件？

**procfs**：由 Kernel 动态生成进程/系统信息；Container Image 可包含 `/proc` 目录，但不应该想象 Image Layer 静态存了 `/proc/1/status`。

**sysfs**：Kernel Device、Driver、Bus 和 Kernel Object 的虚拟 Filesystem。

**`/dev`**：通常涉及 Device Nodes、devpts、tmpfs 等运行时挂载和设备访问控制。

真实容器 RootFS View：

```text
Image Layers
     ↓
Merged RootFS
     ↓
Runtime Mounts added:
  /proc   ← procfs
  /sys    ← sysfs
  /dev    ← device nodes / tmpfs / devpts
  /data   ← optional volume/bind mount
     ↓
Container Process sees the final tree
```

## 实验 4.4-C：在独立 Mount Namespace 内挂 procfs

从正常 WSL Shell（保留 `ROOTFS`）：

```bash
sudo env ROOTFS="$ROOTFS" BASH_PATH="$BASH_PATH" \
  unshare --mount --propagation private bash
```

**新 Mount Namespace Shell：**

```bash
mount -t proc proc "$ROOTFS/proc"
findmnt --mountpoint "$ROOTFS/proc"
chroot "$ROOTFS" "$BASH_PATH" --noprofile --norc
```

在 chroot 里：

```bash
ls /proc | head
cat /proc/1/status | head
uname -r
exit
```

由于目前**只有 Mount Namespace，没有新 PID Namespace**，这个 procfs 对应的还是外部 PID Namespace 的视图。于是 `/proc/1` 可能是 WSL 当前 PID Namespace 的 Init Process。

### 实验 4.4-C 回退 / 验证

仍在隔离的 Mount Namespace Shell：

```bash
umount "$ROOTFS/proc"
exit
```

回到正常 WSL：

```bash
findmnt --mountpoint "$ROOTFS/proc" || echo 'procfs lab unmounted'
```

实验 Mount 没有传播到原 WSL Mount Namespace；RootFS 目录保留用于下一实验。

---

## 实验 4.4-D：RootFS + PID Namespace + UTS Namespace

进一步把几种内核能力组合：

```bash
sudo env ROOTFS="$ROOTFS" BASH_PATH="$BASH_PATH" \
  unshare \
    --uts --pid --fork \
    --mount --propagation private \
    bash -c '
      set -e
      hostname ai-infra-mini-rootfs
      mount -t proc proc "$ROOTFS/proc"
      exec chroot "$ROOTFS" "$BASH_PATH" --noprofile --norc
    '
```

**内部验证：**

```bash
echo "inner PID=$$"     # 通常 1
hostname               # ai-infra-mini-rootfs
cat /etc/os-release    # RootFS 的文件
uname -r               # Host Linux Kernel
ls /proc                # 与新 PID Namespace 相匹配的进程视图
```

现在拥有：

```text
PID Namespace          ✓
UTS Namespace          ✓
Mount Namespace        ✓
RootFS                 ✓
procfs                 ✓
CPU / Memory cgroup    ✗
NetNS / veth           ✗
Capability Hardening   ✗
Seccomp Hardening      ✗
OCI Runtime            ✗
```

这已经是一个很直观的“手工微型容器”，但**不应作为安全沙箱运行不可信代码**。

### 实验 4.4-D 回退 / 验证

在内部：

```bash
exit
```

当 PID 1 退出，临时 PID / UTS / Mount Namespace 通常随该子进程退出而回收；里面的 procfs Mount 不会修改外层 Mount Tree。

在正常 WSL：

```bash
hostname
findmnt --mountpoint "$ROOTFS/proc" || echo 'no leaked procfs mount'
```

---

## 4.4.9 `pivot_root` 与 `chroot` 的本质区别

**`chroot`**：改变某个 Process 的路径解析 Root。它并没有天然提供 Namespace 隔离，也不保证旧 Root Mount 彻底脱离。

**`pivot_root`**：在适当的 Mount Namespace / Mount 配置中，真正把 Root Mount 切换到新的 RootFS，并把原 Root 临时移到新 Root 下的某个目录，再 Unmount / Detach 旧 Root：

```text
Before:
/
└─ newroot

pivot_root(newroot, newroot/.oldroot)
↓
After:
/          ← 原 newroot
/.oldroot  ← 原 Root Mount
↓
umount /.oldroot
```

真实 Runtime 会依实际平台、RootFS 和安全模式使用适当的 Mount/Root 切换策略，不应机械地声称“所有 Container 都必须按完全相同的 pivot_root 步骤运行”。

本教材**不把手写 pivot_root 列为必做实验**：对 Mount Topology、Old Root、Propagation 的前提要求更高；通过前面三个实验已可以完整理解 RootFS/Userland/Kernel 的区别。

---

## 4.4.10 结束整个 RootFS 实验系列：完整回退

回到正常 WSL Shell，先确认没有实验 Mount：

```bash
findmnt | grep 'ai-infra-rootfs' || echo 'no rootfs lab mounts'
```

只删除当前这个 `mktemp` 创建的路径：

```bash
if [ -n "${ROOTFS:-}" ] && [ -d "$ROOTFS" ]; then
  case "$ROOTFS" in
    /tmp/ai-infra-rootfs.*) sudo rm -rf -- "$ROOTFS" ;;
    *) echo "Unexpected ROOTFS path; not deleting: $ROOTFS" >&2 ;;
  esac
fi
unset ROOTFS BASH_PATH
unset -f copy_elf
```

**验证：**

```bash
find /tmp -maxdepth 1 -name 'ai-infra-rootfs.*' -print
findmnt | grep 'ai-infra-rootfs' || echo 'rootfs lab clean'
hostname
```

若 `findmnt` 仍显示有相关挂载，**不要直接删除路径**，先找到持有它的 Namespace/Process 并正确 `umount`。

---

## 4.4.11 Image Layers 与 RootFS（为 4.5 铺垫）

```dockerfile
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y curl
COPY app /app
```

概念上：

```text
Ubuntu Base Layers
 + apt 安装引入的 Filesystem Changes
 + COPY 的 app Files
↓
Image Layer Chain
↓
Runtime 生成最终 Merged RootFS
↓
Container Process 的 /
```

**Image 不只是文件系统**：还含 `CMD`、`ENTRYPOINT`、`ENV`、`WORKDIR`、`USER` 等 Metadata。`FROM` 提供的既是文件层基础，也是相应 Image Config 的起点。

## 4.4.12 与 AI Infra：CUDA Container 的同一逻辑

粗略对应：

```text
Container Image / User Space
  ├─ PyTorch
  ├─ CUDA Runtime / User-space Libraries
  ├─ cuBLAS / NCCL（取决于 Image）
  └─ Python / Application
              ↓
     Device Nodes + Driver Interfaces
              ↓
Host Linux Kernel + NVIDIA Kernel Driver
              ↓
          Physical GPU
```

NVIDIA Container Toolkit 还可把 Host Driver 对应的 User-space Driver Library、Device Nodes 等适当注入 Container，具体取决于驱动与 Runtime。**不要误以为 `FROM nvidia/cuda` 就在容器内启动了 NVIDIA Kernel Driver**。

这也解释了：相同 Image 换一台 Host，由于 Host Kernel、NVIDIA Driver、RDMA Driver 等版本/能力不同，可能出现兼容问题。

## 4.4 十五句话

1. `FROM ubuntu` 提供 Ubuntu User Space / RootFS，不提供独立的 Guest Kernel。
2. Linux Container 使用承载它的 Linux Kernel。
3. `/etc/os-release` 是 RootFS 里的文件；`uname` 查询运行中的 Kernel。
4. Program 经 Runtime/libc/System Call ABI 进入 Kernel。
5. Userland 与 Kernel 仍需 Feature/ABI 兼容。
6. glibc 与 musl 是不同的 User-space libc。
7. 动态 Binary 需要 ELF Loader + Shared Libraries。
8. `scratch` 是空的 Base；静态 Binary 可用但不一定不需要证书等文件。
9. RootFS 指 Process 看到的 `/`。
10. Mount Namespace 决定 Process 的 Mount Tree。
11. `chroot` 改变根路径视图，不等于完整 Container。
12. procfs/sysfs/dev 的真实视图多数来自 Runtime Mount 与 Kernel。
13. `pivot_root` 是一种更接近 Runtime 的 Root Mount 切换手段。
14. Image Layers 组合出 Container RootFS，下一节 OverlayFS 会解释合并细节。
15. CUDA User Space 与 Host GPU Kernel Driver 的分工遵循同样模型。

---

# 4.5 Docker Image / Layer / OverlayFS

> 本节核心问题：`FROM ubuntu` 继承什么？Layer 为什么能共享？Container 运行时对 Image 里的文件修改，最终写到哪里？为什么下一层 `rm` 了一个 1GB 文件，镜像仍可能很大？

## 4.5.1 结论：Image = Layer Chain + Metadata

```text
Container Image
├─ Filesystem Layer 1（base）
├─ Filesystem Layer 2（changes）
├─ Filesystem Layer 3（changes）
└─ Image Metadata
   ├─ ENTRYPOINT / CMD
   ├─ ENV / WORKDIR / USER
   ├─ Architecture / OS
   └─ RootFS Layer/History Information
```

**Filesystem Diff**：一层相对于下层 Filesystem 新增、修改、删除的变化，不是完整 RootFS 的重复副本。

```text
Layer 1:
  /bin、/lib、/etc ...
Layer 2:
  ADD /usr/bin/curl
Layer 3:
  ADD /app/server
```

Layer 2 不需要重新保存整份 `/bin`、`/lib`。镜像之所以可以共享 Base Layers、用 Content Cache 提速，也与此有关。

## 4.5.2 `FROM` 与 Base Layer Chain

```dockerfile
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y curl
COPY app /app
```

概念：

```text
Ubuntu Base Layer(s)
       ↓
RUN 的 FS Diff Layer
       ↓
COPY 的 FS Diff Layer
       ↓
新 Image
```

`FROM` 继承 Base Image 的 Layer Chain 与相应 Config，不继承独立 Linux Kernel。

### “一条 Dockerfile 指令 = 一层”准确吗？

不完全准确。

- `RUN`、`COPY`、`ADD` 等产生文件系统变更的步骤通常会创建 FS Diff Layer。
- `CMD`、`ENTRYPOINT`、`ENV`、`USER`、`LABEL` 等主要影响 Image Configuration；并非每条都要产生有实际文件内容的新 Layer Blob。
- 特定 Builder、平台和特殊指令存在具体实现细节。

因此正确表述：**Image History/Build Steps 与实际 Filesystem Blob Layers 不是简单一一对应。**

## 4.5.3 Content Addressing / Digest / Sharing

**Digest**：对内容进行 Hash 计算得到的标识，如 `sha256:...`。

**Content Addressing**：通过内容本身识别对象。同样的 Layer Blob 可以在多个 Image 之间共享，不必按 Image 名称重复保存。

```text
Image A = Base X + Dependency Y + App A
Image B = Base X + Dependency Y + App B

本地只需：X、Y、A、B 各一份（如果内容相同）
```

`docker pull` 中的 `Already exists` 往往表示本地已经有相同 Content Digest 的 Blob 或可复用数据。

**Deduplication = 去重**。Layer Sharing 可减少网络下载和磁盘存储，但不同 Runtime、Compression、Content Store / Snapshotter 布局会影响实际磁盘占用。

---

## 4.5.4 OverlayFS 是什么

**OverlayFS**：Linux 的一种 Union/Overlay Filesystem，让多棵目录树合并成一个统一的可见 Filesystem。

四个重要概念：

| 名称 | 用途 |
|---|---|
| `lowerdir` | 底层只读数据来源；可以是多层 |
| `upperdir` | 上层可写数据，记录新建/修改/删除信息 |
| `workdir` | OverlayFS 内部操作工作区；需满足与 upperdir 的相关 FS 条件 |
| `merged` | Process 最终看到的合并视图（Mount Point） |

```text
       Application
           │
           ↓
        merged/
           │
        OverlayFS
       ┌───┴────┐
       ↓        ↓
    upper/    lower/
   writable   readonly
```

**重要：** `merged` 不是执行 `cp -r lower merged` 得到的普通复制目录，它是一张由 Kernel 根据 Upper/Lower 计算出来的文件系统视图。

### OverlayFS 和 ext4/xfs 的区别

```text
Application
↓
OverlayFS merged view
↓
Upper/Lower data
↓
Backing filesystem（ext4/xfs 等）
↓
Block Device
```

OverlayFS 更偏“目录层的组合与写时复制机制”，下面仍依靠合适的 Backing Filesystem 存数据。

---

## 4.5 WSL 实验总说明：OverlayFS

这组实验的所有数据都放进 `mktemp` 创建的 `/tmp` 目录，所有 Overlay Mount 都放在**新 Mount Namespace** 里。这样即使忘记卸载，也不会把实验 Mount 带到正常 WSL Mount Tree 中；当然还是应显式 `umount`。

检查（只读）：

```bash
grep -w overlay /proc/filesystems
# 有 overlay 表示当前 Kernel 支持 / 已注册对应 FS
```

如果后面 Mount 报 `permission denied`、`not supported`，不要去修改 WSL Kernel 或全局 Mount 配置；跳过实操即可。

**特别提示：** 本节下面标记“隔离 Shell 内”的命令要在 `sudo ... unshare --mount ... bash` 启动的新 Shell 中执行；标记“外部 Shell”的命令则在正常 WSL 中执行。不要把删除或 Mount 操作从一个 Shell 直接乱复制到另一个。

---

## 实验 4.5-A：创建 lower / upper / work / merged

**外部 WSL Shell：**

```bash
OVL=$(mktemp -d /tmp/ai-infra-overlay.XXXXXX)
mkdir -p "$OVL"/{lower,upper,work,merged}
mkdir -p "$OVL/lower/app"
printf 'version=1\n' > "$OVL/lower/app/config.txt"
printf 'base file\n' > "$OVL/lower/base-only.txt"
printf 'OVL=%s\n' "$OVL"
```

当前：

```text
$OVL/
├─ lower/
│  ├─ app/config.txt（version=1）
│  └─ base-only.txt（base file）
├─ upper/
├─ work/
└─ merged/
```

启动隔离的 Mount Namespace：

```bash
sudo env OVL="$OVL" unshare --mount --propagation private bash
```

**以下均在隔离 Shell 内进行，直到本节统一 `exit`：**

```bash
mount -t overlay overlay \
  -o "lowerdir=$OVL/lower,upperdir=$OVL/upper,workdir=$OVL/work" \
  "$OVL/merged"

findmnt --mountpoint "$OVL/merged"
cat "$OVL/merged/app/config.txt"
cat "$OVL/merged/base-only.txt"
find "$OVL/upper" -maxdepth 2 -print
```

初始 Merged View 有 Lower 的两个文件，而 Upper 几乎为空。文件还没被 Copy-Up。

### 实验 4.5-A 中途回退 / 验证

在隔离 Shell 内：

```bash
umount "$OVL/merged"
findmnt --mountpoint "$OVL/merged" || echo 'overlay unmounted'
```

这一步证明 Mount 是可逆的。接下来为了继续实验，重新挂载：

```bash
mount -t overlay overlay \
  -o "lowerdir=$OVL/lower,upperdir=$OVL/upper,workdir=$OVL/work" \
  "$OVL/merged"
```

---

## 4.5.5 Copy-on-Write / Copy-Up

**Copy-on-Write（CoW，写时复制）**：读的时候可以共享已有数据，需要写的时候才生成新的可写副本。

**Copy-Up**：当文件目前只存在 Lower，但 OverlayFS 需要修改它时，把它复制/提升到 Upper 后再完成修改。

```text
第一次 read:
  merged /app/config.txt → lower/app/config.txt

第一次 write:
  lower file exists
    ↓
  Copy-Up into upper/app/config.txt
    ↓
  write upper copy

以后 read:
  merged /app/config.txt → upper/app/config.txt
```

### 实验 4.5-B：观察 Copy-Up

**隔离 Shell 内：**

```bash
cat "$OVL/merged/app/config.txt"  # version=1

printf 'version=2\n' > "$OVL/merged/app/config.txt"

cat "$OVL/merged/app/config.txt"  # version=2
cat "$OVL/lower/app/config.txt"   # 仍为 version=1
cat "$OVL/upper/app/config.txt"   # version=2
```

同一路径的 Higher Layer 版本优先于 Lower：

```text
lower/app/config.txt → version=1
upper/app/config.txt → version=2
merged/app/config.txt → version=2
```

这就解释了：**Container 里修改一个 Image File，不会回写 Read-only Image Layer。**

### 实验 4.5-B 回退：丢掉 Writable Layer

隔离 Shell 内：

```bash
umount "$OVL/merged"
rm -rf "$OVL/upper" "$OVL/work"
mkdir -p "$OVL/upper" "$OVL/work"
mount -t overlay overlay \
  -o "lowerdir=$OVL/lower,upperdir=$OVL/upper,workdir=$OVL/work" \
  "$OVL/merged"
cat "$OVL/merged/app/config.txt"
# 应回到 version=1
```

这相当于丢弃旧 Container 的 Writable Layer，再基于同一只读 Image 创建新运行视图。

---

## 4.5.6 新文件写在哪里？

如果 Lower 根本没有某个文件：

```text
create /runtime.txt
↓
直接创建 Upper/runtime.txt
```

### 实验 4.5-C：创建 Runtime 文件

**隔离 Shell 内：**

```bash
printf 'runtime data\n' > "$OVL/merged/runtime.txt"
cat "$OVL/upper/runtime.txt"
# runtime data
```

Container 里的 `/tmp`、应用 Log、Cache、下载文件，如果没有独立 Mount/Volume，可能进入 Container Writable Layer。

### 实验 4.5-C 回退

```bash
umount "$OVL/merged"
rm -rf "$OVL/upper" "$OVL/work"
mkdir -p "$OVL/upper" "$OVL/work"
mount -t overlay overlay \
  -o "lowerdir=$OVL/lower,upperdir=$OVL/upper,workdir=$OVL/work" \
  "$OVL/merged"
test ! -e "$OVL/merged/runtime.txt" && echo 'runtime file cleared'
```

---

## 4.5.7 Whiteout：删除 Lower File 不等于真正擦除旧 Layer

当 Container 删除 Lower 里的文件，OverlayFS 不能真的修改 Read-only Lower。它必须在高层记录“这个路径已经删除”的语义。

**Whiteout（白障）**：Higher Layer 用于遮蔽 Lower 文件的一种特殊标记或表示。

```text
Lower:  /base-only.txt     存在
Upper:  Whiteout(base-only.txt)
Merged: /base-only.txt     不存在
```

### 实验 4.5-D：删除 Lower File

**隔离 Shell 内：**

```bash
cat "$OVL/merged/base-only.txt"
rm "$OVL/merged/base-only.txt"

test ! -e "$OVL/merged/base-only.txt" && echo 'hidden in merged'
cat "$OVL/lower/base-only.txt"   # Lower 仍然是 base file
ls -la "$OVL/upper"
```

Upper 中 Whiteout 的具体表现取决于 Kernel/Backing Filesystem：可能使用特殊 Character Device 或带有特殊 Extended Attribute 的 File，不一定是可读的普通 `.wh.name` 文件。

### OCI Image Layer 的 Whiteout 编码

在 Image Layer Tar 的表示里，经常使用类似：

```text
/app/.wh.foo
```

表达下一层删除 `/app/foo`。

而：

```text
.wh..wh..opq
```

是与**Opaque Directory（不合并 Lower 子项）**有关的编码。

**要区分：** OCI Layer Tar 里的 Whiteout 编码 ≠ 运行中的 OverlayFS Upperdir 在 Disk 上必然长得一模一样。应用看到的是“文件不存在”，不会在 Merged View 里看到这些内部标记。

### 实验 4.5-D 回退

```bash
umount "$OVL/merged"
rm -rf "$OVL/upper" "$OVL/work"
mkdir -p "$OVL/upper" "$OVL/work"
mount -t overlay overlay \
  -o "lowerdir=$OVL/lower,upperdir=$OVL/upper,workdir=$OVL/work" \
  "$OVL/merged"
cat "$OVL/merged/base-only.txt"
# 再次出现 base file
```

---

## 4.5.8 多个 Lower Layer：模拟 Image Chain

Lower 不必只有一个。高优先级 Lower 覆盖低优先级 Lower 的同名路径。

```text
Highest Priority:
  upper（Runtime Writable）
  lower2（Image Layer 2）
  lower1（Image Base Layer）
Lowest Priority
```

### 实验 4.5-E：两层 Lower + 一层 Upper

**隔离 Shell 内**，先卸载当前 Mount：

```bash
umount "$OVL/merged"
rm -rf "$OVL/lower" "$OVL/upper" "$OVL/work"
mkdir -p "$OVL"/{lower1,lower2,upper,work}
mkdir -p "$OVL/lower1/etc" "$OVL/lower1/app"
mkdir -p "$OVL/lower2/etc" "$OVL/lower2/app"

printf 'BASE\n' > "$OVL/lower1/etc/version"
printf 'hello v1\n' > "$OVL/lower1/app/app.txt"
printf 'only in base\n' > "$OVL/lower1/base.txt"

printf 'LAYER2\n' > "$OVL/lower2/etc/version"
printf 'hello v2\n' > "$OVL/lower2/app/app.txt"
printf 'new in layer2\n' > "$OVL/lower2/new.txt"
```

挂载：

```bash
mount -t overlay overlay \
  -o "lowerdir=$OVL/lower2:$OVL/lower1,upperdir=$OVL/upper,workdir=$OVL/work" \
  "$OVL/merged"
```

检查：

```bash
cat "$OVL/merged/etc/version"   # LAYER2
cat "$OVL/merged/app/app.txt"  # hello v2
cat "$OVL/merged/base.txt"     # only in base
cat "$OVL/merged/new.txt"      # new in layer2
```

这就是 Image Layer Chain 的核心可见性规则：**相同路径采用更高可见层版本；不冲突的路径继续合并。**

### 实验 4.5-E 回退 / 验证

```bash
umount "$OVL/merged"
findmnt --mountpoint "$OVL/merged" || echo 'multi-layer overlay unmounted'
```

后续实验还需目录，因此只卸载，统一清理在 4.5-J。

---

## 4.5.9 Runtime Writable Layer 和 Image Layer 的生命周期不同

```text
Image Layers
→ Read-only / Immutable
→ 可共享 / 由 Image 生命周期管理

Container Writable Layer
→ Container 私有写入视图
→ 与此 Container 生命周期相关
```

例如：

```text
docker stop X
↓
docker start X
→ 同一个 Container 的 Writable State 通常保留

 docker rm X
↓
docker run same-image
→ 新 Container，新的 Writable State
```

**重要持久数据**（数据库、模型缓存等）不能默认只放在 Container Writable Layer；应考虑 Bind Mount、Named Volume 或外部存储。

## 4.5.10 为什么删除后 Image Size 不一定变小

经典 Dockerfile：

```dockerfile
FROM ubuntu:24.04
RUN create-a-1GB-file
RUN rm /the-1GB-file
```

逻辑：

```text
Layer A：Ubuntu
Layer B：新增 1GB 文件
Layer C：Whiteout 删除该文件

最终 Merged RootFS：看不到这个文件
但 Image Layer Chain：仍需要 Layer B 的原始数据
```

因此：

```text
Visible RootFS Contents
≠
Total Image Layer Storage
```

非常像 Git：后一个 Commit 删掉文件，旧 Commit 的历史对象仍可能存在。这只是概念类比，Container Image 不是 Git。

### 如何改善？

在**同一个** Filesystem-changing Build Step 内创建和删除临时文件，避免临时文件被提交到中间 Layer：

```dockerfile
RUN download-temp-file \
 && process-temp-file \
 && rm -f temp-file
```

经典：

```dockerfile
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*
```

比“前一个 RUN 下载、后一个 RUN 删除”更容易得到较小的最终 Image。

## 4.5.11 Multi-stage Build 的伏笔

```dockerfile
FROM golang AS builder
WORKDIR /app
COPY . .
RUN go build -o server .

FROM scratch
COPY --from=builder /app/server /server
ENTRYPOINT ["/server"]
```

思路：

```text
Build Stage:
Go Compiler / Source / Headers / Cache
         ↓ build
      server Binary
         ↓ COPY only result
Runtime Stage:
      server Binary only
```

前提是 Binary 与目标 Runtime RootFS 兼容（真正静态依赖、证书等），而不是“只要是 Go 就一定能在 scratch 运行”。后面 4.13 单独讲。

---

## 4.5.12 Image Manifest / Config / Layer Blob

OCI/Docker 兼容的镜像通常不只是“一个 tar”：

```text
Image Manifest
├─ Config Descriptor
└─ Layer Descriptor 1
   Layer Descriptor 2
   Layer Descriptor 3
```

**Manifest**：说明 Image 用了什么 Config 和哪些 Layer Descriptor。

**Image Config**：包含 `Env`、`Cmd`、`Entrypoint`、`User`、`WorkingDir`、Architecture/OS、RootFS Diff IDs、History 等。

**Layer Blob**：Registry/Content Store 中的 Layer 内容对象，可采用压缩格式存储。

### Digest vs DiffID

- **Descriptor Digest**：通常标识传输/存储的 Layer Blob（例如压缩后的内容）。
- **DiffID**：通常标识解压后的 Filesystem Diff 内容。

因此压缩对象身份与解压后 Diff 身份可能不同。当前只需知道存在这两个层次，无须背 OCI JSON 字段细节。

### Storage Driver / Snapshotter

运行时会把 Image Filesystem 内容准备成可使用的 Snapshot / Mount：

```text
Registry Blob
↓ Pull
Content Store
↓ Unpack
Snapshotter / Storage Driver
↓
Lower Image Data + Writable Layer
↓
Container RootFS
```

典型名称包括 OverlayFS Snapshotter、Docker overlay2 等，但具体磁盘布局随 Docker Desktop、Docker Engine、containerd、配置和版本而不同。**不要把 `/var/lib/docker/overlay2/...` 当作稳定的公共 API 手动修改。**

---

## 4.5.13 Build Cache 与 Dockerfile 顺序

**Cache Invalidation**：当某 Build Step 的输入发生变化，已缓存结果不再能安全复用。

推荐的 Python Dockerfile 组织思路：

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

为什么：

```text
requirements.txt 没变
↓
Dependency Install Step 可能复用缓存
↓
应用源代码变化
↓
只需重新处理较后面的构建步骤
```

反过来先 `COPY . .`，改一个应用文件就可能导致后续 Dependencies 的 Layer Cache Miss。

真实 Cache Key 还受 Build Context、Instruction、Env/Args、Mount/Secret 配置和 Builder 实现等影响；不是只看“这一行 Dockerfile 文本有没有改”。

## 4.5.14 Layer Sharing 与 Image Size

你将看到不同维度的 Size：

```text
Compressed Registry Size
Uncompressed Layer Size
Image Logical Size
Shared Layer Disk Usage
Private Layer Disk Usage
Container Writable Size
```

两个逻辑显示为 1GB 的 Image，可能共享 900MB Base，所以本地总体存储不一定是 2GB。

例子：

```text
Image A = Base 900MB + App A 100MB
Image B = Base 900MB + App B 100MB

合计唯一 Layer 数据约 1.1GB
而不是简单 2GB
```

此为理想化示例，实际还受压缩、Unpack、Snapshot 和 Filesystem Metadata 影响。

## 4.5.15 OverlayFS Copy-Up 的代价

一些 OverlayFS 模式对 Lower File 的首次修改会 Copy-Up 整个文件（细节与内核特性和文件操作有关），不能假定“只改 1Byte 就只复制 1Byte”。

所以对于：

```text
数据库文件
经常随机写的大文件
持续更新的缓存
```

使用 Container Writable Layer 不一定是理想方案。更合适的可持久化位置往往是 Volume 或外部 Storage（4.9 讲）。

---

## 实验 4.5-F：一次重做 Read / Copy-Up / Create / Whiteout

现在应处于隔离 Mount Namespace Shell，且上一组已卸载。清空 Upper/Work，使用两层 Lower：

```bash
rm -rf "$OVL/upper" "$OVL/work"
mkdir -p "$OVL/upper" "$OVL/work"
mount -t overlay overlay \
  -o "lowerdir=$OVL/lower2:$OVL/lower1,upperdir=$OVL/upper,workdir=$OVL/work" \
  "$OVL/merged"
```

**读取 Lower 文件：**

```bash
cat "$OVL/merged/base.txt"
```

**修改 Lower 文件触发 Copy-Up：**

```bash
printf 'modified by container\n' > "$OVL/merged/base.txt"
cat "$OVL/lower1/base.txt"   # 仍为 only in base
cat "$OVL/upper/base.txt"    # modified by container
```

**新建文件进入 Upper：**

```bash
printf 'runtime only\n' > "$OVL/merged/runtime.txt"
cat "$OVL/upper/runtime.txt"
```

**删除 Lower 文件产生 Whiteout 语义：**

```bash
rm "$OVL/merged/new.txt"
test ! -e "$OVL/merged/new.txt" && echo 'hidden'
cat "$OVL/lower2/new.txt"    # 底层仍有 new in layer2
```

### 实验 4.5-F 回退

```bash
umount "$OVL/merged"
rm -rf "$OVL/upper" "$OVL/work"
mkdir -p "$OVL/upper" "$OVL/work"
```

至此整个 Overlay 实验所有挂载均已卸载；RootFS 的 Lower 示例数据仍存在，等待最终清理。

---

## 实验 4.5-G：整个 OverlayFS 系列最终回退

**在隔离 Mount Namespace Shell 中先验证：**

```bash
findmnt --mountpoint "$OVL/merged" || echo 'unmounted'
exit
```

**回到正常 WSL Shell，删除唯一实验目录：**

```bash
if [ -n "${OVL:-}" ] && [ -d "$OVL" ]; then
  case "$OVL" in
    /tmp/ai-infra-overlay.*) sudo rm -rf -- "$OVL" ;;
    *) echo "Unexpected OVL path: $OVL; refusing to delete" >&2 ;;
  esac
fi
unset OVL
```

**回退验证：**

```bash
find /tmp -maxdepth 1 -name 'ai-infra-overlay.*' -print
findmnt | grep 'ai-infra-overlay' || echo 'no overlay lab mounts'
hostname
ip route
```

不应有本实验的 Mount、专用目录、服务或网络更改。

---

## 4.5.16 完整 Filesystem 链路

```text
Dockerfile
  FROM ubuntu
       ↓
Ubuntu Base Image Layers
       ↓
RUN / COPY filesystem-changing steps
       ↓
Additional Diff Layers
       ↓
Image Manifest + Config + Layer Blobs
       ↓
Image Pull / Unpack / Snapshotter
       ↓
Read-only Lower Image Layers
       +
Container Writable Upper Layer
       ↓
OverlayFS (or another supported snapshot strategy)
       ↓
Merged Container RootFS
       ↓
Mount Namespace / procfs / sysfs / device mounts / volumes
       ↓
Container Application Process
       ↓
System Calls
       ↓
Host Linux Kernel
       ↓
CPU / RAM / Storage / NIC / GPU
```

这张图把 **4.1～4.5** 全部串起来。

## 4.5 最重要的十五句话

1. Image 的核心是 Filesystem Layer Chain + Metadata。
2. 一层通常是文件系统变化的 Diff，不是整份 RootFS 副本。
3. `FROM` 继承 Base Image Layers + Configuration，不是继承 Kernel。
4. Content Digest 可以支持 Layer Sharing / 去重。
5. Dockerfile 一行不总等于一个 FS Layer。
6. OverlayFS 将 Lower、Upper 等组合为统一 Merged View。
7. Image Layer 通常 Read-only，Container 有自己的 Writable Layer。
8. 读 Lower 不复制；首次写入可触发 Copy-Up。
9. 新建文件通常直接进入 Upper。
10. 删除 Lower File 需要 Whiteout 语义，Lower Data 没消失。
11. 在下一层删除旧 Layer 的 1GB 数据，未必会让 Image 变小。
12. 临时大文件尽量在同一 Build Step 内清理。
13. Multi-stage Build 可以让 Compiler/Source/Build Cache 不进入最终 Runtime Image。
14. Persisted Data 应考虑 Volume/External Storage，而不是只存在 Container Writable Layer。
15. 最终链路是 Image Layers → RootFS → Container Process → Host Linux Kernel。

---

# 综合复盘：从 Dockerfile 到 Linux Process

## 你现在应该能够自行回答的八个问题

### Q1：为什么 Image 需要 `FROM ubuntu`，但运行时仍用 Host Linux Kernel？

`FROM ubuntu` 主要提供 Ubuntu User-space RootFS、依赖文件和 Image Config；Linux Container 的应用通过 syscall 与承载它的 Host Kernel 交互，并没有独立启动 Ubuntu Kernel。

### Q2：为什么 `/etc/os-release` 和 `uname -r` 可能对应不同版本？

前者是 RootFS 静态文件，后者查询正在运行的 Kernel。

### Q3：`chroot` 为什么不等于 Container？

它仅改变路径根视图，不能自动隔离 PID、NetNS、Mount Namespace、资源和安全策略，也不能当可靠安全边界。

### Q4：Container 的 CPU Limit 谁真正执行？

Linux Kernel 的 cgroup CPU Controller 和 Scheduler，而不是 Docker 在应用层每秒循环测量。

### Q5：`docker exec` 为什么不是启动一个新的 VM？

它是在现有 Container 的隔离与管理环境中启动新的 Linux Process。

### Q6：Container 内修改 `/app/config`，Image 原文件会被改变吗？

通常不会；若使用 OverlayFS，可能先把 Lower File Copy-Up 到 Container Writable Upper Layer，再在那里修改。

### Q7：为什么下一层 `rm` 一个 1GB 文件，镜像仍可能很大？

删除操作只在新 Diff 中产生 Whiteout 语义，旧 Layer 的 Blob 内容仍在 Layer Chain 中。

### Q8：为什么 Docker Desktop 里的 `eth0`/bridge 不一定在 Ubuntu WSL 里看见？

Docker Engine/Container 实际所在 Linux 环境与用户 Ubuntu WSL 的 Network Namespace 不一定相同，CLI 的可用性不代表二者共享同一个 Linux 网络视图。

---

# 完整术语表

| 术语 | 定义 / 当前理解 | 第一次系统学习 |
|---|---|---|
| Container | Linux Process + 隔离、资源约束、RootFS 和 Runtime 管理的工程抽象 | 4.1 |
| Virtual Machine | 具有独立 Guest Kernel 的虚拟机 | 4.1 |
| Namespace | Kernel 提供的局部系统视图 | 4.1 |
| PID Namespace | Process ID 的局部视图及其层级 | 4.1 / 4.2 |
| Network Namespace | 独立 Network Stack 视图 | 4.1 / 4.2 |
| Mount Namespace | 独立 Mount Tree 视图 | 4.1 / 4.2 |
| UTS Namespace | hostname 等 UTS 信息的隔离 | 4.1 / 4.2 |
| IPC Namespace | 部分 IPC Resources 的隔离 | 4.1 / 4.2 |
| User Namespace | UID/GID 的隔离和映射 | 4.1 / 4.2 |
| Cgroup Namespace | cgroup hierarchy 的可见性隔离 | 4.1 |
| Namespace Handle | `/proc/PID/ns/*` 等 Kernel 暴露的引用 | 4.2 |
| unshare | 创建/脱离 Namespace | 4.2 |
| nsenter | 加入已有 Namespace 并启动新 Process | 4.2 |
| lsns | 列出/整理 Namespace 信息 | 4.2 |
| procfs | Kernel 生成进程/系统信息的虚拟 FS | 4.2 / 4.4 |
| sysfs | Kernel 生成 Device/Object 信息的虚拟 FS | 4.4 |
| tmpfs | 基于内存的临时 Filesystem | 4.2 |
| Mount Propagation | Mount Event 在 Mount Tree / NS 之间传播的规则 | 4.2 |
| Rootless | 不依赖宿主 initial namespace root 来运行/管理容器的模式 | 4.2 |
| cgroup | Control Group；资源统计、控制和分组 | 4.3 |
| Unified Hierarchy | cgroup v2 的统一树状层级 | 4.3 |
| Controller | CPU/Memory/PIDs 等资源控制子系统 | 4.3 |
| cgroup.procs | 一组 Process 的 cgroup Membership 接口 | 4.3 |
| cpu.max | CPU 配额/周期接口 | 4.3 |
| cpu.weight | CPU 竞争相对权重 | 4.3 |
| cpu.stat | CPU 用量与 Throttling 计数 | 4.3 |
| Throttling | CPU 配额耗尽导致暂时限制执行 | 4.3 |
| memory.current | 当前计费内存用量 | 4.3 |
| memory.max | Memory Hard Limit | 4.3 |
| memory.high | 内存高压阈值 | 4.3 |
| memory.events | 内存限制/OOM 事件计数 | 4.3 |
| cgroup OOM | cgroup 资源限制引发的 Out-of-Memory | 4.3 |
| pids.max | Task 数量 Hard Limit | 4.3 |
| pids.current | 当前 Task 数量 | 4.3 |
| cgroup.kill | 结束一个 cgroup 范围内 Tasks 的接口 | 4.3 |
| RootFS | Process 看到的 `/` 文件树 | 4.4 |
| Kernel Space | Kernel 核心代码所在执行环境 | 4.4 |
| User Space | 普通应用、Libc、Runtime、工具 | 4.4 |
| Syscall / ABI | User Space 与 Kernel 交互的接口约定 | 4.4 |
| glibc | GNU C Library | 4.4 |
| musl | Alpine 等常见的 C Library | 4.4 |
| ELF Dynamic Loader | 启动动态 ELF 依赖库的加载器 | 4.4 |
| Base Image | 初始 Layer Chain + Metadata | 4.4 |
| scratch | 逻辑上的空基础镜像 | 4.4 |
| chroot | 改变 Process 的路径根目录 | 4.4 |
| pivot_root | 替换 Mount Namespace 中的 Root Mount | 4.4 |
| Image Layer | 文件系统 Diff Layer | 4.5 |
| OverlayFS | 多个文件树的 Union/Merged FS | 4.5 |
| lowerdir | OverlayFS 底层只读数据来源 | 4.5 |
| upperdir | OverlayFS 可写上层 | 4.5 |
| workdir | OverlayFS 内部工作目录 | 4.5 |
| merged | OverlayFS 合并视图 | 4.5 |
| Copy-on-Write | 首次写入时才复制 | 4.5 |
| Copy-Up | Lower 文件复制/提升到 Upper | 4.5 |
| Whiteout | 遮盖下层文件的删除语义 | 4.5 |
| Opaque Directory | 阻止下层目录内容合并的语义 | 4.5 |
| Content Addressing | 用内容 Digest 识别对象 | 4.5 |
| Digest | 内容 Hash 标识 | 4.5 |
| Manifest | 描述 Config 与 Layers 的清单 | 4.5 |
| Image Config | ENTRYPOINT / CMD / ENV 等镜像元数据 | 4.5 |
| Layer Blob | Registry/Content Store 保存的 Layer 数据对象 | 4.5 |
| DiffID | Uncompressed Filesystem Diff 的内容身份 | 4.5 |
| Deduplication | 共享相同数据、避免重复存储 | 4.5 |
| Snapshotter | 准备/管理可供 Container 使用的 FS Snapshot | 4.5 |
| Cache Invalidation | Build 输入变化导致缓存失效 | 4.5 |
| Writable Layer | Container 私有写入的文件层 | 4.5 |
| Volume | 与 Container Writable Layer 可分离的存储资源（详见 4.9） | 4.5 |

---

# 课程目录

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
    ├─ Container 与 Linux Process
    ├─ Namespace、cgroup、RootFS
    ├─ Container vs VM
    ├─ Image vs Container
    ├─ docker run / exec 的本质
    ├─ Docker Desktop 与 WSL2
    └─ Container Security Mechanisms 初步

✅ 4.2 Linux Namespace 深入
    ├─ unshare / nsenter / lsns
    ├─ /proc/PID/ns
    ├─ PID / UTS / Mount / Network / User / IPC Namespace
    ├─ PID 1 与 --fork
    ├─ procfs / Mount Propagation
    ├─ Container-like Shell
    ├─ Pod Namespace Sharing 伏笔
    └─ 逐组实验回退

✅ 4.3 cgroup：CPU / Memory / PIDs
    ├─ v1 / v2 / Unified Hierarchy
    ├─ Resource Controllers
    ├─ cgroup.procs
    ├─ cpu.max / cpu.weight / cpu.stat
    ├─ CPU Throttling
    ├─ memory.current / max / high / events
    ├─ cgroup OOM
    ├─ pids.max / current / events
    ├─ Hierarchical Control
    ├─ systemd 与 cgroup
    ├─ 容器监控指标来源
    └─ systemd 临时 Unit 实验 + 回退

✅ 4.4 Container RootFS / Mount / chroot / pivot_root
    ├─ Kernel Space / User Space
    ├─ Base Image 与 Host Linux Kernel 的关系
    ├─ FROM / scratch
    ├─ /etc/os-release vs uname
    ├─ System Call ABI
    ├─ glibc / musl / ELF Loader
    ├─ RootFS / chroot
    ├─ procfs / sysfs / dev
    ├─ Mount Namespace + PID Namespace + RootFS
    ├─ pivot_root
    ├─ CUDA Container 的 Kernel/User-space 分工
    └─ 临时 RootFS 实验 + 回退

✅ 4.5 Docker Image / Layer / OverlayFS
    ├─ Image Layer Diff / Content Addressing
    ├─ FROM Layer Chain / Dockerfile 语义
    ├─ lowerdir / upperdir / workdir / merged
    ├─ Copy-on-Write / Copy-Up
    ├─ Whiteout / Opaque Directory
    ├─ 多 Lower Layer 优先级
    ├─ Writable Layer 生命周期
    ├─ 删除大文件为什么未必缩小 Image
    ├─ Multi-stage Build 伏笔
    ├─ Registry Manifest / Config / Layer Blob / DiffID
    ├─ Build Cache / Deduplication
    └─ OverlayFS 实验 + 回退

⬜ 4.6 Docker Engine / containerd / runc / OCI
⬜ 4.7 Container Network：NetNS / veth / bridge
⬜ 4.8 Docker Port Mapping / NAT
⬜ 4.9 Volume / Bind Mount / Container Storage
⬜ 4.10 Container PID 1 / Signal / Zombie
⬜ 4.11 Container Security 基础
⬜ 4.12 Dockerfile / Build Context / Build Cache
⬜ 4.13 Multi-stage Build
⬜ 4.14 Docker 基础排障
⬜ 4.15 Container 综合实验
```

## 下一节预告：4.6 Docker Engine / containerd / runc / OCI

```text
docker CLI
    ↓
Docker Engine / dockerd
    ↓
containerd
    ↓
containerd-shim / OCI Runtime（如 runc）
    ↓
Linux Kernel：Namespaces / cgroups / Mount / Process
```

要回答：每一层做什么？OCI Image Spec / Runtime Spec 是什么？为什么 Kubernetes 可以不依赖 Docker Engine 直接运行 OCI Image？

---

**第 4 章 4.1～4.5 离线笔记结束。**
