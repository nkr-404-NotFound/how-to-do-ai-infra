# LLM / AI Infra 学习笔记
# 第 3 章 Go 完整篇（3.13 ～ 3.20）

> 目标：面向 AI Infra / Cloud Native / Agent / Controller / CLI / Daemon / HTTP Service 学习 Go。
>
> 建议环境：WSL2 + Ubuntu + Go Toolchain。
>
> 本文不是通用 Go 语法手册，而是围绕 AI Infra 实际用途组织：**Linux Process → Go Runtime → Goroutine → HTTP / CLI / Daemon → Agent / Controller**。

---

# 总目录

```text
第 3 章：Python + Go

Python：
✅ 3.1～3.12 完成

Go：
✅ 3.13 Go 在 AI Infra 里的角色
✅ 3.14 Go 基础语法与类型
✅ 3.15 Struct / Interface
✅ 3.16 Goroutine / Channel
✅ 3.16A GMP Scheduler 深入
✅ 3.17 Go HTTP / JSON
✅ 3.18 Go CLI / Daemon
✅ 3.18A signal.NotifyContext 的 stop
✅ 3.19 Python vs Go
✅ 3.20 AI Infra Go 小工具实战
```

---

# 3.13 Go 在 AI Infra 里的角色

## 3.13.1 先建立定位

Go 不是用来替代 Python 的。

在 AI Infra 里，更实用的理解是：

```text
Python
→ 开发效率高
→ Automation / API Client / Benchmark / AI Ecosystem

Go
→ 部署简单
→ Network Service / Agent / CLI / Controller / Infra Daemon
```

一个非常常见的 AI Infra 分层：

```text
Go
↓
Controller / Agent / Gateway
↓
HTTP / gRPC
↓
Python
↓
PyTorch / vLLM / SGLang
↓
C++ / CUDA
↓
GPU
```

---

## 3.13.2 Go 是什么

Go 是一门：

- 静态类型语言（Static Typing）
- 编译型语言（Compiled Language）
- 通用编程语言

例如：

```go
var port int = 8000
```

`port` 的类型已经是 `int`，后面不能直接写：

```go
port = "hello"
```

Python 则是动态类型：

```python
port = 8000
port = "hello"
```

---

## 3.13.3 编译模型

Go：

```text
main.go
↓
Go Compiler
↓
Executable Binary
↓
Linux / macOS / Windows
```

常见：

```bash
go build
```

得到：

```bash
./mytool
```

Python：

```text
app.py
↓
Python Interpreter
↓
Runtime Execute
```

Go：

```text
main.go
↓
go build
↓
Binary
↓
直接运行
```

---

## 3.13.4 Binary

Linux 下可以：

```bash
file ./mytool
```

看到类似：

```text
ELF executable
```

ELF 是 Linux 常见可执行文件格式。

很多 Cloud Native 工具本质上就是普通 Binary：

```text
kubectl
prometheus
terraform
caddy
containerd 生态组件
```

从 OS 视角：

> Go 程序最终仍然只是普通 Linux Process。

---

## 3.13.5 为什么 Go 部署舒服

Python 应用经常需要：

```text
Python Version
venv
Dependencies
pip / uv
site-packages
```

Go 很多时候：

```text
go build
↓
Binary
↓
复制到服务器
↓
运行
```

例如：

```bash
scp mytool server:/usr/local/bin/
```

然后：

```bash
mytool
```

这非常适合：

```text
100 台 Node
1000 台 Node
Container
Kubernetes Pod
CI Runner
Cloud VM
```

---

## 3.13.6 Static / Dynamic Linking

**Static Binary** 粗略理解：

> 程序运行所需的大量代码已经链接进 Binary。

**Dynamic Linking** 则可能依赖：

```text
libc.so
libssl.so
其他 .so
```

`.so` 就是 Linux Shared Object / Dynamic Library。

Go 并不是永远 100% 静态，是否有动态依赖取决于：

```text
Build Options
CGO
System Library
Target Platform
```

---

## 3.13.7 CGO

**CGO** 是 Go 和 C Code 互操作的一种机制。

如果项目依赖：

```text
C Library
System Native Library
```

Build / Linking 会更复杂。

当前只需要认识概念。

---

## 3.13.8 Cross Compilation

**Cross Compilation**：

> 在一个平台上，为另一个 OS / CPU Architecture 编译程序。

例如：

```bash
GOOS=linux \
GOARCH=amd64 \
go build
```

两个重要变量：

```text
GOOS
→ Target Operating System

GOARCH
→ Target CPU Architecture
```

常见：

```text
GOOS:
linux
darwin
windows

GOARCH:
amd64
arm64
```

查看：

```bash
go env GOOS GOARCH
```

---

## 3.13.9 Go Runtime

Go 虽然编译成 Binary，但不是“没有 Runtime”。

Go Runtime 负责：

```text
Memory Management
Garbage Collection
Goroutine Scheduling
Stack Management
Network Polling
```

目标机器通常不需要额外安装一个 Go Runtime 才能运行普通 Go Binary。

---

## 3.13.10 GC

**GC = Garbage Collection**，垃圾回收。

长期 Service 会不断创建：

```text
Request Object
JSON Object
Buffer
Struct
Slice
```

GC 自动回收不再使用的对象，减少手动内存管理复杂度。

但 GC 也有成本：

```text
CPU
Heap Metadata
Object Scan
Pause / Scheduling Cost
```

后续性能章节再深入。

---

## 3.13.11 Daemon / Agent / Exporter

### Daemon

长期后台运行的 Process：

```text
sshd
containerd
prometheus
node exporter
```

模式：

```text
启动
↓
长期运行
↓
监听事件 / 网络 / 文件
↓
直到被停止
```

### Agent

部署在某个 Node 上的小型后台程序，负责：

```text
采集
执行
上报
管理
```

例如：

```text
Node Agent
Monitoring Agent
Log Agent
GPU Agent
```

### Exporter

Prometheus 生态里常表示：

> 采集某类系统指标，并通过 HTTP `/metrics` 暴露。

例如：

```text
Node Exporter
DCGM Exporter
```

---

## 3.13.12 Controller / Reconciliation / Operator

### Controller

可以理解成：

> 持续观察 Current State，并让它靠近 Desired State。

例如：

```text
Desired:
replicas = 3

Current:
replicas = 2
```

Controller：

```text
发现少 1 个
↓
创建 1 个
```

### Reconciliation

```text
Observe
↓
Compare
↓
Act
↓
Observe Again
```

这叫：

**Reconciliation**（调谐 / 状态协调）。

### Operator

Operator 可以理解为：

> 用 Kubernetes API 管理复杂 Application 生命周期的 Controller。

常见于：

```text
Database
Ray Cluster
GPU Workload
AI Platform
```

---

## 3.13.13 Go Standard Library

Go 自带大量 Infra 常用库：

```text
net
net/http
os
io
encoding/json
context
log
sync
time
```

这是 Go 适合 Infra 的重要原因。

---

## 3.13.14 Goroutine 初步

**Goroutine**：

> Go Runtime 管理的轻量级并发执行单元。

```go
go worker()
```

表示：

> 启动一个 Goroutine 执行 `worker()`。

注意：

```text
Goroutine
≠
OS Thread
```

---

## 3.13.15 M:N Scheduling

粗略：

```text
很多 Goroutine
↓
Go Runtime Scheduler
↓
多个 OS Threads
↓
多个 CPU Cores
```

这是一种 M:N 调度模型。

---

## 3.13.16 Channel

**Channel**：

> Goroutine 之间传递数据和同步的机制。

```text
Producer Goroutine
↓
Channel
↓
Consumer Goroutine
```

后面 3.16 深入。

---

## 3.13.17 context

`context` 主要用于传播：

```text
Cancellation
Deadline
Timeout
Request-scoped metadata
```

例如：

```text
Client 取消 Request
↓
Server Handler
↓
DB Query
↓
一起取消
```

---

## 3.13.18 Error Handling

Python：

```python
try:
    ...
except Exception:
    ...
```

Go：

```go
result, err := doSomething()

if err != nil {
    ...
}
```

Go 的思想：

> Error Flow 显式写在控制流里。

---

## 3.13.19 panic

Go 有：

```text
panic
```

但普通业务错误通常应该：

```text
return error
```

例如：

```text
HTTP 503
File Not Found
Invalid Input
```

不应该随便 panic。

---

## 3.13.20 Struct / Interface 初步

### Struct

```go
type Server struct {
    Name string
    Host string
    Port int
}
```

### Interface

```go
type Checker interface {
    Check() error
}
```

后面 3.15 深入。

---

## 3.13.21 Go Module / Toolchain

初始化：

```bash
go mod init example.com/project
```

核心文件：

```text
go.mod
go.sum
```

常用命令：

```bash
go build
go run
go test
go fmt
go vet
```

---

## 3.13.22 最小 Go 程序

```go
package main

import "fmt"

func main() {
    fmt.Println(
        "hello ai infra",
    )
}
```

运行：

```bash
go run main.go
```

编译：

```bash
go build \
  -o ai-infra-demo \
  main.go
```

运行：

```bash
./ai-infra-demo
```

---

## 3.13.23 Go Program 仍然是普通 Linux Process

```go
package main

import (
    "fmt"
    "os"
    "time"
)

func main() {
    fmt.Println(
        "pid:",
        os.Getpid(),
    )

    time.Sleep(
        60 * time.Second,
    )
}
```

运行后：

```bash
ps -fp <PID>
ls /proc/<PID>
```

所以：

```text
Go Binary
↓
Linux Process
↓
PID
Virtual Memory
FD
Threads
Sockets
/proc
```

---

## 3.13 核心结论

1. Go 是静态类型、编译型语言。
2. Go Binary 部署简单，非常适合 Agent / CLI / Daemon。
3. Go 虽然编译，但仍然有 Runtime。
4. Goroutine 不是 OS Thread。
5. Go Runtime Scheduler 管 Goroutine，Linux Scheduler 管 OS Thread。
6. Go Networking / HTTP Standard Library 很强。
7. Static Typing 对大型 Infra 项目维护很有价值。
8. Python 和 Go 在 AI Infra 中是分工关系。
9. Python 更偏 AI / Automation；Go 更偏 Cloud Native / Long-running Infra。
10. 无论 Go 多高级，最终仍然落到 Linux Process / FD / Socket / Scheduler。

---

# 3.14 Go 基础语法与类型

## 3.14.1 Package / main / import

```go
package main

import "fmt"

func main() {
    fmt.Println(
        "hello ai infra",
    )
}
```

`package main`：

> 可执行程序所在 Package。

`func main()`：

> Entry Point。

`import`：

> 导入其他 Package。

---

## 3.14.2 Variable

显式：

```go
var port int = 8000
```

推断：

```go
var port = 8000
```

最常用：

```go
port := 8000
```

### `:=` vs `=`

```text
:=
→ declare + assign

=
→ assign
```

---

## 3.14.3 Scope

**Scope**：变量名有效范围。

```go
func main() {
    port := 8000
}
```

`port` 只在 `main()` 内有效。

---

## 3.14.4 Unused Variable / Import

Go 对无用变量和 Import 很严格。

```go
func main() {
    x := 10
}
```

如果 `x` 未使用，Compiler 报错。

这减少无效代码和旧依赖残留。

---

## 3.14.5 基础类型

```text
bool
string
int
int64
uint
uint64
float64
```

示例：

```go
healthy := true
host := "127.0.0.1"
port := 8000
timeout := 2.5
```

---

## 3.14.6 byte / []byte / rune

`byte` 本质：

```text
uint8
```

常用于：

```text
Network Data
File Data
Buffer
```

`[]byte`：

```go
data := []byte(
    "hello",
)
```

`rune` 本质：

```text
int32
```

通常表示 Unicode Code Point。

---

## 3.14.7 UTF-8

```go
s := "你"
```

`len(s)` 返回 UTF-8 Byte Length，不是字符数量。

遍历 Unicode：

```go
for _, r := range "你好" {
    fmt.Println(r)
}
```

---

## 3.14.8 Type Conversion

Go 不喜欢隐式转换：

```go
var a int = 10
var b int64 = int64(a)
```

这能减少：

```text
Bytes
Milliseconds
Seconds
Port
File Size
```

等单位混淆。

---

## 3.14.9 Zero Value

```go
var port int
var host string
var ok bool
```

得到：

```text
port → 0
host → ""
ok   → false
```

常见：

```text
int      → 0
float64  → 0
bool     → false
string   → ""
pointer  → nil
slice    → nil
map      → nil
```

---

