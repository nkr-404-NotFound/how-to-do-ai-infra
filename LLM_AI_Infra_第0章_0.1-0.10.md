# LLM / AI Infra 学习笔记

## 第 0 章：建立 AI Infra 心智模型
### 0.1 ～ 0.10

> 目标：先建立最基础的 AI Infra 概念地图。  
> 本章前 10 小节不追求复杂数学，也不要求记忆大量工具名，而是先理解：
>
> - 模型是什么
> - 参数是什么
> - LLM 是什么
> - Token 是什么
> - LLM 为什么会一个 Token 一个 Token 地生成
> - Training 和 Inference 有什么区别
> - Infra 是什么
> - AI Infra 是什么
> - CPU 与 GPU 的最基本区别

---

# 0.1 什么是 Model（模型）

普通程序通常是：

```text
输入
 ↓
程序员写好的规则
 ↓
输出
```

例如：

```python
if age >= 18:
    print("adult")
```

这里的规则是程序员直接写出来的。

AI 模型不同。

可以先粗略理解成：

```text
大量数据
   ↓
训练
   ↓
得到大量数字
   ↓
模型
```

**Model（模型）**可以先理解为：

> 一套通过训练得到的大量参数，以及一套使用这些参数完成计算的方法。

这里最重要的新词是：

**Parameter（参数）**

---

# 0.2 Parameter（参数）

先看一个非常简单的公式：

```text
y = ax + b
```

其中：

```text
a
b
```

都可以看作参数。

在这个极简例子中，训练可以粗略理解成：

```text
找到合适的 a
找到合适的 b
```

真实的大语言模型复杂得多。

例如经常会看到：

```text
7B
70B
```

其中：

```text
B = Billion = 十亿
```

因此：

```text
7B 参数  ≈ 70 亿个参数
70B 参数 ≈ 700 亿个参数
```

可以先把模型想象成：

```text
大量参数
+
使用这些参数进行计算的方法
```

而参数本质上就是大量数字。

---

# 0.3 什么是 LLM

**LLM**

全称：

**Large Language Model**

中文：

**大型语言模型 / 大语言模型**

拆开来看：

```text
Large      大型
Language   语言
Model      模型
```

常见的大语言模型包括：

```text
GPT
Qwen
Llama
DeepSeek
Gemma
```

从最基础的角度看，LLM 的核心任务可以先理解成：

> 根据前面的内容，预测接下来应该出现什么。

但模型实际上并不是直接处理“汉字”或“完整单词”。

它处理的是：

**Token**

---

# 0.4 Token 与 Tokenizer

## Token 是什么

**Token** 可以暂时理解成：

> 大语言模型处理文字时使用的基本单位。

例如：

```text
我喜欢人工智能
```

它不一定会被切成：

```text
我
喜
欢
人
工
智
能
```

也不一定一定按照完整词语切分。

不同模型可能使用不同的 Token 划分方式。

---

## Tokenization

把文字拆成 Token 的过程叫：

**Tokenization**

中文常称：

**Token 化 / 分词**

例如：

```text
I love artificial intelligence
```

经过 Tokenization 后，可以抽象成：

```text
Token 1
Token 2
Token 3
Token 4
...
```

---

## Tokenizer

**Tokenizer**

就是：

> 负责把文字转换成 Token 的组件。

整个关系可以先理解成：

```text
用户文字
   ↓
Tokenizer
   ↓
Token
   ↓
数字
   ↓
模型计算
```

Token 最终会被转换为数字，供模型处理。

---

# 0.5 LLM 如何逐 Token 生成内容

假设输入：

```text
中国的首都是
```

模型通常不是一次性直接输出完整句子：

```text
北京。
```

而是类似这样工作：

```text
输入：
中国的首都是

↓

预测下一个 Token：
北京
```

然后当前内容变成：

```text
中国的首都是北京
```

模型再次预测：

```text
下一个 Token：
。
```

