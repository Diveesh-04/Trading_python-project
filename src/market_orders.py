from decimal import Decimal
from .client import BinanceFuturesClient
from .validators import OrderValidator
from .logger import logger, log_order_action

class MarketOrder:
    """Handle market orders"""
    
    def __init__(self, client: BinanceFuturesClient = None):
        self.client = client or BinanceFuturesClient()
        self.validator = OrderValidator()
    
    def execute(self, symbol: str, side: str, quantity: str):
        """Execute a market order"""
        
        log_order_action(logger, 'ORDER_INITIATED', 
                        symbol=symbol, side=side.upper(), quantity=quantity,
                        order_type='MARKET', message=f"Market {side} order initiated")
        
        # Validate inputs
        is_valid, error_msg = self.validator.validate_symbol(symbol)
        if not is_valid:
            log_order_action(logger, 'VALIDATION_FAILED', 
                           symbol=symbol, error_code='INVALID_SYMBOL', message=error_msg)
            return {"success": False, "error": error_msg}
        
        is_valid, error_msg = self.validator.validate_side(side)
        if not is_valid:
            log_order_action(logger, 'VALIDATION_FAILED', 
                           symbol=symbol, side=side, error_code='INVALID_SIDE', message=error_msg)
            return {"success": False, "error": error_msg}
        
        qty, error_msg = self.validator.validate_quantity(quantity)
        if qty is None:
            log_order_action(logger, 'VALIDATION_FAILED', 
                           symbol=symbol, quantity=quantity, error_code='INVALID_QUANTITY', message=error_msg)
            return {"success": False, "error": error_msg}
        
        try:
            # Get current price
            current_price = Decimal(str(self.client.get_price(symbol)))
            current_price_float = float(current_price)
            
            # Get and apply quantity precision first
            qty_precision = self.client.get_quantity_precision(symbol)
            qty_rounded = round(float(qty), qty_precision)
            
            # If rounded quantity doesn't meet minimum notional, round up to next step
            min_notional = float(self.validator.MIN_NOTIONAL)
            if qty_rounded * current_price_float < min_notional:
                # Calculate minimum quantity needed
                min_qty_needed = min_notional / current_price_float
                # Round up to next valid step
                step = 10 ** (-qty_precision)
                qty_rounded = ((min_qty_needed // step) + 1) * step
                qty_rounded = round(qty_rounded, qty_precision)
                logger.info(f"Adjusted quantity to {qty_rounded} to meet minimum notional requirement")
            
            # Validate minimum notional value ($100) with rounded quantity
            qty_rounded_dec = Decimal(str(qty_rounded))
            is_valid, error_msg = self.validator.validate_notional(qty_rounded_dec, current_price)
            if not is_valid:
                logger.error(f"Order validation failed: {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Execute market order
            log_order_action(logger, 'ORDER_PLACING',
                           symbol=symbol, side=side.upper(), quantity=qty_rounded,
                           estimated_value=f"${qty_rounded * current_price_float:.2f}",
                           message=f"Placing MARKET {side} order")
            
            order = self.client.client.futures_create_order(
                symbol=symbol,
                side='BUY' if side.upper() == 'BUY' else 'SELL',
                type='MARKET',
                quantity=qty_rounded
            )
            
            log_order_action(logger, 'ORDER_PLACED',
                           order_id=str(order['orderId']), symbol=symbol, side=order['side'],
                           quantity=order['origQty'], price=order.get('avgPrice', '0'),
                           status=order['status'], message="Market order placed successfully")
            
            return {
                "success": True,
                "order_id": order['orderId'],
                "symbol": order['symbol'],
                "side": order['side'],
                "quantity": order['origQty'],
                "price": order['avgPrice'],
                "status": order['status']
            }
            
        except Exception as e:
            error_str = str(e)
            log_order_action(logger, 'ORDER_FAILED',
                           symbol=symbol, side=side.upper(), error_code='EXECUTION_ERROR',
                           message=f"Market order failed: {error_str}")
            return {"success": False, "error": error_str}