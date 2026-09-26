# LLM / AI Infra 学习笔记

## 第 0 章：建立 AI Infra 心智模型
### 0.21 ～ 0.30

> 目标：把前面已经建立的 Model、Token、Tensor、GPU、矩阵计算等概念继续串起来，理解：
>
> - Tensor Core 是什么
> - 为什么模型参数会占显存
> - 模型文件如何从 SSD 进入 RAM 和 VRAM
> - 矩阵乘法到底怎么算
> - Multiply-Add / MAC / FMA 是什么
> - FLOP / FLOPS 是什么
> - Bandwidth（带宽）是什么
> - Compute Bound 与 Memory Bound 的区别
> - 为什么 HBM 对 AI GPU 特别重要
>
> 关联补充：
>
> 在 0.20 后我们额外补充过 **0.20A：Tensor 多维与底层计算**，其中解释了：
>
> ```text
> Tensor 可以是多维
> 但显存中的数据本质上存在线性地址空间
> 高维 Tensor 运算常被拆成：
> - 逐元素运算
> - 二维矩阵乘法
> - 批量矩阵乘法
> - Reduction（归约）
> ```

---

# 0.21 Tensor Core 初步

**Tensor Core**

是 NVIDIA GPU 中一种：

> 专门针对矩阵乘加运算进行优化的计算硬件。

现代 AI 中，大量计算最终都会转化为矩阵运算。

因此：

```text
LLM
 ↓
大量矩阵计算
 ↓
大量乘法 + 加法
 ↓
Tensor Core 非常擅长
```

Tensor Core 并不是“直接计算任意高维 Tensor”的硬件。它更核心的能力可以抽象成：

```text
D = A × B + C
```

GPU 通常会把大的矩阵拆成很多小块处理。

这些小块叫：

**Tile**

中文可理解为：

**矩阵分块 / 小块**

---

# 0.22 为什么模型参数会占显存

前面已经知道：

```text
模型
=
大量参数
+
使用这些参数进行计算的方法
```

参数本质上是数字。

假设模型有：

```text
1B parameters
```

也就是：

```text
10 亿参数
```

而每个参数占：

```text
2 bytes
```

那么：

```text
10 亿 × 2 bytes
≈ 2 GB
```

这还只是模型参数本身。

## Byte 是什么

**Byte**

中文：

**字节**

一个：

```text
Byte
```

等于：

```text
8 bits
```

这里：

**bit**

中文：

**比特 / 位**

是最基本的信息单位：

```text
0
或
1
```

所以：

```text
1 Byte = 8 bits
```

## 不同精度为什么占不同空间

例如：

```text
32 bits
```

需要：

```text
32 ÷ 8 = 4 Bytes
```

而：

```text
16 bits
```

需要：

```text
16 ÷ 8 = 2 Bytes
```

因此可以先粗略理解：

```text
FP32 ≈ 4 bytes / 参数
FP16 ≈ 2 bytes / 参数
```

## 7B 模型粗略需要多少空间

假设：

```text
7B 参数
```

使用：

```text
FP16 ≈ 2 bytes / 参数
```

则：

```text
7 billion × 2 bytes
≈ 14 GB
```

## 70B 呢

同样：

```text
70B × 2 bytes
≈ 140 GB
```

仅模型参数本身就可能接近：

```text
140 GB
```

这就会引出以后要学的：

**Multi-GPU**

也就是：

> 多张 GPU 一起工作。

## 模型权重显存 ≠ 总显存需求

即使：

```text
模型权重 = 14 GB
GPU 显存 = 16 GB
```

也不代表一定能正常运行。

因为运行时还需要额外空间，例如：

```text
输入
中间计算结果
缓存
临时工作区
```

所以：

```text
模型权重显存
≠
总显存需求
```

---

# 0.23 模型文件与 SSD / RAM / VRAM

训练好的模型参数需要长期保存。

常见模型文件可能看到：

```text
model-00001-of-00008.safetensors
model-00002-of-00008.safetensors
...
```

这里：

**safetensors**

是一种：

> 用于保存模型参数的文件格式。

现阶段只需要理解：

```text
模型文件
≈
模型参数在磁盘上的持久化保存形式
```

## Persistent：持久化

**Persistent**

中文：

**持久化**

意思是：