于是整个过程类似：

```text
输入
 ↓
预测一个 Token
 ↓
把 Token 接到已有内容后面
 ↓
再次预测
 ↓
继续
```

这种生成方式叫：

**Autoregressive**

中文：

**自回归生成**

现阶段不需要死记英文。

只要理解：

> LLM 通常是一个 Token 一个 Token 地向后生成，而不是一次性生成完整答案。

这件事以后会直接影响：

```text
生成速度
显存占用
并发能力
延迟
KV Cache
LLM Serving
```

这些概念后续再逐一展开。

---

# 0.6 Training（训练）

**Training**

中文：

**训练**

前面说：

```text
模型 = 大量参数 + 计算方法
```

那么这些参数从哪里来？

通过训练。

可以非常粗略地理解为：

```text
大量数据
   ↓
给模型学习
   ↓
模型做预测
   ↓
发现预测存在误差
   ↓
调整模型参数
   ↓
再次预测
   ↓
继续调整
   ↓
重复大量次数
```

最终得到一个训练好的模型。

所以：

> **Training = 学习和修改模型参数的过程。**

例如：

```text
随机参数
   ↓
Training
   ↓
训练好的模型参数
```

---

# 0.7 Inference（推理）

**Inference**

中文一般翻译为：

**推理**

这里要特别注意：

机器学习里的“推理”，并不等于日常语言里的“逻辑推理”。

在 AI 系统里，Inference 更准确地表示：

> 使用已经训练好的模型进行计算，并得到结果。

例如用户问：

```text
法国首都是哪里？
```

模型并不会因为这个问题重新训练。

而是：

```text
已经训练好的模型
        ↓
输入问题
        ↓
执行模型计算
        ↓
得到输出
```

这就是：

**Inference**

---

## Training 与 Inference 的区别

| Training | Inference |
|---|---|
| 训练 | 推理 |
| 学习 / 修改参数 | 使用已有参数 |
| 目的是得到模型 | 目的是使用模型 |
| 通常计算量非常大 | 单次请求计算量相对较小 |
| 经常使用大量 GPU | 也经常使用 GPU，但工作模式不同 |

AI Infra 中以后会分别遇到：

```text
Training Infra
```

和：

```text
Inference Infra
```

它们并不是完全相同的一套系统。

---

# 0.8 什么是 Infrastructure（基础设施）

**Infrastructure**

简称：

**Infra**

中文：

**基础设施**

互联网服务背后通常需要：

```text
服务器
网络
存储
数据库
操作系统
监控
负载均衡
容器
```

这些东西本身通常不是最终提供给用户的产品功能。

但没有它们，产品就无法正常运行。

例如一个购物网站，用户看到的是网页和商品。

而背后可能存在：

```text
服务器
网络
数据库
缓存
监控系统
```

这些都属于基础设施的一部分。

可以先把 Infra 理解为：

> 支撑上层应用稳定运行的一整套底层计算、网络、存储和软件系统。

---

# 0.9 什么是 AI Infra

**AI Infrastructure**

简称：

**AI Infra**

可以定义为：

> 让 AI 模型能够训练、部署、运行、扩展、监控并稳定提供服务的一整套基础设施。

可以先建立下面这张粗略地图：

```text
                    AI Infra

        ┌─────────────┼─────────────┐
        │             │             │
       计算           网络           存储
        │             │             │
      CPU/GPU       网络设备       SSD/对象存储
        │             │             │
        └─────────────┼─────────────┘
                      │
                 操作系统
                      │
                   容器
                      │
               集群管理系统
                      │
                AI 运行环境
                      │
                    模型
```

很多词现在还不需要展开。

最重要的是理解：

```text
AI 模型
不能凭空运行
     ↓
需要计算资源
     ↓
需要服务器
     ↓
需要网络
     ↓
需要存储
     ↓
需要软件管理这些资源
     ↓
需要监控它们是否正常
```