## 3.14.10 nil

```go
var p *int
```

此时：

```text
p == nil
```

`nil` 可用于：

```text
Pointer
Slice
Map
Channel
Function
Interface
```

---

## 3.14.11 const

```go
const DefaultPort = 8000
```

Constant 不能重新赋值。

---

## 3.14.12 if / switch

```go
if port == 8000 {
    fmt.Println(
        "default port",
    )
}
```

Go Condition 必须是 bool。

`switch`：

```go
switch protocol {
case "http":
    fmt.Println("HTTP")
case "tcp":
    fmt.Println("TCP")
default:
    fmt.Println("unknown")
}
```

---

## 3.14.13 for

经典：

```go
for i := 0; i < 3; i++ {
    fmt.Println(i)
}
```

while 风格：

```go
for running {
    ...
}
```

无限循环：

```go
for {
    ...
}
```

Daemon / Controller 中很常见。

---

## 3.14.14 Array

```go
var ports [3]int
```

固定长度。

`[3]int` 和 `[4]int` 是不同 Type。

---

## 3.14.15 Slice

```go
ports := []int{
    8000,
    8001,
    8002,
}
```

Slice 可以粗略理解：

```text
Pointer to Backing Array
Length
Capacity
```

### len / cap

```go
len(ports)
cap(ports)
```

### append

```go
ports = append(
    ports,
    9000,
)
```

`append()` 可能分配新的 Backing Array，所以通常必须接住返回值。

---

## 3.14.16 Slice Sharing

```go
a := []int{
    1, 2, 3, 4,
}

b := a[1:3]
```

`a` / `b` 可能共享同一 Backing Array。

```go
b[0] = 99
```

可能导致：

```text
a[1] == 99
```

---

## 3.14.17 copy

需要独立数据：

```go
dst := make(
    []int,
    len(src),
)

copy(
    dst,
    src,
)
```

---

## 3.14.18 make / new

`make` 用于：

```text
Slice
Map
Channel
```

例如：

```go
ports := make(
    []int,
    0,
    10,
)
```

`new(T)`：

> 分配一个 T，返回 `*T`。

```go
p := new(int)
```

---

## 3.14.19 Map

```go
ports := map[string]int{
    "http":    8000,
    "metrics": 9090,
}
```

Lookup：

```go
port := ports["http"]
```

如果 Key 不存在，返回 Zero Value。

所以常用：

```go
port, ok := ports["http"]

if !ok {
    ...
}
```

这叫：

**comma-ok idiom**。

---

## 3.14.20 nil Map

```go
var ports map[string]int
```

读取可以，但写：

```go
ports["http"] = 8000
```

会 panic。

应先：

```go
ports := make(
    map[string]int,
)
```

---

## 3.14.21 range

Slice：

```go
for index, port := range ports {
    fmt.Println(
        index,
        port,
    )
}
```

忽略 index：

```go
for _, port := range ports {
    fmt.Println(port)
}
```

`_`：

**Blank Identifier**，表示明确忽略某个值。

不要用 `_` 随便吞掉 Error。

---

## 3.14.22 Map Iteration Order

不要依赖 Go Map 遍历顺序。

需要稳定输出：

```text
收集 Key
↓
排序
↓
再遍历
```

---

## 3.14.23 Function

```go
func add(
    a int,
    b int,
) int {
    return a + b
}
```

多返回值：

```go
func lookupPort(
    name string,
) (
    int,
    bool,
) {
    ...
}
```

---

## 3.14.24 error

```go
func loadConfig(
    path string,
) (
    []byte,
    error,
) {
    ...
}
```

调用：

```go
data, err := loadConfig(
    "config.json",
)

if err != nil {
    return err
}
```

---

## 3.14.25 Error Wrapping

创建：

```go
err := fmt.Errorf(
    "invalid port: %d",
    port,
)
```

Wrap：

```go
return fmt.Errorf(
    "load config: %w",
    err,
)
```

`%w` 保留底层 Error Chain。

---

## 3.14.26 Pointer

```go
port := 8000
p := &port
```

`&port`：地址。

`p` 类型：

```text
*int
```

解引用：

```go
fmt.Println(
    *p,
)
```

修改：

```go
*p = 9000
```

---

## 3.14.27 Pass by Value

Go 参数全部按 Value 传递。

```go
func setPort(
    port int,
) {
    port = 9000
}
```

不会改调用方。

需要修改：

```go
func setPort(
    port *int,
) {
    *port = 9000
}
```

调用：

```go
setPort(
    &port,
)
```

Slice / Map 也仍然是 Pass by Value，只是 Value 内部持有对底层数据结构的引用信息。

---

## 3.14.28 Variadic

```go
func logValues(
    values ...string,
) {
    ...
}
```

调用：

```go
logValues(
    "a",
    "b",
)
```

已有 Slice：

```go
values := []string{
    "a",
    "b",
}

logValues(
    values...,
)
```

---

## 3.14.29 defer

```go
file, err := os.Open(
    "config.json",
)

if err != nil {
    return err
}

defer file.Close()
```

适合：

```text
File
Socket
HTTP Body
Lock
```

多个 defer：

```text
LIFO
```

---

## 3.14.30 Exported Identifier

大写：

```go
func CheckHealth() {}
```

其他 Package 可访问。

小写：

```go
func checkHealth() {}
```

只在当前 Package 内可访问。

---

## 3.14.31 time.Duration

```go
timeout := 2 * time.Second
```

比：

```go
timeout := 2000
```

语义更明确。

---

## 3.14 核心结论

1. `:=` = declare + assign；`=` = assign。
2. Go 是 Static Typing + Type Inference。
3. Zero Value 是 Go 很重要的设计。
4. Condition 必须是 bool。
5. Array 固定长度，Slice 更常用。
6. Slice 共享 Backing Array 时注意别名问题。
7. `append()` 返回新 Slice。
8. Map Lookup 常用 comma-ok。
9. Map 遍历顺序不可靠。
10. Function 常见 `value, error` 多返回值。
11. `%w` 用于 Error Wrapping。
12. Go 参数全部 Pass by Value。
13. `defer` 用于 Resource Cleanup。
14. Go Infra 风格强调类型明确、错误显式、资源生命周期清楚。

---

# 3.15 Struct / Interface

## 3.15.1 Struct

```go
type Target struct {
    Name string
    Host string
    Port int
}
```

Struct：

> 把多个相关 Field 组合成新的 Type。

创建：

```go
target := Target{
    Name: "vllm-01",
    Host: "10.0.0.21",
    Port: 8000,
}
```

---

## 3.15.2 为什么固定结构优先 Struct

长期业务逻辑不应滥用：

```go
map[string]any
```

Struct 可以让 Compiler 知道：

```text
字段是否存在
字段名是否拼对
字段应该是什么类型
```

---

## 3.15.3 Struct Zero Value

```go
var target Target
```

得到：

```text
Name = ""
Host = ""
Port = 0
```

类型合法不等于业务合法，所以仍需 Validation。

---

## 3.15.4 Method

普通 Function：

```go
func checkTarget(
    target Target,
) error {
    ...
}
```

Method：

```go
func (
    target Target,
) Check() error {
    ...
}
```

调用：

```go
target.Check()
```

---

## 3.15.5 Receiver

```go
func (
    t Target,
) Address() string {
    ...
}
```

`t Target` 就是 Receiver。

---

## 3.15.6 Value Receiver / Pointer Receiver

Value Receiver：

```go
func (
    t Target,
) Address() string {
    ...
}
```

Pointer Receiver：

```go
func (
    t *Target,
) SetPort(
    port int,
) {
    t.Port = port
}
```

Pointer Receiver 常用于：

```text
修改 Struct
避免大 Struct Copy
保持 Receiver 风格一致
```

---

## 3.15.7 Constructor Function

Go 没有传统 Constructor Keyword。

常见：

```go
func NewTarget(
    name string,
    host string,
    port int,
) (
    *Target,
    error,
) {
    if name == "" {
        return nil,
            fmt.Errorf(
                "name cannot be empty",
            )
    }

    return &Target{
        Name: name,
        Host: host,
        Port: port,
    }, nil
}
```

不是每个 Struct 都需要 `NewXxx()`。

---

## 3.15.8 Composition

Go 更偏向：

```text
Composition
+
Interface
```

而不是复杂 Class Inheritance。

例如：

```go
type HTTPChecker struct {
    Client  *http.Client
    Timeout time.Duration
}
```

表示：

> HTTPChecker 拥有一个 Client。

---

## 3.15.9 Embedding

```go
type Metadata struct {
    Name string
}

type Target struct {
    Metadata
    Host string
    Port int
}
```

可以：

```go
target.Name
```

这叫 Field Promotion。

但：

> Embedding ≠ Inheritance。

---

## 3.15.10 Interface

```go
type Checker interface {
    Check() error
}
```

Interface：

> 描述行为 Contract，而不是数据结构。

---

## 3.15.11 Implicit Interface Implementation

```go
type TCPChecker struct {
    Host string
    Port int
}

func (
    c TCPChecker,
) Check() error {
    ...
}
```

只要 Method Set 满足 Interface，就自动实现。

不需要：

```text
implements Checker
```

---

## 3.15.12 Polymorphism

```go
type Checker interface {
    Check() error
}
```

然后：

```text
TCPChecker
HTTPChecker
LLMChecker
```

统一：

```go
checkers := []Checker{
    TCPChecker{},
    HTTPChecker{},
}
```

这就是 Go 常见多态方式。

---

## 3.15.13 Small Interface

推荐：

```go
type Checker interface {
    Check() error
}
```

而不是一次塞十几个 Method。

优点：

```text
实现简单
耦合低
容易测试
容易替换
```

---

## 3.15.14 Consumer Defines Interface

一个很重要的习惯：

> Interface 往往由“使用它的那一方”定义。

因为 Interface 表达：

> 我需要什么能力。

---

## 3.15.15 Method Set

如果：

```go
func (
    t Target,
) Check() error
```

那么 `Target` 和 `*Target` 通常都能调用。

如果：

```go
func (
    t *Target,
) Check() error
```

Interface Satisfaction 主要属于：

```text
*Target
```

编译时检查：

```go
var _ Checker = (
    (*TCPChecker)(nil)
)
```

---

## 3.15.16 any

`any` 是：

```text
interface{}
```

的别名。

```go
var value any

value = 10
value = "hello"
value = Target{}
```

但 Static Type 仍然是 `any`。

---

## 3.15.17 Type Assertion / Type Switch

Assertion：

```go
target, ok :=
    value.(Target)
```

Type Switch：

```go
switch v := value.(type) {
case string:
    fmt.Println(
        "string:",
        v,
    )
case int:
    fmt.Println(
        "int:",
        v,
    )
}
```

---

## 3.15.18 nil Interface 坑

```go
var p *MyError = nil
var err error = p
```

此时：

```text
err != nil
```

可能成立。

可以粗略理解 Interface Value 包含：

```text
Dynamic Type
+
Dynamic Value
```

所以成功返回 `error` 时，直接：

```go
return nil
```

最安全。

---

## 3.15.19 Struct Tag

```go
type Target struct {
    Name string `json:"name"`
    Host string `json:"host"`
    Port int    `json:"port"`
}
```

Struct Tag 是 Field Metadata。

常用于：

```text
JSON
YAML
Validation
ORM
```

---

## 3.15.20 Dependency Injection

```go
type HTTPChecker struct {
    Client *http.Client
    URL    string
}
```

而不是内部每次自己：

```go
client := &http.Client{}
```

从外部传入依赖，有利于：

```text
统一配置
测试
替换实现
复用连接池
```

---

## 3.15.21 Mock / Fake

```go
type FakeClient struct {
    Err error
}

func (
    f FakeClient,
) Check() error {
    return f.Err
}
```

Small Interface 会让测试很舒服。

---

## 3.15.22 “Accept interfaces, return structs”

常见习惯：

> Parameter 可以依赖小 Interface；创建 Function 通常返回 Concrete Struct / Pointer。

不是绝对规则，但很实用。

---

## 3.15 核心结论

1. Struct 定义具体数据结构。
2. Method 定义 Type 的行为。
3. Pointer Receiver 用于修改对象或避免复制。
4. Go 强调 Composition，而不是复杂继承。
5. Interface 描述行为 Contract。
6. Interface 是隐式实现。
7. 小 Interface 更灵活。
8. `any` 不应替代业务 Struct。
9. Struct Tag 是 JSON/YAML 重要桥梁。
10. Dependency Injection 对长期 Infra 项目很重要。
11. Interface 让多个 Concrete Type 可统一处理。

