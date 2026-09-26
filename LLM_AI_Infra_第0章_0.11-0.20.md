# LLM / AI Infra 学习笔记

## 第 0 章：建立 AI Infra 心智模型
### 0.11 ～ 0.20

> 目标：在 0.1～0.10 的基础上继续建立 AI Infra 的底层认知。  
> 本部分重点理解：
>
> - CUDA 是什么
> - PyTorch 是什么
> - API / Server 是什么
> - RAM / VRAM 的区别
> - Streaming 是什么
> - 一次 LLM 请求的大致链路
> - Scalar / Vector / Matrix / Tensor
> - 为什么 AI 大量使用矩阵
> - CPU 与 GPU 的计算特点
> - Parallel（并行）到底是什么意思

---

# 0.11 CUDA 是什么

**CUDA**

是 NVIDIA 提供的一套：

> 让程序使用 NVIDIA GPU 做通用计算的软件平台和编程体系。

这里最重要的是理解：

```text
CUDA ≠ GPU
```

例如：

```text
RTX 4090
A100
H100
```

这些是：

> NVIDIA GPU 硬件。

而：

```text
CUDA
```

是：

> 让软件能够调用 NVIDIA GPU 进行通用计算的一整套软件平台与开发体系。

可以用一个简单比喻：

```text
GPU = 工厂里的机器
CUDA = 操作这台机器的一整套工具和规则
```

所以：

```text
NVIDIA GPU
    │
    ↓
CUDA
    │
    ↓
PyTorch
    │
    ↓
LLM
```

你的 AMD Radeon Pro 5300M 是 GPU，但它不是 NVIDIA GPU，因此不能直接使用 CUDA。

---

# 0.12 PyTorch 是什么

**PyTorch**

是一个：

> 用来构建和运行机器学习 / 深度学习程序的软件框架。

例如：

```python
import torch
```

PyTorch 最核心的数据结构之一就是：

```text
Tensor
```

PyTorch 可以让计算运行在不同设备上。

例如：

```text
CPU
NVIDIA GPU + CUDA
部分 Mac 上的 MPS
```

这里：

**MPS**

是 Apple 平台上的一种 GPU 计算后端。

可以先理解为：

> PyTorch 在部分 Mac 上使用 GPU 的一种方式。

因此可以先建立：

```text
              PyTorch
                 │
       ┌─────────┼─────────┐
       ↓         ↓         ↓
      CPU       CUDA      MPS
                 │         │
              NVIDIA    Mac GPU
               GPU
```

以后看到：

```python
device="cuda"
```

可以理解成：

> 告诉 PyTorch，把这次计算交给 CUDA 管理的 NVIDIA GPU。

---

# 0.13 API / Server 基础

## Server 是什么

**Server**

中文：

**服务器**

可以先理解成：

> 一台或一组专门向其他设备提供服务的计算机。

例如：

```text
你的浏览器
     │
     ↓
互联网
     │
     ↓
服务器
```

---

## API 是什么

**API**

全称：

**Application Programming Interface**

中文：

**应用程序编程接口**

可以先理解成：

> 两个软件之间约定好的交流方式。

例如客户端发送：

```json
{
  "message": "你好"
}
```

服务器返回：

```json
{
  "answer": "你好！"
}
```

这里的重点不是 JSON 本身，而是：

> 双方按照约定格式通信。

这就是 API 的核心思想。

---

## API Server

**API Server**

就是：

> 专门接收和处理 API 请求的服务器程序。

例如：

```text
你的浏览器
     │
     │ HTTP 请求
     ↓
API Server
```

API Server 收到请求后，可能继续把任务交给真正执行模型推理的系统。

---

# 0.14 RAM / VRAM 基础

## RAM 是什么

**RAM**

可以先理解为：

> 计算机运行程序时使用的主内存。

例如：

```text
CPU ←→ RAM
```

程序启动后，很多数据会先放在 RAM 中。

---

## VRAM 是什么

**VRAM**

可以理解为：

> GPU 使用的高速内存。

例如：

```text
GPU ←→ VRAM
```

你的 Radeon Pro 5300M 有：

```text
4 GB VRAM
```

这里的 4 GB 就是显存容量。

---

## RAM 和 VRAM 的区别

可以先记：

```text
RAM
给系统和 CPU 使用

VRAM
给 GPU 使用
```

例如模型运行时，大致可能经历：

