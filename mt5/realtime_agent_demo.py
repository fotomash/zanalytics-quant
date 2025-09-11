"""
Real-time Market Processing Demo
Bootstrap OS v4.3.4 - Live Agent Coordination
"""

import asyncio
import random
from datetime import datetime, timedelta
from multi_agent_memory_integration import MultiAgentOrchestrator

class MarketDataSimulator:
    """Simulate real-time market data"""

    def __init__(self):
        self.base_price = 3320.0
        self.current_price = self.base_price
        self.tick_count = 0

    def generate_tick(self):
        """Generate realistic market tick"""
        # Random walk with occasional spikes
        change = random.gauss(0, 0.1)

        # Occasional large moves (market events)
        if random.random() < 0.05:  # 5% chance
            change *= random.choice([3, -3, 5, -5])

        self.current_price += change
        self.tick_count += 1

        # Calculate spread (wider during volatility)
        volatility = abs(change)
        spread = 0.2 + (volatility * 2)

        return {
            'timestamp': datetime.now(),
            'pair': 'XAUUSD',
            'bid': self.current_price - spread/2,
            'ask': self.current_price + spread/2,
            'last': self.current_price,
            'volume': random.randint(1, 10),
            'change': change,
            'spread': spread
        }

class RealTimeProcessor:
    """Process real-time market data through agent system"""

    def __init__(self):
        self.orchestrator = MultiAgentOrchestrator()
        self.market_sim = MarketDataSimulator()
        self.event_buffer = []
        self.stats = {
            'ticks_processed': 0,
            'events_generated': 0,
            'avg_processing_time': 0
        }

    async def start_processing(self, duration_seconds=30):
        """Start real-time processing simulation"""
        print(f"Starting real-time processing for {duration_seconds} seconds...")
        print("Monitoring for market events...")

        start_time = datetime.now()

        while (datetime.now() - start_time).seconds < duration_seconds:
            # Generate market tick
            tick = self.market_sim.generate_tick()

            # Check for events
            event = self._detect_event(tick)

            if event:
                # Process through agent system
                processing_start = datetime.now()
                result = await self.orchestrator.process_market_event(event)
                processing_time = (datetime.now() - processing_start).total_seconds() * 1000

                # Update stats
                self.stats['events_generated'] += 1
                self.stats['avg_processing_time'] = (
                    (self.stats['avg_processing_time'] * (self.stats['events_generated'] - 1) + processing_time)
                    / self.stats['events_generated']
                )

                # Log event
                print(f"\n🚨 Event: {event['type']} (severity: {event.get('severity', 'N/A')})")
                print(f"   Processing: {processing_time:.1f}ms")
                print(f"   Agents: {list(result['agent_responses'].keys())}")
                print(f"   Token efficiency: {result['orchestration_summary']['token_efficiency']}")

            self.stats['ticks_processed'] += 1

            # Sleep to simulate real-time (10 ticks per second)
            await asyncio.sleep(0.1)

        # Final stats
        print(f"\n📊 Processing Complete:")
        print(f"   Ticks processed: {self.stats['ticks_processed']}")
        print(f"   Events detected: {self.stats['events_generated']}")
        print(f"   Avg processing time: {self.stats['avg_processing_time']:.1f}ms")
        print(f"   Event rate: {self.stats['events_generated']/duration_seconds:.2f} events/sec")

    def _detect_event(self, tick):
        """Detect market events from tick data"""
        # Spread manipulation
        if tick['spread'] > 1.0:
            return {
                'type': 'spread_manipulation',
                'pair': tick['pair'],
                'severity': min(10, int(tick['spread'] * 2)),
                'spread_change': tick['spread'] - 0.2,
                'timestamp': tick['timestamp'].isoformat()
            }

        # High volatility
        if abs(tick['change']) > 2.0:
            return {
                'type': 'volatility_spike',
                'pair': tick['pair'],
                'severity': min(10, int(abs(tick['change']))),
                'pairs': [tick['pair']],
                'timestamp': tick['timestamp'].isoformat()
            }

        # Volume anomaly
        if tick['volume'] > 8:
            return {
                'type': 'volume_anomaly',
                'pair': tick['pair'],
                'severity': 5,
                'volume_change': (tick['volume'] - 5) / 5,
                'timestamp': tick['timestamp'].isoformat()
            }

        return None

async def run_realtime_demo():
    """Run the real-time processing demo"""
    processor = RealTimeProcessor()
    await processor.start_processing(duration_seconds=15)

if __name__ == "__main__":
    print("Bootstrap OS v4.3.4 - Real-time Agent Demo")
    print("=" * 50)
    asyncio.run(run_realtime_demo())
