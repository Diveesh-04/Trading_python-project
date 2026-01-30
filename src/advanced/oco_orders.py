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
            
            # Place take-profit limit order
            try:
                tp_order = self.client.client.futures_create_order(
                    symbol=symbol,
                    side='SELL' if side_upper == 'BUY' else 'BUY',  # Opposite side for TP
                    type='LIMIT',
                    timeInForce='GTC',
                    quantity=qty_rounded,
                    price=tp_price_rounded
                )
                logger.info(f"Take-profit limit order placed: {tp_order['orderId']}")
            except Exception as tp_err:
                logger.error(f"Failed to place take-profit order: {tp_err}")
                return {"success": False, "error": f"TP Order failed: {tp_err}"}
            
            # Place stop-loss order
            try:
                sl_order = self.client.client.futures_create_order(
                    symbol=symbol,
                    side='SELL' if side_upper == 'BUY' else 'BUY',  # Opposite side for SL
                    type='STOP_MARKET',
                    quantity=qty_rounded,
                    stopPrice=sl_price_rounded
                )
                logger.info(f"Stop-loss order placed: {sl_order['orderId']}")
                
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
            except Exception as sl_err:
                error_str = str(sl_err)
                if 'code=-4120' in error_str or 'not supported' in error_str.lower():
                    logger.warning(f"Native stop-loss not supported. Switching to SIMULATED OCO mode for the stop-loss leg.")
                    return self._execute_simulated_oco(
                        symbol, side_upper, qty_rounded, tp_order, sl_price_rounded
                    )
                
                # If SL fails for other reasons, we should probably cancel the TP order
                logger.error(f"Stop-loss failed: {sl_err}. Cancelling TP order for safety.")
                try:
                    self.client.client.futures_cancel_order(symbol=symbol, orderId=tp_order['orderId'])
                except:
                    pass
                return {"success": False, "error": f"SL Order failed: {sl_err}"}
        except Exception as e:
            logger.error(f"OCO execution failed: {e}")
            return {"success": False, "error": str(e)}

    def _execute_simulated_oco(self, symbol, side, quantity, tp_order, sl_price):
        """
        Monitor price to simulate an OCO (cancel TP if SL hit, or vice versa)
        """
        import time
        tp_id = tp_order['orderId']
        logger.info(f"Monitoring OCO for {symbol}: TP Order {tp_id}, SL trigger ${sl_price}")
        
        try:
            while True:
                # 1. Check if TP order was filled
                try:
                    current_tp = self.client.client.futures_get_order(symbol=symbol, orderId=tp_id)
                    if current_tp['status'] == 'FILLED':
                        logger.info(f"OCO SUCCESS: Take-profit order {tp_id} filled. OCO complete.")
                        return {
                            "success": True,
                            "mode": "simulated_oco",
                            "status": "TP_FILLED",
                            "tp_order_id": tp_id
                        }
                    if current_tp['status'] in ['CANCELED', 'EXPIRED', 'REJECTED']:
                        logger.warning(f"Take-profit order {tp_id} was {current_tp['status']}. Stopping OCO.")
                        return {"success": False, "error": f"TP Order {current_tp['status']}"}
                except Exception as e:
                    logger.warning(f"Could not check TP order status: {e}")
                
                # 2. Check if SL price hit
                current_price = Decimal(str(self.client.get_price(symbol)))
                
                sl_triggered = False
                if side == 'BUY':
                    if current_price <= sl_price:
                        sl_triggered = True
                else: # SELL
                    if current_price >= sl_price:
                        sl_triggered = True
                
                if sl_triggered:
                    logger.info(f"SL TRIGGERED: Price reached ${current_price}. Cancelling TP order {tp_id} and placing market SL...")
                    
                    # Cancel TP
                    try:
                        self.client.client.futures_cancel_order(symbol=symbol, orderId=tp_id)
                    except Exception as e:
                        logger.error(f"Failed to cancel TP order during SL trigger: {e}")
                    
                    # Place market SL
                    order = self.client.client.futures_create_order(
                        symbol=symbol,
                        side='SELL' if side == 'BUY' else 'BUY',
                        type='MARKET',
                        quantity=quantity
                    )
                    
                    logger.info(f"OCO SL Executed: Market order {order['orderId']} placed.")
                    return {
                        "success": True,
                        "mode": "simulated_oco",
                        "status": "SL_TRIGGERED",
                        "sl_order_id": order['orderId']
                    }
                
                time.sleep(5)
                
        except KeyboardInterrupt:
            logger.warning("Simulated OCO cancelled by user. TP order is still live!")
            return {"success": False, "error": "Cancelled by user"}
        except Exception as e:
            logger.error(f"Simulated OCO error: {e}")
            return {"success": False, "error": f"Simulation failed: {e}"}
