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

# 导入 mutagen 库用于元数据写入
try:
    from mutagen.flac import FLAC, Picture
    from mutagen.id3 import APIC, ID3, TALB, TIT2, TPE1
    from mutagen.mp3 import MP3
except ImportError:
    print("错误：未找到 mutagen 库。")
    print("请使用 'pip install mutagen' 命令进行安装。")
    exit()

def error_msg(message):
    """输出错误消息"""
    tqdm.write(f"❌ {message}")

def info_msg(message):
    """输出信息消息"""
    tqdm.write(f"ℹ️  {message}")

def success_msg(message):
    """输出成功消息"""
    tqdm.write(f"✅ {message}")

# 使用第一段代码的密钥处理方式
CORE_KEY = bytes([0x68, 0x7A, 0x48, 0x52, 0x41, 0x6D, 0x73, 0x6F, 0x35, 0x6B, 0x49, 0x6E, 0x62, 0x61, 0x78, 0x57])
MODIFY_KEY = bytes([0x23, 0x31, 0x34, 0x6C, 0x6A, 0x6B, 0x5F, 0x21, 0x5C, 0x5D, 0x26, 0x30, 0x55, 0x3C, 0x27, 0x28])

def set_mp3_meta(mp3_file, meta_data, cover_data):
    """为 MP3 文件写入元数据和封面"""
    try:
        audio = MP3(mp3_file, ID3=ID3)
        if audio.tags is None:
            audio.tags = ID3()

        # 写入封面图片
        if cover_data:
            mime_type = 'image/jpeg'
            if cover_data.startswith(b'\x89PNG\r\n\x1a\n'):
                mime_type = 'image/png'
            audio.tags.add(APIC(
                encoding=3, 
                mime=mime_type, 
                type=3, 
                desc='Cover', 
                data=cover_data
            ))

        # 写入元数据
        if meta_data:
            audio.tags.add(TIT2(encoding=3, text=meta_data.get('musicName', 'Unknown')))
            audio.tags.add(TALB(encoding=3, text=meta_data.get('album', 'Unknown')))
            artists = '/'.join(arr[0] for arr in meta_data.get('artist', [['Unknown']]))
            audio.tags.add(TPE1(encoding=3, text=artists))
        
        audio.save()
        return True
    except Exception as e:
        error_msg(f"写入MP3元数据失败 {mp3_file}: {str(e)}")
        return False

def set_flac_meta(flac_file, meta_data, cover_data):
    """为 FLAC 文件写入元数据和封面"""
    try:
        audio = FLAC(flac_file)
        
        # 写入元数据
        if meta_data:
            audio['title'] = meta_data.get('musicName', 'Unknown')
            audio['album'] = meta_data.get('album', 'Unknown')
            artists = '/'.join(arr[0] for arr in meta_data.get('artist', [['Unknown']]))
            audio['artist'] = artists

        # 写入封面图片
        if cover_data:
            pic = Picture()
            pic.data = cover_data
            pic.mime = "image/png" if cover_data.startswith(b'\x89PNG\r\n\x1a\n') else "image/jpeg"
            pic.type = 3
            audio.add_picture(pic)
        
        audio.save()
        return True
    except Exception as e:
        error_msg(f"写入FLAC元数据失败 {flac_file}: {str(e)}")
        return False

def write_metadata(output_path, meta_data, cover_data):
    """根据文件类型写入元数据和封面"""
    if output_path.endswith('.mp3'):
        return set_mp3_meta(output_path, meta_data, cover_data)
    elif output_path.endswith('.flac'):
        return set_flac_meta(output_path, meta_data, cover_data)
    else:
        info_msg(f"不支持的文件格式，跳过元数据写入: {output_path}")
        return False