---

# 3.16 Goroutine / Channel

## 3.16.1 `go` 关键字

普通：

```go
worker("A")
```

当前 Goroutine 会等 `worker()` 返回。

而：

```go
go worker("A")
```

表示：

> 创建新的 Goroutine，让 Runtime 调度执行；当前 Goroutine 继续往下。

---

## 3.16.2 main 本身也是 Goroutine

```text
Go Process
│
├─ main Goroutine
├─ worker A Goroutine
├─ worker B Goroutine
└─ worker C Goroutine
```

main 一旦结束：

> 整个 Process 结束，Go 不会自动等待其他 Goroutine。

---

## 3.16.3 WaitGroup

用于：

> 等待一组 Goroutine 完成。

```go
var wg sync.WaitGroup

wg.Add(3)

go worker(
    "A",
    &wg,
)

go worker(
    "B",
    &wg,
)

go worker(
    "C",
    &wg,
)

wg.Wait()
```

Worker：

```go
func worker(
    name string,
    wg *sync.WaitGroup,
) {
    defer wg.Done()

    ...
}
```

---

## 3.16.4 Channel

```go
ch := make(
    chan string,
)
```

表示一个传输 `string` 的 Channel。

发送：

```go
ch <- "hello"
```

接收：

```go
message := <-ch
```

---

## 3.16.5 Unbuffered Channel

```go
ch := make(
    chan string,
)
```

没有 Buffer。

核心：

> Send / Receive 必须碰面。

所以 Unbuffered Channel 同时是：

```text
Data Transfer
+
Synchronization Point
```

---

## 3.16.6 Buffered Channel

```go
ch := make(
    chan string,
    3,
)
```

只要 Buffer 没满，Sender 可以先放数据。

Buffer 满后再 Send：

> Sender 等待。

---

## 3.16.7 Backpressure

Producer 快、Consumer 慢：

```text
Buffer 满
↓
Producer Block
↓
上游减速
```

这就是 Backpressure。

---

## 3.16.8 close

```go
close(ch)
```

表示：

> 不会再有新 Value 发进来。

通常由 Sender 关闭。

向 Closed Channel Send：

```text
panic
```

---

## 3.16.9 comma-ok / range Channel

```go
value, ok := <-ch
```

如果：

```text
ok = false
```

表示 Channel 已关闭并读空。

常用：

```go
for value := range ch {
    ...
}
```

---

## 3.16.10 Directional Channel

Receive-only：

```go
jobs <-chan int
```

Send-only：

```go
results chan<- int
```

Compiler 会限制错误方向操作。

---

## 3.16.11 Fan-Out / Fan-In

```text
                  Worker 1
                ↗
Jobs Channel ───→ Worker 2 ───→ Results Channel
                ↘
                  Worker 3
```

Fan-Out：分发任务。

Fan-In：汇总结果。

---

## 3.16.12 Worker Pool

固定数量 Worker：

```go
for id := 1;
    id <= workerCount;
    id++ {

    go worker(...)
}
```

优点：

> Bounded Concurrency。

---

## 3.16.13 Deadlock

```go
func main() {
    ch := make(
        chan int,
    )

    ch <- 1
}
```

Unbuffered Channel 没有 Receiver。

唯一 main Goroutine 自己卡在 Send。

可能得到：

```text
fatal error:
all goroutines are asleep - deadlock!
```

---

## 3.16.14 select

```go
select {
case value := <-ch1:
    fmt.Println(value)

case value := <-ch2:
    fmt.Println(value)
}
```

哪个 Channel 先 Ready，就处理哪个。

---

## 3.16.15 Timeout with select

```go
select {
case result := <-results:
    fmt.Println(result)

case <-time.After(
    2 * time.Second,
):
    fmt.Println(
        "timeout",
    )
}
```

---

## 3.16.16 Mutex

**Mutex = Mutual Exclusion**。

```go
var (
    counter int
    mu      sync.Mutex
)
```

更新：

```go
mu.Lock()
counter++
mu.Unlock()
```

被保护的代码叫 Critical Section。

---

## 3.16.17 RWMutex

```go
sync.RWMutex
```

允许多个 Reader，但 Writer 独占。

适合：

```text
Read Many
Write Rarely
```

---

## 3.16.18 Channel vs Mutex

简单判断：

```text
任务 / 数据需要在 Goroutine 之间传递
→ Channel

多个 Goroutine 共享同一内存状态
→ Mutex
```

---

## 3.16.19 Data Race

多个 Goroutine 并发访问同一 Memory，其中至少一个写，而且缺乏同步。

Go Race Detector：

```bash
go run -race .
go test -race ./...
```

---

## 3.16.20 Context

```go
ctx, cancel :=
    context.WithTimeout(
        context.Background(),
        2*time.Second,
    )

defer cancel()
```

Context 用于：

```text
Cancellation
Deadline
Timeout
Request-scoped metadata
```

---

## 3.16.21 `ctx.Done()`

```go
select {
case <-ctx.Done():
    return ctx.Err()
}
```

Context Cancel 或 Deadline 到期：

> `Done()` Channel Ready。

---

## 3.16.22 Goroutine Leak

**Goroutine Leak**：

> Goroutine 因等待永远无法结束而长期残留。

常见来源：

```text
Channel 永远没人 Send
Channel 永远没人 Receive
Network Operation 无 Timeout
忘记监听 Context
Ticker 不 Stop
Worker 永久等待
```

每创建一个长期 Goroutine，要问：

```text
Who owns it?
How does it stop?
Who cancels it?
Who waits for it?
```

---

## 3.16.23 Context 防 Leak

```go
func worker(
    ctx context.Context,
    jobs <-chan Job,
) {
    for {
        select {
        case job, ok := <-jobs:
            if !ok {
                return
            }

            process(job)

        case <-ctx.Done():
            return
        }
    }
}
```

---

## 3.16.24 Fan-In 正确关闭

多个 Worker 向 `results` Send：

```go
go func() {
    wg.Wait()
    close(results)
}()
```

Main：

```go
for result := range results {
    ...
}
```

---

## 3.16.25 Bounded Concurrency

Goroutine 很轻，但以下资源有限：

```text
FD
Memory
Network
Remote Service
NAT Conntrack
Ephemeral Port
```

常用：

```text
Worker Pool
Semaphore
```

Semaphore 简单实现：

```go
sem := make(
    chan struct{},
    10,
)
```

占 Slot：

```go
sem <- struct{}{}
```

释放：

```go
<-sem
```

---

## 3.16 核心结论

1. Goroutine 不等于 OS Thread。
2. WaitGroup 负责等待，不负责传数据。
3. Channel = Typed Data Transfer + Synchronization + Backpressure。
4. Unbuffered Channel 需要 Send / Receive 握手。
5. Buffered Channel 提供有限队列。
6. Sender 通常负责 Close。
7. `select` 同时等待多个事件。
8. Mutex 保护共享内存。
9. Race Detector 是并发调试重要工具。
10. Context 传播取消和 Deadline。
11. 长期 Goroutine 必须有退出路径。
12. Goroutine 轻量不等于资源无限。

---

# 3.16A GMP Scheduler 深入

这是理解 Go Runtime 的关键。

## 3.16A.1 G / M / P

### G

Goroutine：

> 待执行的轻量任务，包括 Stack、执行状态等。

### M

Machine：

> OS Thread。

最终由 Linux Scheduler 调度到 CPU。

### P

Processor：

> 执行普通 Go Code 所需的逻辑调度资源。

可以先把 P 理解：

```text
执行 Go Code 的许可证
+
Runtime 工作台
```

P 还关联：

```text
Local Run Queue
Scheduler State
Allocator State
Timers 等 Runtime State
```

---

## 3.16A.2 为什么不直接 G → M

假设：

```text
4 CPU Cores
4 OS Threads
很多 Goroutines
```

如果：

```text
M0 运行 G1
↓
G1 Blocking Syscall
↓
M0 被 Kernel 卡住
```

只剩：

```text
M1
M2
M3
```

执行 Go Code。

CPU 明明有 4 Core，却只利用 3 个。

可以创建 M4。

但 syscall 返回后：

```text
M0 M1 M2 M3 M4
```

变成 5 个 Thread。

这时系统需要单独维护：

> “虽然 M 有 5 个，但最多只允许 4 个同时执行 Go Code。”

这个执行许可证，就是 P。

---

## 3.16A.3 P 解耦两个维度

```text
OS Thread 数量
```

与：

```text
Go Code Parallelism
```

不再绑死。

例如：

```text
GOMAXPROCS = 4
```

意味着 Runtime 有 4 个 P。

M 数量可以大于 4，因为部分 M 可能：

```text
blocked syscall
cgo
idle
runtime work
```

---

## 3.16A.4 工厂比喻

```text
G
→ 订单

M
→ 工人

P
→ 工作台 + 上岗证 + 工具箱
```

工人很多，但工作台只有 4 张，真正同时执行 Go Code 的最多仍是 4 个。

---

## 3.16A.5 Syscall 中的 P Handoff

开始：

```text
P0 ← M0 → G1
P1 ← M1 → G2
P2 ← M2 → G3
P3 ← M3 → G4
```

G1 Blocking Syscall：

```text
G1
↓
M0
↓
Kernel
```

M0 可以失去 P0：

```text
M0
→ blocked without P
```

P0 交给别的 M：

```text
P0 ← M4 → G5
```

于是 Blocking Thread 不会浪费一个 Go 并行额度。

---

## 3.16A.6 为什么 Runtime State 不绑 M

如果 Local Queue / Allocator State 都绑在 M：

```text
M0 blocked syscall
↓
Local Queue 也跟着卡住
```

P 的设计：

```text
M0 blocked
↓
P0 整体脱离 M0
↓
P0 → M4
```

Runtime State 跟 P，而不是跟可能阻塞的 OS Thread。

---

## 3.16A.7 Local Run Queue

每个 P 有自己的 Local Run Queue：

```text
P0 Queue:
G1 G2 G3

P1 Queue:
G4 G5
```

M 拿着 P 后，优先从本地取 G。

优点：

```text
减少 Global Lock
提高 Scalability
改善 Cache Locality
```

---

## 3.16A.8 Global Run Queue

Global Queue 仍然存在：

```text
Global:
G90 G91 G92
```

用于：

```text
Local Queue Overflow
Global Coordination
Fairness
```

基本原则：

```text
Local Fast Path
Global Coordination Path
```

---

## 3.16A.9 `go worker()` 后发生什么

当前：

```text
Gmain
↓
M0 + P0
```

执行：

```go
go worker()
```

Runtime 大致：

```text
创建新 G
↓
初始化 Stack / Entry Point
↓
变成 Runnable
↓
放入当前 P0 的 Runnable Queue
```

注意：

> `go worker()` 不等于创建一个 OS Thread。

---

## 3.16A.10 Scheduler 找下一个 G

简化模型：

```text
当前 M 持 P
↓
需要 Runnable G

1. Runtime / GC / Timer 特殊工作？
2. 偶尔检查 Global Queue
3. Local Run Queue 有 G？
4. Global Run Queue 有 G？
5. Network Poller 有 Ready G？
6. 从其他 P Work Steal
7. 还是没活 → idle / park / netpoll wait
```

真实实现更复杂，但这个心智模型足够学习 Infra。

---

## 3.16A.11 Work Stealing

```text
P0:
G1 G2 G3 G4 G5 G6

P1:
empty
```

P1 可从 P0 偷一批：

```text
P0:
G1 G2 G3

P1:
G4 G5 G6
```

目标：

```text
避免 CPU 闲置
平衡负载
减少 Global Queue 压力
```

---

## 3.16A.12 GOMAXPROCS

```text
GOMAXPROCS
↓
P 数量
↓
最多这么多个 M 同时持 P
↓
最多这么多个执行流执行普通 Go Code
```

但：

```text
GOMAXPROCS = 4
```

不等于：

```text
Process 只有 4 个 OS Threads
```

完全可以：

```text
P = 4
M = 12
G = 100000
```

---

## 3.16A.13 G / P / M 不是固定绑定

G 可能：

```text
M0 → wait → M3 → wait → M1
```

P 可能：

```text
P0 + M0
↓
M0 syscall
↓
P0 + M4
```

不是固定三元组。

---

## 3.16A.14 Network Poller

网络等待：

```text
G1
↓
Socket Not Ready
↓
Network Poller
↓
G1 Waiting
```

数据到达：

```text
NIC
↓
Kernel TCP
↓
Socket Ready
↓
epoll
↓
Go Network Poller
↓
G1 Runnable
↓
某个 P Queue
↓
某个 M + P Resume G1
```

