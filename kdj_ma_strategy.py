import backtrader as bt

# KDJ指标
class KDJ(bt.Indicator):
    lines = ('k', 'd', 'j',)
    params = (('period', 9), ('k_period', 3), ('d_period', 3))

    def __init__(self):
        low_min = bt.ind.Lowest(self.data.low, period=self.p.period)
        high_max = bt.ind.Highest(self.data.high, period=self.p.period)
        rsv = (self.data.close - low_min) / (high_max - low_min + 1e-9) * 100

        self.l.k = bt.ind.EMA(rsv, period=self.p.k_period)
        self.l.d = bt.ind.EMA(self.l.k, period=self.p.d_period)
        self.l.j = 3 * self.l.k - 2 * self.l.d

# 策略主体
class KDJMAStrategy(bt.Strategy):
    params = (
        ('kdj_period', 9),
        ('kdj_k_period', 3),
        ('kdj_d_period', 3),
        ('ma_period', 20)
    )

    def __init__(self):
        self.kdj = KDJ(self.data, period=self.p.kdj_period,
                       k_period=self.p.kdj_k_period, d_period=self.p.kdj_d_period)
        self.ma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.ma_period)
        self.cross_over = bt.ind.CrossOver(self.kdj.k, self.kdj.d)

    def next(self):
        if not self.position:
            # KDJ金叉 且 收盘价在MA之上 -> 买入
            if self.cross_over[0] > 0 and self.data.close[0] > self.ma[0]:
                self.buy()
        else:
            # KDJ死叉 或 收盘价跌破MA -> 卖出
            if self.cross_over[0] < 0 or self.data.close[0] < self.ma[0]:
                self.sell()

# 回测框架示例
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(KDJMAStrategy)

    # 示例：加载数据（以csv为例，需用你自己的数据文件）
    data = bt.feeds.GenericCSVData(
        dataname='yourdata.csv',   # 替换为你的数据文件
        dtformat=('%Y-%m-%d'),
        timeframe=bt.TimeFrame.Days,
        compression=1,
        datetime=0,
        open=1, high=2, low=3, close=4, volume=5, openinterest=-1,
        headers=True
    )
    cerebro.adddata(data)

    cerebro.broker.set_cash(100000)
    print('初始资金: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('最终资金: %.2f' % cerebro.broker.getvalue())
    cerebro.plot()