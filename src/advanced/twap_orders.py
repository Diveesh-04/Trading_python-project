import time
from decimal import Decimal
from datetime import datetime, timedelta
from ..client import BinanceFuturesClient
from ..validators import OrderValidator
from ..logger import logger

class TWAPOrder:
    """
    Handle TWAP (Time-Weighted Average Price) orders
    Splits large orders into smaller chunks over time
    """
    
    def __init__(self, client: BinanceFuturesClient = None):
        self.client = client or BinanceFuturesClient()
        self.validator = OrderValidator()
    
    def execute(self, symbol: str, side: str, total_quantity: str, 
                duration_minutes: int, num_slices: int = None):
        """
        Execute a TWAP order
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            side: Order side (BUY/SELL)
            total_quantity: Total quantity to execute
            duration_minutes: Duration over which to spread the order
            num_slices: Number of slices (defaults to duration_minutes if not specified)
        """
        
        # Validate inputs
        is_valid, error_msg = self.validator.validate_symbol(symbol)
        if not is_valid:
            return {"success": False, "error": error_msg}
        
        is_valid, error_msg = self.validator.validate_side(side)
        if not is_valid:
            return {"success": False, "error": error_msg}
        
        total_qty, error_msg = self.validator.validate_quantity(total_quantity)
        if total_qty is None:
            return {"success": False, "error": error_msg}
        
        if duration_minutes <= 0:
            return {"success": False, "error": "Duration must be positive"}
        
        if num_slices is None:
            num_slices = min(duration_minutes, 60)  # Default to 1 slice per minute, max 60
        
        if num_slices <= 0:
            return {"success": False, "error": "Number of slices must be positive"}
        
        try:
            # Get precision
            qty_precision = self.client.get_quantity_precision(symbol)
            
            # Calculate slice quantity
            slice_qty = float(total_qty) / num_slices
            slice_qty = round(slice_qty, qty_precision)
            
            # Ensure each slice meets minimum notional
            current_price = Decimal(str(self.client.get_price(symbol)))
            current_price_float = float(current_price)
            min_notional = float(self.validator.MIN_NOTIONAL)
            min_slice_qty = min_notional / current_price_float
            
            if slice_qty < min_slice_qty:
                # 1. First try reducing number of slices to increase quantity per slice
                num_slices = int(float(total_qty) / min_slice_qty)
                if num_slices == 0:
                    num_slices = 1
                
                # Recalculate slice quantity with new number of slices
                slice_qty = float(total_qty) / num_slices
                slice_qty = round(slice_qty, qty_precision)
                
                # 2. If it's still below minimum (due to rounding or total quantity being too small),
                # we must round UP to the next valid step size to ensure it passes the $100 check.
                if slice_qty < min_slice_qty:
                    step = 10 ** (-qty_precision)
                    slice_qty = ((min_slice_qty // step) + 1) * step
                    slice_qty = round(slice_qty, qty_precision)
                    
                    # Recalculate num_slices based on the new larger slice_qty
                    num_slices = int(float(total_qty) / slice_qty)
                    if num_slices == 0:
                        num_slices = 1
                
                logger.info(f"Adjusted to {num_slices} slices of {slice_qty} {symbol} to meet minimum notional per slice")
            
            # Calculate interval between slices
            interval_seconds = (duration_minutes * 60) / num_slices
            
            logger.info(
                f"Executing TWAP {side} order: {total_qty} {symbol} over {duration_minutes} minutes "
                f"({num_slices} slices, {slice_qty} per slice, {interval_seconds:.1f}s interval)"
            )
            
            orders = []
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            for i in range(num_slices):
                # Calculate remaining time and adjust if needed
                current_time = datetime.now()
                if current_time >= end_time:
                    # Execute remaining quantity as one order
                    remaining_qty = float(total_qty) - sum(o.get('quantity', 0) for o in orders)
                    if remaining_qty > 0:
                        remaining_qty = round(remaining_qty, qty_precision)
                        logger.info(f"Executing final slice: {remaining_qty} {symbol}")
                        order = self.client.client.futures_create_order(
                            symbol=symbol,
                            side='BUY' if side.upper() == 'BUY' else 'SELL',
                            type='MARKET',
                            quantity=remaining_qty
                        )
                        orders.append({
                            "order_id": order['orderId'],
                            "quantity": float(order['origQty']),
                            "price": float(order.get('avgPrice', 0)),
                            "status": order['status']
                        })
                    break
                
                # Wait until next slice time (except for first slice)
                if i > 0:
                    sleep_time = interval_seconds - (datetime.now() - current_time).total_seconds()
                    if sleep_time > 0:
                        logger.info(f"Waiting {sleep_time:.1f}s before next slice...")
                        time.sleep(sleep_time)
                
                # Execute slice
                logger.info(f"Executing slice {i+1}/{num_slices}: {slice_qty} {symbol}")
                order = self.client.client.futures_create_order(
                    symbol=symbol,
                    side='BUY' if side.upper() == 'BUY' else 'SELL',
                    type='MARKET',
                    quantity=slice_qty
                )
                
                orders.append({
                    "order_id": order['orderId'],
                    "quantity": float(order['origQty']),
                    "price": float(order.get('avgPrice', 0)),
                    "status": order['status']
                })
                
                logger.info(f"Slice {i+1} executed: Order {order['orderId']}")
            
            total_executed = sum(o['quantity'] for o in orders)
            avg_price = sum(o['price'] * o['quantity'] for o in orders if o['price'] > 0) / total_executed if total_executed > 0 else 0
            
            logger.info(
                f"TWAP order completed: {len(orders)} slices, "
                f"total: {total_executed}, avg price: ${avg_price:.2f}"
            )
            
            return {
                "success": True,
                "symbol": symbol,
                "side": side.upper(),
                "total_quantity": float(total_qty),
                "executed_quantity": total_executed,
                "average_price": avg_price,
                "num_slices": len(orders),
                "orders": orders
            }
            
        except KeyboardInterrupt:
            logger.warning("TWAP order interrupted by user")
            return {
                "success": False,
                "error": "Order interrupted",
                "partial_orders": orders if 'orders' in locals() else []
            }
        except Exception as e:
            logger.error(f"TWAP order failed: {e}")
            return {"success": False, "error": str(e)}