> 程序退出、系统重启后，数据仍然存在。

## SSD 是什么

**SSD**

全称：

**Solid State Drive**

中文：

**固态硬盘**

主要用于长期保存：

```text
文件
程序
照片
模型
```

## SSD、RAM、VRAM 的关系

可以先这样区分：

```text
SSD
长期保存数据

RAM
系统和 CPU 运行程序时使用

VRAM
GPU 计算时使用
```

模型启动时，大致可能经历：

```text
SSD
 │
 │ 模型文件
 ↓
RAM
 │
 ↓
VRAM
 │
 ↓
GPU 计算
```

---

# 0.24 矩阵乘法究竟怎么算

假设：

```text
A = [1  2]
    [3  4]

B = [5  6]
    [7  8]
```

计算：

```text
C = A × B
```

左上角元素：

```text
1×5 + 2×7
= 19
```

右上角：

```text
1×6 + 2×8
= 22
```

左下角：

```text
3×5 + 4×7
= 43
```

右下角：

```text
3×6 + 4×8
= 50
```

最终：

```text
A × B =

[19  22]
[43  50]
```

核心规则：

> 结果矩阵中的每一个元素 = 左边矩阵的一行 × 右边矩阵的一列。

## 矩阵尺寸规则

假设：

```text
A = [M, K]
B = [K, N]
```

那么：

```text
A × B
```

结果：

```text
C = [M, N]
```

也就是：

```text
[M, K] × [K, N]
       ↓
     [M, N]
```

中间的：

```text
K
```

必须一致。

## 计算量为什么增长得很快

假设：

```text
A = [4096, 4096]
B = [4096, 4096]
```

输出：

```text
C = [4096, 4096]
```

C 中有大约：

```text
4096 × 4096
≈ 1677 万
```

个结果元素。

每个结果又要进行约：

```text
4096 次乘法
+
4095 次加法
```

所以一个大矩阵乘法可以包含数百亿次数值操作。

---

# 0.25 Multiply-Add / MAC / FMA

## Multiply-Add

**Multiply-Add**

中文：

**乘加运算**

就是：

```text
a × b + c
```

矩阵乘法中充满了这种操作。

## Accumulator

**Accumulator**

中文：

**累加器**

可以理解成：

> 暂时保存不断累加结果的地方。

例如：

```text
acc = 0
acc = acc + 1×5
acc = acc + 2×7
```

最后：

```text
acc = 19
```

## MAC

**MAC**

全称：

**Multiply-Accumulate**

中文：

**乘累加**

就是：

```text
acc = acc + a × b
```

矩阵乘法可以粗略理解为：

> 海量 MAC 运算。

## FMA

**FMA**

全称：

**Fused Multiply-Add**

中文：

**融合乘加**

表示把：

```text
a × b + c
```

作为一个紧密结合的硬件操作完成。

## Matrix Tile

实际 GPU 通常不会把一个巨大矩阵完全当成一个整体处理。

它会拆成：

```text
Tile
```

也就是：

> 小矩阵块。

这样可以：

```text
提高并行度
重复利用数据
减少不必要的数据搬运
```

---

# 0.26 FLOP / FLOPS

## FLOP

**FLOP**

全称：

**Floating Point Operation**

中文：

**浮点运算**

可以先理解成：

> 一次浮点数数学运算。

## FLOPS

**FLOPS**

全称：

**Floating Point Operations Per Second**

中文：

**每秒浮点运算次数**

表示：

> 一个计算设备每秒能够执行多少浮点运算。

例如：

```text
1 TFLOPS
```

其中：

```text
T = Tera = 10^12
```

因此：

```text
1 TFLOPS
≈ 每秒 1 万亿次浮点运算
```

## FLOP 与 FLOPS 的区别

```text
FLOP = 工作量
FLOPS = 每秒处理能力
```

## 矩阵乘法的计算量

对于：

```text
[M,K] × [K,N]
```

计算量大致：

```text
2 × M × K × N
```

个浮点操作。

---

# 0.27 Bandwidth：带宽

**Bandwidth**

中文：

**带宽**

可以理解成：

> 单位时间内能够传输多少数据。

例如：

```text
100 GB/s
```

表示：

> 每秒能够传输约 100 GB 数据。

## GPU 为什么需要显存带宽

