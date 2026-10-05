# LLM / AI Infra 学习笔记

## 第 3 章：Python + Go
### 3.11 ～ 3.12：Logging / Error Handling 与 AI Infra Python 小工具实战

> 这一部分是 Python 阶段的收官。
>
> 主线：
>
> ```text
> Logging
> ↓
> Exception / Error Handling
> ↓
> Structured Result
> ↓
> Concurrent Endpoint Inspector
> ↓
> CLI / JSON Report / Exit Code
> ```
>
> 建议环境：WSL2 + Ubuntu + `uv`

---

# 3.11 Logging / Error Handling

## 3.11.1 为什么不能长期只用 print()

最开始：

```python
print("service started")
print("request failed")
```

完全没问题。

但程序逐渐变成：

```text
多个 Module
多个 Thread
多个 Worker
后台 Service
长时间运行
```

以后，单纯 `print()` 很快就不够用了。

---

## 3.11.2 Logging

**Logging**

中文：

**日志记录**

表示：

> 程序运行时持续记录重要事件、状态、错误和上下文。

例如：

```text
Service Started
Model Loaded
Request Received
Retrying
Connection Failed
Worker Exited
```

一条完整日志最好能回答：

```text
什么时候
发生了什么
严重程度
哪个组件
哪个请求
哪个对象
为什么失败
```

---

## 3.11.3 Python logging Module

Python Standard Library：

```python
import logging
```

更常见：

```python
logger = logging.getLogger(
    __name__
)

logger.info(
    "service started"
)
```

---

## 3.11.4 Logging Level

常见：

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

### DEBUG

用于排障细节：

```text
参数
内部状态
重试次数
连接目标
解析后的配置
```

### INFO

正常运行的重要事件：

```text
service started
model loaded
worker ready
request completed
```

### WARNING

出现不理想情况，但程序还能继续：

```text
retrying request
slow response
fallback config used
disk usage high
```

### ERROR

当前操作失败：

```text
API request failed
config invalid
database unavailable
```

### CRITICAL

核心功能可能无法继续：

```text
failed to load model
cannot bind required port
all workers unavailable
```

---

## 3.11.5 basicConfig / Format

```python
logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "%(levelname)s "
        "%(name)s "
        "%(message)s"
    ),
)
```

常见 Format Field：

```text
%(asctime)s
→ 时间

%(levelname)s
→ Log Level

%(name)s
→ Logger Name

%(message)s
→ Message

%(process)d
→ PID

%(threadName)s
→ Thread Name
```

Infra 中 PID / Thread 很重要，因为一个服务可能有多个 Worker / Thread。

---

## 3.11.6 Module Logger

```python
logger = logging.getLogger(
    __name__
)
```

假设文件：

```text
infra_tool/network.py
```

Logger Name 可能是：

```text
infra_tool.network
```

这样可以知道日志来自哪个 Module。

---

## 3.11.7 参数化 Logging

推荐：

```python
logger.info(
    "connecting to %s:%d",
    host,
    port,
)
```

相比：

```python
logger.info(
    "host=" + host
)
```

更适合 logging 框架的延迟格式化模式。

---

## 3.11.8 日志 Context

差：

```text
request failed
```

好：

```text
request failed host=10.0.0.12 port=8000 timeout=2
```

更好：

```text
request_id=abc123
target=vllm-01
host=10.0.0.12
port=8000
error=connection_refused
```

---

## 3.11.9 Request ID / Correlation ID

**Request ID**：

> 标识某一个请求。

例如：

```text
request_id=9f2a
```

多个组件带同一个 ID：

```text
API Gateway
↓
Router
↓
Model Worker
```

就能串起整个请求链路。

**Correlation ID** 更泛：

> 用于关联多个相关事件 / 跨服务调用。

---

## 3.11.10 Structured Logging

**Structured Logging**

中文：

**结构化日志**

例如：

```json
{
  "level": "ERROR",
  "event": "request_failed",
  "host": "10.0.0.12",
  "port": 8000,
  "error": "connection_refused"
}
```

适合：

```text
Loki
Elasticsearch
OpenSearch
Cloud Logging
```

因为机器可以按字段查询。

---

## 3.11.11 stdout / stderr 与 Container

Container 应用常见：

```text
Application
↓
stdout / stderr
↓
Container Runtime
↓
Log Collector
↓
Central Logging
```

例如：

```bash
docker logs <container>
kubectl logs <pod>
```

而不是每个 Container 自己维护复杂 `/var/log/...`。

---

## 3.11.12 File Logging / Log Rotation

传统 Server 可能写：

```text
/var/log/app/app.log
```

