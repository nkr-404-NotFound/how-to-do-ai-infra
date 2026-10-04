# LLM / AI Infra 学习笔记

## 第 3 章：Python + Go
### 3.1 ～ 3.5：Python 基础与 Infra 数据处理

> 目标：围绕 AI Infra 场景，掌握 Python Runtime、项目环境、数据结构、函数与模块、文件、JSON、YAML 等后续自动化和 API 工程必需能力。
>
> 建议实验环境：WSL2 + Ubuntu + `uv`

---

# 3.1 Python 在 AI Infra 里的角色

## 3.1.1 Python 是什么

Python 是一门通用、高级、动态类型编程语言。

**High-Level Language（高级语言）**：相比 Assembly / Machine Code，它隐藏了更多寄存器、内存布局等底层细节。

**Dynamic Typing（动态类型）**：同一个变量名可以先后引用不同类型对象。

```python
x = 10
x = "hello"
```

**Variable（变量）**：程序中引用某个对象的名字。

```text
x
↓
Python Object
```

在 AI / Infra 中，Python 常见于：

```text
Model / Training / Inference
Benchmark
Deployment Script
Health Check
API Client
Monitoring Tool
Automation
Configuration Parser
```

---

## 3.1.2 Script / Module / Package

**Script（脚本）**：完成某类自动化任务的小型程序。

**Module（模块）**：一个 Python 代码单元，很多时候一个 `.py` 文件就是一个 Module。

**Package（包）**：一组相关 Module 的集合。

Python Standard Library 常见：

```text
os
sys
json
subprocess
socket
time
pathlib
```

Third-Party Package 常见：

```text
requests
numpy
torch
fastapi
```

---

## 3.1.3 Python Interpreter 与 Linux Process

运行：

```bash
python3 app.py
```

大致：

```text
Linux
↓
Python Interpreter Process
↓
读取 app.py
↓
执行 Python Code
```

Python Program 在 Linux 中仍然拥有：

```text
PID
PPID
Virtual Memory
File Descriptors
Threads
```

### WSL 实验

```bash
mkdir -p ~/ai-infra-lab/python
cd ~/ai-infra-lab/python

cat > process_demo.py <<'PY'
import os
import time

print("PID =", os.getpid())
print("PPID =", os.getppid())

time.sleep(300)
PY

python3 process_demo.py
```

另一个 Terminal：

```bash
ps -fp <PID>
ls -l /proc/<PID>
```

---

## 3.1.4 pathlib / subprocess / Environment

`pathlib`：

```python
from pathlib import Path

p = Path("/proc/meminfo")
print(p.exists())
print(p.read_text())
```

`subprocess`：

```python
import subprocess

result = subprocess.run(
    ["ip", "route"],
    capture_output=True,
    text=True,
)

print(result.stdout)
print(result.stderr)
print(result.returncode)
```

Environment Variable：

```bash
export API_URL=http://127.0.0.1:8000
```

Python：

```python
import os

url = os.environ.get("API_URL")
```

AI Infra 常见：

```text
MODEL_PATH
API_KEY
PORT
HOST
CUDA_VISIBLE_DEVICES
HTTP_PROXY
HTTPS_PROXY
```

---

## 3.1.5 JSON / dict / list / Function / Exception

JSON：

```python
import json

text = '{"model": "qwen", "port": 8000}'
data = json.loads(text)
```

dict：

```python
config = {
    "model": "qwen",
    "port": 8000,
}
```

list：

```python
gpus = ["GPU0", "GPU1", "GPU2"]
```

Function：

```python
def check_port(host, port):
    print(host, port)
```

Exception：

```python
try:
    port = int("abc")
except ValueError:
    print("invalid port")
```

---

## 3.1.6 Python Socket

```python
import socket

socket.create_connection(
    ("127.0.0.1", 8000),
    timeout=2,
)
```

底层仍然是：

```text
Python
↓
Linux Socket API
↓
Kernel Network Stack
↓
TCP
```

---

## 3.1.7 Python → PyTorch → CUDA → GPU

```python
import torch

x = torch.randn(
    1024,
    1024,
    device="cuda",
)
```

真正大规模计算通常发生在：

```text
Python
↓
PyTorch C/C++ Backend
↓
CUDA
↓
GPU Kernel
↓
GPU
```

所以 Python 更多承担 Control / Orchestration。

**Control Plane（控制平面）**：配置、管理、调度、决策。

**Data Plane（数据平面）**：真正高速处理业务数据。

