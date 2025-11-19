# ncm2mp3_for_mac
A shortcuts for MacOS to change .ncm to .mp3
将网易云音乐下载的 .ncm 文件转换为 .mp3 文件

# Usage
1. `clone` 本仓库，将其中的`ncm2mp3.py`放在一个你喜欢的路径下
2. 确保你的Mac上安装了`python3`（可以在终端中运行 python --version）新版 MacOS 一般已预装 python3，然后用`pip3 install pycryptodome` 安装脚本运行所需依赖
3. 打开MacOS自带的“快捷指令”app，创建一个快捷指令：
<img width="1200" alt="image" src="https://github.com/iLern/ncm2mp3_for_mac/assets/43905872/764353dd-ecdb-485f-bb1f-423198403936">

4. 将本仓库中 `run.applescript` 的内容复制到 AppleScript 的输入框里，注意把里面的文件路径改成你实际存放`ncm2mp3.py`的路径，例如 /Users/alun/Documents/ncm2mp3.py
5. 现在你可以在访达中选中你想转换的`.ncm`文件，右键 > 快速操作 > ncm2mp3 完成转换
<img width="338" alt="image" src="https://github.com/iLern/ncm2mp3_for_mac/assets/43905872/9213772a-f543-49b5-8645-7419ba2ce155">

# 转换文件并写入元数据（自动删除源文件）
python ncm_converter.py test.ncm

# 保留源文件但写入元数据
python ncm_converter.py test.ncm --keep-original

# 批量转换并写入元数据
python ncm_converter.py /path/to/ncm/files/ -w 4

安装命令
# 使用pip安装所有依赖
pip install -r requirements.txt

# 或者手动安装
pip install mutagen pycryptodome tqdm