于是要考虑：

```text
Disk Full
Permission
Retention
Rotation
```

**Log Rotation**：

```text
app.log
app.log.1
app.log.2.gz
```

Linux 常见：

```text
logrotate
```

Python 也有：

```text
RotatingFileHandler
TimedRotatingFileHandler
```

---

## 3.11.13 Secret Redaction

不要记录：

```text
Password
API Key
Bearer Token
Cookie
Private Key
Credential
```

例如不要：

```python
logger.info(
    "api_key=%s",
    api_key,
)
```

**Redaction**：

```text
sk-1234567890
↓
sk-****7890
```

或者：

```text
<redacted>
```

---

## 3.11.14 Logging 不是越多越好

过量日志可能造成：

```text
大量 I/O
Disk 膨胀
成本增加
性能下降
噪音增加
```

所以要考虑：

**Signal-to-Noise Ratio**

以及高频场景下的：

**Sampling**

---

# 3.11.15 Exception / Error Handling

**Exception**：

> Python Runtime 中表示异常情况的对象。

例如：

```python
int("abc")
```

产生：

```text
ValueError
```

---

## 3.11.16 raise

```python
if port < 1:
    raise ValueError(
        f"invalid port: {port}"
    )
```

表示：

> 主动抛出 Exception。

---

## 3.11.17 try / except

```python
try:
    do_work()

except ValueError:
    ...
```

最重要原则：

> 只捕获你真正知道如何处理的 Exception。

---

## 3.11.18 不要吞异常

危险：

```python
try:
    do_work()

except Exception:
    pass
```

这种属于：

**Swallow Exception**

并可能造成：

**Silent Failure**

例如：

```text
Backup 没成功
Monitoring 没报警
Data 没同步
Job 没提交
```

但程序没有明确错误，甚至 Exit 0。

---

## 3.11.19 Traceback

**Traceback**

中文：

**异常调用栈**

告诉你：

```text
哪一行失败
谁调用了它
调用链是什么
Exception Type
Exception Message
```

例如：

```text
main()
↓
load_config()
↓
parse_port()
↓
ValueError
```

---

## 3.11.20 logger.exception()

在 `except` 中：

```python
try:
    do_work()

except Exception:
    logger.exception(
        "work failed"
    )
```

会记录：

```text
ERROR Message
+
完整 Traceback
```

也可以：

```python
logger.error(
    "work failed",
    exc_info=True,
)
```

---

## 3.11.21 Exception Chain

例如底层：

```text
ConnectionRefusedError
```

业务层：

```python
raise RuntimeError(
    "service unavailable"
) from exc
```

形成：

```text
业务异常
↓ caused by
底层异常
```

这叫：

**Exception Chaining**

---

## 3.11.22 Layered Error Handling

典型：

```text
Socket Layer
↓
ConnectionRefusedError

HTTP Layer
↓
ConnectionError

Service Client Layer
↓
ServiceUnavailable

CLI Layer
↓
Log + Exit Code
```

一个实用原则：

### Library Layer

```text
raise
convert exception
```

### Application / CLI Layer

```text
最终 Logging
Exit Code
User-facing Error
```

避免同一个 Exception 被每层重复记录。

---

## 3.11.23 Catch / Propagate / Convert

遇到 Exception 常见选择：

```text
Handle
Retry
Convert
Log and re-raise
Propagate
Exit
```

### Convert Example

```python
try:
    socket.create_connection(
        (host, port),
        timeout=2,
    )

except OSError as exc:
    raise RuntimeError(
        f"service unavailable: {host}:{port}"
    ) from exc
```

### Propagate

如果当前层不知道如何处理：

> 不要乱 catch，让异常继续向上传播。

---

## 3.11.24 finally / Context Manager

```python
resource = acquire()

try:
    use(resource)

finally:
    release(resource)
```

如果有 Context Manager：

```python
with open(...) as f:
    ...
```

通常更清晰。

---

## 3.11.25 Narrow Exception Scope

不要：

```python
try:
    load_config()
    connect_db()
    call_api()
    save_file()
    notify()
except Exception:
    ...
```

更好：

> `try` 只包真正需要处理的 Operation。

---

## 3.11.26 Custom Exception

```python
class ConfigError(Exception):
    pass
```

然后：

```python
raise ConfigError(
    "missing server.port"
)
```

只有上层确实需要区别处理时，才值得定义不同 Exception Type。

---

## 3.11.27 Fail Fast

**Fail Fast**

表示：

> 发现关键错误尽早停止，而不是带着错误状态继续运行。

例如：