```text
磁盘上的模型文件
        ↓
       RAM
        ↓
      GPU VRAM
```

之后 GPU 才能高速地使用这些参数进行计算。

---

# 0.15 Streaming（流式输出）

**Streaming**

中文：

**流式输出**

可以理解成：

> 结果还没有全部完成，就先把已经生成的部分发送给用户。

如果没有 Streaming：

```text
模型开始生成
      ↓
生成完整答案
      ↓
全部完成
      ↓
一次性返回
```

如果有 Streaming：

```text
生成一部分
   ↓
立即返回

再生成一部分
   ↓
继续返回
```

所以用户会感觉：

```text
答案正在不断出现……
```

LLM 特别适合流式输出，因为它本身通常就是：

```text
一个 Token
一个 Token
继续向后生成
```

---

# 0.16 一次 LLM 请求的基本链路

现在把前面的概念串起来。

用户输入：

```text
什么是 AI Infra？
```

大致链路可以先理解成：

```text
① 用户
   │
   │ 输入文字
   ↓
② 浏览器 / App
   │
   │ 发送 API 请求
   ↓
③ API Server
   │
   │ 接收请求
   ↓
④ Tokenizer
   │
   │ 文字 → Token
   ↓
⑤ 模型
   │
   │ 使用 GPU / CPU 计算
   ↓
⑥ 生成下一个 Token
   │
   ↓
⑦ 再生成下一个 Token
   │
   ↓
⑧ Streaming
   │
   │ 不断返回
   ↓
⑨ 用户看到答案
```

这就是最基础的：

> LLM Inference 请求链路。

这里：

**Inference**

就是使用已经训练好的模型完成计算。

---

# 0.17 Scalar / Vector / Matrix / Tensor

## Scalar：标量

**Scalar**

中文：

**标量**

就是：

> 一个普通数字。

例如：

```text
3
-7
0.5
42
```

---

## Vector：向量

**Vector**

中文：

**向量**

可以先理解成：

> 一串有顺序的数字。

例如：

```text
[1, 2, 3]
```

或者：

```text
[0.12, -0.8, 2.4, 1.7]
```

一个对象，可以用多个数字描述。

例如：

```text
年龄
身高
体重
```

可以表示成：

```text
[30, 175, 70]
```

---

## Matrix：矩阵

**Matrix**

中文：

**矩阵**

可以理解成：

> 一个二维数字表格。

例如：

```text
1  2  3
4  5  6
```

这是：

```text
2 行 × 3 列
```

也就是：

```text
2 × 3 matrix
```

---

## Tensor：张量

**Tensor**

中文：

**张量**

在深度学习里，可以先理解成：

> 多维数字数组。

例如：

```text
Scalar  → 0D
Vector  → 1D
Matrix  → 2D
```

再往上：

```text
3D Tensor
4D Tensor
5D Tensor
...
```

都可以统一看成 Tensor。

---

# 0.18 为什么 AI 大量使用矩阵

AI 模型内部，本质上是在做大量数字变换。

假设一个输入向量是：

```text
[1, 2, 3]
```

模型内部会让它经过：

```text
输入向量
   ×
权重矩阵
   ↓
新的向量
```

---

## Weight：权重

**Weight**

中文：

**权重**

是模型参数的一种。

例如：

```text
0.2   0.1   -0.4
0.8  -0.3    0.5
0.7   0.2    0.1
```

这可以看作：

```text
Weight Matrix
权重矩阵
```

模型内部很多参数都会以矩阵形式存在。

---

## Matrix Multiplication：矩阵乘法

**Matrix Multiplication**

中文：

**矩阵乘法**

可以先理解成：

> 使用大量乘法和加法，把输入矩阵变换成新的矩阵。

例如：

```text
输入
  ↓
权重矩阵
  ↓
矩阵乘法
  ↓
新的表示
```

现代神经网络和 LLM 中，大量核心计算最后都会变成：

```text
Matrix Multiplication
```

---

## GEMM

以后会频繁看到：

**GEMM**

全称：

**General Matrix Multiplication**

可以理解成：

> 通用矩阵乘法。

AI GPU 中的大量工作都和 GEMM 有关。

---

# 0.19 CPU 与 GPU 的计算特点

不能简单理解成：

```text
CPU 慢
GPU 快
```

更准确的理解是：