矩阵计算：

```text
C = A × B
```

不只是计算。

GPU 还需要：

```text
读取 A
读取 B
计算
写入 C
```

如果数据送不过来：

```text
Tensor Core
CUDA Core
```

可能只能等待。

## Bandwidth 与 Capacity 不一样

```text
VRAM = 80 GB
```

表示：

> 最多能放多少数据。

而：

```text
Memory Bandwidth = 3 TB/s
```

表示：

> 每秒能搬多少数据。

所以：

```text
Memory Capacity
≠
Memory Bandwidth
```

## Latency 与 Bandwidth 也不一样

**Latency**

中文：

**延迟**

表示：

> 一次传输从开始到完成需要多久。

**Bandwidth**

表示：

> 连续传输时，每秒可以通过多少数据。

---

# 0.28 Compute Bound vs Memory Bound

一个程序慢，可能有两种完全不同的原因：

```text
算不过来
```

或者：

```text
数据送不过来
```

## Compute Bound

**Compute Bound**

中文：

**计算受限**

表示：

> 主要瓶颈在计算能力。

可以理解成：

```text
数据够
算力不够
```

## Memory Bound

**Memory Bound**

中文：

**显存 / 内存带宽受限**

表示：

> GPU 主要在等待数据。

可以理解成：

```text
算力够
数据供应不够
```

## 为什么只看 TFLOPS 不够

假设：

```text
GPU A
算力：100 TFLOPS
带宽：1 TB/s
```

```text
GPU B
算力：80 TFLOPS
带宽：3 TB/s
```

不能简单说：

```text
GPU A 一定更快
```

因为：

- Compute Bound 工作负载可能更看重算力
- Memory Bound 工作负载可能更看重带宽

## Decode

**Decode**

在 LLM 推理中，可以先理解成：

> 模型逐个生成新 Token 的阶段。

很多 LLM Decode 场景容易受到：

```text
Memory Bandwidth
```

限制。

## Arithmetic Intensity

**Arithmetic Intensity**

中文：

**算术强度**

可以粗略理解为：

> 每搬一定量数据，能够做多少计算。

如果：

```text
搬很多数据
只算很少
```

更容易：

```text
Memory Bound
```

如果：

```text
搬一次数据
重复算很多次
```

更可能：

```text
Compute Bound
```

---

# 0.29 HBM 为什么对 AI GPU 很重要

**HBM**

全称：

**High Bandwidth Memory**

中文：

**高带宽内存**

它是一类：

> 特别强调极高数据传输带宽的内存技术。

## 为什么 AI GPU 需要 HBM

现代 GPU 的计算能力非常强。

如果显存系统太慢：

```text
Tensor Core
 ↓
等待数据
```

大量计算能力就会浪费。

## HBM 不只是容量问题

HBM 的核心价值之一不是简单：

```text
能放更多数据
```

而是：

```text
能以非常高的速度给 GPU 提供数据
```

## 为什么 LLM 特别需要它

LLM 往往同时具备：

```text
参数很多
+
需要频繁读取大量数据
```

因此需要：

```text
大容量
+
高带宽
```

大容量解决：

```text
模型能不能放得下
```

高带宽解决：

```text
模型数据能不能足够快地送给 GPU
```

## 三个最基本的 GPU 指标

```text
             GPU
              │
      ┌───────┼───────┐
      ↓       ↓       ↓
   Compute  Capacity  Bandwidth
    算力      容量       带宽
```

---

# 0.30 第 0 章总结

## 从文字到 GPU

```text
用户输入文字
      │
      ↓
  Tokenizer
      │
      ↓
    Token
      │
      ↓
   Tensor
      │
      ↓
   模型参数
      │
      ↓
Matrix Multiplication
      │
      ↓
Multiply-Add
      │
      ↓
GPU 并行计算
      │
      ↓
生成下一个 Token
      │
      ↓
 Streaming
      │
      ↓
 用户看到文字
```

## 模型数据从存储到 GPU

```text
SSD
 │
 │ 模型文件
 ↓
RAM
 │
 ↓
VRAM / HBM
 │
 │ 高带宽读取
 ↓
GPU Compute Units
 │
 ├─ CUDA Core
 └─ Tensor Core
```

## GPU 性能的三个基本维度