```text
Load Config
↓
Validate
↓
失败立即退出
```

---

## 3.11.28 Transient / Permanent Error

**Transient Error**：

```text
503
Temporary Network Failure
Connection Reset
```

可能 Retry。

**Permanent Error**：

```text
Invalid Config
Wrong Credential
Bad Request
Unsupported Model
```

重复相同请求通常没有意义。

---

## 3.11.29 Structured Result vs Exception

监控工具中：

```text
目标 Down
```

不一定需要抛 Exception。

例如：

```python
{
    "ok": False,
    "stage": "tcp",
    "error": "connection_refused",
}
```

这叫：

**Structured Result**

而真正 Exception 更适合：

```text
程序自身 Bug
配置解析崩溃
内部状态不一致
```

---

## 3.11.30 Logs / Metrics / Traces

```text
Logs
→ 单次事件 / 详细上下文

Metrics
→ 聚合数字

Traces
→ 请求跨多个 Service 的完整路径
```

后续 OpenTelemetry 会继续深入。

---

# 3.12 AI Infra Python 小工具实战

## 3.12.1 项目目标

实现：

> **Service / Model Endpoint Inspector**

架构：

```text
config.yaml
↓
Validation
↓
Thread Pool
├─ HTTP Check
├─ HTTP Check
├─ TCP Check
└─ TCP Check
↓
Structured Result
↓
Logging
↓
JSON Report
↓
Exit Code
```

---

## 3.12.2 配置示例

```yaml
concurrency: 4
timeout: 2.0

targets:
  - name: local-http
    type: http
    url: http://127.0.0.1:8000
    expected_status: 200

  - name: local-tcp
    type: tcp
    host: 127.0.0.1
    port: 8000

  - name: bad-port
    type: tcp
    host: 127.0.0.1
    port: 65530
```

---

## 3.12.3 为什么使用 Thread Pool

任务主要是：

```text
TCP connect
HTTP request
```

属于：

```text
I/O-bound
```

并且 `requests` 是 Blocking Library。

因此：

> 有界 Thread Pool 是当前最简单、合理的方案。

---

## 3.12.4 Project Structure

```text
endpoint-inspector/
│
├─ pyproject.toml
├─ uv.lock
├─ config.yaml
├─ report.json
│
└─ endpoint_inspector/
    ├─ __init__.py
    ├─ config.py
    ├─ checker.py
    ├─ logging_setup.py
    └─ main.py
```

职责：

```text
config.py
→ Config / Validation

checker.py
→ TCP / HTTP Check

logging_setup.py
→ Logging

main.py
→ CLI / Thread Pool / Report / Exit Code
```

---

## 3.12.5 创建项目

```bash
cd ~/ai-infra-lab/chapter3

mkdir -p endpoint-inspector
cd endpoint-inspector

uv init
uv add requests pyyaml

mkdir -p endpoint_inspector
touch endpoint_inspector/__init__.py
```

---

## 3.12.6 config.py

```python
from pathlib import Path

import yaml


class ConfigError(Exception):
    """Raised when the configuration is invalid."""


def load_config(
    path: Path,
) -> dict:
    try:
        text = path.read_text(
            encoding="utf-8",
        )
    except OSError as exc:
        raise ConfigError(
            f"failed to read config: {path}"
        ) from exc

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(
            "invalid YAML"
        ) from exc

    if not isinstance(raw, dict):
        raise ConfigError(
            "config root must be a mapping"
        )

    concurrency = raw.get(
        "concurrency",
        4,
    )

    timeout = raw.get(
        "timeout",
        2.0,
    )

    targets = raw.get("targets")

    if (
        not isinstance(concurrency, int)
        or isinstance(concurrency, bool)
        or concurrency < 1
    ):
        raise ConfigError(
            "concurrency must be a positive integer"
        )

    if (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or timeout <= 0
    ):
        raise ConfigError(
            "timeout must be a positive number"
        )

    if not isinstance(targets, list):
        raise ConfigError(
            "targets must be a list"
        )

    normalized_targets = []
    names = set()

    for index, target in enumerate(
        targets
    ):
        normalized = validate_target(
            target,
            index=index,
        )

        name = normalized["name"]

        if name in names:
            raise ConfigError(
                f"duplicate target name: {name}"
            )

        names.add(name)

        normalized_targets.append(
            normalized
        )

    return {
        "concurrency": concurrency,
        "timeout": float(timeout),
        "targets": normalized_targets,
    }


def validate_target(
    target: object,
    index: int,
) -> dict:
    if not isinstance(target, dict):
        raise ConfigError(
            f"targets[{index}] must be a mapping"
        )

    name = target.get("name")
    target_type = target.get("type")

    if (
        not isinstance(name, str)
        or not name.strip()
    ):
        raise ConfigError(
            f"targets[{index}].name must be a non-empty string"
        )

    if target_type not in {
        "tcp",
        "http",
    }:
        raise ConfigError(
            f"{name}: type must be tcp or http"
        )

    if target_type == "tcp":
        host = target.get("host")
        port = target.get("port")

        if (
            not isinstance(host, str)
            or not host.strip()
        ):
            raise ConfigError(
                f"{name}: host must be a non-empty string"
            )

        if (
            not isinstance(port, int)
            or isinstance(port, bool)
            or not 1 <= port <= 65535
        ):
            raise ConfigError(
                f"{name}: port must be between 1 and 65535"
            )

        return {
            "name": name,
            "type": "tcp",
            "host": host,
            "port": port,
        }

    url = target.get("url")

    expected_status = target.get(
        "expected_status",
        200,
    )

    if (
        not isinstance(url, str)
        or not url.strip()
    ):
        raise ConfigError(
            f"{name}: url must be a non-empty string"
        )

    if (
        not isinstance(expected_status, int)
        or isinstance(expected_status, bool)
        or not 100 <= expected_status <= 599
    ):
        raise ConfigError(
            f"{name}: invalid expected_status"
        )

    return {
        "name": name,
        "type": "http",
        "url": url,
        "expected_status": expected_status,
    }
```

