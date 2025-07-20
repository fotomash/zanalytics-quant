from celery import Celery, Task
from celery.schedules import crontab
import redis
import json
import logging
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)

app = Celery('zanalytics_tasks')
app.config_from_object('django.conf:settings', namespace='CELERY')

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
redis_stream = redis.Redis(host='localhost', port=6379, db=0)

class CallbackTask(Task):
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f'Task {self.name} succeeded with id {task_id}')

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f'Task {self.name} failed with id {task_id}: {exc}')

@app.task(base=CallbackTask, name='process_market_data')
def process_market_data():
    try:
        streams = {
            'tick_stream:EURUSD': '>',
            'tick_stream:GBPUSD': '>',
            'tick_stream:USDJPY': '>'
        }
        messages = redis_stream.xread(streams, count=100, block=1000)
        processed_count = 0
        for stream_name, stream_messages in messages:
            symbol = stream_name.decode().split(':')[1]
            for message_id, data in stream_messages:
                tick_data = {k.decode(): v.decode() for k, v in data.items()}
                spread = float(tick_data['ask']) - float(tick_data['bid'])
                processed_key = f"processed:{symbol}:{datetime.now().strftime('%Y%m%d')}"
                redis_client.hset(processed_key, message_id.decode(), json.dumps({
                    **tick_data,
                    'spread': spread,
                    'processed_at': datetime.now().isoformat()
                }))
                processed_count += 1
        logger.info(f"Processed {processed_count} market data entries")
        return processed_count
    except Exception as e:
        logger.error(f"Error processing market data: {e}")
        raise

@app.task(base=CallbackTask, name='calculate_aggregates')
def calculate_aggregates(timeframe: str = '5m'):
    try:
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
        for symbol in symbols:
            stream_key = f"tick_stream:{symbol}"
            if timeframe == '1m':
                count = 600
            elif timeframe == '5m':
                count = 3000
            else:
                count = 6000
            messages = redis_stream.xrevrange(stream_key, count=count)
            if not messages:
                continue
            ticks = []
            for msg_id, data in messages:
                tick = {k.decode(): v.decode() for k, v in data.items()}
                ticks.append({
                    'time': float(tick['time']),
                    'bid': float(tick['bid']),
                    'ask': float(tick['ask']),
                    'volume': float(tick['volume'])
                })
            df = pd.DataFrame(ticks)
            ohlc = {
                'open': df['bid'].iloc[-1],
                'high': df['bid'].max(),
                'low': df['bid'].min(),
                'close': df['bid'].iloc[0],
                'volume': df['volume'].sum(),
                'avg_spread': (df['ask'] - df['bid']).mean(),
                'tick_count': len(df),
                'timestamp': datetime.now().isoformat()
            }
            agg_key = f"aggregate:{symbol}:{timeframe}"
            redis_client.hset(agg_key, datetime.now().strftime('%Y%m%d%H%M'), json.dumps(ohlc))
            redis_client.expire(agg_key, 86400)
            logger.info(f"Calculated {timeframe} aggregate for {symbol}")
        return f"Aggregates calculated for {len(symbols)} symbols"
    except Exception as e:
        logger.error(f"Error calculating aggregates: {e}")
        raise

@app.task(base=CallbackTask, name='monitor_positions')
def monitor_positions():
    try:
        positions_data = redis_client.get('open_positions')
        if not positions_data:
            return "No positions to monitor"
        positions = json.loads(positions_data)
        alerts = []
        for pos in positions:
            profit_pct = (pos['profit'] / (pos['volume'] * pos['price_open'])) * 100
            if profit_pct < -2:
                alert = {
                    'type': 'stop_loss_warning',
                    'ticket': pos['ticket'],
                    'symbol': pos['symbol'],
                    'profit_pct': profit_pct,
                    'message': f"Position {pos['ticket']} on {pos['symbol']} is down {profit_pct:.2f}%"
                }
                alerts.append(alert)
                redis_stream.xadd('alerts_stream', alert, maxlen=1000)
            elif profit_pct > 5:
                alert = {
                    'type': 'take_profit_suggestion',
                    'ticket': pos['ticket'],
                    'symbol': pos['symbol'],
                    'profit_pct': profit_pct,
                    'message': f"Position {pos['ticket']} on {pos['symbol']} is up {profit_pct:.2f}%"
                }
                alerts.append(alert)
                redis_stream.xadd('alerts_stream', alert, maxlen=1000)
        logger.info(f"Generated {len(alerts)} position alerts")
        return f"Monitored {len(positions)} positions, {len(alerts)} alerts generated"
    except Exception as e:
        logger.error(f"Error monitoring positions: {e}")
        raise

