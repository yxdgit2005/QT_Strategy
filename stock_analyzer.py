
import pandas as pd
import numpy as np
import os
import glob

def calculate_indicators(df):
    """
    计算常用技术指标：MA, MACD, KDJ, RSI, BOLL, Volume Ratio
    """
    # 确保数据按日期排序
    df = df.sort_values('date').reset_index(drop=True)
    
    # 1. 移动平均线 (MA5, MA10, MA20)
    df['ma5'] = df['close'].rolling(window=5).mean()
    df['ma10'] = df['close'].rolling(window=10).mean()
    df['ma20'] = df['close'].rolling(window=20).mean()
    
    # 2. MACD (12, 26, 9)
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['signal_line']
    
    # 3. KDJ (9, 3, 3)
    low_min = df['low'].rolling(window=9).min()
    high_max = df['high'].rolling(window=9).max()
    rsv = (df['close'] - low_min) / (high_max - low_min) * 100
    df['k'] = rsv.rolling(window=3).mean()
    df['d'] = df['k'].rolling(window=3).mean()
    df['j'] = 3 * df['k'] - 2 * df['d']
    
    # 4. RSI (14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 5. BOLL (20, 2)
    df['boll_mid'] = df['close'].rolling(window=20).mean()
    boll_std = df['close'].rolling(window=20).std()
    df['boll_upper'] = df['boll_mid'] + 2 * boll_std
    df['boll_lower'] = df['boll_mid'] - 2 * boll_std
    
    # 6. 量比 (当日成交量 / 过去5日平均成交量)
    df['vol_ma5'] = df['volume'].rolling(window=5).mean()
    df['volume_ratio'] = df['volume'] / df['vol_ma5']
    
    return df

def find_rally_start_index(df):
    """
    寻找上涨初期的起点索引。
    定义：区间内最低价出现的位置，且随后股价有显著上涨。
    这里简化为：找到100天内最低收盘价的那一天作为“启动前夜”，
    或者使用更复杂的逻辑：寻找突破20日均线的第一个点。
    为了通用性，我们选取区间内涨幅最大段落的起始点。
    """
    # 简单策略：找到最低点后的最大涨幅段落的起点
    # 更稳健的策略：寻找均线金叉或突破点。这里采用“最低点后首次站上5日线”作为近似启动点
    min_price_idx = df['close'].idxmin()
    
    # 如果最低点在最后几天，可能不是好的启动点，向前回溯
    if min_price_idx > len(df) - 10:
        # 尝试找局部低点
        min_price_idx = df['close'].nsmallest(3).index[-1] # 取第三低，避免极端异常
        
    return min_price_idx

def extract_features_at_start(df, start_idx):
    """
    提取启动点当天的技术特征
    """
    if start_idx < 20: # 数据不足计算某些指标
        return None
        
    row = df.iloc[start_idx]
    features = {
        'price_vs_ma5': row['close'] / row['ma5'] if row['ma5'] != 0 else 1,
        'price_vs_ma20': row['close'] / row['ma20'] if row['ma20'] != 0 else 1,
        'macd': row['macd'],
        'macd_hist': row['macd_hist'],
        'kdj_k': row['k'],
        'kdj_d': row['d'],
        'kdj_j': row['j'],
        'rsi': row['rsi'],
        'boll_position': (row['close'] - row['boll_lower']) / (row['boll_upper'] - row['boll_lower']) if (row['boll_upper'] - row['boll_lower']) != 0 else 0.5,
        'volume_ratio': row['volume_ratio'],
        'turnover_rate': row.get('turnover', 0) # 假设CSV中有换手率，如果没有则为0
    }
    return features

def process_csv_files(folder_path):
    """
    处理文件夹下所有CSV文件
    """
    results = []
    csv_files = glob.glob(os.path.join(folder_path, '*.csv'))
    
    print(f"发现 {len(csv_files)} 个CSV文件")
    
    for file in csv_files:
        try:
            # 假设CSV列名为: date, open, high, low, close, volume
            # 根据实际数据可能需要调整列名映射
            df = pd.read_csv(file)

            # 简单的列名标准化检查
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                # 尝试常见中文列名映射
                col_map = {
                    '日期': 'date', '开盘': 'open', '最高': 'high', 
                    '最低': 'low', '收盘': 'close', '成交量': 'volume'
                }
                df.rename(columns=col_map, inplace=True)
                if not all(col in df.columns for col in required_cols):
                    continue
            
            # 计算100天总涨幅
            if len(df) < 100:
                continue
                
            # 取最近100天
            df_recent = df.tail(100).copy()
            df_recent = calculate_indicators(df_recent)
            
            start_price = df_recent['close'].iloc[0]
            end_price = df_recent['close'].iloc[-1]
            total_return = (end_price - start_price) / start_price
            
            # 记录股票代码（文件名）和涨幅
            stock_code = os.path.basename(file).replace('.csv', '')
            results.append({
                'code': stock_code,
                'return': total_return,
                'data': df_recent
            })
            
        except Exception as e:
            print(f"处理文件 {file} 时出错: {e}")
            continue
            
    return results