---

## 3.12.7 Validation / Normalization

外部 YAML：

```text
Unvalidated Input
```

经过：

```text
Parse
↓
Validate
↓
Normalize
```

后面的代码可以假设：

```text
type 一定 tcp/http
port 一定合法
name 一定存在
```

这就是 Fail Fast 在实际工程中的应用。

---

## 3.12.8 checker.py

```python
import socket
import time

import requests


def check_target(
    target: dict,
    timeout: float,
) -> dict:
    if target["type"] == "tcp":
        return check_tcp(
            target,
            timeout,
        )

    if target["type"] == "http":
        return check_http(
            target,
            timeout,
        )

    raise ValueError(
        f"unsupported target type: {target['type']}"
    )


def check_tcp(
    target: dict,
    timeout: float,
) -> dict:
    host = target["host"]
    port = target["port"]

    start = time.perf_counter()

    try:
        with socket.create_connection(
            (host, port),
            timeout=timeout,
        ):
            pass

        return build_result(
            target=target,
            ok=True,
            stage="tcp",
            start=start,
            error_type=None,
            error=None,
            status_code=None,
        )

    except socket.gaierror as exc:
        return build_result(
            target=target,
            ok=False,
            stage="dns",
            start=start,
            error_type=type(exc).__name__,
            error=str(exc),
            status_code=None,
        )

    except ConnectionRefusedError as exc:
        return build_result(
            target=target,
            ok=False,
            stage="tcp",
            start=start,
            error_type=type(exc).__name__,
            error="connection refused",
            status_code=None,
        )

    except (socket.timeout, TimeoutError) as exc:
        return build_result(
            target=target,
            ok=False,
            stage="tcp",
            start=start,
            error_type=type(exc).__name__,
            error="timeout",
            status_code=None,
        )

    except OSError as exc:
        return build_result(
            target=target,
            ok=False,
            stage="tcp",
            start=start,
            error_type=type(exc).__name__,
            error=str(exc),
            status_code=None,
        )


def check_http(
    target: dict,
    timeout: float,
) -> dict:
    url = target["url"]
    expected_status = target[
        "expected_status"
    ]

    start = time.perf_counter()

    try:
        response = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
        )

    except requests.exceptions.Timeout as exc:
        return build_result(
            target=target,
            ok=False,
            stage="http",
            start=start,
            error_type=type(exc).__name__,
            error="timeout",
            status_code=None,
        )

    except requests.exceptions.SSLError as exc:
        return build_result(
            target=target,
            ok=False,
            stage="tls",
            start=start,
            error_type=type(exc).__name__,
            error=str(exc),
            status_code=None,
        )

    except requests.exceptions.ConnectionError as exc:
        return build_result(
            target=target,
            ok=False,
            stage="connection",
            start=start,
            error_type=type(exc).__name__,
            error=str(exc),
            status_code=None,
        )

    except requests.exceptions.RequestException as exc:
        return build_result(
            target=target,
            ok=False,
            stage="http",
            start=start,
            error_type=type(exc).__name__,
            error=str(exc),
            status_code=None,
        )

    ok = (
        response.status_code
        == expected_status
    )

    error = None

    if not ok:
        error = (
            f"expected HTTP "
            f"{expected_status}, "
            f"got {response.status_code}"
        )

    return build_result(
        target=target,
        ok=ok,
        stage="http",
        start=start,
        error_type=(
            None
            if ok
            else "UnexpectedStatus"
        ),
        error=error,
        status_code=response.status_code,
    )


def build_result(
    target: dict,
    ok: bool,
    stage: str,
    start: float,
    error_type: str | None,
    error: str | None,
    status_code: int | None,
) -> dict:
    latency_ms = (
        time.perf_counter()
        - start
    ) * 1000

    if target["type"] == "tcp":
        endpoint = (
            f"{target['host']}:"
            f"{target['port']}"
        )
    else:
        endpoint = target["url"]

    return {
        "name": target["name"],
        "type": target["type"],
        "endpoint": endpoint,
        "ok": ok,
        "stage": stage,
        "latency_ms": round(
            latency_ms,
            2,
        ),
        "status_code": status_code,
        "error_type": error_type,
        "error": error,
    }
```

