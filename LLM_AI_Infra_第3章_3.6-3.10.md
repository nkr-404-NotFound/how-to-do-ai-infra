# LLM / AI Infra 学习笔记

## 第 3 章：Python + Go
### 3.6 ～ 3.10：Linux Automation、HTTP、Socket、并发与 Python 性能

> 建议环境：WSL2 + Ubuntu + `uv`
>
> 主线：
>
> ```text
> subprocess
> ↓
> HTTP Client / API
> ↓
> Socket
> ↓
> Thread / Process / Async
> ↓
> await / Event Loop
> ↓
> GIL / Python Performance
> ```

---

# 3.6 subprocess 与 Linux Automation

## 3.6.1 subprocess

`subprocess` 是 Python Standard Library 中用于启动、控制、等待 Child Process 的模块。

```python
import subprocess

subprocess.run(["ip", "route"])
```

对应：

```text
Python Parent Process
↓
Child Process
↓
ip route
```

### 推荐 Argument List

推荐：

```python
subprocess.run(["ping", "-c", "3", "8.8.8.8"])
```

不推荐默认使用：

```python
subprocess.run("ping -c 3 8.8.8.8", shell=True)
```

`shell=True` 会让 Shell 解析：

```text
|
>
&&
;
$()
```

因此存在 Command Injection 风险。

---

## 3.6.2 CompletedProcess / Exit Code

```python
result = subprocess.run(["ip", "route"])
print(result.returncode)
```

传统约定：

```text
0     → success
非 0  → error / special status
```

注意：

```text
Process Exit Code
≠
HTTP Status Code
```

---

## 3.6.3 stdout / stderr

```text
stdin  → FD 0
stdout → FD 1
stderr → FD 2
```

捕获：

```python
result = subprocess.run(
    ["ip", "route"],
    capture_output=True,
    text=True,
)

print(result.stdout)
print(result.stderr)
```

`capture_output=True`：

```text
stdout → PIPE
stderr → PIPE
```

`text=True`：

```text
bytes → str
```

---

## 3.6.4 check / timeout

```python
subprocess.run(
    ["ip", "route"],
    check=True,
    timeout=5,
)
```

非 0：

```text
CalledProcessError
```

超时：

```text
TimeoutExpired
```

Infra Automation 一定要避免外部命令永久卡住。

---

## 3.6.5 cwd / env

```python
subprocess.run(
    ["ls"],
    cwd="/tmp",
)
```

设置 Child Environment：

```python
import os

env = os.environ.copy()
env["MODEL_NAME"] = "qwen"

subprocess.run(
    ["printenv", "MODEL_NAME"],
    env=env,
)
```

AI Infra 常见：

```text
CUDA_VISIBLE_DEVICES
HTTP_PROXY
HTTPS_PROXY
MODEL_PATH
```

---

## 3.6.6 Popen

`subprocess.run()`：

```text
启动
↓
等待
↓
拿结果
```

`Popen` 更适合：

```text
长时间运行
实时 stdout
主动 terminate / kill
自己控制 stdin
```

```python
process = subprocess.Popen(
    ["sleep", "30"]
)

print(process.pid)
```

常用：

```python
process.wait()
process.poll()
process.terminate()
process.kill()
```

Linux 常见：

```text
terminate → SIGTERM
kill      → SIGKILL
```

---

## 3.6.7 实时 stdout

```python
process = subprocess.Popen(
    ["ping", "127.0.0.1"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

for line in process.stdout:
    print(line.rstrip())
```

适合：

```text
training job
docker build
kubectl logs
long-running server
```

---

## 3.6.8 Buffering / communicate

**Buffering**：Child 可能先把输出放 Buffer，不立即 flush。

Python Child：

```bash
python -u script.py
```

可减少缓冲。

`communicate()`：

```python
stdout, stderr = process.communicate()
```

用于安全完成 Child I/O 并等待结束。

---

## 3.6.9 Machine-Readable Output

自动化优先：

```text
JSON
CSV
固定结构格式
```

例如：

```bash
docker inspect
```

通常比硬解析：

```bash
docker ps
```

更稳。

---

## 3.6.10 通用 Runner

```python
import subprocess


def run_command(
    command: list[str],
    timeout: float = 10,
) -> dict:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": None,
        }

    except FileNotFoundError as exc:
        return {
            "success": False,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "error": str(exc),
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "error": "timeout",
        }
```