> CPU 和 GPU 针对不同类型的工作进行了不同设计。

---

## CPU 更擅长什么

CPU 很适合：

```text
复杂逻辑
大量分支判断
操作系统任务
程序控制
低延迟任务
串行任务
```

例如：

```python
if user_logged_in:
    if permission_ok:
        if resource_exists:
            ...
```

这种逻辑控制很适合 CPU。

---

## GPU 更擅长什么

GPU 更适合：

> 对大量数据重复执行相似计算。

例如：

```text
数字 1 × 2
数字 2 × 2
数字 3 × 2
数字 4 × 2
...
```

这类结构非常规则的计算，可以同时处理很多份。

而矩阵运算恰恰包含大量类似操作。

---

## Core：核心

**Core**

中文：

**核心 / 计算核心**

可以先理解成：

> 能够执行计算的硬件单元。

非常粗略地说：

```text
CPU
少量但功能很强的核心

GPU
大量适合并行计算的计算单元
```

因此 GPU 特别适合：

```text
矩阵
图像
AI
科学计算
```

---

# 0.20 Parallel（并行）

**Parallel**

中文：

**并行**

意思是：

> 多件事情同时进行。

例如：

```text
任务 A
任务 B
任务 C
任务 D
```

串行：

```text
A → B → C → D
```

并行：

```text
A ─┐
B ─┤
C ─┤ 同时运行
D ─┘
```

GPU 的重要优势之一，就是：

> 能让大量相似计算并行执行。

---

## 为什么并行对 AI 很重要

假设有：

```text
100 万个数字
```

每个数字都要做：

```text
× 2
```

如果一个一个处理：

```text
数字 1
数字 2
数字 3
...
```

需要很多步骤。

如果很多数字同时处理：

```text
数字 1 ─┐
数字 2 ─┤
数字 3 ─┤ 同时计算
数字 4 ─┤
...     │
```

就能更快完成。

AI 中的大量矩阵运算正适合这种模式。

因此可以形成：

```text
LLM
 ↓
大量矩阵运算
 ↓
大量相似数值计算
 ↓
适合并行
 ↓
GPU 很合适
```

---

# 0.11～0.20 核心术语表

| 术语 | 英文 | 当前理解 |
|---|---|---|
| CUDA | CUDA | NVIDIA GPU 通用计算平台 |
| PyTorch | PyTorch | 深度学习计算框架 |
| Server | Server | 向其他设备提供服务的计算机 |
| API | Application Programming Interface | 软件之间约定好的通信方式 |
| API Server | API Server | 接收和处理 API 请求的服务器程序 |
| RAM | Random Access Memory | 系统运行时主内存 |
| VRAM | Video RAM | GPU 使用的高速内存 |
| Streaming | Streaming | 结果边生成边返回 |
| Scalar | Scalar | 一个数字 |
| Vector | Vector | 一串有顺序的数字 |
| Matrix | Matrix | 二维数字表 |
| Tensor | Tensor | 多维数字数组 |
| Weight | Weight | 模型参数的一种 |
| Matrix Multiplication | Matrix Multiplication | 矩阵乘法 |
| GEMM | General Matrix Multiplication | 通用矩阵乘法 |
| Core | Core | 执行计算的硬件单元 |
| Parallel | Parallel | 多项任务同时执行 |

---

# 0.11～0.20 心智模型

这一段可以浓缩成下面几张图。

## 软件到 GPU

```text
PyTorch
   │
   ↓
CUDA
   │
   ↓
NVIDIA GPU
```

---

## 一次 LLM 推理请求

```text
用户文字
   ↓
API Server
   ↓
Tokenizer
   ↓
Token
   ↓
模型
   ↓
CPU / GPU
   ↓
输出 Token
   ↓
Streaming
   ↓
用户看到文字
```

---

## AI 为什么适合 GPU

```text
文字
 ↓
Token
 ↓
数字
 ↓
Vector / Matrix / Tensor
 ↓
大量矩阵运算
 ↓
大量相似计算
 ↓
Parallel
 ↓
GPU
```

---

# 学习进度

```text
第 0 章：建立 AI Infra 心智模型

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

后续：
✅ 0.21 Tensor Core 初步
✅ 0.22 参数为什么占显存
✅ 0.23 模型文件与 SSD / RAM / VRAM

下一节：
⬜ 0.24 矩阵乘法究竟怎么算