---

## 3.1 核心结论

1. Python 在 AI Infra 中主要承担自动化、API、Benchmark、配置和系统工具。
2. Python Program 本身仍是 Linux Process。
3. `os`、`subprocess`、`socket`、`json`、`pathlib` 是重要 Infra 标准库。
4. AI 大量重计算往往不由 Python Interpreter 本身完成。
5. Python 和 Go 是互补关系。

---

# 3.2 Python Runtime / venv / uv

## 3.2.1 Runtime

**Runtime（运行时环境）** 可以粗略理解成：

```text
Python Interpreter
+
Standard Library
+
Installed Packages
+
Environment
```

---

## 3.2.2 python / python3 / PATH

检查：

```bash
which python
which python3
python --version
python3 --version
```

不要默认：

```text
python == python3
```

一台机器可以同时存在：

```text
/usr/bin/python3.10
/usr/bin/python3.11
/usr/bin/python3.12
/home/user/project/.venv/bin/python
```

**PATH**：Shell 查找 executable 的目录列表。

```bash
echo $PATH
```

**which**：

```bash
which python
```

用于确认当前 Shell 最终会执行哪个 Python。

---

## 3.2.3 venv / .venv

**venv（Virtual Environment）**：

> 为某个 Project 建立相对独立的 Python Interpreter 入口和 Package 安装目录。

它不是：

```text
VM
Container
```

创建：

```bash
python3 -m venv .venv
```

或：

```bash
uv venv
```

目录通常：

```text
.venv/
├─ bin/
├─ lib/
├─ include/
└─ pyvenv.cfg
```

激活：

```bash
source .venv/bin/activate
```

核心作用之一：

> 把 `.venv/bin` 放到 PATH 前面。

退出：

```bash
deactivate
```

不激活也可：

```bash
.venv/bin/python app.py
```

---

## 3.2.4 pip / python -m pip

`pip` 是 Python Package Installer。

```bash
pip install requests
```

但更稳：

```bash
python -m pip install requests
```

因为这明确指定：

> 使用当前 Python Interpreter 对应的 pip。

---

## 3.2.5 site-packages / sys.path / sys.executable

第三方包常安装到：

```text
.venv/lib/python3.12/site-packages/
```

查看 import 搜索路径：

```bash
python -c 'import sys; print("\n".join(sys.path))'
```

查看当前解释器：

```bash
python -c 'import sys; print(sys.executable)'
```

遇到 `ModuleNotFoundError`，先检查：

```bash
which python
which pip
python --version
pip --version
python -c 'import sys; print(sys.executable)'
python -m pip --version
```

---

## 3.2.6 System Python

例如：

```text
/usr/bin/python3
```

通常由 Linux Distribution 管理。

不要随便破坏系统 Python Package。

现代 Ubuntu 可能提示：

```text
externally-managed-environment
```

推荐使用：

```text
venv
uv
pipx
```

---

## 3.2.7 apt vs pip

```bash
sudo apt install python3
```

属于：

```text
OS Package Manager
```

而：

```bash
pip install requests
```

属于：

```text
Python Package Manager
```

---

## 3.2.8 uv

`uv` 是现代 Python Project / Package Management 工具。

可以处理：

```text
Python Version
Virtual Environment
Package Installation
Dependency Resolution
pyproject.toml
Lock File
Run Command
```

初始化：

```bash
uv init
```

项目配置：

```text
pyproject.toml
```

例如：

```toml
[project]
name = "ai-infra-lab"
version = "0.1.0"
dependencies = [
    "requests",
]
```

添加依赖：

```bash
uv add requests
```

同步：

```bash
uv sync
```

运行：

```bash
uv run python app.py
```

---

## 3.2.9 Dependency / Lock File

**Dependency（依赖）**

例如你的代码使用：

```python
import requests
```

那么 `requests` 是 Direct Dependency。

它自己依赖的 `urllib3` 等属于 Transitive Dependency。

`uv.lock`：

> 锁定实际解析出的精确 Dependency Version。

目标：

**Reproducibility（可复现性）**

---

## 3.2.10 venv ≠ Container

venv 主要隔离：

```text
Python Interpreter Entry
Python Packages
```

Container 还会隔离：

```text
Process
Filesystem
Network
Mount
Hostname
Cgroups
```

常见层次：

```text
Linux Host
↓
Docker Container
↓
Python venv
↓
Python Process
```

---

## 3.2.11 systemd / Docker / CI

