# sshg
先说为什么起这个名字呢？
因为我之前起的几个名字sshx, sshs 都被别人捷足先登了，而且项目写的还不错。可他们的项目又不能满足我快速选择要连接的设备和远程配置的需求，所以我就只起sshg这个名字了

## 支持的功能
- [x] 支持将ip,user,password写入到配置文件中，并快速的键盘选择上下选择功能(VIM的hj也支持)
- [x] 支持ssh跳板机的功能
- [ ] 远程配置的功能

## 安装
```bash
pip install sshg
```

## 使用
创建配置文件 `~/.sshg.yml`

文件内容例子

```yaml
- name: inner-server
  user: appuser
  host: 192.168.8.35
  port: 22
  password: 123456 # login password
  via:
    user: via-server
    host: 10.0.0.38
    port: 2222
- name: dev server fully configured
  user: appuser
  host: 192.168.1.1
  keypath: ~/.ssh/id_rsa
  password: abcdefghijklmn # passphrase
  callback-shells:
    - { delay: 1, cmd: "uptime" }
    - { cmd: "echo 1" }
- name: dev group
  port: 22 # children will inherit all the configs as default
  children:
    - user: pc01
      host: 192.168.3.1
    - user: pc02
      host: 192.168.3.2
    - host: 192.168.3.3 # leave user empty will set to current user
```

```bash
$ sshg
Use the arrow keys to navigate (support vim style): ↓ ↑ 
✨ Select host
  ➤ inner-server appuser@192.168.8.35
    dev server fully configured appuser@192.168.1.1
    dev group

# specify config file
$ sshg --conf ~/.sshg.yml
```


## 开发者文档

```bash
# 没安装就装一下，项目依赖poetry发布
# pip install poetry

poetry self add "poetry-dynamic-versioning[plugin]"
poetry publish --build
```

# Refs
- https://poetry.eustace.io/docs/
- https://pypi.org/project/poetry-dynamic-versioning/
- https://github.com/yinheli/sshw UI风格基本都是参考这个项目
- https://github.com/WqyJh/sshx 本来用这个名字的，发现跟它重复了

# LICENSE
[MIT](LICENSE)