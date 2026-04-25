# -*- coding: utf-8 -*-
"""
Created on Sat Apr 25 10:40:49 2026

@author: 41800
"""

import os
import struct
import datetime

def convert_day_to_csv(input_path, output_dir):
    """将通达信 .day 文件转换为 CSV"""
    try:
        with open(input_path, 'rb') as f:
            filename = os.path.basename(input_path).split('.')[0]
            output_path = os.path.join(output_dir, f"{filename}.csv")
            
            with open(output_path, 'w', encoding='utf-8') as csv_file:
                # 写入表头（根据通达信日线格式调整）
                csv_file.write("Date,Open,High,Low,Close,Volume,Amount,Settlement\n")
                
                while True:
                    data = f.read(32)  # 每条记录32字节
                    if not data:
                        break
                    
                    # 解析字段（低字节在前，需用 little-endian）
                    date = struct.unpack('i', data[0:4])[0]
                    open_price = struct.unpack('f', data[4:8])[0]
                    high = struct.unpack('f', data[8:12])[0]
                    low = struct.unpack('f', data[12:16])[0]
                    close = struct.unpack('f', data[16:20])[0]
                    open_interest = struct.unpack('i', data[20:24])[0]
                    volume = struct.unpack('i', data[24:28])[0]
                    settlement = struct.unpack('f', data[28:32])[0]
                    
                    # 格式化日期：YYYYMMDD → YYYY-MM-DD
                    date_str = datetime.datetime.strptime(str(date), '%Y%m%d').strftime('%Y-%m-%d')
                    
                    # 写入 CSV 行，价格保留两位小数
                    csv_line = f"{date_str},{open_price:.2f},{high:.2f},{low:.2f},{close:.2f},{open_interest},{volume},{settlement:.2f}\n"
                    csv_file.write(csv_line)
                    
        print(f"✅ 转换成功: {filename}.csv")
        
    except Exception as e:
        print(f"❌ 转换失败 {input_path}: {str(e)}")

def batch_convert(input_dir, output_dir):
    """批量转换目录下所有 .day 文件"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    count = 0
    for filename in os.listdir(input_dir):
        if filename.endswith('.day'):
            input_path = os.path.join(input_dir, filename)
            convert_day_to_csv(input_path, output_dir)
            count += 1
    
    print(f"🎉 批量转换完成，共处理 {count} 个文件")

# 使用示例
if __name__ == "__main__":
    raw_data_dir = r"F:\中金财富\vipdoc\sz\lday"  # 修改为你的通达信日线数据路径
    csv_output_dir = "./csv_output"
    batch_convert(raw_data_dir, csv_output_dir)