---

## 3.16A.15 Go Scheduler vs Linux Scheduler

Go Scheduler：

```text
G
↓
哪个 G 给哪个 M/P
```

Linux Scheduler：

```text
M / OS Thread
↓
哪个 Thread 给哪个 CPU Core
```

完整：

```text
G
↓
Go Runtime Scheduler
↓
P + M
↓
Linux Scheduler
↓
CPU Core
```

---

## 3.16A.16 Goroutine Context Switch

如果：

```text
M0 + P0
正在执行 G1
```

G1 等 Channel：

```text
G1 Running
↓
Waiting
```

P0 Queue 有 G2：

```text
M0
↓
Runtime 切到 G2
```

这里可能不需要 OS Thread Context Switch。

---

## 3.16A.17 Spinning M

M 暂时没找到工作，Runtime 不一定立刻 Park。

可能短暂 Spinning：

> 主动寻找即将出现的 Work。

用于平衡：

```text
Latency
vs
CPU Waste
```

---

## 3.16A.18 GMP 心智图

```text
                       Go Process
                           │
                  Runnable Goroutines
                    G G G G G G
                           │
           ┌───────────────┼───────────────┐
           ↓               ↓               ↓
          P0              P1              P2
     ┌──────────┐     ┌──────────┐    ┌──────────┐
     │Local RunQ│     │Local RunQ│    │Local RunQ│
     │Runtime   │     │Runtime   │    │Runtime   │
     └────┬─────┘     └────┬─────┘    └────┬─────┘
          │                │               │
          ↓                ↓               ↓
         M0               M1              M2
      OS Thread        OS Thread       OS Thread
          │                │               │
          └────────── Linux Scheduler ─────┘
                           │
                       CPU Cores
```

额外 M：

```text
M3 → blocked syscall
M4 → cgo
M5 → idle
```

没有 P 时，不能执行普通 Go 用户代码。

---

## 3.16A.19 schedtrace 实验

```bash
GODEBUG=schedtrace=1000 \
go run .
```

更详细：

```bash
GODEBUG=schedtrace=1000,scheddetail=1 \
go run .
```

可以观察：

```text
gomaxprocs=
idleprocs=
threads=
idlethreads=
runqueue=
```

如果：

```text
gomaxprocs=8
threads=13
```

完全正常。

---

## 3.16A 核心结论

> P 不是第三种线程，而是“Go Code 执行许可证 + Runtime 工作台”。

核心意义：

1. 解耦 OS Thread 数量和 Go Parallelism。
2. Blocking syscall 时可以把 P 交给其他 M。
3. Per-P Local Run Queue 减少 Global Lock。
4. Per-P Runtime State 改善 Locality / Scalability。
5. `GOMAXPROCS` 本质上对应 P 数量。
6. G / P / M 都不是永久绑定。

一句比喻：

> **G 是工作，M 是工人，P 是工作台 + 上岗证 + 本地工具箱。**

---

# 3.17 Go HTTP / JSON

## 3.17.1 net/http

Go Standard Library：

```go
import "net/http"
```

可以同时做：

```text
HTTP Server
HTTP Client
```

---

## 3.17.2 Handler

Handler 核心：

```text
Request
↓
Handler
↓
Response
```

Go 标准 Handler Interface：

```go
type Handler interface {
    ServeHTTP(
        ResponseWriter,
        *Request,
    )
}
```

---

## 3.17.3 最小 Server

```go
package main

import (
    "fmt"
    "net/http"
)

func healthHandler(
    w http.ResponseWriter,
    r *http.Request,
) {
    fmt.Fprintln(
        w,
        "ok",
    )
}

func main() {
    mux := http.NewServeMux()

    mux.HandleFunc(
        "/health",
        healthHandler,
    )

    err := http.ListenAndServe(
        ":8080",
        mux,
    )

    if err != nil {
        panic(err)
    }
}
```

测试：

```bash
curl -v \
  http://127.0.0.1:8080/health
```

---

## 3.17.4 ServeMux

**ServeMux**：

> 根据 URL Path 把 Request 分给不同 Handler。

```text
/health
→ healthHandler

/v1/status
→ statusHandler

/metrics
→ metricsHandler
```

---

## 3.17.5 Method / Status / Header

Request Method：

```go
r.Method
```

常量：

```go
http.MethodGet
http.MethodPost
```

Status：

```go
http.StatusOK
http.StatusBadRequest
http.StatusNotFound
http.StatusInternalServerError
http.StatusServiceUnavailable
```

Header：

```go
w.Header().Set(
    "Content-Type",
    "application/json",
)
```

Header 应在 `WriteHeader()` 或首次 `Write()` 前设置。

---

## 3.17.6 JSON

Standard Library：

```go
encoding/json
```

### Marshal

Go → JSON：

```go
data, err := json.Marshal(
    value,
)
```

### Unmarshal

JSON → Go：

```go
err := json.Unmarshal(
    data,
    &target,
)
```

---

## 3.17.7 Struct Tag

```go
type Status struct {
    Name    string `json:"name"`
    Healthy bool   `json:"healthy"`
}
```

输出：

```json
{
  "name": "vllm-01",
  "healthy": true
}
```

---

## 3.17.8 omitempty

```go
Error string `json:"error,omitempty"`
```

如果 Error 是 Zero Value，可以省略。

---

## 3.17.9 Encoder / Decoder

写 Response：

```go
json.NewEncoder(
    w,
).Encode(
    response,
)
```

读 Request：

```go
decoder := json.NewDecoder(
    r.Body,
)

var target Target

err := decoder.Decode(
    &target,
)
```

---

## 3.17.10 DisallowUnknownFields

```go
decoder.DisallowUnknownFields()
```

客户端发：

```json
{
  "prot": 8000
}
```

如果本来应该是 `port`，可以直接拒绝。

这符合 Fail Fast。

---

## 3.17.11 Parse Success ≠ Business Valid

```json
{
  "name": "",
  "port": 0
}
```

JSON 完全合法，但业务上可能非法。

所以：

```text
Decode
↓
Validate
```

必须分开。

---

## 3.17.12 HTTP Server 并发模型

不同 Request 会并发处理：

```text
Request A → Handler Goroutine A
Request B → Handler Goroutine B
Request C → Handler Goroutine C
```

所以 Handler 访问 Shared Mutable State 时要同步。

---

## 3.17.13 Struct Handler

```go
type API struct {
    Client  *http.Client
    Checker Checker
}
```

Method：

```go
func (
    api *API,
) Health(
    w http.ResponseWriter,
    r *http.Request,
) {
    ...
}
```

适合 Dependency Injection。

---

## 3.17.14 http.Client

```go
client := &http.Client{
    Timeout:
        5 * time.Second,
}
```

请求：

```go
response, err := client.Get(
    url,
)
```

工程上：

> `http.Client` 通常应复用。

因为底层：

```text
Transport
↓
Connection Pool
↓
TCP/TLS Connection Reuse
```

---

## 3.17.15 Response Body Close

```go
response, err := client.Get(
    url,
)

if err != nil {
    return err
}

defer response.Body.Close()
```

要认真处理 Response Body 生命周期。

---

## 3.17.16 Transport Error vs HTTP Status

```go
response, err := client.Do(
    request,
)
```

如果：

```text
err != nil
```

通常表示：

```text
DNS
TCP
TLS
Context
Transport
```

问题。

但 HTTP 500 通常：

```text
err == nil
response.StatusCode == 500
```

因为 HTTP Response 已经正常收到。

---

## 3.17.17 Context + HTTP

Server：

```go
ctx := r.Context()
```

下游：

```go
request, err :=
    http.NewRequestWithContext(
        ctx,
        http.MethodGet,
        url,
        nil,
    )
```

这样：

```text
Client Disconnect
↓
Handler Context Cancel
↓
Downstream Request Cancel
```

---

## 3.17.18 Child Timeout

```go
ctx, cancel :=
    context.WithTimeout(
        r.Context(),
        2*time.Second,
    )

defer cancel()
```

Child 同时受：

```text
Parent Cancellation
+
自己的 Timeout
```

控制。

---

## 3.17.19 Production-style Server

```go
server := &http.Server{
    Addr:
        ":8080",
    Handler:
        mux,
    ReadHeaderTimeout:
        5 * time.Second,
    ReadTimeout:
        10 * time.Second,
    WriteTimeout:
        10 * time.Second,
    IdleTimeout:
        60 * time.Second,
}
```

Timeout 是生产 HTTP 服务的重要边界。

---

## 3.17.20 Liveness / Readiness

**Liveness**：

> Process 是否活着？

**Readiness**：

> 是否已经能接业务？

例如：

```text
Process alive
模型还没加载
```

则：

```text
Liveness = true
Readiness = false
```

---

## 3.17.21 Middleware

Middleware 用于：

```text
Logging
Authentication
Request ID
Metrics
Recovery
Rate Limit
```

模型：

```text
Request
↓
Logging Middleware
↓
Auth Middleware
↓
Metrics Middleware
↓
Business Handler
↓
Response
```

示例：

```go
func loggingMiddleware(
    next http.Handler,
) http.Handler {
    return http.HandlerFunc(
        func(
            w http.ResponseWriter,
            r *http.Request,
        ) {
            start := time.Now()

            next.ServeHTTP(
                w,
                r,
            )

            fmt.Printf(
                "method=%s path=%s latency=%s\n",
                r.Method,
                r.URL.Path,
                time.Since(start),
            )
        },
    )
}
```

---

## 3.17.22 Handler 应只负责 HTTP Translation

推荐：

```text
Method Check
↓
Parse
↓
Validate
↓
Call Business Logic
↓
Map Error → HTTP Status
↓
Serialize Response
```

而业务逻辑尽量独立：

```go
func checkTCP(
    ctx context.Context,
    host string,
    port int,
) Result
```

这样 CLI / HTTP / Test 都能复用。

---

## 3.17 核心结论

1. `net/http` 是 Go Infra 核心能力之一。
2. Handler = Request → Response。
3. ServeMux 做 Path Routing。
4. HTTP Handler 默认运行在并发环境。
5. 固定 JSON Schema 优先 Struct。
6. JSON Decode 成功不等于业务合法。
7. `http.Client` 应复用。
8. Response Body 要正确关闭。
9. HTTP Status 和 Transport Error 要分层理解。
10. Client / Server 都必须设计 Timeout。
11. `r.Context()` 是 Request Cancellation 链路入口。
12. Middleware 是 Go HTTP 的重要 Composition Pattern。
13. Handler 负责 HTTP Translation，核心业务逻辑应该独立。

---

# 3.18 Go CLI / Daemon

## 3.18.1 Daemon 生命周期

```text
Process Start
↓
Parse CLI
↓
Load Config
↓
Validate
↓
Create Dependencies
↓
Start Service / Workers
↓
Run
↓
Receive Signal
↓
Cancel Context
↓
Graceful Shutdown
↓
Wait Workers
↓
Exit
```

Daemon 不是简单死循环，而是完整生命周期。

---

## 3.18.2 flag

```go
port := flag.Int(
    "port",
    8080,
    "HTTP listen port",
)

flag.Parse()

fmt.Println(
    *port,
)
```

也可以：

```go
var port int

flag.IntVar(
    &port,
    "port",
    8080,
    "HTTP listen port",
)
```

---

## 3.18.3 Environment Variable

```go
value := os.Getenv(
    "LOG_LEVEL",
)
```

区分不存在：

```go
value, ok :=
    os.LookupEnv(
        "LOG_LEVEL",
    )
```

---

## 3.18.4 Config Precedence

常见：

```text
Default
<
Config File
<
Environment
<
CLI
```

---

## 3.18.5 Signal

常见：

```text
SIGINT
SIGTERM
SIGKILL
SIGHUP
```

### SIGINT

常来自 `Ctrl+C`。

### SIGTERM

请求 Process 正常终止。

systemd / Docker / Kubernetes 常用。

### SIGKILL

Kernel 强制杀死，不能捕获，所以没有 Cleanup 机会。

---

## 3.18.6 signal.NotifyContext

```go
ctx, stop :=
    signal.NotifyContext(
        context.Background(),
        os.Interrupt,
        syscall.SIGTERM,
    )

defer stop()
```

收到 Signal：

```text
SIGINT / SIGTERM
↓
Context Cancel
↓
监听 ctx.Done() 的组件开始 Shutdown
```

---

## 3.18.7 Root Context

长期程序通常有一个 Root Context，代表整个 Process 生命周期。