自动化环境不要依赖人工：

```bash
source .venv/bin/activate
```

更稳：

```text
/opt/app/.venv/bin/python /opt/app/app.py
```

例如 systemd：

```text
ExecStart=/opt/app/.venv/bin/python /opt/app/app.py
```

---

## 3.2 WSL 实验

```bash
mkdir -p ~/ai-infra-lab/chapter3
cd ~/ai-infra-lab/chapter3

uv init
uv venv
source .venv/bin/activate

which python
python --version
python -c 'import sys; print(sys.executable)'
python -m site

uv add requests

uv run python -c 'import requests; print(requests.__version__)'
uv run python -c 'import requests; print(requests.__file__)'
```

心智模型：

```text
Linux
│
├─ System Python
│   └─ /usr/bin/python3
│
└─ Project
    ├─ pyproject.toml
    ├─ uv.lock
    └─ .venv
        ├─ bin/python
        ├─ bin/pip
        └─ lib/pythonX.Y/site-packages
```

---

# 3.3 Python Data Structures

## 3.3.1 基础类型

```text
int
float
str
bool
None
```

int：

```python
gpu_count = 8
port = 8000
```

float：

```python
gpu_util = 82.5
latency = 1.23
```

str：

```python
model = "qwen"
host = "127.0.0.1"
```

bool：

```python
ready = True
healthy = False
```

None：

```python
gpu_name = None
```

---

## 3.3.2 Type Conversion

```python
int("8000")
float("3.14")
str(8000)
```

Environment Variable 通常读出来是 str，所以 Infra Script 很常做类型转换。

---

## 3.3.3 list

**list（列表）**：

> 有顺序、可变、允许重复。

```python
nodes = [
    "node-01",
    "node-02",
    "node-03",
]
```

Index 从 0 开始：

```python
nodes[0]
```

常见：

```python
len(nodes)
nodes.append("node-04")
nodes.remove("node-02")
"node-01" in nodes
```

遍历：

```python
for node in nodes:
    print(node)
```

---

## 3.3.4 tuple

**tuple（元组）**：

> 有顺序，通常不可变。

```python
address = ("127.0.0.1", 8000)
```

适合固定组合值。

---

## 3.3.5 Mutable / Immutable

**Mutable（可变）**

例如：

```text
list
dict
set
```

**Immutable（不可变）**

例如：

```text
str
int
tuple（通常）
```

---

## 3.3.6 dict

**dict（字典）**：

```text
Key → Value
```

```python
node = {
    "name": "gpu-node-01",
    "ip": "10.0.0.21",
    "gpu_count": 8,
}
```

访问：

```python
node["name"]
```

更安全取值：

```python
node.get("temperature")
node.get("temperature", 0)
```

---

## 3.3.7 Nested Data Structure

```python
cluster = {
    "nodes": [
        {
            "name": "node-01",
            "gpus": 8,
        },
        {
            "name": "node-02",
            "gpus": 4,
        },
    ]
}
```

访问：

```python
cluster["nodes"][0]["name"]
```

现实 Infra 数据经常：

```text
dict
↓
list
↓
dict
```

---

## 3.3.8 JSON ↔ Python

| JSON | Python |
|---|---|
| object | dict |
| array | list |
| string | str |
| number | int / float |
| true | True |
| false | False |
| null | None |

---

## 3.3.9 set

**set（集合）**：

> 唯一元素集合。

```python
models = {
    "qwen",
    "llama",
    "deepseek",
}
```

适合：

```text
去重
Membership Check
```

list vs set：

```text
list
→ 有顺序
→ 可重复

set
→ 唯一元素
→ 不依赖顺序
```

---

## 3.3.10 Slicing

```python
nodes[0:2]
```

规则：

```text
包含 start
不包含 end
```

常见：

```python
nodes[:2]
nodes[1:]
nodes[:]
```

---

## 3.3.11 dict.keys / values / items

```python
node.keys()
node.values()
node.items()
```

遍历：

```python
for key, value in node.items():
    print(key, value)
```

---

## 3.3.12 Unpacking

```python
address = ("127.0.0.1", 8000)

host, port = address
```

---

## 3.3.13 List Comprehension

```python
gpu_nodes = [
    node
    for node in nodes
    if node["gpu_count"] > 0
]
```

复杂逻辑不要为了短而强行写成推导式。

---

## 3.3.14 Object Reference / Copy

```python
a = [1, 2, 3]
b = a
```

此时：

```text
a
↓
same object
↑
b
```

