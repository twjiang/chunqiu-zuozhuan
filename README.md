# 春秋左传 Web Query System (Spring and Autumn Zuo Zhuan Web Query System)

本项目是一个基于 Python Flask 框架开发的《春秋左传》Web 查询与阅读系统。它将原始的古籍文本进行了结构化处理，支持按国君纪年查询、全文模糊搜索、人物别名关联查询等功能，并整合了中英文对照翻译。

## 🌟 核心功能

1. **全文查阅与检索**：
   - 提供直观的 Web 界面，方便阅读《左传》全文本。
   - 支持强大的多维度查询 API (`/api/query`)。
   - 后台通过构建“倒排索引”（Inverted Index，包含二字词和单字）和“纪年索引”，实现了 $O(1)$ 级别的极速检索。
2. **纪年与公历映射**：
   - 自动将中国传统的国君纪年（如“隐公元年”）转化为公元前（BCE）年份，方便现代读者理解。
3. **人物别名管理**：
   - 古人常有多重称谓（名、字、号、谥号等），系统内置了人物别名映射表 (`person_aliases.json`)。
   - 提供完善的 API 和后台管理页面 (`/admin/aliases`)，支持对别名进行增删改查（CRUD）操作。
4. **中英双语对照**：
   - 整合了来自 ctext.org (Chinese Text Project) 的原文及英文翻译数据。

## 📂 项目结构

### 1. 核心应用与后台服务
* `app.py`: Flask 主程序。负责提供 Web UI、查询 API (`/api/query`) 以及别名管理 API。启动服务时会在内存中构建高效的搜索索引。
* `static/`: 存放前端静态资源文件（CSS / JS 等）。

### 2. 数据处理脚本
* `parse_data.py`: 数据解析脚本。用于读取来自 Kanripo (汉文史籍自动化系统) 的繁体文本文件 (`KR1e0001_*.txt`)，使用 `opencc` 将其转换为简体中文，解析国君纪年并计算公元前年份，最后生成核心数据文件 `zuozhuan_data.json`。
* `fetch_ctext.py` / `fetch_ctext2.py`: 数据爬取与融合脚本。从 ctext.org 抓取《左传》的中英文对照翻译，并根据国君和纪年与现有的结构化数据合并。

### 3. 数据与语料文件
* `KR1e0001_*.txt`: Kanripo 原始纯文本语料（按卷划分）。
* `zuozhuan_data.json`: 系统核心数据文件，包含结构化解析后的左传条目、纪年、国君列表等。
* `person_aliases.json` / `person_aliases_trad.json`: 人物别名词典，用于关联查询古人的不同称呼。
* `zuozhuan_ctext.json` / `zuozhuan_data_ctext.json` 等: 从 ctext 抓取和合并的中间/拓展数据。

## 🚀 快速启动

**1. 准备环境**
确保你的系统中已安装 Python 3 环境，并且安装了必要的依赖。

```bash
pip install flask opencc
```

**2. 启动服务**
在项目根目录下直接运行 `app.py`：

```bash
python3 app.py
```
*(默认监听 80 端口，可通过修改 `app.py` 底部配置或使用 `nohup` 在后台运行)*

**3. 访问应用**
服务启动后，打开浏览器访问 http://localhost (或对应服务器的 IP / 域名) 即可开始使用。

## 🔧 API 接口一览

* `GET /`: 系统主页。
* `GET /api/query`: 核心查询接口，支持按关键字或年份查询。
* `GET /admin/aliases`: 别名管理后台页面。
* `GET /api/aliases/list`: 获取别名列表。
* `POST /api/aliases/add`: 添加新的别名映射。
* `POST /api/aliases/update`: 更新现有的别名映射。
* `POST /api/aliases/delete`: 删除别名映射。
