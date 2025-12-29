# Remote Mode 架构重设计

## 概述

重新设计 Remote 模式，使其与 Local 模式保持一致。核心理念：**服务器即真相源（Server as Source of Truth）**，GUI 作为远程编辑器，直接读写服务器上的项目数据。

## 架构

```
┌────────────────────────────────────────────────────────┐
│                      GUI                               │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │ UI Pages │→ │ Controller   │→ │ ProjectStorage │   │
│  └──────────┘  └──────────────┘  └────────┬───────┘   │
│                                           │           │
│                    ┌──────────────────────┴───────┐   │
│                    │ LocalStorage / RemoteStorage │   │
│                    └──────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
                              ↓ SSH/SFTP (remote only)
                    ┌──────────────────┐
                    │  服务器 nml/     │
                    └──────────────────┘
```

### 核心原则

- **Local 模式**：项目目录在本地，直接读写
- **Remote 模式**：项目目录在服务器，通过 Sync Engine 读写
- **统一接口**：UI 层不感知 local/remote 差异

## 目录结构

Local 和 Remote 完全一致：

```
项目目录/
  └── nml/
      ├── main-{name}.yaml
      ├── ref-{name}.yaml
      ├── sim-{name}.yaml
      ├── ref/
      │   └── {source}.yaml
      └── sim/
          ├── {source}.yaml
          └── models/
              └── {model}.yaml
```

本地仅存储连接配置：

```
~/.openbench_wizard/
  └── connections.yaml
```

## 同步引擎（Sync Engine）

### 组件

```
┌─────────────────────────────────────────────────────┐
│                   Sync Engine                        │
│  ┌───────────┐  ┌───────────┐  ┌─────────────────┐  │
│  │ Cache     │  │ Change    │  │ Sync            │  │
│  │ Manager   │  │ Tracker   │  │ Worker (后台)    │  │
│  └───────────┘  └───────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 工作流程

1. **打开项目时**
   - 从服务器读取 `nml/` 目录下所有配置
   - 缓存到本地内存（或临时文件）
   - UI 从缓存加载显示

2. **用户修改时**
   - 修改立即写入本地缓存
   - Change Tracker 记录"脏"数据
   - Sync Worker 后台异步写入服务器
   - UI 显示同步状态

3. **网络断开时**
   - 继续允许编辑，修改存入缓存
   - 重连后自动同步所有未同步的修改

### 同步状态指示器

```
● 已同步 (绿色)
◐ 同步中 (黄色/动画)
● 未同步 (红色) - 点击可重试
```

## 统一存储接口

```python
class ProjectStorage:
    def read_file(self, path: str) -> str: ...
    def write_file(self, path: str, content: str): ...
    def list_dir(self, path: str) -> List[str]: ...
    def exists(self, path: str) -> bool: ...
    def glob(self, pattern: str) -> List[str]: ...

class LocalStorage(ProjectStorage):
    """直接读写本地文件系统"""

class RemoteStorage(ProjectStorage):
    """通过 Sync Engine 读写，带本地缓存"""
```

使用方式：

```python
storage = LocalStorage(project_dir)       # local 模式
storage = RemoteStorage(ssh, project_dir) # remote 模式

# UI 代码统一调用
content = storage.read_file("nml/main-test.yaml")
storage.write_file("nml/ref/source1.yaml", new_content)
files = storage.glob("nml/sim/*.yaml")
```

## 路径选择与自动补全

### 弹窗浏览器

统一接口，根据 storage 类型选择实现：

```python
def browse_path(storage: ProjectStorage, start_dir: str) -> str:
    if isinstance(storage, LocalStorage):
        return QFileDialog.getExistingDirectory(...)
    else:
        return RemoteFileBrowser.browse(...)
```

### 路径自动补全

```
用户输入: /data/obs/flux
                      ↓ 触发补全
下拉建议: /data/obs/fluxnet/
          /data/obs/fluxcom/
          /data/obs/flux_tower/
```

实现方式：
- 用户输入时，延迟 300ms 后触发
- 调用 `storage.list_dir()` 获取匹配项
- 使用 `QCompleter` 显示下拉建议
- Remote 模式：结果缓存，避免频繁 SSH 请求

## 连接管理

### 启动流程

```
启动 GUI
    ↓
选择模式: [本地项目] [远程项目]
    ↓
┌─────────────────┬──────────────────────┐
│    本地项目      │      远程项目         │
├─────────────────┼──────────────────────┤
│ 选择本地目录     │ 选择/新建 SSH 连接     │
│       ↓         │         ↓            │
│ 加载项目        │ 连接服务器            │
│                 │         ↓            │
│                 │ 选择远程项目目录       │
│                 │         ↓            │
│                 │ 同步到本地缓存         │
│                 │         ↓            │
│                 │ 加载项目              │
└─────────────────┴──────────────────────┘
```

### 连接配置

```yaml
# ~/.openbench_wizard/connections.yaml
connections:
  - name: "计算集群A"
    host: "user@cluster-a.edu"
    auth_type: "key"
    key_file: "~/.ssh/id_rsa"
    jump_node: null

  - name: "超算中心"
    host: "user@hpc.edu"
    auth_type: "key"
    key_file: "~/.ssh/id_rsa"
    jump_node: "user@login.hpc.edu"
```

### 项目操作

- **打开已有项目**：浏览服务器，选择包含 `nml/` 的目录
- **新建项目**：选择空目录或新建目录，初始化 `nml/` 结构

## 代码改造范围

### 新增组件

| 组件 | 说明 |
|------|------|
| `core/storage.py` | `ProjectStorage` 接口 + `LocalStorage` / `RemoteStorage` |
| `core/sync_engine.py` | 缓存管理、变更追踪、后台同步 |
| `ui/widgets/path_completer.py` | 路径自动补全模型 |
| `ui/dialogs/project_selector.py` | 启动时的项目选择对话框 |
| `ui/widgets/sync_status.py` | 同步状态指示器组件 |

### 改造组件

| 组件 | 改动 |
|------|------|
| `core/config_manager.py` | 改用 `ProjectStorage` 接口读写文件 |
| `core/ssh_manager.py` | 保持不变，被 `RemoteStorage` 调用 |
| `ui/widgets/path_selector.py` | 集成自动补全，移除 local/remote 判断 |
| `ui/pages/page_preview.py` | 简化导出逻辑，统一使用 `storage.write_file()` |
| `ui/pages/page_runtime.py` | 移除执行模式切换，改为启动时选择 |
| `core/data_validator.py` | 改用 `ProjectStorage` 接口 |

### 可移除代码

- `PathSelector` 中的 `set_skip_validation()` 逻辑
- `page_preview.py` 中的 `_export_and_run_remote()` 特殊分支
- 各页面中 `is_remote` 的条件判断

## YAGNI - 不做的事

- 多用户协作/冲突处理（单用户场景）
- 版本历史/回滚（依赖 git）
- 增量同步（文件小，全量即可）

## 收益

1. **代码简化** - 移除大量 `is_remote` 条件分支
2. **一致性** - local/remote 生成完全相同的文件结构
3. **用户体验** - 即时保存，断线恢复，路径自动补全
4. **可维护性** - 统一接口，单一职责