---

## 3.12.9 Structured Result 的设计

区分：

### 被检测对象坏了

```text
Connection refused
Timeout
HTTP 503
DNS failed
```

返回：

```python
{
    "ok": False,
    ...
}
```

### Inspector 自己坏了

```text
代码 Bug
内部状态错误
不支持的类型
```

才属于 Exception。

---

## 3.12.10 TCP Healthy != Application Healthy

TCP 成功只表示：

```text
某个进程接受了 TCP Connection
```

不代表：

```text
HTTP 正常
vLLM Ready
模型已加载
Inference 正常
```

层级：

```text
TCP Healthy
<
HTTP Healthy
<
Application Healthy
```

---

## 3.12.11 logging_setup.py

```python
import logging
import sys


def setup_logging(
    level: str,
) -> None:
    numeric_level = getattr(
        logging,
        level.upper(),
        logging.INFO,
    )

    logging.basicConfig(
        level=numeric_level,
        stream=sys.stderr,
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "pid=%(process)d "
            "thread=%(threadName)s "
            "%(name)s "
            "%(message)s"
        ),
    )
```

设计：

```text
Logs
→ stderr

Machine Result
→ stdout / report.json
```

---

## 3.12.12 main.py

```python
import argparse
import json
import logging
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

from .checker import check_target
from .config import (
    ConfigError,
    load_config,
)
from .logging_setup import (
    setup_logging,
)


logger = logging.getLogger(
    __name__
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Check TCP and HTTP "
            "service endpoints."
        )
    )

    parser.add_argument(
        "--config",
        default="config.yaml",
        help="path to YAML config",
    )

    parser.add_argument(
        "--output",
        default="report.json",
        help="path to JSON report",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=[
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
        ],
    )

    return parser.parse_args()


def run_checks(
    targets: list[dict],
    timeout: float,
    concurrency: int,
) -> list[dict]:
    results = []

    logger.info(
        "starting endpoint checks "
        "targets=%d concurrency=%d "
        "timeout=%.2f",
        len(targets),
        concurrency,
        timeout,
    )

    with ThreadPoolExecutor(
        max_workers=concurrency,
        thread_name_prefix="probe",
    ) as executor:

        future_to_target = {
            executor.submit(
                check_target,
                target,
                timeout,
            ): target
            for target in targets
        }

        for future in as_completed(
            future_to_target
        ):
            target = future_to_target[
                future
            ]

            try:
                result = future.result()

            except Exception:
                logger.exception(
                    "unexpected checker "
                    "failure target=%s",
                    target["name"],
                )

                result = {
                    "name": target["name"],
                    "type": target["type"],
                    "endpoint": None,
                    "ok": False,
                    "stage": "internal",
                    "latency_ms": None,
                    "status_code": None,
                    "error_type": "InternalError",
                    "error": "unexpected checker failure",
                }

            results.append(result)

            if result["ok"]:
                logger.info(
                    "check succeeded "
                    "target=%s "
                    "latency_ms=%s",
                    result["name"],
                    result["latency_ms"],
                )

            else:
                logger.warning(
                    "check failed "
                    "target=%s "
                    "stage=%s "
                    "error_type=%s "
                    "error=%s",
                    result["name"],
                    result["stage"],
                    result["error_type"],
                    result["error"],
                )

    order = {
        target["name"]: index
        for index, target in enumerate(
            targets
        )
    }

    results.sort(
        key=lambda result:
            order[result["name"]]
    )

    return results


def build_report(
    results: list[dict],
) -> dict:
    healthy = sum(
        1
        for result in results
        if result["ok"]
    )

    total = len(results)

    return {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "summary": {
            "total": total,
            "healthy": healthy,
            "unhealthy": total - healthy,
        },
        "results": results,
    }


def write_report(
    report: dict,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    text = json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    temp_path = output_path.with_suffix(
        output_path.suffix + ".tmp"
    )

    temp_path.write_text(
        text,
        encoding="utf-8",
    )

    temp_path.replace(
        output_path
    )


def main() -> int:
    args = parse_args()

    setup_logging(
        args.log_level
    )

    try:
        config = load_config(
            Path(args.config)
        )

    except ConfigError as exc:
        logger.error(
            "configuration error: %s",
            exc,
        )
        return 2

    results = run_checks(
        targets=config["targets"],
        timeout=config["timeout"],
        concurrency=config["concurrency"],
    )

    report = build_report(
        results
    )

    try:
        write_report(
            report,
            Path(args.output),
        )

    except OSError:
        logger.exception(
            "failed to write report "
            "path=%s",
            args.output,
        )
        return 2

    print(
        json.dumps(
            report,
            ensure_ascii=False,
        )
    )

    unhealthy = report["summary"][
        "unhealthy"
    ]

    if unhealthy > 0:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
```

