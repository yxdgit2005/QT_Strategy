# macd_backtest.py
# 依赖: pandas, numpy, matplotlib (后者可选用于画图)
# 用法: python macd_backtest.py price.csv

import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def compute_macd(close, fast=12, slow=26, signal=9):
    """
    计算 MACD, 返回 DataFrame 包含 macd_line, signal_line, hist
    EMA 用 pandas.ewm
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({
        "macd": macd_line,
        "signal": signal_line,
        "hist": hist
    })

def backtest_macd(df,
                  fast=12, slow=26, signal=9,
                  initial_capital=100000,
                  fee_pct=0.0005,      # 手续费比例（按成交额）
                  slippage_pct=0.0005, # 滑点比例（按成交额）
                  annual_trading_days=252):
    """
    df must contain columns: Date (index or column), Close, Open, High, Low, Volume (Volume optional)
    策略：
      - 买入（持仓=1）当 macd_line > signal_line 且 hist > 0
      - 平仓（持仓=0）当 macd_line < signal_line 或 hist < 0
    注意：使用 shift(1) 将信号延迟一天以避免未来函数（假设以次日开盘/当日收盘执行可改）
    返回：包含指标与净值的 dataframe 和 trade log
    """
    data = df.copy().reset_index(drop=False)
    if "Date" not in data.columns:
        data.rename(columns={data.columns[0]: "Date"}, inplace=True)
    data["Date"] = pd.to_datetime(data["Date"])
    data.set_index("Date", inplace=True)
    close = data["Close"]

    macd_df = compute_macd(close, fast=fast, slow=slow, signal=signal)
    data = data.join(macd_df)

    # 生成信号（1 表示当日应持仓），将信号 shift(1) 表示今天持仓由昨日信号决定（无未来函数）
    raw_signal = ((data["macd"] > data["signal"]) & (data["hist"] > 0)).astype(int)
    data["signal"] = raw_signal.shift(1).fillna(0).astype(int)

    # 计算每日回报
    data["ret"] = close.pct_change().fillna(0)
    data["strategy_ret_before_cost"] = data["signal"] * data["ret"]

    # 交易发生（开仓或平仓）时扣手续费和滑点（简单按成交额比例）
    data["pos_change"] = data["signal"].diff().abs().fillna(0)  # 1 表示发生开/平仓
    # 如果想区分开仓与平仓（双向扣费），当前简化为每次变仓扣一次成本
    data["trade_cost_pct"] = data["pos_change"] * (fee_pct + slippage_pct)
    # 将成本从当日策略回报中扣除（把成本当作当日一次性支出）
    data["strategy_ret"] = data["strategy_ret_before_cost"] - data["trade_cost_pct"]

    # 计算净值（按比例增长）
    data["cum_return"] = (1 + data["strategy_ret"]).cumprod()
    data["nav"] = initial_capital * data["cum_return"]

    # 绩效指标
    total_return = data["nav"].iloc[-1] / initial_capital - 1
    days = (data.index[-1] - data.index[0]).days
    years = days / 365.25 if days > 0 else len(data) / annual_trading_days
    cagr = (data["nav"].iloc[-1] / initial_capital) ** (1 / years) - 1 if years > 0 else np.nan
    ann_vol = data["strategy_ret"].std() * np.sqrt(annual_trading_days)
    sharpe = (data["strategy_ret"].mean() / data["strategy_ret"].std()) * np.sqrt(annual_trading_days) if data["strategy_ret"].std() != 0 else np.nan

    # 最大回撤
    running_max = data["nav"].cummax()
    drawdown = data["nav"] / running_max - 1
    max_drawdown = drawdown.min()
    # 额外指标：交易次数、胜率、平均每笔收益
    trades = data.loc[data["pos_change"] == 1].copy()
    trade_count = len(trades)
    # 简单计算每笔收益（仅在平仓时有完整 round-trip，复杂策略需逐笔配对）
    # 这里只输出开/平仓事件日志（不配对盈亏）
    trade_log = trades[["signal","pos_change","Close"]].copy()
    trade_log["action"] = np.where(trade_log["signal"]==1,"BUY","SELL")
    trade_log = trade_log[["action","Close"]]

    metrics = {
        "total_return": total_return,
        "cagr": cagr,
        "annual_volatility": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "trade_count": trade_count
    }

    return data, trade_log, metrics

def plot_results(data):
    plt.figure(figsize=(12,6))
    ax = plt.gca()
    data["nav"].plot(ax=ax, label="NAV")
    ax.set_title("策略净值")
    ax.set_ylabel("资金")
    ax.legend()
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python macd_backtest.py price.csv")
        sys.exit(1)

    fname = sys.argv[1]
    df = pd.read_csv(fname, parse_dates=["Date"])
    results, trades, metrics = backtest_macd(df)

    print("=== 指标 ===")
    for k,v in metrics.items():
        print(f"{k}: {v}")
    print("\n=== 最近若干笔变仓（开/平仓事件） ===")
    print(trades.tail(20))

    # 可视化净值
    plot_results(results)