所以：

```python
b.append(4)
```

`a` 也变化。

Assignment 不等于 Copy。

浅拷贝：

```python
b = a.copy()
```

深拷贝：

```python
import copy

b = copy.deepcopy(a)
```

---

## 3.3.15 Equality / Identity

`==`：

> 比较值。

`is`：

> 判断是否是同一个对象。

检查 None：

```python
if value is None:
    ...
```

---

## 3.3.16 Truthy / Falsy

常见 Falsy：

```python
False
None
0
0.0
""
[]
{}
set()
```

但：

```python
gpus = None
```

与：

```python
gpus = []
```

业务语义可能完全不同。

---

## 3.3.17 Hash Table / Hashable

dict / set 底层核心思想与：

**Hash Table**

有关。

常见可作为 dict Key：

```text
str
int
tuple（内容可哈希时）
```

常见不可直接作为 Key：

```text
list
dict
```

因为它们是 Mutable。

---

## 3.3.18 GPU Inventory 示例

```python
nodes = [
    {
        "name": "gpu-node-01",
        "ip": "10.0.0.11",
        "gpus": [
            {
                "id": 0,
                "model": "H100",
                "memory_gb": 80,
                "healthy": True,
            },
        ],
    },
    {
        "name": "gpu-node-02",
        "ip": "10.0.0.12",
        "gpus": [],
    },
]
```

这里同时使用：

```text
list
dict
str
int
bool
```

---

## 3.3.19 数据结构选择速查

```text
整数
→ int

文本
→ str

是否状态
→ bool

多个有序对象
→ list

固定组合值
→ tuple

对象属性
→ dict

唯一值集合
→ set
```

---

# 3.4 Function / Module / Package

## 3.4.1 层级

```text
Function
↓
Module
↓
Package
↓
Project
```

---

## 3.4.2 Function

```python
def check_port(host, port):
    print(host, port)
```

**Parameter**：Function 定义中的输入。

**Argument**：调用时真正传入的值。

```python
check_port(
    host="127.0.0.1",
    port=8000,
)
```

---

## 3.4.3 Default Argument / Return Value

```python
def check_port(
    host,
    port,
    timeout=2,
):
    ...
```

返回：

```python
def add(a, b):
    return a + b
```

没有显式 `return`：

```text
默认返回 None
```

---

## 3.4.4 Side Effect / Pure Function

**Side Effect（副作用）**：

```text
写文件
打印日志
发送 HTTP Request
修改数据库
启动 Process
修改全局变量
```

**Pure Function（纯函数）**：

> 相同输入产生相同输出，而且不修改外部状态。

```python
def gb_to_bytes(gb):
    return gb * 1024**3
```

---

## 3.4.5 Scope

**Scope（作用域）**

Local Variable：

```python
def demo():
    x = 10
```

Global Variable：

```python
API_URL = "http://127.0.0.1:8000"
```

不要滥用可变 Global State。

---

## 3.4.6 Type Hint

```python
def check_tcp(
    host: str,
    port: int,
    timeout: float = 2.0,
) -> bool:
    ...
```

帮助：

```text
IDE
Static Type Checker
代码阅读
维护
```

常见 Static Checker：

```text
mypy
pyright
```

---

## 3.4.7 Docstring

```python
def check_tcp(host: str, port: int) -> bool:
    """Check whether a TCP endpoint is reachable."""
```

用于说明 Function / Module / Class。

---

## 3.4.8 Single Responsibility

一个 Function 不要同时负责：

```text
解析配置
DNS
TCP
HTTP
写文件
发告警
```

更合理：

```text
load_config()
resolve_host()
check_tcp()
check_http()
save_result()
```

---

## 3.4.9 Module

一个 `.py` 文件通常就是一个 Module。

`network.py`：

```python
def check_tcp(host, port):
    ...
```

`main.py`：

```python
import network

network.check_tcp(...)
```

---

## 3.4.10 import 会执行 Top-Level Code

`network.py`：

```python
print("network module loaded")
```

只要：

```python
import network
```

这个 print 就会执行。

因此：

> Module Top-Level 不要放大量副作用业务逻辑。

---

## 3.4.11 Module Namespace

```python
import network

network.check_tcp()
```

`check_tcp` 属于 `network` Module Namespace。

这里的 Namespace 是 Python 名称空间，不是 Linux Network Namespace。

---

## 3.4.12 Import 形式

```python
import network
```

```python
from network import check_tcp
```

