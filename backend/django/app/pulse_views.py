from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from pulse_kernel import PulseKernel
import json

# Initialize kernel (singleton pattern recommended)
_pulse_kernel = None

def get_pulse_kernel():
    global _pulse_kernel
    if _pulse_kernel is None:
        _pulse_kernel = PulseKernel("pulse_config.yaml")
    return _pulse_kernel

@api_view(['GET'])
def health_check(request):
    """Pulse system health check"""
    kernel = get_pulse_kernel()
    report = kernel.get_session_report()
    return Response({
        'status': 'healthy',
        'version': '11.5.1',
        'behavioral_health': report['behavioral_health'],
        'active_signals': len(report['active_signals'])
    })

@api_view(['POST'])
def get_confluence_score(request):
    """Calculate confluence score for market data"""
    data = request.data
    kernel = get_pulse_kernel()
    result = kernel.confluence_scorer.score(data)
    return Response(result)

@api_view(['GET'])
def get_risk_status(request):
    """Get current risk enforcement status"""
    kernel = get_pulse_kernel()
    behavioral_report = kernel.risk_enforcer.get_behavioral_report()
    return Response(behavioral_report)

@api_view(['GET'])
def get_active_signals(request):
    """Get all active trading signals"""
    kernel = get_pulse_kernel()
    return Response(kernel.active_signals)

@api_view(['POST'])
def process_tick(request):
    """Process incoming tick through Pulse pipeline"""
    tick_data = request.data
    kernel = get_pulse_kernel()
    signal = kernel.process_frame(tick_data)
    if signal:
        return Response({
            'signal_generated': True,
            'symbol': signal.get('symbol'),
            'confluence_score': signal.get('confluence_score'),
            'entry_price': signal.get('entry_price'),
            'reasoning': signal.get('reasoning')
        })
    return Response({'signal_generated': False})
