# DisqusCollector

基于 aiohttp 的用于代理访问 disqus api的服务器, 需部署在能正常访问 disqus 的服务器上, Redis 存储相关代码还未提交

## Getting started

### 安装 Docker

Ubuntu:

```
$ wget -qO- https://get.docker.com/ | sh
```

### 配置

重命名 config_example.py 文件为 config.py, 按注释填入相应字段

Secret Key 和 Public Key 在[这里](https://disqus.com/api/applications/)获取

依据自己服务器的代码文件路径, 更改 dockerfiles/docker-compose.yml 里的volumes

### 构建

```
$ cd dockerfiles/
$ docker build -t="disqus/server:alpha" .
```

### 运行

```
$ docker-compose up -d
```

最后将1065或自定义端口暴露出来即可