---

# 3.7 HTTP Client 与 API

## 3.7.1 HTTP Client / API

**HTTP Client**：主动发起 HTTP Request 的程序。

例如：

```text
Browser
curl
requests
httpx
OpenAI SDK
```

**API**

Application Programming Interface：

> 程序之间约定的调用接口。

AI Infra 常见：

```text
OpenAI-compatible API
vLLM API
Kubernetes API
Prometheus API
Cloud API
```

---

## 3.7.2 requests

安装：

```bash
uv add requests
```

最简单：

```python
import requests

response = requests.get(
    "https://example.com"
)
```

Response 常用：

```python
response.status_code
response.headers
response.text
response.content
response.json()
```

其中：

```text
text    → str
content → bytes
```

---

## 3.7.3 Query Parameter

```python
params = {
    "limit": 10,
    "status": "ready",
}

response = requests.get(
    "https://api.example.com/models",
    params=params,
)
```

requests 会处理 URL Encoding。

---

## 3.7.4 POST / JSON Body

```python
payload = {
    "model": "qwen",
    "messages": [
        {
            "role": "user",
            "content": "hello",
        }
    ],
}

response = requests.post(
    url,
    json=payload,
)
```

`json=`：

```text
Python dict
↓
JSON Serialization
↓
HTTP Body
```

通常不要和：

```python
data=...
```

混淆。

---

## 3.7.5 Header / Bearer Token

```python
headers = {
    "Authorization":
        "Bearer abc123",
}
```

敏感信息应从 Environment 读取：

```python
import os

api_key = os.environ["API_KEY"]
```

---

## 3.7.6 Timeout

```python
requests.get(
    url,
    timeout=(2, 10),
)
```

粗略：

```text
2  → Connect Timeout
10 → Read Timeout
```

LLM 场景 Timeout 要按业务设计，不能机械统一成 5 秒。

---

## 3.7.7 Exception 分层

常见：

```text
Timeout
ConnectionError
SSLError
HTTPError
```

关键：

```text
Connection refused
→ HTTP 还没有成功建立

HTTP 404
→ HTTP Response 已经到达
```

requests 默认不会因为 404 / 500 自动抛异常。

使用：

```python
response.raise_for_status()
```

---

## 3.7.8 分层模型

```text
DNS / TCP / TLS 失败
→ Connection 类 Exception

HTTP 到达
↓
4xx / 5xx
→ HTTPError

HTTP 2xx
↓
JSON Parse
↓
Schema / Field Validation
↓
Application Success
```

---

## 3.7.9 JSON Response

```python
data = response.json()
```

本质：

```text
HTTP Body
↓
JSON Deserialization
↓
dict / list
```

JSON 能解析：

```text
≠
业务一定成功
```

仍需要 Validation。

---

## 3.7.10 Session / Connection Pool

```python
session = requests.Session()
```

作用：

```text
复用 Header
复用 Cookie
复用 TCP/TLS Connection
```

底层使用：

**Connection Pool**

```text
Session
↓
Connection Pool
├─ conn1
├─ conn2
└─ conn3
```

---

## 3.7.11 Retry / Idempotency / Backoff

可能适合 Retry：

```text
502
503
504
Connection Reset
部分 Timeout
```

通常不盲目重试：

```text
400
401
403
404
```

**Idempotency（幂等性）**：

> 同一操作重复执行，最终效果相同。

POST Retry 要特别谨慎。

**Backoff（退避）**：

```text
1s
2s
4s
8s
```

称：

**Exponential Backoff**

用于避免 Retry Storm。

---

## 3.7.12 Streaming / TTFT

LLM 常使用 Streaming：

```python
response = requests.post(
    url,
    json=payload,
    stream=True,
    timeout=(2, 60),
)

for line in response.iter_lines():
    if line:
        print(line)
```

**TTFT**

Time To First Token：

```text
Request Sent
↓
First Token
```

和 Total Latency 不同。

---

## 3.7.13 Proxy / NO_PROXY

requests 通常读取：

```text
HTTP_PROXY
HTTPS_PROXY
NO_PROXY
```

本地 / 内网 Service 要注意 `NO_PROXY`，否则可能错误走外部 Proxy。

---

## 3.7.14 TLS Verification

不要长期：

```python
verify=False
```

正确方向：

```python
verify="/path/to/ca.pem"
```