所有：

```text
HTTP Server
Worker
Poller
Background Loop
```

都可以受它控制。

---

## 3.18.8 Background Worker

```go
func worker(
    ctx context.Context,
) {
    ticker := time.NewTicker(
        5 * time.Second,
    )

    defer ticker.Stop()

    for {
        select {
        case <-ticker.C:
            doWork()

        case <-ctx.Done():
            return
        }
    }
}
```

---

## 3.18.9 HTTP Graceful Shutdown

```go
server.Shutdown(
    ctx,
)
```

高层：

```text
停止接收新连接
↓
关闭 Idle Connection
↓
等待已有 Request 完成
↓
直到全部完成或 Timeout
```

---

## 3.18.10 Shutdown Timeout

```go
shutdownCtx, cancel :=
    context.WithTimeout(
        context.Background(),
        10*time.Second,
    )

defer cancel()

server.Shutdown(
    shutdownCtx,
)
```

不要无限等待。

---

## 3.18.11 ListenAndServe 正常关闭

```go
err := server.ListenAndServe()

if err != nil &&
    err != http.ErrServerClosed {

    ...
}
```

`http.ErrServerClosed` 通常是正常 Shutdown 路径。

---

## 3.18.12 Server Error Propagation

```go
serverErr := make(
    chan error,
    1,
)

go func() {
    serverErr <-
        server.ListenAndServe()
}()
```

main：

```go
select {
case <-ctx.Done():
    ...

case err := <-serverErr:
    ...
}
```

这样 Server Fatal Error 能通知 main。

---

## 3.18.13 Partial Failure

危险状态：

```text
PID alive
HTTP server dead
Worker dead
```

所以关键子组件不能只 log Error 后静默退出。

---

## 3.18.14 Supervisor

main 常扮演内部 Supervisor：

```text
Go Process
↓
main
├─ HTTP Server
├─ Worker
├─ Poller
└─ Metrics Loop
```

外部还有：

```text
systemd
Docker
Kubernetes
```

---

## 3.18.15 Exit Code

例如：

```text
0
→ Normal Shutdown

1
→ Runtime Fatal Error

2
→ Config Error
```

---

## 3.18.16 os.Exit 与 defer

```go
os.Exit(1)
```

重要：

> `os.Exit()` 不执行 defer。

因此不要：

```go
func main() {
    defer cleanup()

    os.Exit(1)
}
```

---

## 3.18.17 run() int Pattern

更好：

```go
func run() int {
    defer cleanup()

    ...
    return 1
}

func main() {
    os.Exit(
        run(),
    )
}
```

---

## 3.18.18 Composition Root

顶层组装：

```text
Config
↓
HTTP Client
↓
Checker
↓
API
↓
HTTP Server
```

这个顶层集中创建依赖的地方叫：

**Composition Root**。

---

## 3.18.19 Shutdown Order

Startup：

```text
Database
↓
Service
↓
HTTP Server
```

Shutdown 常反过来：

```text
HTTP Server
↓
Service
↓
Database
```

也就是：

> 先关入口，再关内部依赖。

---

## 3.18.20 Draining

**Draining**：

> 不再接新工作，但允许已有工作完成。

成熟 Shutdown：

```text
SIGTERM
↓
Mark Not Ready
↓
Stop New Traffic
↓
Drain
↓
Cancel Background Work
↓
Wait Existing Work
↓
Close Resources
↓
Exit
```

---

## 3.18.21 Fatal vs Recoverable

```text
单个 Request 失败
→ Recoverable

Probe 失败
→ Result / Warning

Listener bind 失败
→ Fatal

Config invalid
→ Fatal
```

Fatal Error 更适合退出 Process，让外部 Supervisor 决定是否 Restart。

---

## 3.18.22 Internal Retry vs External Restart

```text
程序内部
→ Retry transient dependency errors

systemd / Kubernetes
→ Restart crashed process
```

---

## 3.18 核心结论

1. Daemon 是完整生命周期，不是死循环。
2. CLI / Config / Env 要有明确优先级。
3. SIGTERM 是长期 Service 正常 Shutdown 的关键。
4. SIGKILL 无法 Cleanup。
5. `signal.NotifyContext` 把 Signal 转成 Context Cancellation。
6. 长期 Worker 必须监听退出信号。
7. HTTP Shutdown 应有 Timeout。
8. Critical Error 要传播给 main。
9. 深层 Library 不要 `os.Exit()`。
10. `os.Exit()` 不执行 defer。
11. Composition Root 集中组装依赖。
12. Shutdown 常按依赖反方向进行。
13. Daemon 对外 Contract 是 Signal / Health / Exit Code / stdout/stderr。

---

# 3.18A `signal.NotifyContext` 的 `stop`

这是一个很容易疑惑的点。

## 3.18A.1 `stop` 是什么

```go
ctx, stop :=
    signal.NotifyContext(
        context.Background(),
        os.Interrupt,
        syscall.SIGTERM,
    )
```

`stop`：

> 就是一个 Function Value。

它不是关键字，也不是你自己定义的函数。

它是 `NotifyContext()` 的第二个返回值。

---

## 3.18A.2 返回类型

概念签名：

```go
func NotifyContext(
    parent context.Context,
    signals ...os.Signal,
) (
    ctx context.Context,
    stop context.CancelFunc,
)
```

`context.CancelFunc` 本质：

```go
type CancelFunc func()
```

也就是：

```text
无参数
无返回值
```

的 Function Type。

---

## 3.18A.3 Function 可以作为值

```go
func createStop() func() {
    return func() {
        fmt.Println(
            "stopped",
        )
    }
}

stop := createStop()

stop()
```

所以：

```go
ctx, stop :=
    signal.NotifyContext(...)
```

只是：

```text
ctx
→ Context Value

stop
→ Function Value
```

---

## 3.18A.4 Method Value

```go
type Server struct {
    Name string
}

func (
    s *Server,
) Stop() {
    fmt.Println(
        "stop:",
        s.Name,
    )
}
```

可以：

```go
server := &Server{
    Name: "api",
}

stop := server.Stop
```

注意没有 `()`。

后面：

```go
stop()
```

等价于：

```go
server.Stop()
```

---

## 3.18A.5 NotifyContext 内部思路

高层大致：

```text
创建 cancellable Context
↓
创建 signalCtx
↓
创建 Signal Channel
↓
注册 os/signal.Notify
↓
启动一个 Goroutine 等 Signal
↓
return ctx, signalCtx.stop
```

所以 `stop` 实际绑定的是内部对象的 Method。

---

## 3.18A.6 stop 做什么

高层：

```text
stop()
│
├─ Cancel Context
│
└─ Stop Signal Notification
```

也就是：

```text
结束 Context 生命周期
+
注销 Signal 监听
```

---

## 3.18A.7 defer stop()

```go
defer stop()
```

表示：

> 当前 Function 返回时，执行 cleanup/cancel function。

流程：

```text
Function return
↓
stop()
↓
Cancel Context
↓
Unregister Signal Notification
```

---

## 3.18A.8 Signal 到达时

```bash
kill -TERM <PID>
```

流程：

```text
Linux Kernel
↓
SIGTERM
↓
Go Runtime / os.signal
↓
内部 Signal Channel
↓
NotifyContext internal goroutine
↓
Cancel Context
↓
ctx.Done() ready
```

你的：

```go
<-ctx.Done()
```

被唤醒。

---

## 3.18A.9 为什么 Signal 已经 Cancel 还要 stop

因为：

> Cancel Context 和注销 Signal Notification 不是完全同一件事。

最终 `stop()` 还负责解除 Signal Notification 和清理相关资源。

---

## 3.18A 核心结论

> `stop` 不是魔法，它只是一个函数值。

`NotifyContext()` 返回：

```text
Context
+
Cancel/Cleanup Function
```

最终：

```text
stop()
→ Cancel Context
→ Stop Signal Notification
```

---

# 3.19 Python vs Go

## 3.19.1 总定位

```text
Python
→ Fast Development
→ Dynamic
→ AI Ecosystem
→ Automation
→ Benchmark
→ Data / Experiment

Go
→ Static Type
→ Compiled Binary
→ Goroutine
→ Network Service
→ Long-running Daemon
→ Agent / Controller
→ Cloud Native
```

---

## 3.19.2 Runtime Model

Python：

```text
.py
↓
Python Interpreter
↓
Runtime
↓
OS Process
```

Go：

```text
.go
↓
Compiler
↓
Binary
↓
Go Runtime
↓
OS Process
```

---

## 3.19.3 Deployment

Python：

```text
Python Version
venv
Dependencies
site-packages
pyproject
lockfile
```

Go：

```text
go build
↓
Binary
↓
copy / container
↓
run
```

大量 Node 分发时 Go 很有优势。

---

## 3.19.4 Development Speed

Python：

```python
import requests

response = requests.get(
    url,
)

print(
    response.json(),
)
```

非常适合：

```text
实验
一次性脚本
Glue Code
Benchmark
Data Analysis
```

Go 代码通常更正式：

```text
Type
Error Check
Struct
Explicit Control Flow
```

短期开发速度一般不如 Python。

---

## 3.19.5 Glue Code

**Glue Code**：

> 把多个现有系统连接起来的代码。

例如：

```text
读 YAML
↓
调用 Kubernetes API
↓
调用 HTTP API
↓
写 JSON
↓
发告警
```

Python 很擅长。

---

## 3.19.6 Type System

Python：

```text
Dynamic Typing
+
Type Hint
```

Go：

```text
Static Typing
+
Compile-time Checking
```

大型项目里：

```text
Refactor
API Contract
Struct
Interface
```

Go 更稳。

---

## 3.19.7 CPU

纯 Python CPU Loop 通常不如 Go。

传统 CPython 还有 GIL 对多线程纯 Python CPU 并行的限制。

Go：

```text
Compiled Machine Code
+
Goroutine
+
Multiple OS Threads
```

更适合 CPU-heavy 服务逻辑。

---

## 3.19.8 为什么 Python AI 仍然快

因为：

```text
Python
↓
NumPy / PyTorch
↓
C / C++ / CUDA
↓
CPU SIMD / GPU
```

重计算不在 Python Interpreter。

---

## 3.19.9 Concurrency

Python：

```text
Thread
Process
asyncio
```

Go：

```text
Goroutine
Channel
GMP Scheduler
```

### Python Thread

适合 Blocking I/O。

### Python Async

适合大量 I/O Connection，但要求 async-aware Library。

### Go Goroutine

轻量、同步风格、Runtime 自动调度，并且可以多 Core 并行。

---

## 3.19.10 Error Model

Python：Exception Propagation。

Go：Explicit error return。

Python 主路径更简洁；Go 的 Error Path 更显式。

Infra 中 I/O Error 很多，Go 这种显式风格常常是优点。

---

## 3.19.11 Networking

Python：

```text
requests
httpx
aiohttp
FastAPI
```

Go：

```text
net
net/http
context
io
```

Standard Library 就很强。

所以：

```text
Proxy
Gateway
Agent
Controller
Webhook
Exporter
```

Go 很自然。

---

## 3.19.12 AI Ecosystem

Python 明显占优势：

```text
PyTorch
NumPy
Transformers
vLLM
SGLang
Jupyter
Pandas
```

所以 Model Training / Serving 基本绕不开 Python。

---

## 3.19.13 Cloud Native Ecosystem

Go 非常常见：

```text
Kubernetes
Prometheus
etcd
Terraform
containerd
Caddy
Traefik
```

因此读 Cloud Native 源码时，Go 很重要。

---

## 3.19.14 Control Plane / Data Plane

常见：

```text
Go Control Plane
↓
Python Model Serving
↓
C++ / CUDA Data Plane
```

这不是绝对规律，但很常见。

---

## 3.19.15 场景选择表

| 场景 | 更优先 |
|---|---|
| 一次性脚本 | Python |
| 快速 API 调用 | Python |
| Benchmark | Python |
| Data Analysis | Python |
| PyTorch / LLM | Python |
| Jupyter 实验 | Python |
| Node Agent | Go |
| Kubernetes Operator | Go |
| Controller | Go |
| Exporter | Go |
| Gateway / Proxy | Go |
| Cross-platform CLI | Go |
| Long-running Daemon | Go |
| Cloud Native Core Service | Go |
| AI Model Serving Backend | Python + C++/CUDA |

---

## 3.19.16 Language Selection Model

不要问：

```text
Python 还是 Go？
```

应该问：

```text
1. 生命周期多长？
2. 并发规模多大？
3. 是否强依赖 AI Library？
4. 是否部署大量 Node？
5. 是否需要单 Binary？
6. 类型稳定性重要吗？
7. 需求变化速度快吗？
```

