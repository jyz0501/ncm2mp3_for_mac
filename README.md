# ncm2mp3_for_mac

   使用macOS 的（ShortCuts）快捷指令一键转换网易云音乐NCM格式


# ✨ 功能特性   

-    格式保留：能够识别原始文件是 MP3 还是 FLAC 格式，并生成对应格式的文件。

-    元数据嵌入：自动将歌曲的元数据（如歌名、专辑、艺术家）写入转换后的音乐文件中。

-    封面嵌入：自动提取并嵌入歌曲的专辑封面图片。

-    跨平台运行：基于 Python 编写，可在 Windows, macOS, Linux 等操作系统上运行。

-    自动删除：转换后自动删除ncm源文件。

-    Todo（待开发）：……多线程模式、批量转换：自动处理指定文件夹内的所有 .ncm 文件。

# ⚙️ 环境要求   

-    操作系统: macOS

-    Python 3: macOS 一般已预装 Python 3，可在终端运行 python3 --version 检查

-    依赖包: mutagen、pycryptodome、tqdm

# 🚀 使用步骤

1. 获取脚本文件：克隆本仓库或下载 ncm2mp3.py 文件

   将 ncm2mp3.py 放置在你喜欢的路径下，例如 /Users/你的用户名/Documents/ncm2mp3.py

2. 安装依赖
   
```python
    #在终端中执行以下命令安装所需依赖
    pip install -r requirements.txt
```

   或者手动安装
   
```python
   pip install mutagen pycryptodome tqdm
```

3. 导入快捷指令
   
   双击打开 网易云转换.shortcut

4. 配置脚本路径
   
   将本仓库中 `run.applescript` 的内容复制到 AppleScript 的输入框里，注意把里面的文件路径（YOUR ncm2mp3.py FILE PATH）改成你实际存放`ncm2mp3.py`的路径

   ```python
   -- 示例：将路径修改为你的实际路径
   set python_script to "/Users/你的用户名/Documents/ncm2mp3.py"
   ```
<img width="1200" alt="image" src="https://github.com/iLern/ncm2mp3_for_mac/assets/43905872/764353dd-ecdb-485f-bb1f-423198403936">

5. 使用转换功能
   
   在访达（Finder）中选中要转换的 .ncm文件，右键点击文件

   选择「快速操作」> 「网易云转换」

   转换后的 .mp3文件将生成在同一目录下

<img width="338" alt="image" src="https://github.com/iLern/ncm2mp3_for_mac/assets/43905872/9213772a-f543-49b5-8645-7419ba2ce155">

# 注意事项

   确保 Python 脚本具有正确的执行权限

   如果遇到权限问题，可在终端运行：`chmod +x /path/to/your/ncm2mp3.py`

# 特别鸣谢

   项目参考：

   https://github.com/ww-rm/ncmdump-py

   https://github.com/iLern/ncm2mp3_for_mac