---

## 3.12.13 argparse / CLI

**CLI**

Command-Line Interface。

例如：

```bash
python -m endpoint_inspector.main \
  --config prod.yaml \
  --output result.json \
  --log-level DEBUG
```

`argparse` 是 Python Standard Library 的 CLI 参数解析工具。

Infra Tool 很适合 CLI：

```text
同一份代码
+
不同参数
↓
Dev / Test / Prod / CI / Container
```

---

## 3.12.14 ThreadPoolExecutor / Bounded Concurrency

```python
with ThreadPoolExecutor(
    max_workers=concurrency,
) as executor:
```

例如：

```yaml
concurrency: 4
```

表示最多 4 个 Probe 同时运行。

不是：

```text
10000 Target
→ 10000 Thread
```

---

## 3.12.15 Future / as_completed

```python
future = executor.submit(
    check_target,
    target,
    timeout,
)
```

得到：

```text
Future
```

`as_completed()`：

> 谁先完成就先处理谁。

最后重新 `sort()`，让报告顺序和配置一致。

这叫：

**Deterministic Output**

---

## 3.12.16 Worker 内部异常

正常网络故障已经转成 Result：

```text
Connection refused
Timeout
HTTP 503
```

所以 `future.result()` 外层：

```python
except Exception:
    logger.exception(...)
```

只负责：

> 未预料到的 Internal Error。

Monitoring Tool 可以记录某个 Target Internal Error，然后继续检查其他 Target。

---

## 3.12.17 Aggregation

多个结果：

```text
Target A healthy
Target B healthy
Target C down
```

汇总：

```json
{
  "total": 3,
  "healthy": 2,
  "unhealthy": 1
}
```

这叫：

**Aggregation**

---

## 3.12.18 UTC Timestamp

```python
datetime.now(
    timezone.utc
)
```

Infra 内部时间通常优先统一 UTC，因为：

```text
跨时区
多机房
Cloud
日志关联
夏令时
```

更容易处理。

---

## 3.12.19 Atomic Write

```text
report.json.tmp
↓
写完整
↓
replace
↓
report.json
```

避免程序中途崩溃留下半截 JSON。

---

## 3.12.20 Exit Code Design

设计：

```text
0
→ 所有 Target Healthy

1
→ Inspector 正常执行，但存在 Unhealthy Target

2
→ Inspector 自己无法完成
   例如 Config Error / Report Write Error
```

Shell / CI 因此可以区分：

```text
目标故障
vs
工具故障
```

---

## 3.12.21 SystemExit

```python
if __name__ == "__main__":
    raise SystemExit(
        main()
    )
```

`main()` 返回：

```text
0 → exit 0
1 → exit 1
2 → exit 2
```

---

# 3.12.22 WSL 测试

启动 HTTP Server：

```bash
cd ~/ai-infra-lab/chapter3/endpoint-inspector

python3 -m http.server \
  8000 \
  --bind 127.0.0.1
```

检查：

```bash
ss -ltnp | grep ':8000'
```

运行：

```bash
uv run python \
  -m endpoint_inspector.main
```

查看 Exit Code：

```bash
echo $?
```

查看报告：

```bash
cat report.json
```

---

## 3.12.23 测试：全部成功

删除 `bad-port` 后：

```bash
uv run python \
  -m endpoint_inspector.main

echo $?
```

预期：

