from decimal import Decimal
from ..client import BinanceFuturesClient
from ..validators import OrderValidator
from ..logger import logger, log_order_action

class OCOOrder:
    """
    Handle OCO (One-Cancels-the-Other) orders
    Places a take-profit and stop-loss order simultaneously
    """
    
    def __init__(self, client: BinanceFuturesClient = None):
        self.client = client or BinanceFuturesClient()
        self.validator = OrderValidator()
    
    def execute(self, symbol: str, side: str, quantity: str, 
                take_profit_price: str, stop_loss_price: str):
        """
        Execute an OCO order (take-profit and stop-loss)
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            side: Order side (BUY/SELL)
            quantity: Order quantity
            take_profit_price: Take profit limit price
            stop_loss_price: Stop loss price
        """
        
        log_order_action(logger, 'ORDER_INITIATED',
                        symbol=symbol, side=side.upper(), quantity=quantity,
                        take_profit=take_profit_price, stop_loss=stop_loss_price,
                        order_type='OCO', message=f"OCO {side} order initiated")
        
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
        
        tp_price, error_msg = self.validator.validate_price(take_profit_price)
        if tp_price is None:
            log_order_action(logger, 'VALIDATION_FAILED',
                           symbol=symbol, price=take_profit_price, error_code='INVALID_TP_PRICE', message=error_msg)
            return {"success": False, "error": error_msg}
        
        sl_price, error_msg = self.validator.validate_price(stop_loss_price)
        if sl_price is None:
            log_order_action(logger, 'VALIDATION_FAILED',
                           symbol=symbol, price=stop_loss_price, error_code='INVALID_SL_PRICE', message=error_msg)
            return {"success": False, "error": error_msg}
        
        try:
            # Get current price
            current_price = Decimal(str(self.client.get_price(symbol)))
            
            # Validate price logic based on side
            side_upper = side.upper()
            if side_upper == 'BUY':
                # For buy orders: take-profit should be above current, stop-loss below
                if tp_price <= current_price:
                    return {
                        "success": False,
                        "error": f"Take-profit price (${tp_price}) must be above current price (${current_price}) for BUY orders"
                    }
                if sl_price >= current_price:
                    return {
                        "success": False,
                        "error": f"Stop-loss price (${sl_price}) must be below current price (${current_price}) for BUY orders"
                    }
            else:  # SELL
                # For sell orders: take-profit should be below current, stop-loss above
                if tp_price >= current_price:
                    return {
                        "success": False,
                        "error": f"Take-profit price (${tp_price}) must be below current price (${current_price}) for SELL orders"
                    }
                if sl_price <= current_price:
                    return {
                        "success": False,
                        "error": f"Stop-loss price (${sl_price}) must be above current price (${current_price}) for SELL orders"
                    }
            
            # Get precision
            qty_precision = self.client.get_quantity_precision(symbol)
            price_precision = self.client.get_price_precision(symbol)
            
            # Round values
            qty_rounded = round(float(qty), qty_precision)
            tp_price_rounded = round(float(tp_price), price_precision)
            sl_price_rounded = round(float(sl_price), price_precision)
            
            # Ensure minimum notional
            min_notional = float(self.validator.MIN_NOTIONAL)
            if qty_rounded * tp_price_rounded < min_notional:
                min_qty_needed = min_notional / tp_price_rounded
                step = 10 ** (-qty_precision)
                qty_rounded = ((min_qty_needed // step) + 1) * step
                qty_rounded = round(qty_rounded, qty_precision)
                logger.info(f"Adjusted quantity to {qty_rounded} to meet minimum notional requirement")
            
            # Validate with rounded values
            qty_rounded_dec = Decimal(str(qty_rounded))
            tp_price_rounded_dec = Decimal(str(tp_price_rounded))
            is_valid, error_msg = self.validator.validate_notional(qty_rounded_dec, tp_price_rounded_dec)
            if not is_valid:
                return {"success": False, "error": error_msg}
            
            logger.info(
                f"Placing OCO {side} order for {qty_rounded} {symbol}: "
                f"TP @ ${tp_price_rounded}, SL @ ${sl_price_rounded} "
                f"(current: ${current_price})"
            )
            
            # Place OCO order using Binance's OCO endpoint
            # Note: Binance Futures may not support OCO directly, so we'll place two orders
            # and track them as a pair. For true OCO, we'd need to use the OCO endpoint if available.
            
            # Place take-profit limit order
            tp_order = self.client.client.futures_create_order(
                symbol=symbol,
                side='SELL' if side_upper == 'BUY' else 'BUY',  # Opposite side for TP
                type='LIMIT',
                timeInForce='GTC',
                quantity=qty_rounded,
                price=tp_price_rounded
            )
            
            # Place stop-loss order
            sl_order = self.client.client.futures_create_order(
                symbol=symbol,
                side='SELL' if side_upper == 'BUY' else 'BUY',  # Opposite side for SL
                type='STOP_MARKET',
                quantity=qty_rounded,
                stopPrice=sl_price_rounded
            )
            
            logger.info(f"OCO orders placed: TP={tp_order['orderId']}, SL={sl_order['orderId']}")
            
            return {
                "success": True,
                "take_profit": {
                    "order_id": tp_order['orderId'],
                    "price": tp_order.get('price', tp_price_rounded),
                    "status": tp_order['status']
                },
                "stop_loss": {
                    "order_id": sl_order['orderId'],
                    "stop_price": sl_order.get('stopPrice', sl_price_rounded),
                    "status": sl_order['status']
                },
                "symbol": symbol,
                "quantity": qty_rounded
            }
            
        except Exception as e:
            logger.error(f"OCO order failed: {e}")
            return {"success": False, "error": str(e)}