```python
import network as net
```

通常不推荐：

```python
from network import *
```

---

## 3.4.13 `__name__` / Main Guard

如果文件被直接执行：

```text
__name__ == "__main__"
```

经典：

```python
def main():
    ...


if __name__ == "__main__":
    main()
```

作用：

> 被直接运行时执行 main()，被 import 时不自动执行。

---

## 3.4.14 Package

目录：

```text
infra_tool/
├─ __init__.py
├─ network.py
├─ system.py
└─ config.py
```

`infra_tool` 是 Package。

Absolute Import：

```python
from infra_tool.network import check_tcp
```

Relative Import：

```python
from .network import check_tcp
```

---

## 3.4.15 `python -m`

```bash
python -m infra_tool.network
```

表示：

> 以 Module 方式运行 Package 中的 Module。

对于 Package，通常比：

```bash
python infra_tool/network.py
```

更规范。

---

## 3.4.16 Bytecode / `__pycache__`

Python Source：

```text
.py
```

可能缓存成：

```text
__pycache__/
network.cpython-312.pyc
```

粗略：

```text
.py Source
↓
Python Compiler
↓
Bytecode
↓
Python VM
↓
Execution
```

---

## 3.4.17 Circular Import

例如：

```text
a.py → import b
b.py → import a
```

容易导致问题。

应改善：

```text
职责拆分
Dependency Direction
```

一个简单健康方向：

```text
main / cli
↓
business logic
↓
low-level utility
```

---

## 3.4.18 Mutable Default Argument 坑

错误：

```python
def add_node(node, nodes=[]):
    nodes.append(node)
    return nodes
```

默认 List 会被多次调用复用。

正确：

```python
def add_node(node, nodes=None):
    if nodes is None:
        nodes = []

    nodes.append(node)
    return nodes
```

---

## 3.4.19 Naming

Function / Variable：

```text
snake_case
```

例如：

```python
check_tcp()
load_config()
get_gpu_count()
```

Constant：

```python
DEFAULT_PORT = 8000
DEFAULT_TIMEOUT = 2.0
```

Module：

```text
network_utils.py
gpu_monitor.py
```

---

## 3.4.20 小型 Package 实战

目录：

```text
chapter3/
├─ pyproject.toml
├─ uv.lock
├─ main.py
└─ infra_tool/
   ├─ __init__.py
   ├─ network.py
   └─ system.py
```

`network.py`：

```python
import socket


def check_tcp(
    host: str,
    port: int,
    timeout: float = 2.0,
) -> bool:
    try:
        with socket.create_connection(
            (host, port),
            timeout=timeout,
        ):
            return True
    except OSError:
        return False
```

`system.py`：

```python
import os


def process_info() -> dict:
    return {
        "pid": os.getpid(),
        "ppid": os.getppid(),
    }
```

`main.py`：

```python
from infra_tool.network import check_tcp
from infra_tool.system import process_info


def main():
    info = process_info()

    print("PID :", info["pid"])
    print("PPID:", info["ppid"])

    ok = check_tcp(
        "127.0.0.1",
        8000,
    )

    print("TCP:", ok)


if __name__ == "__main__":
    main()
```

运行：

```bash
uv run python main.py
```

---

# 3.5 File / JSON / YAML

## 3.5.1 File / File Object

Python：

```python
f = open("config.txt")
```

返回 File Object。

底层大致：

```text
Python
↓
open()
↓
Linux syscall
↓
Kernel
↓
File Descriptor
↓
Filesystem
```

---

## 3.5.2 with / Context Manager

推荐：

```python
with open("config.txt") as f:
    data = f.read()
```

**Context Manager（上下文管理器）**：

> 自动管理资源进入和退出。

大致：

```text
进入 with
↓
打开资源
↓
执行
↓
离开 with
↓
自动 close
```

---

## 3.5.3 File Mode

```text
r → read
w → write
a → append
b → binary
```

注意：

```python
open("config.txt", "w")
```

通常会清空原文件。

---

## 3.5.4 Text / Binary / Bytes

Text：

```text
JSON
YAML
Config
Log
```

Binary：

```text
Image
Model Weights
Compressed File
Executable
```

```python
text = "hello"   # str
raw = b"hello"   # bytes
```

---

## 3.5.5 Encoding

**Encoding（字符编码）**

磁盘实际存 Bytes。

```text
str
↓ Encode
bytes

bytes
↓ Decode
str
```

推荐明确：

```python
encoding="utf-8"
```