---

## 3.19.17 Rewrite Cost

不要因为：

```text
Go 更快
```

就重写一个已经够好的 Python Tool。

重写成本包括：

```text
Bug
测试
迁移
兼容性
运维
学习成本
```

合理演进：

```text
Python Prototype
↓
验证需求
↓
发现明确 Bottleneck
↓
关键组件 Go 重写
```

---

## 3.19.18 Service Boundary

Python / Go 可以通过：

```text
HTTP
gRPC
Message Queue
Files
```

协作。

但不要为了“看起来高级”而无意义拆 Microservice。

每多一个 Service，都增加：

```text
Network
Timeout
Retry
Auth
Deploy
Metrics
Tracing
Failure Modes
```

---

## 3.19 核心结论

1. Python / Go 在 AI Infra 中是分工关系。
2. Python 强在 AI / Automation / Data / Experiment。
3. Go 强在 Long-running Service / Agent / Controller / Network。
4. 选型看 Lifecycle / Concurrency / Deployment / Ecosystem。
5. 不要无理由 Rewrite。
6. 不要过早 Microservice 化。
7. AI Infra 天生是多语言系统。

---

# 3.20 AI Infra Go 小工具实战
# Mini Endpoint Agent

这一节是 Go 部分收官。

目标：

> 做一个长期运行的 Endpoint Agent。

功能：

```text
读取 Config
↓
周期检查 HTTP / TCP Endpoint
↓
Worker Pool 并发
↓
保存最新 Snapshot
↓
HTTP API 暴露状态
↓
Signal / Context / Graceful Shutdown
```

---

## 3.20.1 Architecture

```text
                        config.json
                            │
                            ↓
                     Load / Validate
                            │
                            ↓
                    []Checker Interface
                   ┌────────┼─────────┐
                   ↓        ↓         ↓
                 TCP      HTTP      HTTP
               Checker   Checker    Checker
                   │        │         │
                   └────────┼─────────┘
                            ↓
                       Agent Loop
                            │
                         Ticker
                            │
                            ↓
                       Worker Pool
                  ┌─────────┼─────────┐
                  ↓         ↓         ↓
                 G1        G2        G3
                  │         │         │
                  └─────────┼─────────┘
                            ↓
                     Results Channel
                            │
                            ↓
                         Snapshot
                            │
                            ↓
                     HTTP API Server
                 ┌──────────┼──────────┐
                 ↓          ↓          ↓
              /health     /ready   /v1/results
```

Shutdown：

```text
SIGTERM / Ctrl+C
        ↓
 signal.NotifyContext
        ↓
  Root Context Cancel
        ↓
 ┌──────┴─────────┐
 ↓                ↓
Agent Stop    HTTP Shutdown
 ↓                ↓
Worker Exit   Drain Requests
 └──────┬─────────┘
        ↓
      Exit
```

---

## 3.20.2 Project Structure

```text
endpoint-agent/
│
├── go.mod
├── config.json
│
├── main.go
├── config.go
├── checker.go
├── agent.go
└── api.go
```

职责：

```text
config.go
→ Config / Validation

checker.go
→ Checker Interface
→ TCPChecker
→ HTTPChecker

agent.go
→ Worker Pool
→ Periodic Probe
→ Snapshot

api.go
→ HTTP API

main.go
→ CLI
→ Signal
→ Dependency Wiring
→ Graceful Shutdown
```

---

## 3.20.3 创建项目

```bash
mkdir -p \
  ~/ai-infra-lab/chapter3/endpoint-agent

cd \
  ~/ai-infra-lab/chapter3/endpoint-agent

go mod init \
  example.com/ai-infra/endpoint-agent
```

只使用 Standard Library。

---

## 3.20.4 config.json

```json
{
  "interval": "5s",
  "timeout": "2s",
  "shutdown_timeout": "10s",
  "workers": 4,
  "targets": [
    {
      "name": "local-http",
      "type": "http",
      "url": "http://127.0.0.1:8000/",
      "expected_status": 200
    },
    {
      "name": "local-tcp",
      "type": "tcp",
      "host": "127.0.0.1",
      "port": 8000
    },
    {
      "name": "bad-port",
      "type": "tcp",
      "host": "127.0.0.1",
      "port": 65530
    }
  ]
}
```

---

## 3.20.5 config.go

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "os"
    "time"
)

type RawConfig struct {
    Interval        string         `json:"interval"`
    Timeout         string         `json:"timeout"`
    ShutdownTimeout string         `json:"shutdown_timeout"`
    Workers         int            `json:"workers"`
    Targets         []TargetConfig `json:"targets"`
}

type Config struct {
    Interval        time.Duration
    Timeout         time.Duration
    ShutdownTimeout time.Duration
    Workers         int
    Targets         []TargetConfig
}

type TargetConfig struct {
    Name           string `json:"name"`
    Type           string `json:"type"`
    URL            string `json:"url,omitempty"`
    Host           string `json:"host,omitempty"`
    Port           int    `json:"port,omitempty"`
    ExpectedStatus int    `json:"expected_status,omitempty"`
}

func loadConfig(
    path string,
) (Config, error) {
    data, err := os.ReadFile(
        path,
    )

    if err != nil {
        return Config{},
            fmt.Errorf(
                "read config %s: %w",
                path,
                err,
            )
    }

    var raw RawConfig

    decoder := json.NewDecoder(
        bytes.NewReader(data),
    )

    decoder.DisallowUnknownFields()

    if err := decoder.Decode(
        &raw,
    ); err != nil {

        return Config{},
            fmt.Errorf(
                "decode config: %w",
                err,
            )
    }

    return normalizeConfig(
        raw,
    )
}

func normalizeConfig(
    raw RawConfig,
) (Config, error) {
    interval, err := time.ParseDuration(
        raw.Interval,
    )

    if err != nil ||
        interval <= 0 {

        return Config{},
            fmt.Errorf(
                "invalid interval: %q",
                raw.Interval,
            )
    }

    timeout, err := time.ParseDuration(
        raw.Timeout,
    )

    if err != nil ||
        timeout <= 0 {

        return Config{},
            fmt.Errorf(
                "invalid timeout: %q",
                raw.Timeout,
            )
    }

    shutdownTimeout, err :=
        time.ParseDuration(
            raw.ShutdownTimeout,
        )

    if err != nil ||
        shutdownTimeout <= 0 {

        return Config{},
            fmt.Errorf(
                "invalid shutdown_timeout: %q",
                raw.ShutdownTimeout,
            )
    }

    if raw.Workers < 1 {
        return Config{},
            fmt.Errorf(
                "workers must be positive",
            )
    }

    if len(raw.Targets) == 0 {
        return Config{},
            fmt.Errorf(
                "targets cannot be empty",
            )
    }

    names := make(
        map[string]struct{},
    )

    targets := make(
        []TargetConfig,
        0,
        len(raw.Targets),
    )

    for i, target :=
        range raw.Targets {

        if err := validateTarget(
            &target,
        ); err != nil {

            return Config{},
                fmt.Errorf(
                    "targets[%d]: %w",
                    i,
                    err,
                )
        }

        if _, exists :=
            names[target.Name];
            exists {

            return Config{},
                fmt.Errorf(
                    "duplicate target name: %s",
                    target.Name,
                )
        }

        names[target.Name] =
            struct{}{}

        targets = append(
            targets,
            target,
        )
    }

    return Config{
        Interval:
            interval,
        Timeout:
            timeout,
        ShutdownTimeout:
            shutdownTimeout,
        Workers:
            raw.Workers,
        Targets:
            targets,
    }, nil
}

func validateTarget(
    target *TargetConfig,
) error {
    if target.Name == "" {
        return fmt.Errorf(
            "name cannot be empty",
        )
    }

    switch target.Type {
    case "tcp":
        if target.Host == "" {
            return fmt.Errorf(
                "%s: host cannot be empty",
                target.Name,
            )
        }

        if target.Port < 1 ||
            target.Port > 65535 {

            return fmt.Errorf(
                "%s: invalid port %d",
                target.Name,
                target.Port,
            )
        }

    case "http":
        if target.URL == "" {
            return fmt.Errorf(
                "%s: url cannot be empty",
                target.Name,
            )
        }

        if target.ExpectedStatus == 0 {
            target.ExpectedStatus =
                200
        }

        if target.ExpectedStatus < 100 ||
            target.ExpectedStatus > 599 {

            return fmt.Errorf(
                "%s: invalid expected_status %d",
                target.Name,
                target.ExpectedStatus,
            )
        }

    default:
        return fmt.Errorf(
            "%s: unsupported type %q",
            target.Name,
            target.Type,
        )
    }

    return nil
}
```

---

## 3.20.6 RawConfig vs Config

外部：

```json
"timeout": "2s"
```

是 String。

内部：

```go
time.Duration
```

流程：

```text
External Representation
↓
RawConfig
↓
Parse / Validate / Normalize
↓
Internal Config
```

这就是 Config Boundary。

---

## 3.20.7 `map[string]struct{}` 作为 Set

```go
names := make(
    map[string]struct{},
)
```

我们只关心 Key 是否出现，不需要 Value。

因此 `struct{}` 很合适。

---

## 3.20.8 checker.go

```go
package main

import (
    "context"
    "fmt"
    "net"
    "net/http"
    "strconv"
    "time"
)

type Result struct {
    Name       string    `json:"name"`
    Type       string    `json:"type"`
    Endpoint   string    `json:"endpoint"`
    OK         bool      `json:"ok"`
    CheckedAt  time.Time `json:"checked_at"`
    LatencyMS  float64   `json:"latency_ms"`
    StatusCode int       `json:"status_code,omitempty"`
    Error      string    `json:"error,omitempty"`
}

type Checker interface {
    Name() string
    Check(
        ctx context.Context,
    ) Result
}

type TCPChecker struct {
    Target  TargetConfig
    Timeout time.Duration
}

func (
    c *TCPChecker,
) Name() string {
    return c.Target.Name
}

func (
    c *TCPChecker,
) Check(
    parent context.Context,
) Result {
    start := time.Now()

    address := net.JoinHostPort(
        c.Target.Host,
        strconv.Itoa(
            c.Target.Port,
        ),
    )

    ctx, cancel :=
        context.WithTimeout(
            parent,
            c.Timeout,
        )

    defer cancel()

    dialer := net.Dialer{}

    conn, err := dialer.DialContext(
        ctx,
        "tcp",
        address,
    )

    if err != nil {
        return Result{
            Name:
                c.Target.Name,
            Type:
                "tcp",
            Endpoint:
                address,
            OK:
                false,
            CheckedAt:
                time.Now().UTC(),
            LatencyMS:
                elapsedMS(start),
            Error:
                err.Error(),
        }
    }

    defer conn.Close()

    return Result{
        Name:
            c.Target.Name,
        Type:
            "tcp",
        Endpoint:
            address,
        OK:
            true,
        CheckedAt:
            time.Now().UTC(),
        LatencyMS:
            elapsedMS(start),
    }
}

type HTTPChecker struct {
    Target  TargetConfig
    Timeout time.Duration
    Client  *http.Client
}

func (
    c *HTTPChecker,
) Name() string {
    return c.Target.Name
}

func (
    c *HTTPChecker,
) Check(
    parent context.Context,
) Result {
    start := time.Now()

    ctx, cancel :=
        context.WithTimeout(
            parent,
            c.Timeout,
        )

    defer cancel()

    request, err :=
        http.NewRequestWithContext(
            ctx,
            http.MethodGet,
            c.Target.URL,
            nil,
        )

    if err != nil {
        return Result{
            Name:
                c.Target.Name,
            Type:
                "http",
            Endpoint:
                c.Target.URL,
            OK:
                false,
            CheckedAt:
                time.Now().UTC(),
            LatencyMS:
                elapsedMS(start),
            Error:
                fmt.Sprintf(
                    "create request: %v",
                    err,
                ),
        }
    }

    response, err :=
        c.Client.Do(
            request,
        )

    if err != nil {
        return Result{
            Name:
                c.Target.Name,
            Type:
                "http",
            Endpoint:
                c.Target.URL,
            OK:
                false,
            CheckedAt:
                time.Now().UTC(),
            LatencyMS:
                elapsedMS(start),
            Error:
                err.Error(),
        }
    }

    defer response.Body.Close()

    ok := (
        response.StatusCode ==
            c.Target.ExpectedStatus
    )

    result := Result{
        Name:
            c.Target.Name,
        Type:
            "http",
        Endpoint:
            c.Target.URL,
        OK:
            ok,
        CheckedAt:
            time.Now().UTC(),
        LatencyMS:
            elapsedMS(start),
        StatusCode:
            response.StatusCode,
    }

    if !ok {
        result.Error =
            fmt.Sprintf(
                "expected HTTP %d, got %d",
                c.Target.ExpectedStatus,
                response.StatusCode,
            )
    }

    return result
}