```text
0
```

---

## 3.12.24 测试：Config Error

例如：

```yaml
port: 99999
```

预期：

```text
configuration error
```

Exit：

```text
2
```

---

## 3.12.25 测试：DNS Error

加入：

```yaml
  - name: bad-dns
    type: tcp
    host: this-host-should-not-exist.invalid
    port: 8000
```

预期：

```json
{
  "ok": false,
  "stage": "dns"
}
```

---

## 3.12.26 测试：HTTP 404

```yaml
  - name: missing-page
    type: http
    url: http://127.0.0.1:8000/not-found
    expected_status: 200
```

预期：

```json
{
  "ok": false,
  "stage": "http",
  "status_code": 404
}
```

说明：

```text
TCP 成功
HTTP 成功到达
Application Result 不符合预期
```

---

## 3.12.27 测试：Connection Refused

停止本地 HTTP Server 后运行 Inspector。

TCP Target 可能：

```text
ConnectionRefusedError
```

HTTP Target 可能：

```text
requests.ConnectionError
```

这说明：

> 高层 Library 越方便，通常也会隐藏更多底层细节。

---

## 3.12.28 stdout / stderr 分离

```bash
uv run python \
  -m endpoint_inspector.main \
  > stdout.json
```

日志仍出现在 Terminal，因为：

```text
Logs → stderr
```

而：

```bash
cat stdout.json
```

只有机器可解析 JSON。

还可以：

```bash
uv run python \
  -m endpoint_inspector.main \
  2> inspector.log \
  > result.json
```

得到：

```text
inspector.log
→ Human Diagnostic

result.json
→ Machine Data
```

---

# 3.12.29 为什么这已经像真正 Infra Tool

它已经包含：

```text
Configuration
Validation
Package Structure
Concurrency
Timeout
Error Classification
Logging
Structured Result
CLI
JSON Report
Atomic Write
Exit Code
```

这已经不是简单：

```python
print(requests.get(url))
```

而是完整的 Engineering 结构。

---

## 3.12.30 为什么暂时不加 Retry

Health Inspector 的目标：

> 描述当前状态。

如果失败自动 Retry 很多次：

```text
真实 Latency 被掩盖
Probe 时间增长
故障发现变慢
```

当前先保持：

```text
一次 Probe
→ 一次 Result
```

---

## 3.12.31 为什么暂时不使用 Async

当前：

```text
几个～几百 Target
+
requests Blocking API
```

Thread Pool 足够合理。

如果未来：

```text
10000 Endpoints
高频 Probe
大量 Streaming
```

再考虑：

```text
asyncio
httpx.AsyncClient
Semaphore
```

---

## 3.12.32 为什么不使用 subprocess + curl

虽然可以：

```text
Python
↓
subprocess
↓
curl
```

但已有 `requests`，能直接得到：

```text
status_code
Exception
Headers
Response
```

原则：

> 有稳定 Library 时，不要什么都包成 CLI。

---

# 3.12.33 完整数据流

```text
               config.yaml
                    │
                    ↓
               load_config
                    │
              YAML safe_load
                    │
                Validation
                    │
                    ↓
               Python dict
                    │
                    ↓
          ThreadPoolExecutor
          ┌─────────┼──────────┐
          ↓         ↓          ↓
       TCP Check HTTP Check  TCP Check
          │         │          │
          ↓         ↓          ↓
       Socket    requests    Socket
          │         │          │
          └─────────┼──────────┘
                    ↓
             Structured Results
                    │
          ┌─────────┴─────────┐
          ↓                   ↓
       Logging             build_report
       stderr                  │
                               ↓
                           JSON Object
                               │
                    ┌──────────┴──────────┐
                    ↓                     ↓
                stdout                 report.json
                                           │
                                      Atomic Write
```

---

# 3.12.34 Concurrency 模型

```text
Main Thread
│
├─ Worker 0 → Target A → wait network
├─ Worker 1 → Target B → wait network
└─ Worker 2 → Target C → wait network

Main Thread
↓
as_completed()
↓
谁先完成先收结果
```

Worker 完成后会复用，而不是一个 Target 永久对应一个 Thread。

---

# 3.12.35 高并发时真正要考虑什么

不要看到：

```text
max_workers=5000
```

就只想到“更快”。

Infra Engineer 应该同时想到：

```text
FD Limit
Ephemeral Port
DNS Capacity
Remote Rate Limit
Memory
Socket Buffer
NAT Conntrack
TIME_WAIT
Proxy
Timeout
```

这就是前两章 Linux / Network 基础开始真正发挥作用。

---

