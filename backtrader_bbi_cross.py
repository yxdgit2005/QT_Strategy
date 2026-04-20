import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt

# ==== 策略部分 ====

class BBIStrategy(bt.Strategy):
    params = (('ma1', 3), ('ma2', 6), ('ma3', 12), ('ma4', 24),)
    
    def __init__(self):
        self.ma1 = bt.ind.MovingAverageSimple(self.datas[0], period=self.p.ma1)
        self.ma2 = bt.ind.MovingAverageSimple(self.datas[0], period=self.p.ma2)
        self.ma3 = bt.ind.MovingAverageSimple(self.datas[0], period=self.p.ma3)
        self.ma4 = bt.ind.MovingAverageSimple(self.datas[0], period=self.p.ma4)
        self.bbi = (self.ma1 + self.ma2 + self.ma3 + self.ma4) / 4
        
        self.crossup = bt.ind.CrossUp(self.datas[0].close, self.bbi)
        self.crossdown = bt.ind.CrossDown(self.datas[0].close, self.bbi)
        
        self.buyprice = None
        self.trade_list = []  # 记录每一笔买卖

    def next(self):
        if not self.position:
            if self.crossup[0]:
                self.order = self.buy()
                self.buyprice = self.datas[0].close[0]
                self.buydatetime = self.datas[0].datetime.date(0)
        else:
            if self.crossdown[0]:
                self.order = self.sell()
                profit = self.datas[0].close[0] - self.buyprice
                profit_pct = profit / self.buyprice
                self.trade_list.append({
                    'buydate': self.buydatetime,
                    'buyprice': self.buyprice,
                    'selldate': self.datas[0].datetime.date(0),
                    'sellprice': self.datas[0].close[0],
                    'profit': profit,
                    'profit_pct': profit_pct
                })
                self.buyprice = None  # 清空，等待下次买入

    def stop(self):
        # 打印结果
        df = pd.DataFrame(self.trade_list)
        print(df)
        df.to_csv('trade_record.csv', index=False)
        self.df = df

# ==== 数据部分 ====

# 用你自己的csv或数据源
def get_data():
    # 假设有一个带有datetime, open, high, low, close, volume列的CSV
    data = bt.feeds.GenericCSVData(
        dataname='your_data.csv',
        dtformat=('%Y-%m-%d'),
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        openinterest=-1,
        )
    return data

# ==== 回测运行部分 ====

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    data = get_data()
    cerebro.adddata(data)
    strat = cerebro.addstrategy(BBIStrategy)

    cerebro.broker.setcash(100000.0)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=99)
    print('初始资金: %.2f' % cerebro.broker.getvalue())
    res = cerebro.run()
    print('最终资金: %.2f' % cerebro.broker.getvalue())

    # ===== 图表展示 (含盈亏曲线与买卖点) =====
    strategy = res[0]
    df = getattr(strategy, 'df', None)
    if df is not None and not df.empty:
        fig, ax = plt.subplots()
        df['cum_profit_pct'] = (1 + df['profit_pct']).cumprod() - 1
        ax.plot(df['selldate'], df['cum_profit_pct'], marker='.', label='累计收益率')
        ax.set_ylabel('累计收益率')
        ax.set_xlabel('卖出日期')
        ax.legend()
        plt.show()
    
    #===== backtrader 原生展示买卖点和BBI综合线 ======
    cerebro.plot(style='candle')