func elapsedMS(
    start time.Time,
) float64 {
    return float64(
        time.Since(start).
            Microseconds(),
    ) / 1000
}

func buildCheckers(
    cfg Config,
    client *http.Client,
) []Checker {
    checkers := make(
        []Checker,
        0,
        len(cfg.Targets),
    )

    for _, target :=
        range cfg.Targets {

        switch target.Type {
        case "tcp":
            checkers = append(
                checkers,
                &TCPChecker{
                    Target:
                        target,
                    Timeout:
                        cfg.Timeout,
                },
            )

        case "http":
            checkers = append(
                checkers,
                &HTTPChecker{
                    Target:
                        target,
                    Timeout:
                        cfg.Timeout,
                    Client:
                        client,
                },
            )
        }
    }

    return checkers
}
```

---

## 3.20.9 Interface + Factory

Config：

```text
type=tcp
→ *TCPChecker

type=http
→ *HTTPChecker
```

高层只处理：

```go
[]Checker
```

把 Interface / Factory / Dependency Injection 全部串起来。

---

## 3.20.10 Context Tree

```text
Root Context
│
├─ TCP Probe Context
│     timeout=2s
│
├─ HTTP Probe Context
│     timeout=2s
│
└─ HTTP Probe Context
      timeout=2s
```

如果：

```text
SIGTERM
↓
Root Cancel
```

所有 Probe 一起 Cancel。

---

## 3.20.11 agent.go

```go
package main

import (
    "context"
    "log"
    "sort"
    "sync"
    "time"
)

type Summary struct {
    Total     int `json:"total"`
    Healthy   int `json:"healthy"`
    Unhealthy int `json:"unhealthy"`
}

type Snapshot struct {
    GeneratedAt time.Time `json:"generated_at"`
    Summary     Summary   `json:"summary"`
    Results     []Result  `json:"results"`
}

type Agent struct {
    checkers []Checker
    workers  int
    interval time.Duration

    mu       sync.RWMutex
    ready    bool
    snapshot Snapshot
}

func NewAgent(
    checkers []Checker,
    workers int,
    interval time.Duration,
) *Agent {
    return &Agent{
        checkers:
            checkers,
        workers:
            workers,
        interval:
            interval,
    }
}

func (
    a *Agent,
) Run(
    ctx context.Context,
) {
    log.Println(
        "agent started",
    )

    defer log.Println(
        "agent stopped",
    )

    a.runCycle(
        ctx,
    )

    ticker := time.NewTicker(
        a.interval,
    )

    defer ticker.Stop()

    for {
        select {
        case <-ticker.C:
            a.runCycle(
                ctx,
            )

        case <-ctx.Done():
            return
        }
    }
}

func (
    a *Agent,
) runCycle(
    ctx context.Context,
) {
    if ctx.Err() != nil {
        return
    }

    log.Printf(
        "probe cycle started targets=%d workers=%d",
        len(a.checkers),
        a.workers,
    )

    jobs := make(
        chan Checker,
    )

    results := make(
        chan Result,
    )

    workerCount := a.workers

    if workerCount >
        len(a.checkers) {

        workerCount =
            len(a.checkers)
    }

    var wg sync.WaitGroup

    for id := 0;
        id < workerCount;
        id++ {

        wg.Add(1)

        go func(
            workerID int,
        ) {
            defer wg.Done()

            a.worker(
                ctx,
                workerID,
                jobs,
                results,
            )
        }(id)
    }

    go func() {
        defer close(jobs)

        for _, checker :=
            range a.checkers {

            select {
            case jobs <- checker:

            case <-ctx.Done():
                return
            }
        }
    }()

    go func() {
        wg.Wait()

        close(results)
    }()

    collected := make(
        []Result,
        0,
        len(a.checkers),
    )

    for result :=
        range results {

        collected = append(
            collected,
            result,
        )
    }

    if ctx.Err() != nil {
        return
    }

    sort.Slice(
        collected,
        func(
            i int,
            j int,
        ) bool {
            return (
                collected[i].Name <
                    collected[j].Name
            )
        },
    )

    healthy := 0

    for _, result :=
        range collected {

        if result.OK {
            healthy++
        }
    }

    snapshot := Snapshot{
        GeneratedAt:
            time.Now().UTC(),
        Summary:
            Summary{
                Total:
                    len(collected),
                Healthy:
                    healthy,
                Unhealthy:
                    len(collected) -
                        healthy,
            },
        Results:
            collected,
    }

    a.mu.Lock()

    a.snapshot =
        snapshot

    a.ready =
        true

    a.mu.Unlock()

    log.Printf(
        "probe cycle finished healthy=%d unhealthy=%d",
        snapshot.Summary.Healthy,
        snapshot.Summary.Unhealthy,
    )
}

func (
    a *Agent,
) worker(
    ctx context.Context,
    workerID int,
    jobs <-chan Checker,
    results chan<- Result,
) {
    for {
        select {
        case checker, ok :=
            <-jobs:

            if !ok {
                return
            }

            result :=
                checker.Check(
                    ctx,
                )

            log.Printf(
                "probe worker=%d target=%s ok=%t latency_ms=%.2f",
                workerID,
                result.Name,
                result.OK,
                result.LatencyMS,
            )

            select {
            case results <-
                result:

            case <-ctx.Done():
                return
            }

        case <-ctx.Done():
            return
        }
    }
}

func (
    a *Agent,
) Snapshot() (
    Snapshot,
    bool,
) {
    a.mu.RLock()

    defer a.mu.RUnlock()

    if !a.ready {
        return Snapshot{},
            false
    }

    resultsCopy := append(
        []Result(nil),
        a.snapshot.Results...,
    )

    snapshot := a.snapshot
    snapshot.Results =
        resultsCopy

    return snapshot,
        true
}
```

---

## 3.20.12 Worker Pool 数据流

```text
[]Checker
↓
jobs Channel
↓
Worker Pool
↓
Checker.Check()
↓
results Channel
↓
Aggregation
↓
Snapshot
```

---

## 3.20.13 为什么 Worker Pool

如果：

```text
10000 Targets
workers=20
```

则：

```text
最多 20 个并发 Probe
```

避免：

```text
FD 风暴
Remote overload
Memory spike
瞬间 10000 Network Request
```

---

## 3.20.14 Channel Ownership

Producer：

```text
发送 jobs
↓
发完
↓
close(jobs)
```

所有 Worker Done 后：

```go
go func() {
    wg.Wait()
    close(results)
}()
```

这就是正确 Fan-In Close Pattern。

---

## 3.20.15 为什么不能先 Wait 再 Receive

如果 Results Channel 是 Unbuffered：

```text
Worker
↓
results <- result
↓
等待 Receiver
```

Main 如果先：

```go
wg.Wait()
```

就会：

```text
Main 等 Worker
Worker 等 Main Receive
```

Deadlock。

正确：

```text
协调 Goroutine Wait + close
Main 同时 range results
```

---

## 3.20.16 Deterministic Output

并发完成顺序不稳定：

```text
run1: A C B
run2: C A B
```

所以：

```go
sort.Slice(...)
```

让 API 输出稳定。

---

## 3.20.17 Snapshot + RWMutex

Agent 周期写 Snapshot，HTTP Handler 同时读。

属于：

```text
Concurrent Shared Mutable State
```

所以：

```go
sync.RWMutex
```

很合适。

---

## 3.20.18 Defensive Copy

```go
resultsCopy := append(
    []Result(nil),
    a.snapshot.Results...,
)
```

创建新 Backing Array，避免调用方修改内部 Slice。

---

## 3.20.19 api.go

```go
package main

import (
    "encoding/json"
    "net/http"
)

type API struct {
    Agent *Agent
}

type HealthResponse struct {
    Status string `json:"status"`
}

type ReadyResponse struct {
    Ready bool `json:"ready"`
}

func writeJSON(
    w http.ResponseWriter,
    status int,
    value any,
) {
    data, err := json.Marshal(
        value,
    )

    if err != nil {
        http.Error(
            w,
            "internal error",
            http.StatusInternalServerError,
        )

        return
    }

    w.Header().Set(
        "Content-Type",
        "application/json",
    )

    w.WriteHeader(
        status,
    )

    _, _ = w.Write(
        data,
    )
}

func (
    api *API,
) Health(
    w http.ResponseWriter,
    r *http.Request,
) {
    if r.Method != http.MethodGet {
        http.Error(
            w,
            "method not allowed",
            http.StatusMethodNotAllowed,
        )

        return
    }

    writeJSON(
        w,
        http.StatusOK,
        HealthResponse{
            Status:
                "alive",
        },
    )
}

func (
    api *API,
) Ready(
    w http.ResponseWriter,
    r *http.Request,
) {
    if r.Method != http.MethodGet {
        http.Error(
            w,
            "method not allowed",
            http.StatusMethodNotAllowed,
        )

        return
    }

    _, ready :=
        api.Agent.Snapshot()

    status :=
        http.StatusOK

    if !ready {
        status =
            http.StatusServiceUnavailable
    }

    writeJSON(
        w,
        status,
        ReadyResponse{
            Ready:
                ready,
        },
    )
}

func (
    api *API,
) Results(
    w http.ResponseWriter,
    r *http.Request,
) {
    if r.Method != http.MethodGet {
        http.Error(
            w,
            "method not allowed",
            http.StatusMethodNotAllowed,
        )

        return
    }

    snapshot, ready :=
        api.Agent.Snapshot()

    if !ready {
        writeJSON(
            w,
            http.StatusServiceUnavailable,
            map[string]string{
                "error":
                    "no probe snapshot available",
            },
        )

        return
    }

    writeJSON(
        w,
        http.StatusOK,
        snapshot,
    )
}
```

---

## 3.20.20 `/health` / `/ready` / `/v1/results`

### `/health`

回答：

> Process / HTTP Server 是否活着？

```json
{
  "status": "alive"
}
```

### `/ready`

回答：

> Agent 是否至少完成过一次 Probe Cycle？

未完成：

```text
HTTP 503
```

完成：

```text
HTTP 200
```

### `/v1/results`

```json
{
  "generated_at": "...",
  "summary": {
    "total": 3,
    "healthy": 2,
    "unhealthy": 1
  },
  "results": []
}
```

---

## 3.20.21 main.go

```go
package main

import (
    "context"
    "flag"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"
)

func run() int {
    configPath := flag.String(
        "config",
        "config.json",
        "path to config file",
    )

    listen := flag.String(
        "listen",
        "127.0.0.1:8080",
        "HTTP listen address",
    )

    flag.Parse()

    cfg, err := loadConfig(
        *configPath,
    )

    if err != nil {
        log.Printf(
            "config error: %v",
            err,
        )

        return 2
    }

    client := &http.Client{}

    checkers := buildCheckers(
        cfg,
        client,
    )

    agent := NewAgent(
        checkers,
        cfg.Workers,
        cfg.Interval,
    )

    api := &API{
        Agent:
            agent,
    }

    mux := http.NewServeMux()

    mux.HandleFunc(
        "/health",
        api.Health,
    )

    mux.HandleFunc(
        "/ready",
        api.Ready,
    )

    mux.HandleFunc(
        "/v1/results",
        api.Results,
    )

    server := &http.Server{
        Addr:
            *listen,
        Handler:
            mux,
        ReadHeaderTimeout:
            5 * time.Second,
        ReadTimeout:
            10 * time.Second,
        WriteTimeout:
            10 * time.Second,
        IdleTimeout:
            60 * time.Second,
    }

    ctx, stop :=
        signal.NotifyContext(
            context.Background(),
            os.Interrupt,
            syscall.SIGTERM,
        )

    defer stop()

    agentDone := make(
        chan struct{},
    )

    go func() {
        defer close(
            agentDone,
        )

        agent.Run(
            ctx,
        )
    }()

    serverErr := make(
        chan error,
        1,
    )

    go func() {
        log.Printf(
            "HTTP server started addr=%s",
            server.Addr,
        )

        serverErr <-
            server.ListenAndServe()
    }()

    exitCode := 0

    select {
    case <-ctx.Done():
        log.Println(
            "shutdown signal received",
        )

    case err := <-serverErr:
        if err != nil &&
            err != http.ErrServerClosed {

            log.Printf(
                "HTTP server failed: %v",
                err,
            )

            exitCode = 1
        }

        stop()
    }

    shutdownCtx, cancel :=
        context.WithTimeout(
            context.Background(),
            cfg.ShutdownTimeout,
        )

    defer cancel()

    log.Println(
        "shutting down HTTP server",
    )

    if err := server.Shutdown(
        shutdownCtx,
    ); err != nil {

        log.Printf(
            "graceful HTTP shutdown failed: %v",
            err,
        )

        _ = server.Close()

        exitCode = 1
    }

    select {
    case <-agentDone:
        log.Println(
            "agent shutdown complete",
        )

    case <-shutdownCtx.Done():
        log.Println(
            "agent shutdown timeout",
        )

        exitCode = 1
    }

    log.Println(
        "process shutdown complete",
    )

    return exitCode
}