def delete_source_file(filepath, output_path):
    """删除源文件，并进行安全检查"""
    try:
        # 安全检查：确保输出文件存在且大小合理
        if not os.path.exists(output_path):
            error_msg(f"输出文件不存在，跳过删除源文件: {filepath}")
            return False
        
        output_size = os.path.getsize(output_path)
        if output_size < 1024:  # 小于1KB的文件可能转换失败
            error_msg(f"输出文件大小异常({output_size}字节)，跳过删除源文件: {filepath}")
            return False
        
        # 删除源文件
        os.remove(filepath)
        success_msg(f"已删除源文件: {os.path.basename(filepath)}")
        return True
        
    except PermissionError:
        error_msg(f"权限不足，无法删除源文件: {filepath}")
        return False
    except OSError as e:
        error_msg(f"删除源文件失败: {filepath} - {str(e)}")
        return False
    except Exception as e:
        error_msg(f"删除源文件时发生未知错误: {filepath} - {str(e)}")
        return False

def dump_single_file(filepath, delete_original=True):
    """转换单个NCM文件"""
    try:
        filename = os.path.basename(filepath)
        if not filename.endswith('.ncm'): 
            return None
        filename = filename[:-4]
        
        # 检查是否已存在转换后的文件
        for ftype in ['mp3', 'flac']:
            fname = f'{filename}.{ftype}'
            if os.path.isfile(os.path.join(os.path.dirname(filepath), fname)):
                info_msg(f'跳过 "{filepath}"，文件 "{fname}" 已存在')
                return None

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
            else:
                info_msg(f"文件 {filepath} 缺少元数据信息")

            # 跳过CRC32和1字节
            f.seek(5, 1)

            # 处理封面图像数据
            image_space = struct.unpack('<I', f.read(4))[0]
            image_size = struct.unpack('<I', f.read(4))[0]
            cover_data = f.read(image_size) if image_size > 0 else None
            
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
        
        # 写入元数据和封面
        if meta_data or cover_data:
            if write_metadata(output_path, meta_data, cover_data):
                success_msg(f"元数据写入成功: {output_path}")
            else:
                error_msg(f"元数据写入失败: {output_path}")
        
        # 转换成功后删除源文件
        if delete_original:
            delete_source_file(filepath, output_path)
        
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

def dump(*paths, n_workers=None, delete_original=True):
    """主转换函数
    
    Args:
        paths: 文件或目录路径列表
        n_workers: 并行工作进程数
        delete_original: 是否在转换成功后删除源文件
    """
    if n_workers is None:
        n_workers = 1
        
    # 显示简洁的头部信息
    header = f"""
    ==== 删除源文件: {'是' if delete_original else '否'} ====
    元数据支持: MP3/FLAC
    """
    info_msg(header.strip())

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
        # 为多进程创建参数列表
        task_args = [(fp, delete_original) for fp in all_filepaths]
        with Pool(processes=n_workers) as p:
            results = p.starmap(dump_single_file, task_args)
            # 统计成功和失败的数量
            successful = [r for r in results if r is not None]
            deleted_count = len([r for r in results if r is not None and delete_original])
            info_msg(f"转换完成: {len(successful)} 个成功, {len(all_filepaths) - len(successful)} 个失败")
            if delete_original:
                info_msg(f"已删除 {deleted_count} 个源文件")
    else:
        info_msg("使用单进程模式转换")
        successful = 0
        deleted_count = 0
        for fp in tqdm(all_filepaths, leave=False, desc="转换进度"):
            result = dump_single_file(fp, delete_original)
            if result is not None:
                successful += 1
                if delete_original:
                    deleted_count += 1
        info_msg(f"转换完成: {successful} 个成功, {len(all_filepaths) - successful} 个失败")
        if delete_original:
            info_msg(f"已删除 {deleted_count} 个源文件")

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(description='NCM文件转换工具（支持元数据和封面写入）')
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
    parser.add_argument(
        '--keep-original',
        action='store_true',
        help='保留源文件（不自动删除）'
    )
    
    args = parser.parse_args()
    dump(*args.paths, n_workers=args.workers, delete_original=not args.keep_original)