@app.task(base=CallbackTask, name='cleanup_old_data')
def cleanup_old_data(days_to_keep: int = 7):
    try:
        cleanup_count = 0
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        for key in redis_client.scan_iter("processed:*"):
            date_str = key.split(':')[-1]
            try:
                key_date = datetime.strptime(date_str, '%Y%m%d')
                if key_date < cutoff_date:
                    redis_client.delete(key)
                    cleanup_count += 1
            except Exception:
                continue
        streams = ['tick_stream:*', 'indicator_stream:*', 'position_stream', 'alerts_stream']
        for pattern in streams:
            for key in redis_client.scan_iter(pattern):
                redis_stream.xtrim(key, maxlen=100000, approximate=True)
        logger.info(f"Cleaned up {cleanup_count} old keys")
        return f"Cleanup completed: {cleanup_count} keys removed"
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise

@app.task(base=CallbackTask, name='generate_daily_report')
def generate_daily_report():
    try:
        report_date = datetime.now().strftime('%Y-%m-%d')
        report = {'date': report_date, 'generated_at': datetime.now().isoformat()}
        account_data = redis_client.get('account_info')
        if account_data:
            report['account'] = json.loads(account_data)
        positions_data = redis_client.get('open_positions')
        if positions_data:
            positions = json.loads(positions_data)
            report['positions_summary'] = {
                'total_positions': len(positions),
                'total_profit': sum(p['profit'] for p in positions),
                'symbols': list({p['symbol'] for p in positions})
            }
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
        symbol_stats = {}
        for symbol in symbols:
            agg_key = f"aggregate:{symbol}:5m"
            today_aggregates = []
            for field in redis_client.hkeys(agg_key):
                if field.startswith(datetime.now().strftime('%Y%m%d')):
                    data = json.loads(redis_client.hget(agg_key, field))
                    today_aggregates.append(data)
            if today_aggregates:
                df = pd.DataFrame(today_aggregates)
                symbol_stats[symbol] = {
                    'total_volume': df['volume'].sum(),
                    'avg_spread': df['avg_spread'].mean(),
                    'high': df['high'].max(),
                    'low': df['low'].min(),
                    'tick_count': df['tick_count'].sum()
                }
        report['symbol_statistics'] = symbol_stats
        alerts_count = {'stop_loss_warning': 0, 'take_profit_suggestion': 0}
        alert_messages = redis_stream.xrange('alerts_stream', min=f"{int(datetime.now().timestamp() * 1000)}-0", max='+')
        for _, alert_data in alert_messages:
            alert = {k.decode(): v.decode() for k, v in alert_data.items()}
            if alert['type'] in alerts_count:
                alerts_count[alert['type']] += 1
        report['alerts_summary'] = alerts_count
        report_key = f"daily_report:{report_date}"
        redis_client.setex(report_key, 86400 * 30, json.dumps(report))
        logger.info(f"Generated daily report for {report_date}")
        return report
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        raise

app.conf.beat_schedule = {
    'process-market-data': {
        'task': 'process_market_data',
        'schedule': 10.0,
    },
    'calculate-1m-aggregates': {
        'task': 'calculate_aggregates',
        'schedule': 60.0,
        'args': ('1m',)
    },
    'calculate-5m-aggregates': {
        'task': 'calculate_aggregates',
        'schedule': 300.0,
        'args': ('5m',)
    },
    'monitor-positions': {
        'task': 'monitor_positions',
        'schedule': 30.0,
    },
    'cleanup-old-data': {
        'task': 'cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),
        'args': (7,)
    },
    'generate-daily-report': {
        'task': 'generate_daily_report',
        'schedule': crontab(hour=23, minute=55),
    }
}

app.conf.task_routes = {
    'process_market_data': {'queue': 'high_priority'},
    'monitor_positions': {'queue': 'high_priority'},
    'calculate_aggregates': {'queue': 'medium_priority'},
    'cleanup_old_data': {'queue': 'low_priority'},
    'generate_daily_report': {'queue': 'low_priority'}
}

app.conf.task_time_limit = 300
app.conf.task_soft_time_limit = 240
app.conf.result_expires = 3600