即：

> 建立正确 Trust Chain，而不是关闭验证。

---

## 3.7.15 Health Check

**Liveness**

问：

> Service 还活着吗？

**Readiness**

问：

> Service 已经可以接业务了吗？

LLM Server 可能：

```text
Process 已启动
→ Liveness OK

Model 还在加载
→ Readiness False
```

---

## 3.7.16 Latency Probe

```python
import time
import requests


def probe(url: str) -> dict:
    start = time.perf_counter()

    try:
        response = requests.get(
            url,
            timeout=(2, 5),
        )

        latency_ms = (
            time.perf_counter() - start
        ) * 1000

        return {
            "ok":
                200 <= response.status_code < 300,
            "status_code":
                response.status_code,
            "latency_ms":
                latency_ms,
            "error":
                None,
        }

    except requests.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "latency_ms":
                (time.perf_counter() - start) * 1000,
            "error": str(exc),
        }
```

---

# 3.8 Socket 初步

## 3.8.1 Socket

**Socket**

> Process 使用 Kernel Network Stack 的通信端点。

Linux：

```text
Process
↓
File Descriptor
↓
Kernel Socket Object
```

Python：

```python
import socket
```

只是对 OS Socket API 的封装。

---

## 3.8.2 AF_INET / SOCK_STREAM

TCP：

```python
sock = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM,
)
```

```text
AF_INET     → IPv4
AF_INET6    → IPv6
SOCK_STREAM → TCP-like Stream
SOCK_DGRAM  → UDP-like Datagram
```

---

## 3.8.3 TCP Client

```text
socket()
↓
connect()
↓
TCP Handshake
↓
send / recv
↓
close()
```

`connect()` 可能触发：

```text
Route Lookup
Neighbor
SYN
SYN+ACK
ACK
```

---

## 3.8.4 TCP Server

```text
socket()
↓
bind()
↓
listen()
↓
accept()
↓
recv / send
↓
close()
```

`bind(("127.0.0.1", 8000))`：

```text
只监听 Loopback
```

`bind(("0.0.0.0", 8000))`：

```text
监听当前 NetNS 多个 IPv4 Interface
```

---

## 3.8.5 Listening Socket vs Connected Socket

```python
server.listen()

conn, addr = server.accept()
```

此时：

```text
server
→ Listening Socket

conn
→ Connected Socket
```

模型：

```text
Listening Socket :8000
├─ Client A Socket
├─ Client B Socket
└─ Client C Socket
```

---

## 3.8.6 recv / sendall

```python
data = conn.recv(1024)
```

返回：

```text
bytes
```

因为 TCP 是：

```text
Byte Stream
```

发送：

```python
conn.sendall(
    b"hello"
)
```

`send()` 可能只发送一部分；`sendall()` 尽量发完整。

---

## 3.8.7 TCP 没有 Message Boundary

Client：

```python
sock.sendall(b"hello")
sock.sendall(b"world")
```

Server 可能收到：

```text
helloworld
```

也可能分成多次。

所以 Application Protocol 要设计：

**Framing**

常见：

```text
Delimiter
Length Prefix
Content-Length
Chunked
固定长度
```

---

## 3.8.8 recv() 返回 b""

通常意味着：

> 对端关闭了 Connection / 到达 EOF。

常见：

```python
while True:
    data = conn.recv(1024)

    if not data:
        break
```

---

## 3.8.9 Blocking

```python
accept()
recv()
```

默认可能 Blocking。

这直接引出：

```text
Thread
Process
Async
```

---

## 3.8.10 Socket Timeout

```python
sock.settimeout(3)
```

限制某些 Blocking Socket Operation 等待时间。

---

## 3.8.11 create_connection / getaddrinfo

```python
socket.create_connection(
    ("example.com", 80),
    timeout=5,
)
```

`getaddrinfo()`：

```python
socket.getaddrinfo(
    "example.com",
    443,
)
```

可能返回：

```text
IPv4
IPv6
多个地址候选
```

---

## 3.8.12 Raw HTTP over TCP

HTTP/1.1：

```python
request = (
    "GET / HTTP/1.1
"
    "Host: example.com
"
    "Connection: close
"
    "
"
)
```

其中：

```text


→ CRLF




→ Headers 结束
```

说明：

> HTTP 本质建立在 TCP Byte Stream 上。

---

## 3.8.13 TLS