例如：

```python
with open(
    "config.txt",
    "r",
    encoding="utf-8",
) as f:
    data = f.read()
```

---

## 3.5.6 pathlib.Path

```python
from pathlib import Path

path = Path("/tmp/demo/config.json")
```

常用：

```python
path.name
path.parent
path.suffix
path.exists()
```

路径拼接：

```python
base = Path("/tmp/demo")
file = base / "config.json"
```

文本：

```python
text = Path("config.txt").read_text(
    encoding="utf-8"
)
```

写：

```python
Path("config.txt").write_text(
    "hello\n",
    encoding="utf-8",
)
```

Binary：

```python
Path("model.bin").read_bytes()
Path("output.bin").write_bytes(raw)
```

---

# 3.5.7 JSON

**JSON**

JavaScript Object Notation。

是一种：

> 文本形式结构化数据格式。

例如：

```json
{
  "model": "qwen",
  "port": 8000,
  "ready": true
}
```

JSON 与 Python：

| JSON | Python |
|---|---|
| object | dict |
| array | list |
| string | str |
| number | int / float |
| true | True |
| false | False |
| null | None |

---

## 3.5.8 Serialization / Deserialization

**Serialization（序列化）**

```text
Python Object
↓
JSON / YAML Text
```

**Deserialization（反序列化）**

```text
JSON / YAML Text
↓
Python Object
```

---

## 3.5.9 json.load / loads / dump / dumps

```python
import json
```

| 方法 | 作用 |
|---|---|
| `json.load()` | File → Python |
| `json.loads()` | String → Python |
| `json.dump()` | Python → File |
| `json.dumps()` | Python → String |

例如：

```python
text = '{"model":"qwen","port":8000}'
data = json.loads(text)
```

Pretty Print：

```python
json.dumps(
    data,
    indent=2,
    ensure_ascii=False,
)
```

---

## 3.5.10 JSON 的 Infra 角色

常见：

```text
HTTP API
Cloud API
Model API
Metadata
```

优点：

```text
结构明确
跨语言
机器处理方便
```

不足：

```text
原生不适合普通注释
人工写长配置较累
```

---

# 3.5.11 YAML

**YAML**

YAML Ain't Markup Language。

更适合：

> 人类维护的结构化配置。

例如：

```yaml
model: qwen
host: 0.0.0.0
port: 8000
enabled: true
```

常见：

```text
Kubernetes Manifest
Docker Compose
GitHub Actions
Ansible
Prometheus
Helm Values
```

---

## 3.5.12 YAML Mapping / Sequence

Mapping：

```yaml
server:
  host: 0.0.0.0
  port: 8000
```

Python：

```python
{
    "server": {
        "host": "0.0.0.0",
        "port": 8000,
    }
}
```

Sequence：

```yaml
models:
  - qwen
  - llama
```

Python：

```python
{
    "models": [
        "qwen",
        "llama",
    ]
}
```

---

## 3.5.13 YAML Indentation

YAML 对缩进敏感。

推荐：

```text
Spaces
不要 Tab
```

Kubernetes 常见：

```text
2 spaces
```

YAML 支持注释：

```yaml
# API port
port: 8000
```

---

## 3.5.14 PyYAML

安装：

```bash
uv add pyyaml
```

读取：

```python
import yaml

with open(
    "config.yaml",
    encoding="utf-8",
) as f:
    config = yaml.safe_load(f)
```

配置文件优先：

```python
yaml.safe_load(...)
```

写：

```python
yaml.safe_dump(
    config,
    f,
    sort_keys=False,
)
```

---

# 3.5.15 Kubernetes Manifest

```yaml
apiVersion: v1
kind: Pod

metadata:
  name: demo

spec:
  containers:
    - name: app
      image: nginx
```

本质：

> Structured YAML Data。

解析后仍然只是：

```text
dict
↓
list
↓
dict
```

---

## 3.5.16 Declarative / Imperative

**Declarative（声明式）**

> 描述最终想要什么状态。

```yaml
replicas: 3
```

**Imperative（命令式）**

> 描述一步一步执行什么操作。

```text
create
start
delete
restart
```

Kubernetes 强调 Declarative Model。

---

# 3.5.17 Config Validation

Parse 成功：

```text
≠
配置业务上合法
```

例如：

```yaml
port: -1
```

YAML 合法，但 TCP Port 不合法。

所以：

```text
Parse
↓
Validate
↓
Use
```

例如：