func main() {
    os.Exit(
        run(),
    )
}
```

---

## 3.20.22 Composition Root

`run()`：

```text
Load Config
↓
Build http.Client
↓
Build []Checker
↓
Build Agent
↓
Build API
↓
Build HTTP Server
↓
Build Root Context
↓
Start Components
```

这就是 Composition Root。

---

## 3.20.23 Runtime Goroutine 结构

```text
main G
│
├─ HTTP Server
│   └─ 每个 Request 有自己的 Handler G
│
└─ Agent G
    └─ Probe Cycle
        ├─ Worker G0
        ├─ Worker G1
        ├─ Worker G2
        ├─ Worker G3
        ├─ Producer G
        └─ Result closer G
```

最终：

```text
Goroutines
↓
P Local Run Queue
↓
Go Scheduler
↓
M
↓
Linux Scheduler
↓
CPU
```

---

## 3.20.24 Critical Error Propagation

如果 Port 被占用：

```text
ListenAndServe
↓
Fatal Error
↓
serverErr
↓
main
↓
stop()
↓
Root Context Cancel
↓
Agent Stop
↓
Exit non-zero
```

而不是让 PID 假装健康。

---

## 3.20.25 Agent Done Channel

```go
agentDone := make(
    chan struct{},
)
```

我们只需要表达：

> Agent 已结束。

不需要传 Data，所以 `chan struct{}` 很合适。

---

## 3.20.26 运行实验

Terminal A：

```bash
python3 -m http.server \
  8000 \
  --bind 127.0.0.1
```

Terminal B：

```bash
go run . \
  -config config.json \
  -listen 127.0.0.1:8080
```

Health：

```bash
curl -i \
  http://127.0.0.1:8080/health
```

Ready：

```bash
curl -i \
  http://127.0.0.1:8080/ready
```

Results：

```bash
curl -s \
  http://127.0.0.1:8080/v1/results \
  | python3 -m json.tool
```

---

## 3.20.27 故障实验

停掉 Python HTTP Server，等待下一轮 Probe：

```bash
curl -s \
  http://127.0.0.1:8080/v1/results \
  | python3 -m json.tool
```

可以看到状态自动更新。

---

## 3.20.28 Signal Shutdown

编译：

```bash
go build \
  -o endpoint-agent
```

运行：

```bash
./endpoint-agent \
  -config config.json
```

另一个 Terminal：

```bash
pgrep endpoint-agent
```

然后：

```bash
kill -TERM <PID>
```

流程：

```text
SIGTERM
↓
NotifyContext
↓
Root Cancel
↓
Agent Stop
↓
HTTP Shutdown
↓
agentDone
↓
Exit
```

---

## 3.20.29 Exit Code

设计：

```text
0
→ Normal Shutdown

1
→ Runtime Fatal Error

2
→ Config Error
```

测试：

```bash
./endpoint-agent

echo $?
```

---

## 3.20.30 Race Detector

```bash
go run -race . \
  -config config.json
```

同时大量读 Snapshot：

```bash
for i in $(seq 1 100); do
    curl -s \
      http://127.0.0.1:8080/v1/results \
      >/dev/null &
done

wait
```

如果 RWMutex 正确，不应该出现 DATA RACE。

---

## 3.20.31 查看 Thread / FD / Socket

Thread：

```bash
ps -T \
  -p <PID>
```

Socket：

```bash
ss -ltnp \
  | grep endpoint-agent
```

FD：

```bash
ls \
  /proc/<PID>/fd
```

再次验证：

```text
Go Runtime
最终仍建立在：
Linux Process
Thread
FD
Socket
Scheduler
```

---

## 3.20.32 未来扩展

Checker Interface 可以继续增加：

```text
DNSChecker
TLSChecker
LLMChecker
GPUChecker
DiskChecker
KubernetesChecker
```

只需实现：

```go
type XxxChecker struct {
    ...
}

func (
    c *XxxChecker,
) Check(
    ctx context.Context,
) Result
```

---

## 3.20.33 LLMChecker 方向

未来：

```text
POST /v1/chat/completions
↓
最小 Prompt
↓
记录 TTFT
↓
记录 Total Latency
↓
验证 Response
```

可以把 Agent 变成 LLM Health Agent。

---

## 3.20.34 Prometheus Exporter 方向

增加：

```text
GET /metrics
```

例如：

```text
endpoint_up{name="vllm-01"} 1

endpoint_latency_seconds{
  name="vllm-01"
} 0.023
```

---

## 3.20.35 Kubernetes DaemonSet 方向

这个 Binary 很适合：

```text
Build
↓
Docker Image
↓
Kubernetes DaemonSet
```

例如：

```text
GPU Node Agent
Network Agent
Monitoring Agent
Log Agent
```

---

## 3.20.36 Production 还缺什么

当前已经是正确骨架，但 Production 还需要：

```text
Unit Test
Integration Test
Structured Logging
Metrics
Tracing
pprof
Auth
TLS
Retry / Backoff
Config Reload
Rate Limit
Build Pipeline
Container Image
Kubernetes Manifest
SLO
Alert
```

这些会在后面的课程里逐层加入。

---

# Go 部分最终心智模型

```text
                  AI Infra Go Program
                         │
                         ↓
                    Linux Process
                         │
      ┌──────────────────┼──────────────────┐
      ↓                  ↓                  ↓
   Config             Runtime            Network
      │                  │                  │
   Struct             Goroutine          net/http
 Interface              GMP             Socket
 Validation            Channel            FD
      │                Context             │
      └──────────────┬───┴──────────────────┘
                     ↓
                  Daemon
                     │
      ┌──────────────┼──────────────┐
      ↓              ↓              ↓
    Agent         Controller      Gateway
      │              │              │
      └──────────────┼──────────────┘
                     ↓
                  Kubernetes
```

---

# Go 核心术语总表

| 术语 | 当前理解 |
|---|---|
| Static Typing | 类型主要在编译阶段明确 |
| Binary | 编译得到的可执行文件 |
| Cross Compilation | 为另一 OS / CPU 架构编译 |
| Runtime | Go 程序运行时支持 |
| GC | Garbage Collection |
| Goroutine | Runtime 管理的轻量并发执行单元 |
| G | Goroutine |
| M | OS Thread |
| P | Go Code 执行许可证 + Runtime 工作台 |
| GOMAXPROCS | P 数量 / Go 并行执行上限 |
| Local Run Queue | 每个 P 自己的 Runnable G 队列 |
| Work Stealing | 空闲 P 从其他 P 获取工作 |
| Network Poller | Runtime 等待网络 FD 事件机制 |
| Channel | Typed Data Transfer + Synchronization |
| WaitGroup | 等待一组 Goroutine 完成 |
| Mutex | 保护共享 Mutable State |
| RWMutex | 多 Reader / 单 Writer Lock |
| Data Race | 缺乏同步的并发内存读写 |
| Context | Cancellation / Deadline / Timeout 传播 |
| Goroutine Leak | Goroutine 无法结束造成泄漏 |
| Worker Pool | 固定数量 Worker 消费任务 |
| Fan-Out | 分发任务 |
| Fan-In | 汇总结果 |
| Struct | 具体数据结构 |
| Method | 绑定到 Type 的 Function |
| Receiver | Method 接收者 |
| Interface | 行为 Contract |
| Implicit Implementation | Method 满足即可实现 Interface |
| Composition | 通过组合构建类型 |
| Dependency Injection | 从外部传入依赖 |
| Struct Tag | JSON/YAML 等 Field Metadata |
| Handler | HTTP Request 处理对象 |
| ServeMux | HTTP Path Router |
| Marshal | Go → JSON |
| Unmarshal | JSON → Go |
| Transport | HTTP Client 底层传输组件 |
| Connection Pool | 复用 TCP/TLS Connection |
| Liveness | Process 是否活着 |
| Readiness | Service 是否能接业务 |
| Middleware | 包装 Handler 的通用逻辑 |
| Daemon | 长期运行的后台 Process |
| SIGTERM | 请求正常终止 |
| SIGKILL | 强制杀死 |
| Graceful Shutdown | 有序停止 Service |
| Draining | 停止新流量并等待旧请求结束 |
| Composition Root | 程序顶层依赖组装点 |
| Snapshot | 某时间点系统状态 |
| Agent | 节点侧长期采集/执行程序 |
| Controller | 调整 Current State → Desired State |
| Reconciliation | Observe / Compare / Act 循环 |
| Operator | Kubernetes 领域 Controller |
| Exporter | 暴露 Metrics 的采集程序 |

---

# Go 部分最重要的 25 句话

1. Go 是静态类型、编译型语言。
2. Go Binary 很适合 Agent / CLI / Daemon 分发。
3. Go 有 Runtime，不是“编译以后就没有 Runtime”。
4. Goroutine 不等于 OS Thread。
5. G 是工作，M 是工人，P 是工作台 + 上岗证 + 本地工具箱。
6. `GOMAXPROCS` 本质上对应 P 的数量。
7. M 数量可以大于 P，因为 OS Thread 可能阻塞在 syscall 等状态。
8. 每个 P 的 Local Run Queue 能显著减少全局调度竞争。
9. Work Stealing 用来平衡不同 P 的 Runnable Work。
10. Channel 不只是 Queue，它同时带同步和 Backpressure 语义。
11. WaitGroup 用于等待，不用于传数据。
12. Mutex 适合保护共享内存；Channel 适合任务流和数据流。
13. 长期 Goroutine 必须明确退出条件。
14. Context 是 Go Infra 中 Cancellation / Timeout 传播的核心。
15. Struct 表达数据；Method 表达行为；Interface 表达调用方需要的能力。
16. Go Interface 是隐式实现，小 Interface 通常更好。
17. 固定业务 Schema 优先 Struct，而不是 `map[string]any`。
18. `http.Client` 应复用，因为底层有 Connection Pool。
19. HTTP Status 和 Transport Error 必须分层理解。
20. Handler 默认运行在并发环境，访问共享状态必须同步。
21. Daemon 不是死循环，而是完整 Lifecycle。
22. SIGTERM → Context Cancel → Worker Stop → HTTP Shutdown，是典型 Go Service 生命周期链。
23. 深层函数应该 `return error`，而不是随便 `os.Exit()`。
24. Python 和 Go 在 AI Infra 中是互补关系。
25. Go Runtime 的一切最终仍建立在 Linux Process、Thread、FD、Socket、Scheduler 之上。

---

# 第 3 章最终进度

```text
第 0 章：AI Infra 心智模型
✅ 完成

第 1 章：Linux 与计算机系统基础
✅ 完成

第 2 章：计算机网络基础
✅ 完成

第 3 章：Python + Go
✅ 完成

Python：
✅ 3.1～3.12

Go：
✅ 3.13 Go 在 AI Infra 里的角色
✅ 3.14 Go 基础语法与类型
✅ 3.15 Struct / Interface
✅ 3.16 Goroutine / Channel
✅ 3.16A GMP Scheduler 深入
✅ 3.17 Go HTTP / JSON
✅ 3.18 Go CLI / Daemon
✅ 3.18A signal.NotifyContext 的 stop
✅ 3.19 Python vs Go
✅ 3.20 AI Infra Go 小工具实战

下一主章：
⬜ 第 4 章 Docker 与 Container Internals
```

---

# 下一章预告

下一章不从背 Docker 命令开始。

先回答：

```text
Container 到底是什么？
```

然后从已经学过的：

```text
Linux Process
Namespace
cgroup
Filesystem
Network Namespace
veth
Bridge
PID
Mount
```

一步一步推导：

> **Container 本质上为什么仍然只是 Linux Process，以及 Docker 到底替你做了哪些事情。**