HTTPS：

```text
TCP
↓
TLS Handshake
↓
Encrypted Channel
↓
HTTP
```

Python：

```python
import ssl
```

`SSLContext` 用于建立 TLS Socket。

---

## 3.8.14 Socket Buffer

发送：

```text
Application
↓
Socket Send Buffer
↓
TCP Stack
↓
NIC
```

接收：

```text
NIC
↓
TCP Stack
↓
Socket Receive Buffer
↓
recv()
```

`sendall()` 成功：

```text
≠
远端业务处理成功
```

TCP ACK：

```text
≠
HTTP 200
```

---

## 3.8.15 Socket Error

```text
socket.gaierror
→ DNS / address resolution

ConnectionRefusedError
→ TCP refused

socket.timeout
→ timeout

OSError
→ generic OS/socket error
```

---

## 3.8.16 UDP

UDP：

```python
socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM,
)
```

常见：

```text
bind
sendto
recvfrom
```

无需：

```text
listen
accept
3-way handshake
```

UDP 保留 Datagram Boundary。

---

## 3.8.17 Network Namespace / Docker / Kubernetes

Socket 属于某个 NetNS。

因此：

```text
Host localhost
Container localhost
Pod localhost
```

可能不是同一个网络空间。

Docker：

```text
Host :8080
↓
DNAT / Port Mapping
↓
Container :8000
↓
Python Listening Socket
```

Kubernetes Pod 内多个 Container 通常共享 Pod NetNS，因此可以共享：

```text
127.0.0.1
Port Namespace
```

---

# 3.9 Thread / Process / Async

## 3.9.1 Concurrency vs Parallelism

**Concurrency**

> 同一时间段内多个任务推进。

**Parallelism**

> 同一时刻多个任务真正执行。

---

## 3.9.2 I/O-bound vs CPU-bound

I/O-bound：

```text
Network
Disk
DB
Socket
```

CPU-bound：

```text
Pure CPU Calculation
Python Loop
Compression
Data Processing
```

粗略：

```text
I/O-bound
→ Thread / Async

CPU-bound
→ Process
```

---

## 3.9.3 Thread

同一 Process：

```text
Process
├─ Thread A
├─ Thread B
└─ Thread C
```

共享：

```text
Heap
Global Variables
FD
Socket
Virtual Address Space
```

每个 Thread 自己有：

```text
Stack
Registers
Execution State
```

---

## 3.9.4 Thread 基础

```python
import threading


def worker():
    print("hello")


thread = threading.Thread(
    target=worker
)

thread.start()
thread.join()
```

`start()`：

> 启动。

`join()`：

> 等待完成。

---

## 3.9.5 Thread 适合 I/O-bound

如果 3 个任务各：

```python
time.sleep(2)
```

串行：

```text
≈ 6s
```

Thread：

```text
≈ 2s
```

因为等待时间重叠。

---

## 3.9.6 Race Condition / Lock

多个 Thread 共享 Mutable State：

> 可能出现 Race Condition。

保护：

```python
lock = threading.Lock()

with lock:
    counter += 1
```

临界区：

**Critical Section**

过度 Lock 可能：

```text
降低性能
增加复杂度
导致 Deadlock
```

---

## 3.9.7 Thread Pool

```python
from concurrent.futures import (
    ThreadPoolExecutor,
)
```

例如：

```python
with ThreadPoolExecutor(
    max_workers=20
) as executor:
    ...
```

比：

```text
无限创建 Thread
```

更可控。

---

## 3.9.8 Process

多个 Process：

```text
Process A
→ Memory A

Process B
→ Memory B
```

默认普通 Python Heap 不共享。

优点：

```text
Memory Isolation
Multi-Core CPU Parallelism
```

缺点：

```text
Startup Cost
Memory Cost
IPC
Serialization
```

---

## 3.9.9 IPC / Queue

**IPC**

Inter-Process Communication：

```text
Pipe
Queue
Shared Memory
Socket
File
```

Queue：

```text
Producer
↓
Queue
↓
Consumer
```

通常 FIFO。

---

## 3.9.10 Process Pool

```python
from concurrent.futures import (
    ProcessPoolExecutor,
)
```

适合：

```text
Pure Python CPU-heavy work
```

---

## 3.9.11 Async

**Async**

Asynchronous。

核心：

> 当前 Task 等 I/O 时主动让出执行权。