# 3.12.36 扩展为 LLM Inspector

未来可以检查：

```yaml
targets:
  - name: qwen-vllm
    type: http
    url: http://10.0.0.21:8000/v1/models
    expected_status: 200
```

进一步：

```text
GET /v1/models
↓
Parse JSON
↓
检查 qwen 是否存在
```

再进一步：

```text
POST /v1/chat/completions
↓
发送最小 Prompt
↓
记录 TTFT
↓
记录 Total Latency
↓
验证 Response
```

最终可以演化为：

```text
LLM Health Checker
+
Benchmark Tool
```

---

# 3.12.37 扩展 GPU / Prometheus

以后可加入：

```text
nvidia-smi
DCGM
Prometheus
```

例如：

```text
endpoint_up{target="vllm01"} 1
endpoint_latency_ms{target="vllm01"} 23.4
```

从 CLI Tool 演变为：

```text
Prometheus Exporter
```

---

# 3.11 ～ 3.12 综合工程模型

```text
External Input
↓
Configuration
↓
Validation
↓
Normalization
↓
Execution
↓
Bounded Concurrency
↓
Error Classification
↓
Structured Result
↓
Logging
↓
Aggregation
↓
Machine Output
↓
Exit Status
```

这套模型可以复用到：

```text
GPU Checker
Kubernetes Cleaner
Cloud API Tool
Storage Checker
LLM Benchmark
Ray Worker Inspector
```

---

# 核心术语表

| 术语 | 当前理解 |
|---|---|
| Logging | 记录程序运行事件和上下文 |
| Log Level | DEBUG / INFO / WARNING / ERROR / CRITICAL |
| Logger | 日志记录对象 |
| Structured Logging | 字段化日志 |
| Request ID | 单请求唯一标识 |
| Correlation ID | 跨组件关联标识 |
| Redaction | 敏感信息脱敏 |
| Log Rotation | 日志轮转 |
| Sampling | 高频事件采样 |
| Exception | Python 异常对象 |
| Traceback | 异常调用栈 |
| Exception Chain | 异常因果链 |
| Propagate | 异常向上传播 |
| Fail Fast | 尽早验证并失败 |
| Silent Failure | 失败但没有明确信号 |
| Transient Error | 暂时性错误 |
| Permanent Error | 持续性错误 |
| Structured Result | 用字段表达检测结果 |
| CLI | Command-Line Interface |
| argparse | Python CLI 参数解析标准库 |
| Probe | 主动检查目标状态 |
| Normalization | 将输入整理成统一内部结构 |
| Aggregation | 汇总多个结果 |
| Deterministic Output | 稳定、可重复的输出 |
| Atomic Write | 临时文件完整写入后替换正式文件 |
| Bounded Concurrency | 有上限的并发 |
| Internal Error | 工具自身错误 |
| Target Failure | 被检测对象故障 |
| Exit Code | Process 返回给 Shell 的状态码 |

---

# 最重要的十五句话

1. `print()` 适合临时实验，长期 Infra 程序应逐渐使用 Logging。
2. 日志必须有 Context，不要只输出 `failed`。
3. 不要把 Password、Token、API Key 等 Secret 写入日志。
4. 只捕获你真正知道如何处理的 Exception。
5. `except Exception: pass` 会制造 Silent Failure。
6. `logger.exception()` 可以保留完整 Traceback。
7. `raise NewError(...) from exc` 可以提升错误抽象，同时保留原始原因。
8. Library Layer 更适合 raise / convert；Application Layer 更适合最终 Log / Exit。
9. 被检测 Service Down 往往应该成为 Structured Result，而不是让 Inspector 崩溃。
10. 一个可靠 Infra Tool 应先 Validate Input，再开始执行。
11. I/O-bound Probe 非常适合有界 Thread Pool。
12. TCP Healthy 不等于 HTTP / Application Healthy。
13. stderr 放日志、stdout 放机器结果，是非常实用的 CLI 设计。
14. Exit Code 应区分“目标故障”和“工具自身故障”。
15. Python Infra 工程的核心链路是 Configuration → Validation → Execution → Concurrency → Error → Logging → Output。

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

Python：

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
✅ 3.11 Logging / Error Handling
✅ 3.12 AI Infra Python 小工具实战

Python 阶段
✅ 完成

Go：

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

> 下一节：**3.13 Go 在 AI Infra 里的角色**
>
> 先解释为什么 Kubernetes、Prometheus、Terraform、Docker 周边和大量 Cloud Native 组件都大量采用 Go，以及 Compiled Binary、Static Binary、Runtime、GC、Goroutine 分别解决什么工程问题。