```python
port = config["server"]["port"]

if not 1 <= port <= 65535:
    raise ValueError(
        f"invalid port: {port}"
    )
```

---

## 3.5.18 Required / Optional Field

Required：

```text
model.name
```

缺失应该报错。

Optional：

```text
timeout
```

可以：

```python
timeout = config.get(
    "timeout",
    5,
)
```

---

## 3.5.19 Nested get 坑

不要：

```python
config.get("server").get("port")
```

因为 `server` 不存在时：

```text
None.get(...)
```

仍会报错。

更稳：

```python
server = config.get(
    "server",
    {},
)

port = server.get(
    "port",
    8000,
)
```

---

# 3.5.20 Configuration Precedence

**Configuration Precedence（配置优先级）**

常见：

```text
Default
<
Config File
<
Environment Variable
<
CLI Argument
```

具体规则由项目决定。

---

# 3.5.21 Secret 注意事项

不要随便把：

```text
API Key
Password
Token
```

写进：

```text
Git-tracked YAML
Docker Image
日志
```

常见方案：

```text
Environment Variable
Secret Manager
Kubernetes Secret
Vault
Cloud Secret Service
```

---

# 3.5.22 Atomic Write

**Atomic Write（原子写入）**

直接覆盖配置文件时，如果程序中途崩溃，可能留下半截文件。

常见思路：

```text
写临时文件
↓
确认成功
↓
rename
↓
替换正式文件
```

例如：

```text
config.json.tmp
↓
config.json
```

---

# 3.5.23 YAML Multi-Document

一个 YAML 文件可以有多个 Document：

```yaml
---
kind: Service
metadata:
  name: demo

---
kind: Deployment
metadata:
  name: demo
```

分隔符：

```text
---
```

Python：

```python
with open(
    "resources.yaml",
    encoding="utf-8",
) as f:
    documents = list(
        yaml.safe_load_all(f)
    )
```

Kubernetes 中很常见。

---

# 3.5.24 WSL 实验：YAML Config

```bash
cd ~/ai-infra-lab/chapter3

uv add pyyaml

cat > config.yaml <<'YAML'
cluster:
  name: ai-lab

server:
  host: 127.0.0.1
  port: 8000

models:
  - qwen
  - llama

gpu:
  enabled: true
  count: 2
YAML
```

创建：

```bash
cat > config_demo.py <<'PY'
from pathlib import Path

import yaml


def load_config(path: str) -> dict:
    text = Path(path).read_text(
        encoding="utf-8",
    )

    config = yaml.safe_load(text)

    if not isinstance(config, dict):
        raise ValueError(
            "config root must be a mapping"
        )

    return config


def validate_config(config: dict) -> None:
    server = config.get(
        "server",
        {},
    )

    port = server.get("port")

    if not isinstance(port, int):
        raise ValueError(
            "server.port must be int"
        )

    if not 1 <= port <= 65535:
        raise ValueError(
            f"invalid port: {port}"
        )


def main():
    config = load_config(
        "config.yaml"
    )

    validate_config(config)

    print(
        "cluster:",
        config["cluster"]["name"],
    )

    print(
        "endpoint:",
        config["server"]["host"],
        config["server"]["port"],
    )

    print(
        "models:",
        config["models"],
    )

    print(
        "gpu count:",
        config["gpu"]["count"],
    )


if __name__ == "__main__":
    main()
PY

uv run python config_demo.py
```

---

# 3.5.25 YAML → Python → JSON

```bash
cat > convert_demo.py <<'PY'
import json
from pathlib import Path

import yaml


config = yaml.safe_load(
    Path(
        "config.yaml"
    ).read_text(
        encoding="utf-8",
    )
)

json_text = json.dumps(
    config,
    indent=2,
    ensure_ascii=False,
)

Path(
    "config.json"
).write_text(
    json_text + "\n",
    encoding="utf-8",
)

print(json_text)
PY

uv run python convert_demo.py
cat config.json
```

数据流：

```text
YAML File
↓
yaml.safe_load
↓
Python dict / list
↓
json.dumps
↓
JSON Text
↓
write_text
↓
config.json
```

---

# 3.1 ～ 3.5 综合心智模型

```text
Linux Host
↓
Python Runtime
├─ Interpreter
├─ Standard Library
├─ site-packages
└─ Environment
     ↓
Project
├─ pyproject.toml
├─ uv.lock
├─ .venv
└─ Python Code
     ↓
Function
↓
Module
↓
Package
↓
Data Structures
├─ list
├─ tuple
├─ dict
├─ set
├─ str
├─ int
├─ float
├─ bool
└─ None
     ↓
File / Config
├─ Text
├─ Bytes
├─ Encoding
├─ JSON
└─ YAML
```