典型：

```text
1 Process
↓
1 Thread
↓
1 Event Loop
↓
很多 Async Tasks
```

---

## 3.9.12 async def / await

```python
async def worker():
    await asyncio.sleep(2)
```

`async def` 创建 Coroutine Function。

调用后得到：

```text
Coroutine Object
```

`await`：

> 等待异步结果，并允许 Event Loop 去运行其他 Task。

---

## 3.9.13 asyncio.gather

```python
await asyncio.gather(
    worker("A"),
    worker("B"),
    worker("C"),
)
```

多个 Task 可以重叠等待 I/O。

---

## 3.9.14 Cooperative Scheduling

Async：

```text
Task
↓
await
↓
主动让出执行权
```

叫：

**Cooperative Scheduling**

Thread：

```text
Kernel Scheduler
→ 可以抢占
```

叫：

**Preemptive Scheduling**

---

## 3.9.15 Async 不是多线程

经典：

```text
1 Thread
↓
Event Loop
├─ Task A
├─ Task B
└─ Task C
```

Task 不是 OS Thread。

---

## 3.9.16 Blocking Code 会卡 Event Loop

错误：

```python
async def handler():
    requests.get(...)
```

`requests.get()` 是 Blocking。

Async 代码要配：

```text
Async-compatible Library
```

例如：

```text
httpx.AsyncClient
aiohttp
```

---

## 3.9.17 Backpressure

**Backpressure**

下游处理不过来：

```text
Buffer 满
↓
上游被迫放慢
```

网络 Server 中非常重要。

---

## 3.9.18 Future / as_completed

```python
future = executor.submit(
    fetch,
    url,
)
```

Future：

> 未来会得到结果的对象。

```python
future.result()
```

获得结果。

`as_completed()`：

> 谁先完成先处理谁。

---

## 3.9.19 Resource Exhaustion

并发过高可能耗尽：

```text
Thread
FD
Memory
Connection Pool
Ephemeral Port
```

所以要使用：

**Bounded Concurrency**

---

## 3.9.20 Semaphore

**Semaphore**

用于：

> 限制同时最多 N 个 Task 进入某段逻辑。

例如：

```text
1000 URL
↓
Semaphore 20
↓
最多 20 个并发请求
```

---

## 3.9.21 Thread / Process / Async 选型

```text
中等规模 I/O + Blocking SDK
→ Thread

大量 I/O + Async Library
→ Async

Pure Python CPU-heavy
→ Process
```

现实系统可以混合。

---

# 3.9A await / Event Loop 调度深入

## 3.9A.1 核心例子

```python
import asyncio


async def worker(name):
    print(name, "start")

    await asyncio.sleep(2)

    print(name, "done")


async def main():
    await asyncio.gather(
        worker("A"),
        worker("B"),
        worker("C"),
    )


asyncio.run(main())
```

总耗时约 2 秒。

---

## 3.9A.2 Coroutine

调用：

```python
worker("A")
```

首先返回：

```text
Coroutine Object
```

Coroutine 保存：

```text
执行位置
Local Variables
等待状态
```

可以：

```text
暂停
恢复
```

---

## 3.9A.3 Event Loop

`asyncio.run(main())` 大致：

```text
创建 Event Loop
↓
调度 main Coroutine
↓
运行直到 main 完成
↓
关闭 Event Loop
```

---

## 3.9A.4 Ready Queue / Task State

Task 状态可理解：

```text
CREATED
↓
READY
↓
RUNNING
↓
await
↓
WAITING
↓
事件完成
↓
READY
↓
RUNNING
↓
DONE
```

Ready Queue：

> 当前可以运行的 Task 队列。

---

## 3.9A.5 await 发生什么

当 A 执行：

```python
await asyncio.sleep(2)
```

如果等待对象未完成：

```text
保存 A 当前执行状态
↓
A → WAITING
↓
注册 2 秒 Timer
↓
控制权返回 Event Loop
↓
Event Loop 运行 B / C
```

所以：

> `await` 的核心不是“卡住等待”，而是“暂停当前 Task，让别人先运行”。

---

## 3.9A.6 time.sleep vs asyncio.sleep

```python
time.sleep(2)
```

会：

```text
阻塞整个 OS Thread
↓
Event Loop 也停
```

```python
await asyncio.sleep(2)
```

会：

```text
只暂停当前 Task
↓
Event Loop 继续
```