```text
GPU Performance
     │
 ┌───┼─────────┐
 ↓   ↓         ↓
Compute   Capacity   Bandwidth
算力       容量       带宽
```

## GPU 性能排查的最初级思路

如果一个 AI 工作负载很慢，可以先问三个问题：

```text
① 算力是不是不够？
→ Compute Bound

② 数据是不是搬不过来？
→ Memory Bound

③ 模型是不是根本放不下？
→ Memory Capacity
```

---

# 0.21～0.30 核心术语表

| 术语 | 英文 | 当前理解 |
|---|---|---|
| Tensor Core | Tensor Core | 专门擅长矩阵乘加的 GPU 计算硬件 |
| Tile | Tile | 矩阵分块 |
| Byte | Byte | 8 个 bit |
| Persistent | Persistent | 程序退出后数据仍长期保存 |
| SSD | Solid State Drive | 固态硬盘，长期存储数据 |
| Matrix Multiplication | Matrix Multiplication | 矩阵乘法 |
| Accumulator | Accumulator | 保存累加结果的地方 |
| MAC | Multiply-Accumulate | 乘累加 |
| FMA | Fused Multiply-Add | 融合乘加 |
| FLOP | Floating Point Operation | 浮点运算数量 |
| FLOPS | Floating Point Operations Per Second | 每秒浮点运算能力 |
| Bandwidth | Bandwidth | 单位时间的数据传输量 |
| Latency | Latency | 一次操作 / 传输需要多久 |
| Compute Bound | Compute Bound | 性能主要受计算能力限制 |
| Memory Bound | Memory Bound | 性能主要受数据传输速度限制 |
| Arithmetic Intensity | Arithmetic Intensity | 每单位数据搬运对应多少计算 |
| Decode | Decode | LLM 逐 Token 生成阶段 |
| HBM | High Bandwidth Memory | 高带宽内存 |
| Memory Capacity | Memory Capacity | 显存可以容纳多少数据 |
| Memory Bandwidth | Memory Bandwidth | 显存每秒可传输多少数据 |

---

# 第 0 章完整学习进度

```text
✅ 0.1  什么是 Model
✅ 0.2  Parameter 参数
✅ 0.3  什么是 LLM
✅ 0.4  Token / Tokenizer
✅ 0.5  LLM 如何逐 Token 生成
✅ 0.6  Training 训练
✅ 0.7  Inference 推理
✅ 0.8  Infrastructure 基础设施
✅ 0.9  AI Infrastructure
✅ 0.10 CPU / GPU 初步区别
✅ 0.11 CUDA 是什么
✅ 0.12 PyTorch 是什么
✅ 0.13 API / Server 基础
✅ 0.14 RAM / VRAM 基础
✅ 0.15 Streaming 流式输出
✅ 0.16 一次 LLM 请求的基本链路
✅ 0.17 Scalar / Vector / Matrix / Tensor
✅ 0.18 为什么 AI 大量使用矩阵
✅ 0.19 CPU 与 GPU 的计算特点
✅ 0.20 Parallel 并行计算
✅ 0.20A Tensor 多维与底层计算
✅ 0.21 Tensor Core 初步
✅ 0.22 参数为什么占显存
✅ 0.23 模型文件与 SSD / RAM / VRAM
✅ 0.24 矩阵乘法究竟怎么算
✅ 0.25 Multiply-Add / MAC / FMA
✅ 0.26 FLOP / FLOPS
✅ 0.27 Bandwidth 带宽
✅ 0.28 Compute Bound vs Memory Bound
✅ 0.29 HBM 为什么重要
✅ 0.30 第 0 章总结
```

# 下一章

```text
第 1 章：Linux 与计算机系统基础

⬜ 1.1  Operating System 是什么
⬜ 1.2  Kernel 是什么
⬜ 1.3  User Space / Kernel Space
⬜ 1.4  Process 进程
⬜ 1.5  Thread 线程
⬜ 1.6  CPU Core 与 Scheduler
⬜ 1.7  Context Switch
⬜ 1.8  Virtual Memory
⬜ 1.9  Page / Page Fault
⬜ 1.10 OOM
⬜ 1.11 File Descriptor
⬜ 1.12 /proc 与 /sys
⬜ 1.13 systemd
⬜ 1.14 Linux 基础排障
```
