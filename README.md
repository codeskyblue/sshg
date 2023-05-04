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