---

## 3.9A.7 Timer 到期

两秒后：

```text
Timer Ready
↓
Task A WAITING → READY
↓
进入 Ready Queue
↓
Event Loop 再次调度 A
↓
从 await 后继续
```

不是从函数开头重新执行。

---

## 3.9A.8 Future

**Future**

可以理解：

> 一个以后才有结果的对象。

状态：

```text
PENDING
↓
DONE
```

Task 等待 Future：

```text
Future 完成
↓
Task 重新 READY
```

---

## 3.9A.9 epoll

Linux Event Loop 常使用：

**epoll**

用于：

> 高效等待大量 File Descriptor 可读 / 可写事件。

不是不断轮询：

```text
A 有数据吗？
B 有数据吗？
C 有数据吗？
```

而是：

```text
Event Loop
↓
epoll_wait()
↓
Kernel
↓
FD Ready 时唤醒
```

---

## 3.9A.10 两级调度

最重要：

```text
CPU
↑
Linux Scheduler
↑
OS Thread
↑
Event Loop
↑
Task A / B / C
```

Kernel：

> 调度 Thread。

Event Loop：

> 调度 Async Task。

Linux Kernel 不知道 Python Task A/B/C 的存在。

---

## 3.9A.11 Async Task Switch ≠ OS Context Switch

Task A：

```text
await
↓
Event Loop
↓
Task B
```

A / B 通常都在同一个 OS Thread。

因此：

> Task Switch 通常不需要完整 Kernel Thread Context Switch。

---

## 3.9A.12 完整 Socket 等待链

```text
Task A
↓
await socket.read()
↓
A WAITING
↓
Event Loop 无 READY Task
↓
epoll_wait()
↓
Python Thread Sleep
```

网络来了：

```text
NIC
↓
Kernel TCP Stack
↓
Socket FD Ready
↓
epoll wakeup
↓
Python Thread Runnable
↓
Linux Scheduler 给 CPU
↓
Event Loop
↓
Task A READY
↓
Task A resume
```

---

## 3.9A.13 Event Loop Blocking

错误：

```python
async def bad():
    while True:
        pass
```

或者：

```python
async def handler():
    huge_cpu_work()
```

长时间不 `await`：

> 会霸占 Event Loop Thread，其他 Task 全部被拖住。

---

# 3.10 GIL 与 Python 性能初步

## 3.10.1 CPython

**CPython**

是最主流的 Python Interpreter 实现之一。

区别：

```text
Python
→ Programming Language

CPython
→ Interpreter Implementation
```

---

## 3.10.2 GIL

**GIL**

Global Interpreter Lock。

传统 CPython 中：

> 一个 Process 内通常只有一个 Thread 能在某一时刻执行 Python Bytecode。

错误理解：

```text
Python 只能有一个 Thread
```

正确：

```text
一个 Process 可以有很多 Thread
但 Python Bytecode 执行受到 GIL 限制
```

---

## 3.10.3 GIL 与业务 Lock 不同

GIL：

```text
保护 Interpreter 内部执行
```

不是：

```text
自动保护你的 dict / counter / list
```

所以 Shared State 仍可能 Race。

---

## 3.10.4 CPU-bound Thread

```python
def cpu_work(n):
    total = 0

    for i in range(n):
        total += i * i

    return total
```

多个 Thread 都持续需要执行 Python Bytecode，因此都竞争 GIL。

结果通常：

```text
2 Threads
≠
2x Speedup
```

甚至可能因为：

```text
Context Switch
GIL Contention
Cache Effect
```

更慢。

---

## 3.10.5 Multi-Process

```text
Process A
→ Interpreter A
→ GIL A

Process B
→ Interpreter B
→ GIL B
```

因此可以：

```text
Core 0 → A
Core 1 → B
```

真正多核运行纯 Python CPU Work。

---

## 3.10.6 I/O-bound Thread

Socket / HTTP 等待时：

```text
Thread
↓
Kernel I/O Wait
```

不需要持续执行 Python Bytecode。

其他 Thread 可以获得运行机会。

所以：

```text
I/O-bound
→ Thread 很有价值
```

---

## 3.10.7 关键判断

```text
Pure Python CPU-bound
→ GIL 影响大

I/O-bound
→ GIL 通常不是主要问题
```

---

## 3.10.8 Native Code

**Native Code**

编译后的本地机器代码。

