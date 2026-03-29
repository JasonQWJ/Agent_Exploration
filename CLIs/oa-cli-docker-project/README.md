# oa-cli-docker-project

本目录是 `oa-cli` 在本机上的 Docker 运行封装，不是 `oa-cli` 上游源码本体。

对应源码目录：
- `../oa-cli`

对应用途：
- 挂载宿主机 `~/.openclaw`（只读）
- 在容器里运行 `oa collect`
- 启动本地 dashboard
- 保存本地 SQLite 数据与运行配置

## 目录结构

- `Dockerfile` - Docker 镜像定义
- `docker-compose.yml` - 本地运行编排
- `Makefile` - 常用命令入口
- `config.yaml` - 运行时生成/更新的 OA 配置
- `data/monitor.db` - 本地指标数据库
- `dist/*.whl` - 从 `../oa-cli` 构建出的 wheel

## 访问地址

启动后可访问：

- <http://127.0.0.1:3460>

## 常用命令

先进入目录：

```bash
cd /Users/jason/Documents/Agent_Exploration/CLIs/oa-cli-docker-project
```

### 查看帮助

```bash
make help
```

### 重建并启动（最常用）

会先从 `../oa-cli` 构建 wheel，再重建镜像并启动容器。

```bash
make rebuild
```

### 查看健康状态

```bash
make health
```

### 查看容器状态

```bash
make ps
```

### 查看日志

```bash
make logs
```

### 停止服务

```bash
make down
```

### 启动服务（不强制重建）

```bash
make up
```

### 单独构建 wheel

```bash
make wheel
```

### 单独构建镜像

```bash
make build
```

## 工作方式说明

容器启动时会做这些事：

1. 读取宿主机挂载的 `/data/openclaw`（对应宿主机 `~/.openclaw`）
2. 自动扫描 OpenClaw agents / sessions
3. 生成或更新 `/work/config.yaml`
4. 执行一次 `oa collect`
5. 启动 dashboard 服务，监听 `0.0.0.0:3460`

## 数据来源

当前主要分析这些 OpenClaw 数据：

- `~/.openclaw/cron/jobs.json`
- `~/.openclaw/cron/runs/*.jsonl`
- `~/.openclaw/sessions/`
- `~/.openclaw/agents/<id>/sessions/`
- `~/.openclaw/workspace/memory/`

说明：它主要是**读文件式分析**，不是直接连接 OpenClaw 进程内部状态。

## 修改 oa-cli 源码后的更新流程

如果你修改了：
- `../oa-cli/src/...`
- `../oa-cli/tests/...`

通常直接执行：

```bash
make rebuild
```

就会重新打 wheel、重建镜像并拉起容器。

## 故障排查

### 端口冲突

如果 3460 被占用：

```bash
make down
```

然后检查是否还有旧容器：

```bash
docker ps -a | grep oa-cli-dashboard
```

必要时删除旧容器：

```bash
docker rm -f oa-cli-dashboard
```

再重新启动：

```bash
make rebuild
```

### 健康检查失败

先看日志：

```bash
make logs
```

再看接口：

```bash
make health
```

## 备注

- `docker-compose.yml` 里宿主机 `~/.openclaw` 是只读挂载
- 本目录里的 `data/` 和 `config.yaml` 属于本机运行产物
- `oa-cli` 源码改动应在 `../oa-cli` 中进行
