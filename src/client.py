from binance.client import Client  # pyright: ignore[reportMissingImports]
from binance.exceptions import BinanceAPIException  # pyright: ignore[reportMissingImports]
from .config import settings
from .logger import logger

class BinanceFuturesClient:
    """Wrapper for Binance Futures API with error handling"""
    
    def __init__(self, testnet: bool = None):
        testnet = testnet if testnet is not None else settings.FUTURES_TESTNET
        
        # Validate API credentials
        if not settings.BINANCE_API_KEY or not settings.BINANCE_API_KEY.strip():
            raise ValueError("BINANCE_API_KEY is not set in .env file")
        if not settings.BINANCE_API_SECRET or not settings.BINANCE_API_SECRET.strip():
            raise ValueError("BINANCE_API_SECRET is not set in .env file")
        
        if testnet:
            self.base_url = 'https://testnet.binancefuture.com'
            logger.info("Connecting to Binance FUTURES TESTNET")
        else:
            self.base_url = 'https://fapi.binance.com'
            logger.info("Connecting to Binance FUTURES LIVE")
        
        self.client = Client(
            api_key=settings.BINANCE_API_KEY.strip(),
            api_secret=settings.BINANCE_API_SECRET.strip(),
            testnet=testnet
        )
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if symbol exists on Binance Futures"""
        try:
            exchange_info = self.client.futures_exchange_info()
            symbols = [s['symbol'] for s in exchange_info['symbols']]
            return symbol.upper() in symbols
        except BinanceAPIException as e:
            logger.error(f"Symbol validation failed: {e}")
            return False
    
    def get_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            raise
    
    def get_symbol_info(self, symbol: str) -> dict:
        """Get symbol information including precision filters"""
        try:
            exchange_info = self.client.futures_exchange_info()
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol.upper():
                    filters = {}
                    for f in s.get('filters', []):
                        filter_type = f.get('filterType')
                        if filter_type == 'LOT_SIZE':
                            filters['quantity'] = {
                                'minQty': float(f.get('minQty', 0)),
                                'maxQty': float(f.get('maxQty', 0)),
                                'stepSize': float(f.get('stepSize', 0))
                            }
                        elif filter_type == 'PRICE_FILTER':
                            filters['price'] = {
                                'minPrice': float(f.get('minPrice', 0)),
                                'maxPrice': float(f.get('maxPrice', 0)),
                                'tickSize': float(f.get('tickSize', 0))
                            }
                        elif filter_type == 'MIN_NOTIONAL':
                            filters['notional'] = {
                                'minNotional': float(f.get('notional', 0))
                            }
                    return {
                        'symbol': s['symbol'],
                        'status': s['status'],
                        'filters': filters
                    }
            raise ValueError(f"Symbol {symbol} not found")
        except BinanceAPIException as e:
            logger.error(f"Failed to get symbol info for {symbol}: {e}")
            raise
    
    def get_quantity_precision(self, symbol: str) -> int:
        """Get the number of decimal places allowed for quantity"""
        try:
            symbol_info = self.get_symbol_info(symbol)
            step_size = symbol_info['filters'].get('quantity', {}).get('stepSize', 0)
            if step_size == 0:
                return 8  # Default to 8 decimal places
            # Calculate precision from step size (e.g., 0.001 -> 3 decimals)
            step_str = f"{step_size:.10f}".rstrip('0')
            if '.' in step_str:
                return len(step_str.split('.')[1])
            return 0
        except Exception as e:
            logger.warning(f"Could not determine quantity precision for {symbol}, using default: {e}")
            return 8
    
    def get_price_precision(self, symbol: str) -> int:
        """Get the number of decimal places allowed for price"""
        try:
            symbol_info = self.get_symbol_info(symbol)
            tick_size = symbol_info['filters'].get('price', {}).get('tickSize', 0)
            if tick_size == 0:
                return 2  # Default to 2 decimal places
            # Calculate precision from tick size (e.g., 0.01 -> 2 decimals)
            tick_str = f"{tick_size:.10f}".rstrip('0')
            if '.' in tick_str:
                return len(tick_str.split('.')[1])
            return 0
        except Exception as e:
            logger.warning(f"Could not determine price precision for {symbol}, using default: {e}")
            return 2