NumPy：

```text
Python
↓
NumPy
↓
C / BLAS
↓
CPU
```

PyTorch CPU：

```text
Python
↓
PyTorch
↓
C++ Backend
↓
CPU Kernel
```

PyTorch GPU：

```text
Python
↓
PyTorch
↓
CUDA
↓
GPU Kernel
```

---

## 3.10.9 GIL 不锁 GPU

GIL 只和：

```text
CPython Interpreter Execution
```

有关。

它不是：

```text
CPU 全局锁
GPU 全局锁
整台机器锁
```

GPU 仍然按照自己的 Massive Parallelism 工作。

---

## 3.10.10 Vectorization

**Vectorization**

将：

```text
大量逐元素 Python Loop
```

交给：

```text
NumPy / PyTorch / Native Library
```

批量处理。

例如：

```python
result = values * 2
```

通常比 Python for-loop 快很多。

---

## 3.10.11 Interpreter / Object Overhead

Python 操作可能涉及：

```text
Bytecode
Type
Object Metadata
Reference Count
Operation Dispatch
```

Python `list[float]` 通常比：

```text
NumPy float32 array
```

内存更松散、Object Overhead 更大。

---

## 3.10.12 Memory Layout

NumPy Array 更接近：

```text
[float][float][float][float]
```

连续、紧凑。

更适合：

```text
CPU Cache
SIMD
BLAS
GPU Transfer
```

---

## 3.10.13 Bottleneck

**Bottleneck**

限制系统性能的主要部分。

AI Infra 可能是：

```text
CPU
GPU Compute
GPU Memory Bandwidth
KV Cache
Network
Storage
Scheduler
Tokenization
```

所以：

> 看到 Python 不等于 Python 一定是瓶颈。

---

## 3.10.14 Profiling

正确优化流程：

```text
Measure
↓
Find Bottleneck
↓
Optimize
↓
Measure Again
```

**Profiling**

用于确定：

```text
时间花在哪里
CPU 花在哪里
Memory 花在哪里
```

简单：

```python
start = time.perf_counter()

do_work()

elapsed = (
    time.perf_counter() - start
)
```

---

## 3.10.15 Wall Time / CPU Time

**Wall Time**

实际经过时间。

**CPU Time**

真正使用 CPU 的累计时间。

例如：

```text
程序跑 10 秒
9 秒在等网络
1 秒在算
```

则：

```text
Wall Time ≈ 10s
CPU Time ≈ 1s
```

---

## 3.10.16 Speedup / Scaling

Speedup：

```text
串行 10s
并行 6s

10 / 6
≈ 1.67x
```

Scaling：

> 增加资源后性能如何变化。

不应期待：

```text
N Core
→ 精确 N 倍
```

---

## 3.10.17 Amdahl's Law

**Amdahl's Law**

核心：

> 如果程序有一部分永远不能并行，那么增加无限 CPU 也无法获得无限加速。

当前理解概念即可。

---

## 3.10.18 Async 与 GIL

Async 通常是：

```text
1 Thread
↓
很多 Task
```

它解决：

```text
I/O Concurrency
```

不是：

```text
CPU Multi-Core Parallelism
```

Async 中重 CPU Code 仍会卡 Event Loop。

---

## 3.10.19 Async + Thread / Process Pool

现实常见：

```text
Event Loop
├─ Async HTTP
├─ Async Socket
│
├─ Blocking SDK
│   ↓
│ Thread Pool
│
└─ CPU-heavy Work
    ↓
  Process Pool
```

---

## 3.10.20 Latency / Throughput

**Latency**

单请求耗时。

**Throughput**

单位时间完成工作量：

```text
Requests/sec
Tokens/sec
```

并发提高可能：

```text
Throughput ↑
Latency ↑
```

所以性能分析不能只看“快不快”。

---

# 3.6 ～ 3.10 综合心智模型

```text
Python Automation
│
├─ subprocess
│   └─ Linux Child Process
│
├─ HTTP
│   ├─ requests
│   ├─ JSON
│   ├─ Session
│   └─ Retry / Timeout
│
├─ Socket
│   ├─ TCP
│   ├─ UDP
│   └─ Kernel Network Stack
│
├─ Concurrency
│   ├─ Thread
│   ├─ Process
│   └─ Async
│
├─ Event Loop
│   ├─ Coroutine
│   ├─ Task
│   ├─ Future
│   ├─ Ready Queue
│   └─ epoll
│
└─ Performance
    ├─ GIL
    ├─ CPU-bound
    ├─ I/O-bound
    ├─ Native Code
    ├─ Vectorization
    ├─ Profiling
    └─ Bottleneck
```