---

# 3.1 ～ 3.5 核心术语表

| 术语 | 当前理解 |
|---|---|
| Python Interpreter | 执行 Python Code 的程序 |
| Runtime | Python 程序运行所需整体环境 |
| Module | Python 代码单元，常见为 `.py` |
| Package | 一组相关 Module |
| Standard Library | Python 自带模块 |
| Third-Party Package | 外部安装的 Python 包 |
| PATH | Shell 查找 Executable 的目录列表 |
| venv | Python 虚拟环境 |
| `.venv` | 常见 Project venv 目录 |
| pip | Python Package Installer |
| site-packages | 第三方 Package 安装目录 |
| `sys.path` | Python import 搜索路径 |
| `sys.executable` | 当前 Python Interpreter 路径 |
| uv | Python 项目 / 环境 / 依赖管理工具 |
| pyproject.toml | Python Project Metadata |
| uv.lock | Dependency Lock File |
| Reproducibility | 可复现性 |
| list | 有序可变集合 |
| tuple | 固定、通常不可变序列 |
| dict | Key → Value |
| set | 唯一值集合 |
| Mutable | 可变 |
| Immutable | 不可变 |
| Object Reference | 变量引用对象 |
| Function | 可复用代码逻辑 |
| Parameter | Function 定义输入 |
| Argument | 调用 Function 时的实际值 |
| Return Value | Function 返回结果 |
| Scope | 名称可见范围 |
| Type Hint | 类型提示 |
| Docstring | 文档字符串 |
| Main Guard | `if __name__ == "__main__"` |
| Entry Point | 程序入口 |
| Circular Import | 循环导入 |
| File Object | Python 对打开文件的访问对象 |
| Context Manager | 自动管理资源生命周期 |
| str / bytes | 文本 / 原始字节 |
| Encoding | 字符与 Bytes 的编码规则 |
| UTF-8 | 常用 Unicode 编码 |
| pathlib | Python 路径操作标准库 |
| JSON | 常用机器交换格式 |
| YAML | 常用 Infra 配置格式 |
| Serialization | Object → Data Format |
| Deserialization | Data Format → Object |
| Validation | 配置业务合法性校验 |
| Declarative | 描述目标状态 |
| Imperative | 描述操作步骤 |
| Configuration Precedence | 配置优先级 |
| Atomic Write | 更安全地替换文件 |

---

# 复习重点

1. Python 在 AI Infra 里主要承担自动化、API、配置、Benchmark、系统工具和控制逻辑。
2. Python 程序本身仍是 Linux Process。
3. 一台机器上可以存在多个 Python Interpreter，排环境问题先看 `sys.executable`。
4. venv 隔离 Python Package Environment，但不是 VM / Container。
5. `uv + pyproject.toml + uv.lock` 是当前课程推荐工作流。
6. 现实 Infra 数据大量使用 `dict + list` 嵌套。
7. Python Variable 保存对象引用，`b = a` 通常不是复制。
8. Function 封装逻辑，Module 组织一类逻辑，Package 组织多个 Module。
9. `if __name__ == "__main__"` 让 Module 既能 import 又能直接运行。
10. 文本文件最终保存 Bytes，所以 Encoding 很重要。
11. JSON 更常用于 API / 机器交换，YAML 更常用于人工维护的 Infra 配置。
12. JSON / YAML 解析后本质仍然是 Python dict / list / 基础类型。
13. 配置解析成功不代表业务合法，必须 Validation。
14. Kubernetes Manifest 本质是声明式结构化数据。
15. 自动化项目应逐步从大脚本演进为职责清晰的 Function / Module / Package。

---

# 当前学习目录

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
    （已学习，但本文件按要求不展开）

⬜ 3.7 HTTP Client 与 API
⬜ 3.8 Socket 初步
⬜ 3.9 Thread / Process / Async
⬜ 3.10 GIL 与 Python 性能初步
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

> 下一主线：**3.7 HTTP Client 与 API**
>
> 会把第 2 章 HTTP / DNS / TLS 与 Python 正式连接起来，使用 Python 完成 GET / POST、Header、Bearer Token、JSON Body、Timeout、异常分类，并编写 OpenAI-compatible / vLLM API Client。