def analyze_common_features(top_stocks_data):
    """
    分析前50只股票启动初期的共同特征
    """
    all_features = []
    
    for item in top_stocks_data:
        df = item['data']
        start_idx = find_rally_start_index(df)
        feats = extract_features_at_start(df, start_idx)
        if feats:
            feats['code'] = item['code']
            all_features.append(feats)
            
    if not all_features:
        print("未提取到有效特征")
        return
        
    feat_df = pd.DataFrame(all_features)
    
    print("\n" + "="*30)
    print("前50只牛股启动初期共同特征分析")
    print("="*30)
    
    # 计算均值和中位数
    numeric_cols = feat_df.select_dtypes(include=[np.number]).columns
    summary = feat_df[numeric_cols].describe()
    
    print("\n【技术指标统计摘要 (均值/中位数)】")
    for col in numeric_cols:
        mean_val = summary.loc['mean', col]
        median_val = summary.loc['50%', col]
        print(f"{col:20s}: 均值={mean_val:.4f}, 中位数={median_val:.4f}")
        
    print("\n【共同特征结论】")
    # 基于常见技术分析逻辑进行解读
    avg_rsi = summary.loc['mean', 'rsi']
    avg_vol_ratio = summary.loc['mean', 'volume_ratio']
    avg_macd = summary.loc['mean', 'macd']
    avg_boll_pos = summary.loc['mean', 'boll_position']
    
    print(f"1. RSI水平: 平均为 {avg_rsi:.2f}。", end="")
    if avg_rsi < 30:
        print("处于超卖区，表明启动前经历了充分回调。")
    elif 30 <= avg_rsi <= 50:
        print("处于弱势整理区，多空平衡偏向多头酝酿。")
    else:
        print("处于强势区，表明启动前已有资金介入。")
        
    print(f"2. 量能变化: 平均量比为 {avg_vol_ratio:.2f}。", end="")
    if avg_vol_ratio > 1.5:
        print("启动初期伴随明显放量，资金活跃度高。")
    else:
        print("量能温和，可能是缩量上涨或逐步建仓。")
        
    print(f"3. MACD状态: 平均MACD值为 {avg_macd:.4f}。", end="")
    if avg_macd > 0:
        print("处于零轴上方，趋势偏多。")
    else:
        print("处于零轴下方，可能是底部反转信号。")
        
    print(f"4. 布林带位置: 平均相对位置为 {avg_boll_pos:.2f}。", end="")
    if avg_boll_pos < 0.2:
        print("股价贴近下轨，存在超跌反弹需求。")
    elif 0.4 <= avg_boll_pos <= 0.6:
        print("股价在中轨附近，正在选择方向。")
    else:
        print("股价接近上轨，突破意愿强烈。")

def main():
    # 配置数据文件夹路径
    DATA_FOLDER = './data_sh' # 请确保此文件夹下有CSV文件
    
    if not os.path.exists(DATA_FOLDER):
        print(f"错误: 找不到数据文件夹 '{DATA_FOLDER}'")
        print("请创建该文件夹并放入股票CSV数据文件。")
        # 为了演示，如果没有数据，生成一些模拟数据提示
        return

    # 1. 处理所有CSV，计算涨幅
    print("正在处理股票数据...")
    all_stocks = process_csv_files(DATA_FOLDER)
    
    if not all_stocks:
        print("未找到有效的股票数据。")
        return
        
    # 2. 筛选涨幅最大的前50只
    all_stocks.sort(key=lambda x: x['return'], reverse=True)
    top_50 = all_stocks[:50]
    
    print(f"\n已筛选出涨幅最高的前50只股票:")
    for i, stock in enumerate(top_50):
        print(f"{i+1}. {stock['code']}: 涨幅 {stock['return']*100:.2f}%")
        
    # 3. 提取特征并分析共同点
    analyze_common_features(top_50)

if __name__ == "__main__":
    main()
