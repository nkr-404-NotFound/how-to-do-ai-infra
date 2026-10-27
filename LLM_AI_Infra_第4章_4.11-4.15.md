# LLM / AI Infra 第 4 章（4.11–4.15）
## Container Security → Dockerfile / BuildKit → Multi-stage → Troubleshooting → 综合实验

> 文件名：`LLM_AI_Infra_第4章_4.11-4.15.md`  
> 适用范围：第 4 章 4.11～4.15  
> 状态：第 4 章已完成  
> 学习方式：新术语先定义；概念 → 机制 → 实验 → 回退 → 排障

---

# 目录

- [4.11 Container Security 基础](#411-container-security-基础)
- [4.12 Dockerfile / Build Context / BuildKit / Build Cache](#412-dockerfile--build-context--buildkit--build-cache)
- [4.13 Multi-stage Build](#413-multi-stage-build)
- [4.14 Docker 系统化排障](#414-docker-系统化排障)
- [4.15 Container 综合实验](#415-container-综合实验)
- [第 4 章总复盘](#第-4-章总复盘)
- [第 4 章收官小测与答案](#第-4-章收官小测与答案)
- [课程全局进度](#课程全局进度)

---

# 4.11 Container Security 基础

## 4.11.1 先建立安全模型

Container 不是一个天然“安全沙箱”。它本质上仍然是 Host Kernel 上的 Linux Process，只是被多层机制约束：

```text
Container Process
    │
    ├─ Namespace        → 看见什么
    ├─ cgroup           → 能用多少资源
    ├─ UID / GID        → 以谁的身份运行
    ├─ Capabilities     → root 权限拆分后的能力
    ├─ seccomp          → 哪些 syscall 可以调用
    ├─ LSM              → AppArmor / SELinux 等额外强制策略
    ├─ Mount flags      → ro / noexec / nosuid 等
    ├─ Devices          → 能访问哪些设备
    └─ RootFS           → 能看到和修改哪些文件
```

核心原则：

> **Least Privilege（最小权限）**：只给应用完成工作所需的最少权限、最少可写路径、最少设备、最少系统调用和最少资源。

## 4.11.2 UID/GID 与 Non-root

Linux 最终看的是数字 UID/GID。Container 中 `uid=0(root)` 仍表示 UID 0，但 UID 0 不等于拥有 Host 上所有 root 能力，因为还可能受到 Capability、seccomp、LSM、User Namespace、Mount、Device 等限制。

生产服务若不需要 root，应尽量：

```dockerfile
USER 10001:10001
```

或：

```bash
docker run --user 10001:10001 image
```

Non-root 是重要防线，但不是完整安全边界。

## 4.11.3 Linux Capabilities

Capabilities 把传统 root 权力拆成多个独立能力，例如：

```text
CAP_NET_BIND_SERVICE
CAP_NET_ADMIN
CAP_SYS_ADMIN
CAP_CHOWN
CAP_SETUID
CAP_SETGID
CAP_SYS_PTRACE
```

查看进程 Capability：

```bash
grep -E 'Cap(Inh|Prm|Eff|Bnd|Amb)' /proc/1/status
```

Docker 侧：

```bash
docker inspect \
  --format \
  'CapAdd={{json .HostConfig.CapAdd}} CapDrop={{json .HostConfig.CapDrop}}' \
  <container>
```

如果应用不需要特殊能力：

```bash
docker run \
  --cap-drop ALL \
  image
```

需要时只按需加回：

```bash
docker run \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \
  image
```

## 4.11.4 `--privileged` 为什么危险

`--privileged` 会显著放宽 Container 对 Host 的访问能力。排障看到 `Operation not permitted` 时，不应第一反应上 `--privileged`。

正确顺序：

```text
UID/GID
↓
Mount 权限
↓
Capability
↓
seccomp
↓
LSM
↓
Device
```

只添加真正缺少的权限。

## 4.11.5 seccomp

**seccomp（Secure Computing Mode）** 是 Linux syscall 过滤机制。Application 与 Kernel 交互依赖系统调用，例如：

```text
openat()
read()
write()
socket()
clone()
mount()
ptrace()
```

seccomp 可以定义哪些 syscall 被允许或拒绝。

查看：

```bash
grep '^Seccomp:' /proc/1/status
```

## 4.11.6 LSM：AppArmor / SELinux

**LSM = Linux Security Modules**。常见实现：

```text
AppArmor
SELinux
```

它们可以在 UID/GID 权限之外继续限制文件、设备、对象访问。因此 `Permission denied` / `Operation not permitted` 不一定只是 chmod/chown 问题。

## 4.11.7 `no-new-privileges`

```bash
docker run \
  --security-opt no-new-privileges=true \
  image
```

核心语义：进程及其后代不能通过 `execve()` 等路径获得新的特权，降低 setuid/file capability 等路径的提权空间。

## 4.11.8 Read-only RootFS + tmpfs + Volume

生产常见：

```bash
docker run \
  --read-only \
  --tmpfs /tmp:rw,nosuid,noexec,size=64m \
  --mount type=volume,src=app-data,dst=/data \
  image
```

理想布局：

```text
/
read-only

/tmp
explicit writable tmpfs

/data
explicit writable persistent storage
```

原则：应用只需要 `/data` 可写，就只开放 `/data`，而不是让整个 RootFS 可写。

## 4.11.9 User Namespace / Rootless

User Namespace 可以把 Container 内 UID 映射到 Host 上不同 UID：

```text
Container UID 0
        │
        │ user namespace mapping
        ▼
Host UID 100000+
```

Rootless Docker/Container Runtime 的目标则是让 daemon/runtime 本身也不依赖 Host root。它能降低 Host 风险，但也可能带来网络、设备和兼容性限制。

## 4.11.10 Defense in Depth

生产安全通常是多层叠加：

```text
Non-root
+
cap-drop ALL
+
按需 cap-add
+
seccomp
+
AppArmor/SELinux
+
no-new-privileges
+
read-only rootfs
+
显式 writable mount
+
resource limits
+
network policy
```

没有哪一项单独等于“安全”。

## 4.11.11 综合安全实验

```bash
C411="ai-infra-411-$$"

docker run \
  -d \
  --name "$C411" \
  --user 10001:10001 \
  --read-only \
  --tmpfs /tmp:rw,nosuid,noexec,size=16m \
  --cap-drop ALL \
  --security-opt no-new-privileges=true \
  busybox:1.36 \
  sleep 600
```

检查 Runtime 配置：

```bash
docker inspect \
  "$C411" \
  --format '
User={{.Config.User}}
Readonly={{.HostConfig.ReadonlyRootfs}}
Privileged={{.HostConfig.Privileged}}
CapDrop={{json .HostConfig.CapDrop}}
SecurityOpt={{json .HostConfig.SecurityOpt}}
Tmpfs={{json .HostConfig.Tmpfs}}
'
```

测试 RootFS 与 tmpfs：

```bash
docker exec \
  "$C411" \
  sh -c '
    touch /should-fail 2>/dev/null \
      || echo "rootfs read-only"

    echo ok >/tmp/works
    cat /tmp/works
  '
```

查看 Kernel effective state：

```bash
docker exec \
  "$C411" \
  sh -c '
    grep -E \
      "^(Uid|Gid|CapInh|CapPrm|CapEff|CapBnd|CapAmb|NoNewPrivs|Seccomp):" \
      /proc/1/status
  '
```

### 回退

```bash
docker rm -f "$C411"
unset C411
```

验证：

```bash
docker ps -a \
  --format '{{.Names}}' \
  | grep '^ai-infra-411-' \
  || echo "4.11 clean"
```

## 4.11.12 核心结论

1. Container Security 是多层约束，不是单一 Namespace。
2. UID 0 与 Capability 是不同维度。
3. 生产 Runtime 尽量 Non-root。
4. `--cap-drop ALL` 后按需加权限，比 `--privileged` 好。
5. seccomp 限制 syscall。
6. AppArmor/SELinux 属于 LSM。
7. `no-new-privileges` 限制后续权限提升。
8. RootFS 可只读，真正需要写的目录单独 Mount。
9. User Namespace 可以做 UID 映射。
10. Rootless 进一步降低 daemon/runtime 权限。
11. 安全依赖 Defense in Depth。
12. 权限报错应分层排查，而不是 `chmod 777` 或 `--privileged`。

---

# 4.12 Dockerfile / Build Context / BuildKit / Build Cache

## 4.12.1 Dockerfile 的生产级心智模型

Dockerfile 不只是“一串 Shell 命令”，而是：

```text
Dockerfile
=
Build Graph Description
+
Filesystem Transformation
+
Image Runtime Metadata
+
Dependency Boundary
+
Cache Strategy
+
Supply-chain Inputs
+
Runtime Contract
```

现代构建链：

```text
Project Files
    │
    ▼
Build Context
    │
    ▼
Dockerfile Frontend
    │
    ▼
LLB
    │
    ▼
BuildKit Solver
    │
    ├─ RUN
    ├─ COPY / ADD
    ├─ cache mount
    ├─ secret mount
    └─ stage DAG
    │
    ▼
Image Layers + Config
```

## 4.12.2 Build Context

```bash
docker build .
```

最后的 `.` 表示 **Build Context**，即 Builder 可以访问的文件集合，不是“Dockerfile 所在目录”。

例如：

```text
project/
├─ src/
├─ requirements.txt
└─ docker/
   └─ prod.Dockerfile
```

执行：

```bash
cd project

docker build \
  -f docker/prod.Dockerfile \
  .
```

则：

```text
Dockerfile = docker/prod.Dockerfile
Context    = project/
```

`COPY` Source 相对于 Context Root。

## 4.12.3 Context 是 Trust Boundary

Builder 不能通过 `COPY ../../...` 任意读取 Context 外 Host 文件。Context 同时也是安全边界和 Cache Input。

## 4.12.4 `.dockerignore`

典型：

```dockerignore
.git/
.env
.env.*

.venv/
venv/
__pycache__/
*.pyc

node_modules/

dist/
build/

logs/
*.log

models/
datasets/
checkpoints/

secrets/
*.pem
*.key

.idea/
.vscode/
.DS_Store
```

价值：

```text
Context 更小
Cache 更稳定
Secret 暴露面更小
```

AI 项目尤其要排除大型 Model / Dataset / Checkpoint。

## 4.12.5 `FROM`

```dockerfile
FROM python:3.13-slim
```

继承的是 userspace/image layers，不是新的 Kernel。

生产构建要控制 Base 漂移：

```text
Tag
→ 人类友好

Digest
→ content-addressed
```

## 4.12.6 `ARG` vs `ENV`

```dockerfile
ARG APP_VERSION=dev
ENV APP_ENV=production
```

```text
ARG
→ build-time variable

ENV
→ 进入 image config
→ runtime 默认环境变量
```

Scope 例子：

```dockerfile
ARG VERSION=3.13

FROM python:$VERSION

ARG VERSION
RUN echo "$VERSION"
```

## 4.12.7 Secret 不能用 ARG / ENV

错误：

```dockerfile
ARG TOKEN
ENV PASSWORD=secret
```

正确：

```dockerfile
RUN --mount=type=secret,id=api_token \
    TOKEN="$(cat /run/secrets/api_token)" \
    && command "$TOKEN"
```

Build：

```bash
docker build \
  --secret id=api_token,src=token.txt \
  .
```

Secret Mount 只负责安全交付；如果 Dockerfile 主动把 Secret 写进文件或打印到日志，仍会泄漏。

## 4.12.8 SSH Mount

```dockerfile
RUN --mount=type=ssh \
    git clone git@github.com:company/private.git
```

```bash
docker buildx build \
  --ssh default \
  .
```

不要把 Private Key `COPY` 进 Layer 再删除。

## 4.12.9 `WORKDIR`

```dockerfile
WORKDIR /app
```

不要依赖 Base Image 隐含工作目录。

## 4.12.10 `COPY`

```dockerfile
COPY requirements.txt ./
COPY src/ ./src/

COPY --chown=10001:10001 src/ /app/src/
COPY --chmod=755 entrypoint.sh /usr/local/bin/
```

`COPY --link`、`COPY --exclude` 属于更高级的 BuildKit 能力。

## 4.12.11 `ADD`

普通 Local File 优先 `COPY`。`ADD` 更适合 Remote/Git/Archive/Checksum 场景。

```dockerfile
ADD \
  --checksum=sha256:... \
  https://example.com/tool.tar.gz \
  /tmp/tool.tar.gz
```

## 4.12.12 Build Cache

```text
Build Operation
+
Inputs
+
Parent State
↓
Cache Key
```

Internet 上 Package Repository 变了，BuildKit 不会自动知道。

坏：

```dockerfile
RUN apt-get update
RUN apt-get install -y curl
```

好：

```dockerfile
RUN apt-get update \
 && apt-get install -y curl \
 && rm -rf /var/lib/apt/lists/*
```

## 4.12.13 Cache Boundary

坏：

```dockerfile
COPY . .
RUN pip install -r requirements.txt
```

好：

```dockerfile
COPY requirements.txt ./

RUN pip install \
  -r requirements.txt

COPY src/ ./src/
```

原则：**稳定、昂贵、低频变化的 Step 靠前；高频 Source 靠后。**

## 4.12.14 BuildKit Cache Mount

```dockerfile
RUN \
  --mount=type=cache,target=/root/.cache/pip \
  pip install -r requirements.txt
```

Go：

```dockerfile
RUN \
  --mount=type=cache,target=/go/pkg/mod \
  --mount=type=cache,target=/root/.cache/go-build \
  go build ...
```

两级 Cache：

```text
Layer Cache
→ 整个 RUN 命中则不执行

Cache Mount
→ RUN 重执行时仍复用下载/编译缓存
```

## 4.12.15 Build Mount 类型

```text
type=cache
type=secret
type=ssh
type=bind
type=tmpfs
```

这些是 Build-time Mount，不是 Runtime Mount。

## 4.12.16 ENTRYPOINT / CMD

推荐 Exec Form：

```dockerfile
ENTRYPOINT ["python", "-m", "myapp"]
CMD ["--port", "8000"]
```

```text
ENTRYPOINT
→ 主 executable

CMD
→ 默认 arguments
```

长期服务避免 Shell-form ENTRYPOINT，因为可能引入 PID1 / Signal 问题。

## 4.12.17 EXPOSE / STOPSIGNAL / HEALTHCHECK

```dockerfile
EXPOSE 8000
STOPSIGNAL SIGTERM
```

`EXPOSE` 只是 Metadata，不等于 `-p`。

Healthcheck：

```dockerfile
HEALTHCHECK \
  --interval=30s \
  --timeout=3s \
  --retries=3 \
  CMD python -c \
  'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health")'
```

`unhealthy` 不等于 Engine 必然自动 Restart。

## 4.12.18 Multi-platform 基础

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  .
```

常见变量：

```text
BUILDPLATFORM
TARGETPLATFORM
TARGETOS
TARGETARCH
```

Go：

```dockerfile
FROM --platform=$BUILDPLATFORM golang:1.25 AS build

ARG TARGETOS
ARG TARGETARCH

RUN GOOS=$TARGETOS \
    GOARCH=$TARGETARCH \
    go build ...
```

## 4.12.19 生产 Dockerfile 常见反模式

```text
COPY . . 放最前
没有 .dockerignore
ARG TOKEN / ENV PASSWORD
apt-get update 和 install 分开
Builder toolchain 留在 runtime
运行时 root
Shell-form ENTRYPOINT
COPY private key 再 rm
curl latest | sh
model/checkpoint/dataset 无脑 COPY 进 image
chmod -R 777
盲目 Alpine
```

## 4.12.20 4.12 参考模板

```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.13-slim

ARG APP_VERSION=dev

LABEL \
  org.opencontainers.image.title="ai-api" \
  org.opencontainers.image.version=$APP_VERSION

ENV \
  PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt ./

RUN \
  --mount=type=cache,target=/root/.cache/pip \
  pip install -r requirements.txt

RUN useradd \
      --uid 10001 \
      --create-home \
      appuser

COPY \
  --chown=10001:10001 \
  src/ \
  ./src/

USER 10001:10001

EXPOSE 8000
STOPSIGNAL SIGTERM

ENTRYPOINT ["python", "-m", "src.server"]
CMD ["--host", "0.0.0.0", "--port", "8000"]
```

回退原则：只删除精确实验资源，不执行全局 prune。

---

# 4.13 Multi-stage Build

## 4.13.1 核心：Artifact Boundary

```text
Source
  │
  ▼
Builder
compiler / headers / source / cache / secret
  │
  │ produce
  ▼
Artifact Boundary
  │
  ▼
Runtime
only required runtime dependencies
```

## 4.13.2 最简单示例

```dockerfile
FROM golang:1.25 AS build

WORKDIR /src
COPY . .

RUN go build \
    -o /out/server \
    ./cmd/server

FROM debian:bookworm-slim AS production

COPY \
  --from=build \
  /out/server \
  /usr/local/bin/server

ENTRYPOINT ["/usr/local/bin/server"]
```

最终 Runtime 不自动包含 Compiler、Source、Build Cache。

## 4.13.3 Stage 与 `COPY --from`

每个 `FROM` 创建独立 Stage，具有自己的 RootFS / Build State。

```dockerfile
COPY \
  --from=build \
  /out/server \
  /server
```

Source 从 Source Stage 的 `/` 解析，不从其 `WORKDIR` 解析。因此推荐最终产物统一输出 `/out`。

## 4.13.4 `FROM previous-stage` vs `COPY --from`

```dockerfile
FROM build AS test
```

表示继承整个 Build Stage。

```dockerfile
COPY --from=build /out/app /app
```

只复制明确 Artifact。

如果生产写：

```dockerfile
FROM build AS production
```

通常意味着 Compiler/Source/Toolchain 也被继承，要警惕。

## 4.13.5 Stage DAG / `--target`

```text
             base
           /      \
        deps      lint
          │
          ▼
        build
       /  |  \
    test debug artifact
              │
              ▼
          production
```

Build：

```bash
docker build --target test .
docker build --target debug .
docker build --target production .
```

默认 Target 是最后一个 Stage，所以通常把 Production 放最后。

## 4.13.6 Go + scratch

```dockerfile
FROM golang:1.25 AS build

WORKDIR /src
COPY . .

RUN CGO_ENABLED=0 \
    go build \
      -trimpath \
      -ldflags="-s -w" \
      -o /out/app \
      .

FROM scratch AS production

COPY \
  --from=build \
  --chmod=0555 \
  /out/app \
  /app

USER 10001:10001
ENTRYPOINT ["/app"]
```

`scratch` 几乎没有 shell、libc、CA、timezone 数据。

## 4.13.7 CGO / glibc / musl

`CGO_ENABLED=1` 可能引入 glibc/libstdc++ 等动态依赖。

Builder Debian/glibc、Runtime Alpine/musl 是经典 ABI 不匹配场景。

检查：

```bash
file /out/app
ldd /out/app
```

文件存在但执行 `no such file or directory` 时，要怀疑 ELF Dynamic Loader。

## 4.13.8 Dependency Closure

**Dependency Closure** = Artifact 运行所需的全部依赖集合。

```text
app
↓
libfoo.so
↓
libbar.so
↓
glibc
```

只复制 `app` 不等于依赖完整。

## 4.13.9 scratch vs distroless

```text
scratch
→ 几乎空

distroless
→ 只保留 Runtime 所需 userspace
→ 通常无 shell / package manager
```

工程目标：**最小必要 Runtime，不是数学意义最小 Image。**

## 4.13.10 Debug / Test / Production

```dockerfile
FROM runtime-base AS debug
RUN apt-get update \
 && apt-get install -y curl procps strace \
 && rm -rf /var/lib/apt/lists/*

FROM runtime-base AS production
USER 10001:10001
ENTRYPOINT ["/usr/local/bin/server"]
```

Test Stage：

```dockerfile
FROM build AS test
RUN go test ./...
```

注意：Test Stage 存在不等于 Production Build 一定会跑 Test，CI 应显式 `--target test`。

## 4.13.11 Python Wheel Builder

```dockerfile
FROM python:3.13-slim AS builder

WORKDIR /build

RUN apt-get update \
 && apt-get install -y build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src/ ./src/

RUN \
  --mount=type=cache,target=/root/.cache/pip \
  pip wheel \
    --wheel-dir /wheels \
    .

FROM python:3.13-slim AS production

COPY --from=builder /wheels /wheels

RUN pip install \
      --no-index \
      --find-links=/wheels \
      myapp \
 && rm -rf /wheels
```

Builder/Runtime 必须兼容 Python ABI、Architecture、libc 和 Native Extensions。

## 4.13.12 Multi-platform + Cross Compile

```dockerfile
FROM \
  --platform=$BUILDPLATFORM \
  golang:1.25 \
  AS build

ARG TARGETOS
ARG TARGETARCH

RUN CGO_ENABLED=0 \
    GOOS=$TARGETOS \
    GOARCH=$TARGETARCH \
    go build \
      -o /out/app \
      .
```

CGO/C/C++/CUDA Cross Compile 还需要目标架构 compiler、headers、libc、linker。

## 4.13.13 CUDA / PyTorch Multi-stage 思路

```text
CUDA devel image
├─ nvcc
├─ headers
├─ compiler
└─ build custom op
      │
      ▼
 wheel / .so / binary
      │
      ▼
CUDA runtime image
├─ runtime libraries
├─ Python/PyTorch
└─ app artifact
```

需要同时考虑：

```text
CPU arch
libc
Python ABI
PyTorch ABI
CUDA version
compiler ABI
GPU SM architecture
```

Model Weight 一般继续与 Application Image 生命周期分离。

## 4.13.14 Allowlist Artifact Assembly

Builder 可以有：

```text
secret
cache
compiler
source
tests
```

Final 只 COPY 明确 Artifact：

```text
/out/app
/out/static
/out/wheels
```

不要：

```dockerfile
COPY --from=builder / /
```

## 4.13.15 Build Once / Test Same Artifact

理想：

```text
Source
↓
Build Artifact A
↓
Test A
↓
Package A
↓
Deploy A
```

避免 Test 一个 Artifact，Release 时重新构建另一个不完全相同的 Artifact。

## 4.13.16 Static C 综合实验

```bash
LAB=$(mktemp -d /tmp/ai-infra-413-cbuild.XXXXXX)
cd "$LAB"
```

```c
#include <stdio.h>

int main(void) {
    puts("hello from multi-stage");
    return 0;
}
```

Dockerfile：

```dockerfile
FROM alpine:3.23 AS build

RUN apk add \
      --no-cache \
      build-base

WORKDIR /src
COPY hello.c .

RUN cc \
      -static \
      -O2 \
      -o /out \
      hello.c

FROM scratch AS production

COPY --from=build /out /hello
ENTRYPOINT ["/hello"]
```

Build：

```bash
IMG413_C="ai-infra-413-c:lab"

docker build \
  -t "$IMG413_C" \
  .
```

运行：

```bash
docker run --rm "$IMG413_C"
```

验证 scratch 没 shell：

```bash
docker run \
  --rm \
  --entrypoint /bin/sh \
  "$IMG413_C"
```

### 回退

```bash
docker image rm "$IMG413_C"
cd /
rm -rf "$LAB"
unset LAB
unset IMG413_C
```

---

# 4.14 Docker 系统化排障

## 4.14.1 核心：先定位层，再选工具

```text
Build
Image
Container Lifecycle
Process
Resource
Filesystem
Network
Security
Docker Engine/Desktop/WSL
```

第一轮：

```bash
docker version
docker context show
docker ps -a
docker inspect <container>
docker logs <container>
```

## 4.14.2 Client / Server / Context

`docker version` 同时看 Client 和 Server。只有 Client 没有 Server 时，应优先排 Engine/Context/Desktop。

```bash
docker context show

docker context inspect \
  "$(docker context show)"
```

要避免“以为在看本地，实际连着 remote context”。

## 4.14.3 Docker Desktop + WSL 边界

Ubuntu WSL 中 `docker CLI` 可以连接 Docker Desktop backend，因此 Ubuntu WSL 中看不到 `dockerd/containerd/docker0/veth` 不代表 Docker 没运行。

优先使用：

```text
docker inspect
docker top
docker stats
docker network inspect
```

## 4.14.4 `docker ps -a` 与 `inspect`

```bash
docker inspect \
  --format '
Name={{.Name}}
Status={{.State.Status}}
Running={{.State.Running}}
Paused={{.State.Paused}}
Restarting={{.State.Restarting}}
OOMKilled={{.State.OOMKilled}}
Dead={{.State.Dead}}
Pid={{.State.Pid}}
ExitCode={{.State.ExitCode}}
Error={{.State.Error}}
StartedAt={{.State.StartedAt}}
FinishedAt={{.State.FinishedAt}}
RestartCount={{.RestartCount}}
' \
  <container>
```

## 4.14.5 常见 Exit Code

```text
0   → 正常结束
1   → 通用应用错误
126 → 找到命令但无法执行
127 → command not found
137 → 128 + SIGKILL(9)
143 → 128 + SIGTERM(15)
```

137 不能直接等于 OOM；要结合 `OOMKilled`、memory limit、events、cgroup。

## 4.14.6 `docker logs`

主要看到 stdout/stderr。

```bash
docker logs \
  --tail 200 \
  --since 10m \
  --timestamps \
  <container>
```

如果应用只写文件日志，`docker logs` 为空并不意味着应用没日志。

## 4.14.7 `docker events`

适合观察：

```text
create
start
health_status
oom
die
restart
destroy
```

特别适合 Crash Loop / OOM / Restart / Health Timeline。

## 4.14.8 Restart Loop

```bash
docker inspect \
  --format '
RestartCount={{.RestartCount}}
Policy={{.HostConfig.RestartPolicy.Name}}
ExitCode={{.State.ExitCode}}
Error={{.State.Error}}
' \
  container
```

Restart Policy 往往只是反复暴露 Application Crash，不是根因。

## 4.14.9 `docker top`

```bash
docker top container
```

不依赖 Container 内安装 `ps`，对 scratch/distroless 很有价值。

## 4.14.10 起不来：Architecture / Loader / Permission

`exec format error`：

```bash
docker image inspect \
  image \
  --format \
  'OS={{.Os}} Arch={{.Architecture}}'

uname -m
```

文件存在但 `no such file or directory`：

```bash
file /out/app
ldd /out/app
```

高度怀疑 ELF Dynamic Loader / ABI / Shared Library。

## 4.14.11 `docker diff`

```bash
docker diff container
```

```text
A = Added
C = Changed
D = Deleted
```

主要反映 Container Writable Layer，不是 Volume/Bind 的完整 Diff。

## 4.14.12 `docker stats` / cgroup

```bash
docker stats
```

快速看 CPU/Memory/Network/Block I/O/PIDs。

CPU 慢但不满，可能是 quota throttling：

```bash
docker inspect \
  --format '
NanoCpus={{.HostConfig.NanoCpus}}
CpuQuota={{.HostConfig.CpuQuota}}
CpuPeriod={{.HostConfig.CpuPeriod}}
CpusetCpus={{.HostConfig.CpusetCpus}}
' \
  container
```

cgroup v2 继续看：

```text
cpu.max
cpu.stat
nr_throttled
throttled_usec
```

## 4.14.13 Memory / OOM

```bash
docker inspect \
  --format '
Memory={{.HostConfig.Memory}}
MemorySwap={{.HostConfig.MemorySwap}}
OOMKilled={{.State.OOMKilled}}
ExitCode={{.State.ExitCode}}
' \
  container
```

较强证据链：

```text
ExitCode=137
+
OOMKilled=true
+
memory.events oom_kill 增加
```

## 4.14.14 PIDs

症状：

```text
fork:
Resource temporarily unavailable
```

检查：

```bash
docker stats

docker inspect \
  --format \
  'PidsLimit={{.HostConfig.PidsLimit}}' \
  container
```

再看 cgroup：

```text
pids.current
pids.max
```

## 4.14.15 文件写不了

第一问：**这个 Path 来自哪种 Mount？**

```bash
docker inspect \
  container \
  --format \
  '{{json .Mounts}}'
```

然后依次：

```text
RO/RW?
UID/GID?
mode/ACL?
Capability/LSM?
disk full?
inode full?
```

## 4.14.16 Disk

```bash
df -h
df -i
docker system df -v
```

可能是：

```text
filesystem capacity
inode
Docker Desktop virtual disk
log
writable layer
volume
build cache
```

## 4.14.17 Network Inside-Out

```text
Process alive?
↓
App listen?
↓
Container localhost works?
↓
Container network/IP?
↓
Port published?
↓
Host localhost?
↓
Host LAN?
↓
Firewall/VPN/proxy?
```

如果 App 只监听 `127.0.0.1:8080`，Container 外通常访问不到。通常服务监听 `0.0.0.0:8080`。

## 4.14.18 `docker port`

```bash
docker port container
```

例如：

```text
8080/tcp -> 127.0.0.1:18080
```

`EXPOSE` 不等于 `-p`。

## 4.14.19 Docker Network / DNS

```bash
docker network ls

docker network inspect network

docker inspect \
  container \
  --format \
  '{{json .NetworkSettings.Networks}}'
```

User-defined Network 上优先使用 Container Name / Alias，而不是写死 IP。

## 4.14.20 DNS vs TCP

```text
IP 通，DNS 不通
→ DNS

DNS 通，TCP timeout
→ route/firewall/upstream

TCP refused
→ 目标 TCP stack 到达，但 port 无 listener 或明确 reject
```

`ping` 不等于真实业务协议测试。

## 4.14.21 localhost 口诀

第一句话：

> **这是哪个 Network Namespace 的 localhost？**

Container `127.0.0.1` 默认不是 Windows/WSL Host。Docker Desktop 常用 `host.docker.internal` 访问 Host Service。

## 4.14.22 Security 故障

`Operation not permitted`：

```text
UID/GID
↓
Mount
↓
Capability
↓
NoNewPrivs
↓
seccomp
↓
AppArmor/SELinux
↓
Device
```

快速：

```bash
grep -E \
  '^(Uid|Gid|CapInh|CapPrm|CapEff|CapBnd|CapAmb|NoNewPrivs|Seccomp):' \
  /proc/1/status
```

## 4.14.23 Healthcheck

```bash
docker inspect \
  container \
  --format \
  '{{json .State.Health}}'
```

关注：

```text
Status
FailingStreak
Log
```

Running ≠ Healthy；Unhealthy ≠ 一定自动 Restart。

## 4.14.24 Build 排障

```bash
docker buildx build \
  --progress=plain \
  .
```

拆：

```text
Context
Base pull
Dependency download
Cache
Compile
Export
Push
```

不要默认上 `--no-cache`，否则容易掩盖 Cache Dependency 问题。

## 4.14.25 Registry / Platform

```text
manifest unknown
→ tag/repository/权限

no matching manifest for linux/arm64
→ 没有目标 architecture variant
```

## 4.14.26 Observation First

先：

```text
docker inspect
docker logs
docker events
docker stats
docker top
docker port
docker network inspect
```

再执行会改变状态的命令：

```text
restart
rm
chmod
chown
cap-add
privileged
firewall change
```

不要无脑：

```bash
docker system prune -a
docker volume prune
docker builder prune -a
sudo iptables -F
sudo nft flush ruleset
```

## 4.14.27 现场采集模板

```bash
NAME="<container>"

echo "=== ps ==="
docker ps -a \
  --filter "name=$NAME"

echo
echo "=== state ==="
docker inspect \
  "$NAME" \
  --format '
Status={{.State.Status}}
Running={{.State.Running}}
Restarting={{.State.Restarting}}
OOMKilled={{.State.OOMKilled}}
ExitCode={{.State.ExitCode}}
Error={{.State.Error}}
Pid={{.State.Pid}}
StartedAt={{.State.StartedAt}}
FinishedAt={{.State.FinishedAt}}
RestartCount={{.RestartCount}}
'

echo
echo "=== config ==="
docker inspect \
  "$NAME" \
  --format '
Image={{.Config.Image}}
User={{.Config.User}}
Entrypoint={{json .Config.Entrypoint}}
Cmd={{json .Config.Cmd}}
WorkingDir={{.Config.WorkingDir}}
ReadonlyRootfs={{.HostConfig.ReadonlyRootfs}}
NetworkMode={{.HostConfig.NetworkMode}}
'

echo
echo "=== mounts ==="
docker inspect \
  "$NAME" \
  --format \
  '{{json .Mounts}}'

echo
echo "=== networks ==="
docker inspect \
  "$NAME" \
  --format \
  '{{json .NetworkSettings.Networks}}'

echo
echo "=== recent logs ==="
docker logs \
  --tail 200 \
  --timestamps \
  "$NAME"
```

---

# 4.15 Container 综合实验

## 4.15.1 最终架构

```text
Host / WSL
    │
    │ 127.0.0.1:18081
    ▼
Docker Port Publishing
    │
    ▼
┌────────────────────────────┐
│ Container                  │
│                            │
│ UID 10001                  │
│ cap-drop ALL               │
│ no-new-privileges          │
│ read-only rootfs           │
│                            │
│ Go PID1                    │
│   ├─ :8080                 │
│   ├─ /health               │
│   ├─ /write                │
│   └─ /                     │
│                            │
│ /data → Docker Volume      │
│ /tmp  → tmpfs              │
└─────────────┬──────────────┘
              │
              ▼
          Linux Kernel
       Namespaces / cgroups
```

Runtime Limits：

```text
CPU      0.5 CPU
Memory   96 MiB
PIDs     64
RootFS   read-only
UID      10001
Caps     ALL dropped
NNP      enabled
```

## 4.15.2 Build Artifact 设计

Application 提供多个 Mode：

```text
serve
healthcheck
fail
allocate
spawn
child
```

用途：

```text
serve        → 正常服务
healthcheck  → 自己做 HTTP Probe
fail         → 制造 ExitCode
allocate     → 制造 OOM
spawn        → 制造 PIDs Limit
```

服务核心：

```go
server := &http.Server{
    Addr: ":8080",
    Handler: mux,
}

ctx, stop := signal.NotifyContext(
    context.Background(),
    syscall.SIGTERM,
    syscall.SIGINT,
)

go func() {
    <-ctx.Done()

    shutdownCtx, cancel :=
        context.WithTimeout(
            context.Background(),
            5*time.Second,
        )

    defer cancel()
    _ = server.Shutdown(shutdownCtx)
}()
```

Endpoints：

```text
/
→ hello + request counter

/health
→ 200 OK

/write?msg=x
→ append /data/events.log
```

## 4.15.3 `.dockerignore`

```dockerignore
.git/
.gitignore

*.log

.env
.env.*

tmp/
data/

bin/
dist/

.DS_Store
```

Runtime Data 不应进入 Build Context。

## 4.15.4 Dockerfile

```dockerfile
# syntax=docker/dockerfile:1

FROM golang:1.25-alpine AS build

WORKDIR /src

COPY go.mod ./

RUN \
  --mount=type=cache,target=/go/pkg/mod \
  go mod download

COPY \
  main.go \
  main_test.go \
  ./

RUN \
  --mount=type=cache,target=/root/.cache/go-build \
  CGO_ENABLED=0 \
  go test \
    ./...

RUN \
  --mount=type=cache,target=/root/.cache/go-build \
  CGO_ENABLED=0 \
  go build \
    -trimpath \
    -ldflags="-s -w" \
    -o /out/app \
    .

FROM build AS test

RUN /out/app \
      fail \
      --code 0

FROM alpine:3.23 AS debug

COPY \
  --from=build \
  --chmod=0555 \
  /out/app \
  /app

ENTRYPOINT ["/app"]
CMD ["serve", "--listen", ":8080", "--data", "/data"]

FROM scratch AS production

COPY \
  --from=build \
  --chmod=0555 \
  /out/app \
  /app

USER 10001:10001
EXPOSE 8080
STOPSIGNAL SIGTERM

HEALTHCHECK \
  --interval=3s \
  --timeout=1s \
  --start-period=2s \
  --retries=3 \
  CMD ["/app", "healthcheck", "--url", "http://127.0.0.1:8080/health"]

ENTRYPOINT ["/app"]
CMD ["serve", "--listen", ":8080", "--data", "/data"]
```

## 4.15.5 Build

```bash
IMG_TEST="ai-infra-415:test"
IMG_DEBUG="ai-infra-415:debug"
IMG_PROD="ai-infra-415:prod"
```

```bash
docker build \
  --progress=plain \
  --target test \
  -t "$IMG_TEST" \
  .

docker build \
  --target debug \
  -t "$IMG_DEBUG" \
  .

docker build \
  --target production \
  -t "$IMG_PROD" \
  .
```

## 4.15.6 Network / Volume

```bash
NET="ai-infra-415-net-$$"
VOL="ai-infra-415-data-$$"

docker network create "$NET"
docker volume create "$VOL"
```

初始化 Volume Ownership：

```bash
docker run \
  --rm \
  --mount type=volume,src="$VOL",dst=/data \
  busybox:1.36 \
  sh -c '
    chown 10001:10001 /data
    chmod 0750 /data
    ls -ldn /data
  '
```

## 4.15.7 启动 Production

```bash
APP="ai-infra-415-app-$$"

docker run \
  -d \
  --name "$APP" \
  --network "$NET" \
  --read-only \
  --tmpfs /tmp:rw,nosuid,noexec,size=16m \
  --cap-drop ALL \
  --security-opt no-new-privileges=true \
  --memory 96m \
  --cpus 0.50 \
  --pids-limit 64 \
  --mount type=volume,src="$VOL",dst=/data \
  -p 127.0.0.1:18081:8080 \
  "$IMG_PROD"
```

## 4.15.8 第一轮检查

```bash
docker ps \
  --filter "name=$APP"

docker inspect \
  "$APP" \
  --format '
Status={{.State.Status}}
Pid={{.State.Pid}}
OOMKilled={{.State.OOMKilled}}
ExitCode={{.State.ExitCode}}
'

docker logs "$APP"
docker top "$APP"
```

预期日志：

```text
starting server pid=1 uid=10001 listen=:8080 data=/data
```

## 4.15.9 Health

```bash
sleep 5

docker inspect \
  "$APP" \
  --format \
  '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}'
```

应为 `healthy`。

scratch 没有 curl，但 Application 自己的 `/app healthcheck` 可以完成 Probe。

## 4.15.10 Port Publishing

```bash
docker port "$APP"
```

预期：

```text
8080/tcp -> 127.0.0.1:18081
```

Host：

```bash
curl http://127.0.0.1:18081/
```

## 4.15.11 Container-to-Container DNS

```bash
docker run \
  --rm \
  --network "$NET" \
  busybox:1.36 \
  wget \
    -qO- \
    "http://$APP:8080/"
```

这里走 User-defined Docker Network + Embedded DNS，不走 Host `18081`。

## 4.15.12 Persistent Volume

写：

```bash
docker run \
  --rm \
  --network "$NET" \
  busybox:1.36 \
  wget \
    -qO- \
    "http://$APP:8080/write?msg=hello-volume"
```

读：

```bash
docker run \
  --rm \
  --mount type=volume,src="$VOL",dst=/data,readonly \
  busybox:1.36 \
  cat \
  /data/events.log
```

Restart 后数据仍应存在。

## 4.15.13 Runtime Resource / Security

```bash
docker stats \
  --no-stream \
  "$APP"
```

```bash
docker inspect \
  "$APP" \
  --format '
Memory={{.HostConfig.Memory}}
NanoCpus={{.HostConfig.NanoCpus}}
PidsLimit={{.HostConfig.PidsLimit}}
User={{.Config.User}}
Readonly={{.HostConfig.ReadonlyRootfs}}
Privileged={{.HostConfig.Privileged}}
CapDrop={{json .HostConfig.CapDrop}}
SecurityOpt={{json .HostConfig.SecurityOpt}}
'
```

## 4.15.14 Graceful Shutdown

```bash
docker stop \
  -t 5 \
  "$APP"

docker logs "$APP"
```

预期：

```text
received shutdown signal
server stopped cleanly
```

Inspect：

```bash
docker inspect \
  "$APP" \
  --format '
Status={{.State.Status}}
ExitCode={{.State.ExitCode}}
OOMKilled={{.State.OOMKilled}}
'
```

正常应为 ExitCode 0。

## 4.15.15 Fault A：Exit 42

```bash
FAIL="ai-infra-415-fail-$$"

docker run \
  --name "$FAIL" \
  "$IMG_PROD" \
  fail \
  --code 42
```

排查：

```bash
docker inspect \
  "$FAIL" \
  --format '
Status={{.State.Status}}
ExitCode={{.State.ExitCode}}
OOMKilled={{.State.OOMKilled}}
Error={{.State.Error}}
'

docker logs "$FAIL"
```

根因层：Application。

回退：

```bash
docker rm "$FAIL"
unset FAIL
```

## 4.15.16 Fault B：Read-only RootFS + 缺少 `/data`

```bash
NOVOL="ai-infra-415-novol-$$"

docker run \
  --name "$NOVOL" \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges=true \
  "$IMG_PROD"
```

典型日志：

```text
mkdir /data:
read-only file system
```

正确修复是给 `/data` Writable Volume，而不是取消整个 `--read-only`。

回退：

```bash
docker rm "$NOVOL"
unset NOVOL
```

## 4.15.17 Fault C：Memory OOM

```bash
OOM="ai-infra-415-oom-$$"

docker run \
  -d \
  --name "$OOM" \
  --network none \
  --memory 32m \
  --memory-swap 32m \
  "$IMG_PROD" \
  allocate \
  --mb 256
```

等待：

```bash
sleep 3
```

检查：

```bash
docker inspect \
  "$OOM" \
  --format '
Status={{.State.Status}}
ExitCode={{.State.ExitCode}}
OOMKilled={{.State.OOMKilled}}
MemoryLimit={{.HostConfig.Memory}}
'
```

典型：

```text
ExitCode=137
OOMKilled=true
```

这时才形成比较完整的 OOM 证据链。

回退：

```bash
docker rm "$OOM"
unset OOM
```

## 4.15.18 Fault D：PIDs Limit

```bash
PIDS="ai-infra-415-pids-$$"

docker run \
  -d \
  --name "$PIDS" \
  --network none \
  --pids-limit 12 \
  "$IMG_PROD" \
  spawn \
  --n 50
```

检查：

```bash
sleep 2

docker logs "$PIDS"
docker top "$PIDS"
docker stats --no-stream "$PIDS"

docker inspect \
  "$PIDS" \
  --format \
  'PidsLimit={{.HostConfig.PidsLimit}}'
```

典型：

```text
spawn failed:
resource temporarily unavailable
```

回退：

```bash
docker rm -f "$PIDS"
unset PIDS
```

## 4.15.19 四类故障横向比较

| 故障 | 关键现象 | 关键证据 | 根因层 |
|---|---|---|---|
| `fail 42` | Exit 42 | logs + inspect | Application |
| `/data` 未挂 | read-only error | logs + Mount Config | Filesystem |
| Memory OOM | Exit 137 | `OOMKilled=true` | cgroup Memory |
| PIDs Limit | spawn failure | PidsLimit + Process Count | cgroup PIDs |

## 4.15.20 从 `docker run` 到 PID1

```text
Docker CLI
↓
Docker API
↓
dockerd
↓
containerd
↓
snapshot/rootfs
↓
containerd-shim
↓
runc
↓
Linux namespaces
Linux cgroups
mounts
security settings
↓
exec /app
↓
PID1
```

最终 Go Application 才开始 `listen :8080`。

## 4.15.21 Image → RootFS

```text
Image read-only layer
+
Container writable layer
↓
Merged RootFS
```

再叠加：

```text
/data → Docker Volume
/tmp  → tmpfs
```

## 4.15.22 最终清理

```bash
docker rm -f "$APP"

docker volume rm "$VOL"

docker network rm "$NET"

docker image rm \
  "$IMG_TEST" \
  "$IMG_DEBUG" \
  "$IMG_PROD"

cd /
rm -rf "$LAB"

unset LAB
unset APP
unset NET
unset VOL
unset IMG_TEST
unset IMG_DEBUG
unset IMG_PROD
```

## 4.15.23 最终验证

```bash
echo "=== containers ==="

docker ps -a \
  --format '{{.Names}}' \
  | grep '^ai-infra-415-' \
  || echo "clean"

echo
echo "=== networks ==="

docker network ls \
  --format '{{.Name}}' \
  | grep '^ai-infra-415-' \
  || echo "clean"

echo
echo "=== volumes ==="

docker volume ls \
  --format '{{.Name}}' \
  | grep '^ai-infra-415-' \
  || echo "clean"

echo
echo "=== images ==="

docker image ls \
  --format '{{.Repository}}:{{.Tag}}' \
  | grep '^ai-infra-415:' \
  || echo "clean"

echo
echo "=== temporary dirs ==="

find \
  /tmp \
  -maxdepth 1 \
  -name 'ai-infra-415.*' \
  -print

echo
echo "=== Docker Engine ==="

docker info \
  >/dev/null \
  && echo "Docker Engine OK"

echo
echo "=== WSL route ==="

ip route
```

本节没有修改：

```text
WSL systemd
sysctl
iptables
nftables
Docker daemon.json
Docker Desktop Settings
Host cgroup
Host mount
Host security policy
```

---

# 第 4 章总复盘

## 一张图串起整个 Container Runtime

```text
                         SOURCE CODE
                              │
                              ▼
                      Build Context
                              │
                       .dockerignore
                              │
                              ▼
                         Dockerfile
                              │
                              ▼
                         BuildKit
                              │
                           LLB DAG
                              │
              ┌───────────────┴──────────────┐
              │                              │
              ▼                              ▼
         Builder Stage                  Test Stage
     compiler/source/cache                  tests
              │
              ▼
          /out/app
              │
              │ Artifact Boundary
              ▼
       Production Stage
            scratch
              │
              ▼
           OCI Image
     ┌────────┴────────┐
     │                 │
   Layers            Config
                     ├─ USER
                     ├─ ENTRYPOINT
                     ├─ CMD
                     ├─ HEALTHCHECK
                     └─ STOPSIGNAL
              │
              ▼
       Docker Image Store
              │
              ▼
         Docker Engine
              │
              ▼
          containerd
              │
              ▼
             shim
              │
              ▼
             runc
              │
              ▼
     ┌────────────────────────┐
     │ Linux Kernel           │
     │ Namespace              │
     │ cgroup                 │
     │ mount                  │
     │ capability             │
     │ seccomp                │
     │ LSM                    │
     │ networking             │
     └──────────┬─────────────┘
                │
                ▼
            Container
     ┌────────────────────────┐
     │ PID1 = /app            │
     │ UID 10001              │
     │ :8080                  │
     │ /      read-only       │
     │ /data  volume          │
     │ /tmp   tmpfs           │
     └──────────┬─────────────┘
                │
                ▼
          Docker Network
          /             \
         ▼               ▼
 Other Containers   Port Publish
                        │
                        ▼
               Host 127.0.0.1:18081
```

## 第 4 章关键定义

### Container

```text
普通 Linux Process
+
Namespaces
+
cgroups
+
RootFS
+
mounts
+
network
+
security context
```

### Image

```text
Content-addressed filesystem layers
+
runtime configuration
+
metadata
```

### Dockerfile

```text
Build Graph Description
+
Filesystem Transformation
+
Runtime Contract
+
Cache / Dependency / Artifact Boundary
```

### BuildKit

```text
Dockerfile Frontend
↓
LLB DAG
↓
Build Solver
↓
Cache / Mount / Secret / Parallelism
```

### containerd

```text
High-level container runtime manager
负责 image / snapshot / task / lifecycle
```

### runc

```text
Low-level OCI runtime
把 OCI config + rootfs
变成真正 Linux Process
```

### Namespace

```text
Process 看见什么系统世界
```

### cgroup

```text
Process Group 可以使用多少资源
```

### Volume

```text
Data Lifecycle
与
Container Lifecycle
分离
```

### PID1

```text
Container 生命周期主进程
+
signal handling
+
child reaping
```

### Container Security

```text
Namespace
+
UID/GID
+
Capabilities
+
seccomp
+
LSM
+
Mount
+
Device
+
cgroup
+
Kernel
```

---

# 第 4 章收官小测与答案

用户答案：

```text
1B 2C 3B 4B 5C 6B 7B 8B 9B 10C
```

结果：

```text
10 / 10
```

1. `ExitCode=137, OOMKilled=false` → **B：SIGKILL，但不能证明 OOM**
2. Non-root + Read-only，需要写 `/data` → **C：只挂 Writable Volume**
3. Multi-stage Go Builder → **B：Final 不自动包含 Compiler**
4. Container 内 localhost 正常、Host Port 失败 → **B：优先 Port Publishing / Bind Address**
5. Container `127.0.0.1` → **C：当前 NetNS Loopback**
6. UID 0 + CapEff=0 → **B：UID 与 Capability 是不同维度**
7. 文件存在但执行 `no such file` → **B：Dynamic Loader / ABI**
8. `unhealthy` 是否一定自动 Restart → **B：否**
9. `COPY . .` 后 `pip install` → **B：Source 改动容易使 Dependency Cache 失效**
10. scratch 中 `docker exec sh` 失败 → **C：RootFS 没有 `/bin/sh`**

---

# 第 4 章能力验收

| 现象 | 第一怀疑层 |
|---|---|
| Container 启动即退出 | PID1 / ExitCode |
| Exit 137 | SIGKILL，再查 OOM |
| Memory 不足 | cgroup Memory |
| CPU 不满但很慢 | CPU quota / throttling |
| fork 失败 | PIDs cgroup |
| 文件重建后消失 | Writable Layer vs Volume |
| Permission denied | Mount + UID/GID + Security |
| HTTP 不通 | Listen → NetNS → Port Publish |
| Container Name 不解析 | Docker Network / DNS |
| localhost 不对 | Network Namespace |
| Image 巨大 | Layer / Build / Multi-stage |
| Build 很慢 | Context / Cache / Dependency |
| exec format error | Architecture / Binary Format |
| 文件存在但无法执行 | ELF Loader / ABI |
| stop 不优雅 | PID1 / Signal |
| root 仍无法操作 | Capability / seccomp / LSM |
| Docker Engine 不通 | Client / Server / Context |
| WSL 看不到 dockerd/veth | Docker Desktop Backend Boundary |

---

# 课程全局进度

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
✅ 完成
    ├─ 4.1 Container 到底是什么
    ├─ 4.2 Linux Namespace
    ├─ 4.3 cgroup
    ├─ 4.4 RootFS / Mount / chroot / pivot_root
    ├─ 4.5 Image / Layer / OverlayFS
    ├─ 4.6 Docker Engine / containerd / runc / OCI
    ├─ 4.7 NetNS / veth / bridge
    ├─ 4.8 Port Mapping / Routing / NAT
    ├─ 4.9 Volume / Bind Mount / tmpfs
    ├─ 4.10 PID1 / Signal / Zombie
    ├─ 4.11 Container Security
    ├─ 4.12 Dockerfile / BuildKit / Build Cache
    ├─ 4.13 Multi-stage Build
    ├─ 4.14 Docker 系统化排障
    └─ 4.15 Container 综合实验

第 5 章：GPU 与 CUDA
➡️ 下一章

第 6 章：GPU Cluster
⬜ 未开始

第 7 章：LLM 系统基础
⬜ 未开始

第 8 章：LLM Inference
⬜ 未开始

第 9 章：分布式 GPU
⬜ 未开始

第 10 章：分布式训练
⬜ 未开始

第 11 章：AI Platform
⬜ 未开始

第 12 章：Observability / SRE
⬜ 未开始

第 13 章：综合 AI Infra 项目
⬜ 未开始
```

---

# 结束

第 4 章到这里正式完成。

从第 5 章开始，课程主线从：

```text
Linux / Network / Go / Container
```

转向：

```text
GPU
CUDA
Tensor
LLM Runtime
GPU Cluster
Distributed AI
```

后续继续遵循：

```text
新术语先定义
→ 建立执行模型
→ 再讲复杂逻辑
→ 做可回退实验
→ 每节维护目录和进度
```