这些问题，正是 AI Infra 工程师需要处理的内容。

---

# 0.10 CPU 与 GPU 的初步区别

## CPU 是什么

**CPU**

全称：

**Central Processing Unit**

中文：

**中央处理器**

它是计算机中的通用处理器。

CPU 很擅长：

```text
复杂逻辑
程序控制
分支判断
操作系统任务
串行任务
低延迟任务
```

例如：

```python
if user_logged_in:
    if permission_ok:
        ...
```

这类复杂控制逻辑非常适合 CPU。

---

## GPU 是什么

**GPU**

全称：

**Graphics Processing Unit**

中文：

**图形处理器**

GPU 最早主要服务于：

```text
图形
游戏
3D 渲染
```

后来人们发现：

AI 中存在大量这样的计算：

> 很多相似的小计算，需要同时对大量数据执行。

GPU 非常适合这种工作。

---

## Parallel Computing：并行计算

**Parallel**

中文：

**并行**

可以理解成：

> 多件事情同时进行。

例如有四个任务：

```text
A
B
C
D
```

串行执行：

```text
A → B → C → D
```

并行执行：

```text
A ─┐
B ─┤
C ─┤ 同时运行
D ─┘
```

GPU 的重要优势之一，就是拥有大量适合并行计算的硬件资源。

---

## 一个粗略比喻

CPU 可以先想象成：

```text
少量非常能干的工人
每个人能处理复杂任务
```

GPU 可以先想象成：

```text
大量适合同时处理相似任务的工人
```

这个比喻并不严格，但非常适合建立第一层理解。

---

## 为什么 AI 大量使用 GPU

LLM 内部包含大量：

```text
矩阵运算
```

矩阵运算中有许多相似的乘法和加法可以并行执行。

因此：

```text
LLM
 ↓
大量数值计算
 ↓
大量矩阵运算
 ↓
大量可并行的小计算
 ↓
GPU 非常适合
```

现阶段只要理解到这里即可。

矩阵、Tensor、Tensor Core、显存带宽等内容，会在后续小节正式展开。

---

# 0.1～0.10 核心术语表

| 术语 | 英文 | 当前阶段的理解 |
|---|---|---|
| 模型 | Model | 参数 + 使用这些参数进行计算的方法 |
| 参数 | Parameter | 训练过程中学习得到的数字 |
| 大语言模型 | LLM | 用于处理和生成语言的大型模型 |
| Token | Token | LLM 处理文字的基本单位 |
| Tokenizer | Tokenizer | 把文字转换为 Token 的组件 |
| 训练 | Training | 学习和修改模型参数 |
| 推理 | Inference | 使用已经训练好的模型进行计算 |
| 基础设施 | Infrastructure / Infra | 支撑上层应用运行的底层系统 |
| AI 基础设施 | AI Infra | 支撑 AI 训练和推理的一整套基础设施 |
| CPU | Central Processing Unit | 通用处理器，擅长复杂控制和逻辑 |
| GPU | Graphics Processing Unit | 擅长大规模并行数值计算 |
| 并行 | Parallel | 多项工作同时执行 |

---

# 本阶段的核心心智模型

到 0.10 为止，可以先建立下面这张图：

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
                    已训练好的模型
                          │
                          ↓
                       Inference
                          │
                    ┌─────┴─────┐
                    │           │
                   CPU         GPU
                                │
                          大量并行计算
                                │
                                ↓
                           输出 Token
                                │
                                ↓
                              文字
```

而 AI Infra 负责支撑这整个系统：

```text
计算 + 网络 + 存储 + 操作系统 + 集群管理 + 监控
                         │
                         ↓
                    AI 模型稳定运行
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

后续：
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
✅ 0.21 Tensor Core 初步
✅ 0.22 参数为什么占显存
✅ 0.23 模型文件与 SSD / RAM / VRAM

下一节：
⬜ 0.24 矩阵乘法究竟怎么算
```
