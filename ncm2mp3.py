import os
import json
import base64
import struct
from glob import glob
from tqdm.auto import tqdm
from textwrap import dedent
from Crypto.Cipher import AES
from multiprocessing import Pool
from Crypto.Util.Padding import unpad

def error_msg(message):
    """输出错误消息"""
    tqdm.write(f"❌ {message}")

def info_msg(message):
    """输出信息消息（可选，用于重要提示）"""
    tqdm.write(f"ℹ️  {message}")

# 密钥处理方式
CORE_KEY = bytes([0x68, 0x7A, 0x48, 0x52, 0x41, 0x6D, 0x73, 0x6F, 0x35, 0x6B, 0x49, 0x6E, 0x62, 0x61, 0x78, 0x57])
MODIFY_KEY = bytes([0x23, 0x31, 0x34, 0x6C, 0x6A, 0x6B, 0x5F, 0x21, 0x5C, 0x5D, 0x26, 0x30, 0x55, 0x3C, 0x27, 0x28])

def dump_single_file(filepath):
    try:
        filename = os.path.basename(filepath)
        if not filename.endswith('.ncm'): 
            return
        filename = filename[:-4]
        
        # 检查是否已存在转换后的文件
        for ftype in ['mp3', 'flac']:
            fname = f'{filename}.{ftype}'
            if os.path.isfile(fname):
                info_msg(f'跳过 "{filepath}"，文件 "{fname}" 已存在')
                return

        with open(filepath, 'rb') as f:
            # 检查文件头
            header = f.read(8)
            if header != b'CTENFDAM':
                error_msg(f"文件 {filepath} 不是有效的NCM文件")
                return None
            
            f.seek(2, 1)  # 跳过2字节

            # 处理密钥数据
            key_length = struct.unpack('<I', f.read(4))[0]
            key_data = bytearray(f.read(key_length))
            
            # XOR解密
            for i in range(len(key_data)):
                key_data[i] ^= 0x64
                
            # AES解密
            cipher = AES.new(CORE_KEY, AES.MODE_ECB)
            key_data = cipher.decrypt(key_data)
            key_data = unpad(key_data, AES.block_size)[17:]  # 移除前17字节
            
            # 初始化key_box
            key_box = bytearray(range(256))
            c = 0
            last_byte = 0
            key_offset = 0
            
            for i in range(256):
                swap = key_box[i]
                c = (swap + last_byte + key_data[key_offset]) & 0xff
                key_offset = (key_offset + 1) % len(key_data)
                key_box[i], key_box[c] = key_box[c], swap
                last_byte = c

            # 处理元数据
            meta_length = struct.unpack('<I', f.read(4))[0]
            meta_data = None
            if meta_length > 0:
                meta_data = bytearray(f.read(meta_length))
                for i in range(len(meta_data)):
                    meta_data[i] ^= 0x63
                
                try:
                    meta_data = base64.b64decode(meta_data[22:])
                    cipher = AES.new(MODIFY_KEY, AES.MODE_ECB)
                    meta_data = unpad(cipher.decrypt(meta_data), AES.block_size).decode('utf-8')[6:]
                    meta_data = json.loads(meta_data)
                except Exception as e:
                    error_msg(f"解析 {filepath} 的元数据失败: {str(e)}")
                    meta_data = None

            # 跳过CRC32和1字节
            f.seek(5, 1)

            # 处理封面图像数据
            image_space = struct.unpack('<I', f.read(4))[0]
            image_size = struct.unpack('<I', f.read(4))[0]
            image_data = f.read(image_size) if image_size > 0 else None
            
            # 跳过剩余的图像空间
            if image_space > image_size:
                f.seek(image_space - image_size, 1)

            # 确定输出文件名和格式
            output_format = meta_data['format'] if meta_data and 'format' in meta_data else 'mp3'
            output_filename = f"{filename}.{output_format}"
            output_path = os.path.join(os.path.dirname(filepath), output_filename)

            # 解密并写入音频数据
            with open(output_path, 'wb') as out_file:
                while True:
                    chunk = bytearray(f.read(0x8000))
                    if not chunk:
                        break
                    
                    # 使用key_box解密
                    for i in range(len(chunk)):
                        j = (i + 1) & 0xff
                        chunk[i] ^= key_box[(key_box[j] + key_box[(key_box[j] + j) & 0xff]) & 0xff]
                    
                    out_file.write(chunk)

        info_msg(f'成功转换文件: "{output_path}"')
        return output_path

    except KeyboardInterrupt:
        error_msg('用户中断操作')
        quit()
    except Exception as e:
        error_msg(f'处理文件 {filepath} 时出错: {str(e)}')
        return None

def list_filepaths(path):
    """递归列出所有文件路径"""
    if os.path.isfile(path):
        return [path]
    elif os.path.isdir(path):
        return [fp for p in glob(f'{path}/*') for fp in list_filepaths(p)]
    else:
        error_msg(f'无法识别的路径: {path}')
        return []

def dump(*paths, n_workers=None):
    """主转换函数"""
    if n_workers is None:
        n_workers = 1
        
    # 显示简洁的头部信息
    # header = """
    # NCM文件转换工具
    # ==============
    # """
    # info_msg(header.strip())

    # 收集所有文件路径
    all_filepaths = []
    for path in paths:
        all_filepaths.extend(list_filepaths(path))
    
    if not all_filepaths:
        error_msg("未找到任何NCM文件")
        return

    info_msg(f"找到 {len(all_filepaths)} 个文件需要转换")
    
    # 执行转换
    if n_workers > 1:
        info_msg(f"使用 {n_workers} 个进程并行转换")
        with Pool(processes=n_workers) as p:
            results = p.map(dump_single_file, all_filepaths)
            # 统计成功和失败的数量
            successful = [r for r in results if r is not None]
            info_msg(f"转换完成: {len(successful)} 个成功, {len(all_filepaths) - len(successful)} 个失败")
    else:
        info_msg("使用单进程模式转换")
        successful = 0
        for fp in tqdm(all_filepaths, leave=False, desc="转换进度"):
            result = dump_single_file(fp)
            if result is not None:
                successful += 1
        info_msg(f"转换完成: {successful} 个成功, {len(all_filepaths) - successful} 个失败")

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(description='NCM文件转换工具')
    parser.add_argument(
        'paths',
        metavar='路径',
        type=str,
        nargs='+',
        help='一个或多个NCM文件或目录路径'
    )
    parser.add_argument(
        '-w', '--workers',
        metavar='数量',
        type=int,
        help='并行转换进程数 (默认: 1)',
        default=1
    )
    args = parser.parse_args()
    dump(*args.paths, n_workers=args.workers)