---

# 高频速查

## subprocess

```python
subprocess.run(
    command,
    capture_output=True,
    text=True,
    timeout=5,
)
```

## HTTP

```python
response = requests.get(
    url,
    timeout=(2, 10),
)

response.raise_for_status()

data = response.json()
```

## TCP Client

```python
with socket.create_connection(
    (host, port),
    timeout=3,
) as sock:
    sock.sendall(data)
    response = sock.recv(4096)
```

## Thread Pool

```python
with ThreadPoolExecutor(
    max_workers=20
) as executor:
    ...
```

## Process Pool

```python
with ProcessPoolExecutor(
    max_workers=4
) as executor:
    ...
```

## Async

```python
async def worker():
    result = await something()
    return result
```

---

# 3.6 ～ 3.10 最重要的 20 句话

1. `subprocess` 把 Python 和 Linux Child Process 连接起来。
2. 自动化默认优先 Argument List，而不是 `shell=True`。
3. Command Automation 必须考虑 Exit Code、stderr、Timeout。
4. 机器自动化优先使用 JSON / CSV 等 Machine-Readable Output。
5. Python HTTP Client 的底层仍然是 DNS → TCP → TLS → HTTP。
6. ConnectionError 与 HTTP 404/500 是不同层次的问题。
7. HTTP Retry 必须考虑 Idempotency 和 Backoff。
8. Socket 是 Process 使用 Kernel Network Stack 的通信端点。
9. TCP 是 Byte Stream，不保留 Application Message Boundary。
10. `bind → listen → accept` 是 TCP Server 基本路径。
11. Concurrency 不等于 Parallelism。
12. Thread 适合中等规模 I/O-bound。
13. Process 更适合 Pure Python CPU-bound。
14. Async 适合大量 I/O Connection。
15. Event Loop 调度 Task，Linux Kernel 调度 OS Thread，这是两级调度。
16. `await` 的本质是：等待对象未完成时暂停当前 Task，并把执行权还给 Event Loop。
17. Linux Event Loop 常通过 epoll 等机制等待大量 FD 事件。
18. GIL 主要限制传统 CPython 同一 Process 内 Python Bytecode 的并行执行。
19. NumPy / PyTorch 大量计算进入 Native Code / CUDA，不等于被 GIL 限制住全部计算。
20. 性能优化第一原则是先找 Bottleneck，再决定 Thread / Process / Async / Native / GPU。

---

# 当前课程目录

```text
第 0 章：AI Infra 心智模型
✅ 完成

第 1 章：Linux 与计算机系统基础
✅ 完成

第 2 章：计算机网络基础
✅ 完成

第 3 章：Python + Go
🟨 进行中

✅ 3.1 Python 在 AI Infra 里的角色
✅ 3.2 Python Runtime / venv / uv
✅ 3.3 Python Data Structures
✅ 3.4 Function / Module / Package
✅ 3.5 File / JSON / YAML
✅ 3.6 subprocess 与 Linux Automation
✅ 3.7 HTTP Client 与 API
✅ 3.8 Socket 初步
✅ 3.9 Thread / Process / Async
✅ 3.9A await / Event Loop 调度机制深入
✅ 3.10 GIL 与 Python 性能初步

⬜ 3.11 Logging / Error Handling
⬜ 3.12 AI Infra Python 小工具实战

⬜ 3.13 Go 在 AI Infra 里的角色
⬜ 3.14 Go 基础语法与类型
⬜ 3.15 Struct / Interface
⬜ 3.16 Goroutine / Channel
⬜ 3.17 Go HTTP / JSON
⬜ 3.18 Go CLI / Daemon
⬜ 3.19 Python vs Go
⬜ 3.20 AI Infra Go 小工具实战
```

---

> 下一主线：**3.11 Logging / Error Handling**
>
> 会把前面的 subprocess、HTTP、Socket、Concurrency 代码进一步变成生产式 Infra Tool：Logging Level、Structured Logging、Traceback、Exception Chain、何时 catch、何时 raise，以及怎样输出既适合机器解析又方便人排障的日志。
